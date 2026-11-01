"""
anomalies.py — Generate labelled anomaly records.

For each entity type (reviews, responses, messages), generates n anomaly
records split equally across 5 anomaly types (~n/5 each):

  label_contradiction   — sentiment label opposes the text tone
  duplicate_response    — exact copy of an existing row's text + customer_id
  pii_leak              — real-looking name/email embedded in the text
  out_of_taxonomy_theme — theme_id not in the 15-item taxonomy
  test_label_in_input   — literal "TEST" marker in a text field

Outputs
-------
  reviews_anomalies.csv   → data/anomalies/   (has issue_type column)
  responses_anomalies.csv → data/anomalies/
  messages_anomalies.csv  → data/anomalies/
  ground_truth.csv        → data/ground_truth/  (record_id, entity_type,
                            issue_type, correct_sentiment_label, correct_theme_id, notes)

The main data/raw/ files are never touched by this module.
issue_type is NOT present in the clean raw files — no leakage.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from faker import Faker

from cfa.generators.schema import (
    STAR_TO_SENTIMENT, response_rating_to_sentiment,
    SENTIMENT_LABELS, ANOMALY_TYPES,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _flip_sentiment(label: str) -> str:
    """Return the opposite sentiment label (positive->negative, negative->positive, neutral->negative)."""
    flip = {"positive": "negative", "negative": "positive", "neutral": "negative"}
    return flip.get(label, "negative")


def _inject_pii(text: str, faker: Faker) -> str:
    """Embed a fake name and email into the text string."""
    name  = faker.name()
    email = faker.email()
    return f"{text} — Submitted by {name} ({email})"


def _fake_theme_id() -> str:
    """Return a theme ID that does NOT exist in the taxonomy."""
    return "THEME-999999"


_TEST_MARKER = " [TEST_RECORD — DO NOT USE IN PRODUCTION]"


# ── Per-entity anomaly generators ─────────────────────────────────────────────

def generate_review_anomalies(
    n: int,
    reviews_df: pd.DataFrame,
    rng: np.random.Generator,
    faker: Faker,
    review_themes_df: pd.DataFrame,
    id_offset: int = 0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build n anomalous review rows (n/5 per anomaly type).
    Returns (anomalies_df, ground_truth_rows_df).
    IDs continue from id_offset+1.
    """
    n_each = max(1, n // len(ANOMALY_TYPES))
    base   = reviews_df.sample(n=min(n, len(reviews_df)), random_state=int(rng.integers(0, 1_000_000)), replace=True).reset_index(drop=True)

    anomalies, gt_rows = [], []
    counter = id_offset

    for a_idx, atype in enumerate(ANOMALY_TYPES):
        chunk = base.iloc[a_idx * n_each: (a_idx + 1) * n_each].copy()

        for _, row in chunk.iterrows():
            counter += 1
            rev_id = f"REV-2026-{counter:06d}"
            correct_sentiment = STAR_TO_SENTIMENT[row["star_rating"]]

            # Decide which theme to record in ground truth
            gt_theme = review_themes_df.loc[
                review_themes_df["review_id"] == row["review_id"], "theme_id"
            ].iloc[0] if not review_themes_df.empty else "THEME-000001"

            text    = str(row["review_text"])
            sent    = str(row["sentiment_label"])
            gt_sent = correct_sentiment
            notes   = ""

            if atype == "label_contradiction":
                sent = _flip_sentiment(correct_sentiment)
                notes = f"Label flipped from '{correct_sentiment}' to '{sent}'"

            elif atype == "duplicate_response":
                # Keep text and customer identical to an existing record
                notes = f"Duplicate of original review_id={row['review_id']}"

            elif atype == "pii_leak":
                text  = _inject_pii(text, faker)
                notes = "PII (name + email) injected into review_text"

            elif atype == "out_of_taxonomy_theme":
                gt_theme = _fake_theme_id()
                notes    = "theme_id outside the 15-item taxonomy"

            elif atype == "test_label_in_input":
                text  = text + _TEST_MARKER
                notes = "TEST marker present in review_text"

            anomalies.append({
                "review_id":      rev_id,
                "customer_id":    row["customer_id"],
                "product_id":     row["product_id"],
                "channel_id":     row["channel_id"],
                "review_text":    text,
                "star_rating":    row["star_rating"],
                "sentiment_label":sent,
                "language":       row["language"],
                "reviewed_at":    row["reviewed_at"],
                "is_ambiguous":   row["is_ambiguous"],
                "issue_type":     atype,
            })
            gt_rows.append({
                "record_id":              rev_id,
                "entity_type":            "review",
                "issue_type":             atype,
                "correct_sentiment_label":gt_sent,
                "correct_theme_id":       gt_theme if atype != "out_of_taxonomy_theme" else review_themes_df.loc[review_themes_df["review_id"] == row["review_id"], "theme_id"].iloc[0] if not review_themes_df.empty else "THEME-000001",
                "notes":                  notes,
            })

    return pd.DataFrame(anomalies), pd.DataFrame(gt_rows)


def generate_response_anomalies(
    n: int,
    responses_df: pd.DataFrame,
    rng: np.random.Generator,
    faker: Faker,
    response_themes_df: pd.DataFrame,
    id_offset: int = 0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build n anomalous survey_response rows.
    Returns (anomalies_df, ground_truth_rows_df).
    """
    n_each = max(1, n // len(ANOMALY_TYPES))
    base   = responses_df.sample(n=min(n, len(responses_df)), random_state=int(rng.integers(0, 1_000_000)), replace=True).reset_index(drop=True)

    anomalies, gt_rows = [], []
    # Use a separate survey counter to avoid ID conflicts
    anom_counter: dict[str, int] = {}

    for a_idx, atype in enumerate(ANOMALY_TYPES):
        chunk = base.iloc[a_idx * n_each: (a_idx + 1) * n_each].copy()

        for local_i, (_, row) in enumerate(chunk.iterrows()):
            sur_id = str(row["survey_id"])
            anom_counter[sur_id] = anom_counter.get(sur_id, 900) + 1
            resp_id = f"RESP-{sur_id}-{anom_counter[sur_id]:03d}"

            correct_sentiment = response_rating_to_sentiment(int(row["rating"]))
            gt_theme = response_themes_df.loc[
                response_themes_df["response_id"] == row["response_id"], "theme_id"
            ].iloc[0] if not response_themes_df.empty else "THEME-000001"

            text = str(row["response_text"])
            sent = str(row["sentiment_label"])
            gt_sent = correct_sentiment
            notes   = ""

            if atype == "label_contradiction":
                sent  = _flip_sentiment(correct_sentiment)
                notes = f"Label flipped from '{correct_sentiment}' to '{sent}'"
            elif atype == "duplicate_response":
                notes = f"Duplicate of original response_id={row['response_id']}"
            elif atype == "pii_leak":
                text  = _inject_pii(text, faker)
                notes = "PII injected into response_text"
            elif atype == "out_of_taxonomy_theme":
                gt_theme = _fake_theme_id()
                notes    = "theme_id outside taxonomy"
            elif atype == "test_label_in_input":
                text  = text + _TEST_MARKER
                notes = "TEST marker in response_text"

            anomalies.append({
                "response_id":    resp_id,
                "survey_id":      sur_id,
                "customer_id":    row["customer_id"],
                "response_text":  text,
                "rating":         row["rating"],
                "sentiment_label":sent,
                "language":       row["language"],
                "submitted_at":   row["submitted_at"],
                "is_ambiguous":   row["is_ambiguous"],
                "issue_type":     atype,
            })
            gt_rows.append({
                "record_id":              resp_id,
                "entity_type":            "survey_response",
                "issue_type":             atype,
                "correct_sentiment_label":gt_sent,
                "correct_theme_id":       response_themes_df.loc[response_themes_df["response_id"] == row["response_id"], "theme_id"].iloc[0] if not response_themes_df.empty else "THEME-000001",
                "notes":                  notes,
            })

    return pd.DataFrame(anomalies), pd.DataFrame(gt_rows)


def generate_message_anomalies(
    n: int,
    messages_df: pd.DataFrame,
    rng: np.random.Generator,
    faker: Faker,
    message_themes_df: pd.DataFrame,
    id_offset: int = 0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build n anomalous support_message rows.
    Returns (anomalies_df, ground_truth_rows_df).
    """
    n_each = max(1, n // len(ANOMALY_TYPES))
    base   = messages_df.sample(n=min(n, len(messages_df)), random_state=int(rng.integers(0, 1_000_000)), replace=True).reset_index(drop=True)

    anomalies, gt_rows = [], []
    tkt_counter: dict[str, int] = {}

    for a_idx, atype in enumerate(ANOMALY_TYPES):
        chunk = base.iloc[a_idx * n_each: (a_idx + 1) * n_each].copy()

        for _, row in chunk.iterrows():
            tkt_id = str(row["ticket_id"])
            tkt_counter[tkt_id] = tkt_counter.get(tkt_id, 900) + 1
            msg_id = f"MSG-{tkt_id}-{tkt_counter[tkt_id]:03d}"

            correct_sentiment = str(row["sentiment_label"])  # messages don't have a derived label
            gt_theme = message_themes_df.loc[
                message_themes_df["message_id"] == row["message_id"], "theme_id"
            ].iloc[0] if not message_themes_df.empty else "THEME-000001"

            text = str(row["message_text"])
            sent = correct_sentiment
            notes = ""

            if atype == "label_contradiction":
                sent  = _flip_sentiment(correct_sentiment)
                notes = f"Label flipped from '{correct_sentiment}' to '{sent}'"
            elif atype == "duplicate_response":
                notes = f"Duplicate of original message_id={row['message_id']}"
            elif atype == "pii_leak":
                text  = _inject_pii(text, faker)
                notes = "PII injected into message_text"
            elif atype == "out_of_taxonomy_theme":
                gt_theme = _fake_theme_id()
                notes    = "theme_id outside taxonomy"
            elif atype == "test_label_in_input":
                text  = text + _TEST_MARKER
                notes = "TEST marker in message_text"

            anomalies.append({
                "message_id":     msg_id,
                "ticket_id":      tkt_id,
                "sender_type":    row["sender_type"],
                "message_text":   text,
                "sentiment_label":sent,
                "language":       row["language"],
                "sent_at":        row["sent_at"],
                "is_ambiguous":   row["is_ambiguous"],
                "issue_type":     atype,
            })
            gt_rows.append({
                "record_id":              msg_id,
                "entity_type":            "support_message",
                "issue_type":             atype,
                "correct_sentiment_label":correct_sentiment,
                "correct_theme_id":       message_themes_df.loc[message_themes_df["message_id"] == row["message_id"], "theme_id"].iloc[0] if not message_themes_df.empty else "THEME-000001",
                "notes":                  notes,
            })

    return pd.DataFrame(anomalies), pd.DataFrame(gt_rows)


def build_ground_truth(
    review_gt: pd.DataFrame,
    response_gt: pd.DataFrame,
    message_gt: pd.DataFrame,
) -> pd.DataFrame:
    """Combine per-entity ground truth rows into the single ground_truth.csv."""
    return pd.concat([review_gt, response_gt, message_gt], ignore_index=True)
