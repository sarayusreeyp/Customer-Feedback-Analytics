"""
validate_raw.py — Module 1 Validation Gate.

Validates the raw incoming datasets (which contain injected anomalies):
  - Filters out records with PII leaks (names/emails embedded in text).
  - Filters out records with test markers ("[TEST_RECORD ...").
  - Filters out records with label contradictions (sentiment contradicts rating).
  - Filters out duplicate records (exact copies of existing submissions).
  - Filters out bridge theme assignments outside the allowed 15-item taxonomy.

Separates clean validated records into data/validated/ (for database ingestion)
and logs excluded anomalies with explicit failure reasons into data/excluded_anomalies/
(or reports) so verification of validation can be easily confirmed.
"""

from __future__ import annotations

import re
from pathlib import Path
import pandas as pd

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
TEST_MARKER_REGEX = re.compile(r"\[TEST_RECORD")
STAR_MAP = {1: "negative", 2: "negative", 3: "neutral", 4: "positive", 5: "positive"}


def _rating_to_sentiment(r: int) -> str:
    if r >= 8:
        return "positive"
    if r >= 5:
        return "neutral"
    return "negative"


def validate_reviews(reviews_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Validates reviews dataframe.
    Returns (validated_df, excluded_df).
    """
    df = reviews_df.copy()
    
    c_pii = df["review_text"].astype(str).str.contains(EMAIL_REGEX)
    c_test = df["review_text"].astype(str).str.contains(TEST_MARKER_REGEX)
    c_contradict = df["star_rating"].map(STAR_MAP) != df["sentiment_label"]
    c_dup = df.duplicated(subset=["customer_id", "product_id", "reviewed_at"], keep="first")
    
    df["exclusion_reason"] = None
    df.loc[c_pii, "exclusion_reason"] = "pii_leak"
    df.loc[c_test & df["exclusion_reason"].isna(), "exclusion_reason"] = "test_label_in_input"
    df.loc[c_contradict & df["exclusion_reason"].isna(), "exclusion_reason"] = "label_contradiction"
    df.loc[c_dup & df["exclusion_reason"].isna(), "exclusion_reason"] = "duplicate_submission"
    
    excluded = df[df["exclusion_reason"].notna()].copy()
    validated = df[df["exclusion_reason"].isna()].drop(columns=["exclusion_reason"]).copy()
    
    return validated, excluded


def validate_survey_responses(responses_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Validates survey responses dataframe.
    Returns (validated_df, excluded_df).
    """
    df = responses_df.copy()
    
    c_pii = df["response_text"].astype(str).str.contains(EMAIL_REGEX)
    c_test = df["response_text"].astype(str).str.contains(TEST_MARKER_REGEX)
    c_contradict = df["rating"].apply(_rating_to_sentiment) != df["sentiment_label"]
    c_dup = df.duplicated(subset=["survey_id", "customer_id", "submitted_at"], keep="first")
    
    df["exclusion_reason"] = None
    df.loc[c_pii, "exclusion_reason"] = "pii_leak"
    df.loc[c_test & df["exclusion_reason"].isna(), "exclusion_reason"] = "test_label_in_input"
    df.loc[c_contradict & df["exclusion_reason"].isna(), "exclusion_reason"] = "label_contradiction"
    df.loc[c_dup & df["exclusion_reason"].isna(), "exclusion_reason"] = "duplicate_submission"
    
    excluded = df[df["exclusion_reason"].notna()].copy()
    validated = df[df["exclusion_reason"].isna()].drop(columns=["exclusion_reason"]).copy()
    
    return validated, excluded


def validate_support_messages(messages_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Validates support messages dataframe.
    Returns (validated_df, excluded_df).
    """
    df = messages_df.copy()
    
    c_pii = df["message_text"].astype(str).str.contains(EMAIL_REGEX)
    c_test = df["message_text"].astype(str).str.contains(TEST_MARKER_REGEX)
    c_dup = df.duplicated(subset=["ticket_id", "sent_at"], keep="first")
    
    df["exclusion_reason"] = None
    df.loc[c_pii, "exclusion_reason"] = "pii_leak"
    df.loc[c_test & df["exclusion_reason"].isna(), "exclusion_reason"] = "test_label_in_input"
    df.loc[c_dup & df["exclusion_reason"].isna(), "exclusion_reason"] = "duplicate_submission"
    
    excluded = df[df["exclusion_reason"].notna()].copy()
    validated = df[df["exclusion_reason"].isna()].drop(columns=["exclusion_reason"]).copy()
    
    return validated, excluded


def validate_theme_bridge(
    bridge_df: pd.DataFrame,
    allowed_theme_ids: set[str],
    id_col: str = "theme_id"
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Validates theme bridge records against the allowed 15-item taxonomy.
    Flags and separates records with out_of_taxonomy_theme.
    Returns (validated_bridge_df, excluded_bridge_df).
    """
    df = bridge_df.copy()
    c_out = ~df[id_col].astype(str).isin(allowed_theme_ids)
    
    df["exclusion_reason"] = None
    df.loc[c_out, "exclusion_reason"] = "out_of_taxonomy_theme"
    
    excluded = df[df["exclusion_reason"].notna()].copy()
    validated = df[df["exclusion_reason"].isna()].drop(columns=["exclusion_reason"]).copy()
    
    return validated, excluded
