"""
priority_scoring.py — Ranks service priorities from feedback themes and syncs live action items.

Calculates composite Priority Score based on:
  1. Volume (mentions of the theme).
  2. Negative Sentiment Ratio (percentage of mentions with negative sentiment).
  3. Support Ticket Weight (tickets/messages represent higher friction than self-serve reviews).

Formula:
  Priority Score = Total Mentions * (Negative Sentiment Ratio ^ 1.5) * Support Weight Factor
"""

from __future__ import annotations

import pandas as pd
from datetime import datetime
from sqlalchemy import text
from cfa.generators.transactions import _ACTION_TITLES


def compute_service_priorities(engine) -> pd.DataFrame:
    """
    Ranks feedback themes into service action priorities (Critical, High, Medium, Low).
    Returns DataFrame: [theme_id, theme_name, total_mentions, negative_mentions,
                        negative_ratio, priority_score, priority_rank, recommended_urgency]
    """
    query = """
        -- 1. Reviews mentions & sentiment
        WITH rev_data AS (
            SELECT
                rt.theme_id,
                COUNT(*) as total_cnt,
                SUM(CASE WHEN COALESCE(r.predicted_sentiment, r.sentiment_label) = 'negative' THEN 1 ELSE 0 END) as neg_cnt,
                0 as is_support
            FROM review_themes rt
            JOIN reviews r ON rt.review_id = r.review_id
            GROUP BY rt.theme_id
        ),
        -- 2. Survey response mentions & sentiment
        resp_data AS (
            SELECT
                st.theme_id,
                COUNT(*) as total_cnt,
                SUM(CASE WHEN COALESCE(s.predicted_sentiment, s.sentiment_label) = 'negative' THEN 1 ELSE 0 END) as neg_cnt,
                0 as is_support
            FROM response_themes st
            JOIN survey_responses s ON st.response_id = s.response_id
            GROUP BY st.theme_id
        ),
        -- 3. Support message mentions & sentiment
        msg_data AS (
            SELECT
                mt.theme_id,
                COUNT(*) as total_cnt,
                SUM(CASE WHEN COALESCE(m.predicted_sentiment, m.sentiment_label) = 'negative' THEN 1 ELSE 0 END) as neg_cnt,
                1 as is_support
            FROM message_themes mt
            JOIN support_messages m ON mt.message_id = m.message_id
            GROUP BY mt.theme_id
        )
        SELECT
            t.theme_id,
            t.name as theme_name,
            COALESCE(SUM(all_data.total_cnt), 0) as total_mentions,
            COALESCE(SUM(all_data.neg_cnt), 0) as negative_mentions,
            COALESCE(SUM(CASE WHEN all_data.is_support = 1 THEN all_data.total_cnt ELSE 0 END), 0) as support_mentions
        FROM themes t
        LEFT JOIN (
            SELECT * FROM rev_data
            UNION ALL
            SELECT * FROM resp_data
            UNION ALL
            SELECT * FROM msg_data
        ) all_data ON t.theme_id = all_data.theme_id
        GROUP BY t.theme_id, t.name;
    """

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)

    if df.empty:
        return pd.DataFrame()

    # Derived calculations
    df["negative_ratio"] = (df["negative_mentions"] / df["total_mentions"].replace(0, 1)).round(4)

    # Support friction factor: themes appearing frequently in support tickets get a bump (1.0 to 1.5)
    df["support_factor"] = (1.0 + (df["support_mentions"] / df["total_mentions"].replace(0, 1)) * 0.5).round(3)

    # Composite Priority Score: mentions * (negative_ratio ^ 1.5) * support_factor
    df["priority_score"] = (
        df["total_mentions"] * (df["negative_ratio"] ** 1.5) * df["support_factor"]
    ).round(2)

    df = df.sort_values(by="priority_score", ascending=False).reset_index(drop=True)
    df["priority_rank"] = df.index + 1

    # Classify into Urgency Buckets
    def assign_urgency(rank: int, total: int) -> str:
        if rank <= max(2, int(total * 0.2)):
            return "Critical"
        if rank <= max(4, int(total * 0.5)):
            return "High"
        if rank <= max(6, int(total * 0.8)):
            return "Medium"
        return "Low"

    n_themes = len(df)
    df["recommended_urgency"] = [assign_urgency(r, n_themes) for r in df["priority_rank"]]

    cols = [
        "priority_rank", "theme_id", "theme_name", "total_mentions",
        "negative_mentions", "negative_ratio", "priority_score", "recommended_urgency"
    ]
    return df[cols]


def sync_live_action_items_from_priorities(
    engine,
    priorities_df: pd.DataFrame,
    threshold: int = 50
) -> pd.DataFrame:
    """
    Derive live ActionItem records from analyzed service priorities.
    Updates the action_items table in SQLite and logs state change history.
    """
    if priorities_df.empty:
        return pd.DataFrame()

    today_str = datetime.now().strftime("%Y-%m-%d")
    now_iso = datetime.now().isoformat()
    action_records = []
    history_records = []

    counter = 1
    for _, row in priorities_df.iterrows():
        mentions = int(row["total_mentions"])
        if mentions < threshold:
            continue

        urgency = row["recommended_urgency"]
        prio_map = {"Critical": "high", "High": "high", "Medium": "medium", "Low": "low"}
        action_priority = prio_map.get(urgency, "medium")

        act_id = f"ACT-2026-{counter:06d}"
        title = _ACTION_TITLES.get(row["theme_id"], f"Address priority issues for {row['theme_name']}")

        action_records.append({
            "action_id": act_id,
            "theme_id": row["theme_id"],
            "title": title,
            "priority": action_priority,
            "status": "open",
            "created_at": today_str,
            "mention_count": mentions,
        })

        history_records.append({
            "history_id": f"HIST-ACT-{act_id}-01",
            "entity_type": "action_item",
            "entity_id": act_id,
            "old_status": None,
            "new_status": "open",
            "changed_at": now_iso,
            "changed_by": "analytics_engine",
        })
        counter += 1

    actions_df = pd.DataFrame(action_records)
    if not actions_df.empty:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM action_items"))
            for rec in action_records:
                conn.execute(
                    text("""
                        INSERT INTO action_items (action_id, theme_id, title, priority, status, created_at, mention_count)
                        VALUES (:action_id, :theme_id, :title, :priority, :status, :created_at, :mention_count)
                    """),
                    rec
                )
            for h in history_records:
                conn.execute(
                    text("""
                        INSERT INTO status_history (history_id, entity_type, entity_id, old_status, new_status, changed_at, changed_by)
                        VALUES (:history_id, :entity_type, :entity_id, :old_status, :new_status, :changed_at, :changed_by)
                        ON CONFLICT(history_id) DO UPDATE SET
                            new_status=excluded.new_status,
                            changed_at=excluded.changed_at,
                            changed_by=excluded.changed_by
                    """),
                    h
                )

    return actions_df
