"""
trend_analysis.py — Analyze sentiment shifts over time and across dimensions.

Computes:
  - Weekly and monthly sentiment breakdown (positive, neutral, negative counts & net sentiment score).
  - Net Sentiment Score (NSS) = (% Positive - % Negative) * 100.
  - Inflection points where net sentiment shifts significantly between consecutive periods.
  - Product and channel dimension filtering for targeted operational analysis.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text


def compute_sentiment_trends(
    engine,
    freq: str = "W",
    product_id: str | None = None,
    channel_id: str | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Aggregate sentiment over time across reviews, survey responses, and support messages,
    while maintaining direct record traceability to raw events.
    Supports optional drill-down by product_id and channel_id.
    freq: 'W' (weekly) or 'M' (monthly).
    Returns (trends_df, lineage_df):
      - trends_df: [period, total_feedback, positive_count, neutral_count, negative_count, net_sentiment_score, sample_source_record_ids]
      - lineage_df: [period, record_id, entity_type, dt, sentiment, product_id, channel_id]
    """
    with engine.connect() as conn:
        q_reviews = """
            SELECT review_id as record_id, 'review' as entity_type,
                   substr(reviewed_at, 1, 10) as dt,
                   coalesce(predicted_sentiment, sentiment_label) as sentiment,
                   product_id, channel_id
            FROM reviews
            WHERE reviewed_at IS NOT NULL
        """
        q_surveys = """
            SELECT r.response_id as record_id, 'survey_response' as entity_type,
                   substr(r.submitted_at, 1, 10) as dt,
                   coalesce(r.predicted_sentiment, r.sentiment_label) as sentiment,
                   s.product_id, s.channel_id
            FROM survey_responses r
            JOIN surveys s ON r.survey_id = s.survey_id
            WHERE r.submitted_at IS NOT NULL
        """
        q_messages = """
            SELECT m.message_id as record_id, 'support_message' as entity_type,
                   substr(m.sent_at, 1, 10) as dt,
                   coalesce(m.predicted_sentiment, m.sentiment_label) as sentiment,
                   t.product_id, t.channel_id
            FROM support_messages m
            JOIN support_tickets t ON m.ticket_id = t.ticket_id
            WHERE m.sent_at IS NOT NULL
        """

        df_rev = pd.read_sql(text(q_reviews), conn)
        df_surv = pd.read_sql(text(q_surveys), conn)
        df_msg = pd.read_sql(text(q_messages), conn)

    df_all = pd.concat([df_rev, df_surv, df_msg], ignore_index=True)
    if df_all.empty:
        empty_trends = pd.DataFrame(columns=[
            "period", "total_feedback", "positive_count", "neutral_count",
            "negative_count", "net_sentiment_score", "sample_source_record_ids"
        ])
        empty_lineage = pd.DataFrame(columns=[
            "period", "record_id", "entity_type", "dt", "sentiment", "product_id", "channel_id"
        ])
        return empty_trends, empty_lineage

    # Apply dimensional filters if specified
    if product_id is not None:
        df_all = df_all[df_all["product_id"] == product_id]
    if channel_id is not None:
        df_all = df_all[df_all["channel_id"] == channel_id]

    if df_all.empty:
        empty_trends = pd.DataFrame(columns=[
            "period", "total_feedback", "positive_count", "neutral_count",
            "negative_count", "net_sentiment_score", "sample_source_record_ids"
        ])
        empty_lineage = pd.DataFrame(columns=[
            "period", "record_id", "entity_type", "dt", "sentiment", "product_id", "channel_id"
        ])
        return empty_trends, empty_lineage

    df_all["dt_parsed"] = pd.to_datetime(df_all["dt"], errors="coerce")
    df_all = df_all.dropna(subset=["dt_parsed"])

    # Group by weekly or monthly period
    if freq.upper() == "M":
        df_all["period"] = df_all["dt_parsed"].dt.to_period("M").astype(str)
    else:
        df_all["period"] = df_all["dt_parsed"].dt.to_period("W").astype(str)

    lineage_df = df_all[["period", "record_id", "entity_type", "dt", "sentiment", "product_id", "channel_id"]].sort_values(
        ["period", "dt", "record_id"]
    ).reset_index(drop=True)

    # Pivot sentiment counts
    grouped = df_all.groupby(["period", "sentiment"]).size().unstack(fill_value=0)
    for col in ["positive", "neutral", "negative"]:
        if col not in grouped.columns:
            grouped[col] = 0

    grouped["total_feedback"] = grouped["positive"] + grouped["neutral"] + grouped["negative"]

    # Compute Net Sentiment Score (NSS): % Positive - % Negative (-100 to +100)
    grouped["net_sentiment_score"] = (
        (grouped["positive"] - grouped["negative"]) / grouped["total_feedback"] * 100
    ).round(2)

    # Attach sample source IDs for traceability directly in the aggregate table
    sample_ids = df_all.groupby("period")["record_id"].apply(
        lambda ids: "; ".join(ids.head(3))
    ).to_dict()

    result = grouped.reset_index().rename(columns={
        "positive": "positive_count",
        "neutral": "neutral_count",
        "negative": "negative_count",
    })
    result["sample_source_record_ids"] = result["period"].map(sample_ids)

    return result.sort_values("period").reset_index(drop=True), lineage_df


def detect_sentiment_inflection_points(trends_df: pd.DataFrame, threshold: float = 10.0) -> pd.DataFrame:
    """
    Identify periods where Net Sentiment Score shifted by more than `threshold` points
    compared to the previous period.

    The default threshold of 10.0 is the operational value used in report generation.
    A higher value (e.g. 15.0) can be passed for a more conservative filter.
    """
    if len(trends_df) < 2:
        return pd.DataFrame()

    df = trends_df.copy()
    df["prev_nss"] = df["net_sentiment_score"].shift(1)
    df["nss_change"] = (df["net_sentiment_score"] - df["prev_nss"]).round(2)
    df["is_inflection"] = df["nss_change"].abs() >= threshold

    inflections = df[df["is_inflection"]].copy()
    return inflections[["period", "net_sentiment_score", "prev_nss", "nss_change"]].reset_index(drop=True)
