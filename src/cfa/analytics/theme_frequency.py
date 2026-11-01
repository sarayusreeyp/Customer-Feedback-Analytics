"""
theme_frequency.py — Compute recurring theme frequency and volume distribution.

Aggregates:
  - Total mentions per theme across bridge tables and predicted themes.
  - Percentage share of all feedback.
  - Breakdown by source (reviews, survey responses, support messages).
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text


def compute_theme_frequencies(engine) -> pd.DataFrame:
    """
    Computes total occurrences and percentage share of every taxonomy theme.
    Returns DataFrame: [theme_id, theme_name, review_count, response_count, message_count, total_count, percentage_share]
    """
    query = """
        WITH rev_counts AS (
            SELECT theme_id, COUNT(*) as cnt
            FROM review_themes
            GROUP BY theme_id
        ),
        resp_counts AS (
            SELECT theme_id, COUNT(*) as cnt
            FROM response_themes
            GROUP BY theme_id
        ),
        msg_counts AS (
            SELECT theme_id, COUNT(*) as cnt
            FROM message_themes
            GROUP BY theme_id
        )
        SELECT
            t.theme_id,
            t.name as theme_name,
            COALESCE(r.cnt, 0) as review_count,
            COALESCE(s.cnt, 0) as response_count,
            COALESCE(m.cnt, 0) as message_count,
            (COALESCE(r.cnt, 0) + COALESCE(s.cnt, 0) + COALESCE(m.cnt, 0)) as total_count
        FROM themes t
        LEFT JOIN rev_counts r ON t.theme_id = r.theme_id
        LEFT JOIN resp_counts s ON t.theme_id = s.theme_id
        LEFT JOIN msg_counts m ON t.theme_id = m.theme_id
        ORDER BY total_count DESC;
    """

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)

    total_mentions = df["total_count"].sum()
    if total_mentions > 0:
        df["percentage_share"] = ((df["total_count"] / total_mentions) * 100).round(2)
    else:
        df["percentage_share"] = 0.0

    return df
