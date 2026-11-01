"""
queries.py — Standard query helpers for Analytics (Module 5) and Evaluation (Module 6).

Avoids scattered raw SQL throughout the codebase.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import select, func, and_, text
from cfa.db.models import (
    reviews, survey_responses, support_messages,
    themes, review_themes, response_themes, message_themes,
    customers, products, channels, action_items
)


def get_all_unprocessed_texts(conn, limit: int | None = None) -> dict[str, pd.DataFrame]:
    """
    Fetch texts needing sentiment and theme prediction (where predicted_* is NULL).
    Returns a dict with DataFrames for 'reviews', 'responses', and 'messages'.
    """
    rev_stmt = select(
        reviews.c.review_id,
        reviews.c.review_text,
        reviews.c.language,
        reviews.c.sentiment_label
    )
    if limit:
        rev_stmt = rev_stmt.limit(limit)
    df_rev = pd.read_sql(rev_stmt, conn)

    resp_stmt = select(
        survey_responses.c.response_id,
        survey_responses.c.response_text,
        survey_responses.c.language,
        survey_responses.c.sentiment_label
    )
    if limit:
        resp_stmt = resp_stmt.limit(limit)
    df_resp = pd.read_sql(resp_stmt, conn)

    msg_stmt = select(
        support_messages.c.message_id,
        support_messages.c.message_text,
        support_messages.c.language,
        support_messages.c.sentiment_label
    )
    if limit:
        msg_stmt = msg_stmt.limit(limit)
    df_msg = pd.read_sql(msg_stmt, conn)

    return {
        "reviews": df_rev,
        "responses": df_resp,
        "messages": df_msg,
    }


def get_theme_mention_counts(conn) -> pd.DataFrame:
    """
    Aggregate theme mentions across all 3 text sources (reviews, responses, messages).
    Returns DataFrame: [theme_id, theme_name, review_count, response_count, message_count, total_count]
    """
    # Count in reviews
    rev_counts = (
        select(
            review_themes.c.theme_id,
            func.count(review_themes.c.review_id).label("rev_cnt")
        )
        .group_by(review_themes.c.theme_id)
        .subquery()
    )

    # Count in survey responses
    resp_counts = (
        select(
            response_themes.c.theme_id,
            func.count(response_themes.c.response_id).label("resp_cnt")
        )
        .group_by(response_themes.c.theme_id)
        .subquery()
    )

    # Count in messages
    msg_counts = (
        select(
            message_themes.c.theme_id,
            func.count(message_themes.c.message_id).label("msg_cnt")
        )
        .group_by(message_themes.c.theme_id)
        .subquery()
    )

    stmt = (
        select(
            themes.c.theme_id,
            themes.c.name.label("theme_name"),
            func.coalesce(rev_counts.c.rev_cnt, 0).label("review_count"),
            func.coalesce(resp_counts.c.resp_cnt, 0).label("response_count"),
            func.coalesce(msg_counts.c.msg_cnt, 0).label("message_count"),
            (
                func.coalesce(rev_counts.c.rev_cnt, 0)
                + func.coalesce(resp_counts.c.resp_cnt, 0)
                + func.coalesce(msg_counts.c.msg_cnt, 0)
            ).label("total_count"),
        )
        .outerjoin(rev_counts, themes.c.theme_id == rev_counts.c.theme_id)
        .outerjoin(resp_counts, themes.c.theme_id == resp_counts.c.theme_id)
        .outerjoin(msg_counts, themes.c.theme_id == msg_counts.c.theme_id)
        .order_by(text("total_count DESC") if "text" in globals() else func.coalesce(rev_counts.c.rev_cnt, 0).desc())
    )

    return pd.read_sql(stmt, conn)


def get_sentiment_trends_by_product(conn) -> pd.DataFrame:
    """
    Query review sentiment trends grouped by product and rating.
    """
    stmt = (
        select(
            products.c.product_id,
            products.c.name.label("product_name"),
            reviews.c.sentiment_label,
            func.count(reviews.c.review_id).label("count")
        )
        .join(reviews, products.c.product_id == reviews.c.product_id)
        .group_by(products.c.product_id, products.c.name, reviews.c.sentiment_label)
    )
    return pd.read_sql(stmt, conn)
