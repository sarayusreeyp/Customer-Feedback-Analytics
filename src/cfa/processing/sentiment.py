"""
sentiment.py — Sentiment inference using HuggingFace Transformers or heuristic fallback.

Features:
  - Sarcasm & ambiguity pattern detection for edge cases.
  - Returns prediction labels and confidence scores.
  - Updates `predicted_sentiment` in reviews, survey_responses, and support_messages.
"""

from __future__ import annotations

import re
import pandas as pd
from sqlalchemy import text


# Precompiled word boundaries for fast rule-based sentiment fallback
_POS_PATTERNS = re.compile(
    r"\b("
    r"excellent|great|exceptional|impressive|delighted|flawlessly|outstanding|love|perfect|fast|"
    r"reliable|smooth|helpful|easy|breeze|top-notch|clean|transparent|clear|seamless|guided|rock-solid|"
    r"satisfecho|excelente|excepcional|sobresaliente|fant[aá]stico|parfaitement|remarquable|"
    r"hervorragend|zufrieden|ausgezeichnet|erstklassig"
    r")\b",
    re.IGNORECASE
)
_NEG_PATTERNS = re.compile(
    r"\b("
    r"terrible|disappointed|poor|defective|horrible|broken|worst|useless|unacceptable|nightmare|"
    r"frustrating|slow|damaged|crushed|waste|unreliable|crashes|freezes|failed|confusing|outdated|"
    r"wasteful|condescending|rude|incompetent|refused|ripped off|overpriced|broke|"
    r"decepcionante|p[eé]simo|da[nñ]ado|d[eé][cç]u|catastrophique|d[eé]plorable|entt[aä]uschend|schrecklich|kaputt|besch[aä]digt"
    r")\b",
    re.IGNORECASE
)
_NEU_PATTERNS = re.compile(
    r"\b("
    r"moderate|average|typical|standard|standardmäßig|standardmässig|acceptable|passable|ordinario|"
    r"convenable|routine|neutre|mittelmäßig|mittelmässig"
    r")\b",
    re.IGNORECASE
)

# Sarcasm markers (often mix positive adjectives with negative consequences)
_SARCASM_PATTERNS = re.compile(
    r"\b("
    r"oh wow|sure.*whether it actually works|love spending.*troubleshooting|five stars for effort|"
    r"perfect.*if by perfect you mean|only took.*wrong addresses|until it broke after a week|"
    r"refreshingly simple.*if you enjoy explaining|absolutely nothing has changed"
    r")\b",
    re.IGNORECASE
)


def _heuristic_sentiment_with_confidence(text_val: str) -> tuple[str, float, bool]:
    """
    Returns (predicted_sentiment, confidence, is_ambiguous_or_sarcastic).
    """
    text_clean = text_val.strip()
    is_sarcastic = bool(_SARCASM_PATTERNS.search(text_clean))

    if is_sarcastic:
        # Sarcastic remarks are negative tone masked by sarcastic positive wording
        return "negative", 0.75, True

    pos_count = len(_POS_PATTERNS.findall(text_clean))
    neg_count = len(_NEG_PATTERNS.findall(text_clean))
    neu_count = len(_NEU_PATTERNS.findall(text_clean))

    total = pos_count + neg_count + neu_count
    if total == 0:
        return "neutral", 0.50, False

    if neu_count > 0 and pos_count == 0 and neg_count == 0:
        return "neutral", 0.85, False

    if pos_count > neg_count:
        conf = round(pos_count / (pos_count + neg_count + 0.5), 2)
        return "positive", min(0.95, conf), False

    if neg_count > pos_count:
        conf = round(neg_count / (pos_count + neg_count + 0.5), 2)
        return "negative", min(0.95, conf), False

    # Equal positive and negative matches indicate mixed/ambiguous sentiment
    return "neutral", 0.60, True


class SentimentClassifier:
    """Wrapper for sentiment analysis with HuggingFace pipeline & rule-based options."""

    def __init__(self, model_name: str = "distilbert-base-uncased-finetuned-sst-2-english", use_model: bool = False):
        self.model_name = model_name
        self.pipeline = None
        if use_model:
            try:
                from transformers import pipeline
                self.pipeline = pipeline(
                    "sentiment-analysis",
                    model=model_name,
                    device="cpu",
                    truncation=True,
                    max_length=512
                )
            except Exception as e:
                print(f"[SentimentClassifier] Notice: HuggingFace model deferred ({e}). Using rule-based classifier.")
                self.pipeline = None

    def predict_batch_with_details(self, texts: list[str]) -> list[dict]:
        """Predict sentiment, confidence, and ambiguity flag for a list of texts."""
        if not texts:
            return []

        if self.pipeline is not None:
            try:
                results = self.pipeline(texts)
                details = []
                for t, res in zip(texts, results):
                    # Check sarcasm first
                    if _SARCASM_PATTERNS.search(t):
                        details.append({"label": "negative", "confidence": 0.80, "is_sarcastic": True})
                        continue

                    label = res["label"].lower()
                    score = float(res.get("score", 1.0))
                    if score < 0.65:
                        details.append({"label": "neutral", "confidence": score, "is_sarcastic": False})
                    elif "pos" in label:
                        details.append({"label": "positive", "confidence": score, "is_sarcastic": False})
                    else:
                        details.append({"label": "negative", "confidence": score, "is_sarcastic": False})
                return details
            except Exception as e:
                print(f"[SentimentClassifier] Inference error: {e}. Using heuristic fallback.")

        # Heuristic fallback
        details = []
        for t in texts:
            lbl, conf, amb = _heuristic_sentiment_with_confidence(t)
            details.append({"label": lbl, "confidence": conf, "is_sarcastic": amb})
        return details

    def predict_batch(self, texts: list[str]) -> list[str]:
        """Predict sentiment ('positive', 'neutral', 'negative') for a list of texts."""
        details = self.predict_batch_with_details(texts)
        return [d["label"] for d in details]


def update_predicted_sentiment(engine, classifier: SentimentClassifier, batch_size: int = 64) -> dict[str, int]:
    """
    Fetch unpredicted rows from reviews, survey_responses, and support_messages,
    run batched sentiment inference, and update predicted_sentiment column in SQLite.
    """
    tables_config = [
        ("reviews", "review_id", "review_text"),
        ("survey_responses", "response_id", "response_text"),
        ("support_messages", "message_id", "message_text"),
    ]

    updated_counts = {}

    with engine.connect() as conn:
        for table_name, id_col, text_col in tables_config:
            # Query rows needing prediction
            stmt = text(f"""
                SELECT "{id_col}", "{text_col}"
                FROM "{table_name}"
                WHERE predicted_sentiment IS NULL
            """)
            rows = conn.execute(stmt).fetchall()
            if not rows:
                updated_counts[table_name] = 0
                continue

            ids = [r[0] for r in rows]
            raw_texts = [str(r[1]) if r[1] is not None else "" for r in rows]

            # Batch inference
            preds = []
            for i in range(0, len(raw_texts), batch_size):
                batch_texts = raw_texts[i: i + batch_size]
                preds.extend(classifier.predict_batch(batch_texts))

            # Batch updates to SQLite
            with engine.begin() as trans_conn:
                update_sql = text(f"""
                    UPDATE "{table_name}"
                    SET predicted_sentiment = :sentiment
                    WHERE "{id_col}" = :rec_id
                """)
                params = [{"sentiment": p, "rec_id": r_id} for p, r_id in zip(preds, ids)]
                trans_conn.execute(update_sql, params)

            updated_counts[table_name] = len(ids)

    return updated_counts
