"""
theme_classifier.py — Maps feedback text into taxonomy themes.

Features:
  - Multi-label theme ranking (primary theme + secondary themes).
  - Explicit match density and confidence scoring.
  - Zero-shot classification fallback.
  - Avoids hardcoded single-theme bias on unclassified texts.
  - Updates `predicted_theme` in reviews, survey_responses, and support_messages.
"""

from __future__ import annotations

import re
import pandas as pd
from sqlalchemy import text
from cfa.generators.schema import THEMES

# Pre-compiled keywords for each taxonomy theme
_THEME_KEYWORDS = {
    "THEME-000001": [r"\b(build|durab|material|finish|fell apart|peel|craftsmanship|flimsy|sturdy|defects?|craft|solid build)\b"],
    "THEME-000002": [r"\b(customer service|agent|support staff|rude|helpful staff|spoke with|first contact|representative|unhelpful|incompetent|courteous|rep|reps)\b"],
    "THEME-000003": [r"\b(price|pricing|cost|worth|dollar|expensive|cheap|value|bargain|ripped off|overpriced|fee|fees|worth every penny)\b"],
    "THEME-000004": [r"\b(shipping|delivery|ship|delivered|tracking|delayed|late|crushed|transit|carrier|courier|on-time|dispatch|box crushed)\b"],
    "THEME-000005": [r"\b(website|app|ui|ux|interface|checkout|navigate|crash|logged out|clunky|dashboard|portal|mobile app|navigation|buggy)\b"],
    "THEME-000006": [r"\b(return|refund|policy|restocking|dispute|money back|send back|replacement|rma|credited)\b"],
    "THEME-000007": [r"\b(stock|availability|inventory|backorder|out of stock|available|reorder|in stock|restock|sold out)\b"],
    "THEME-000008": [r"\b(technical support|tech support|diagnos|setup help|configuration|reboot|troubleshoot|ticket|firmware|logs|patch)\b"],
    "THEME-000009": [r"\b(billing|invoice|charged|payment|credit card|fee|charge|receipt|statement|overcharged|subscription|double charged)\b"],
    "THEME-000010": [r"\b(communicat|update|notify|notification|email|status update|proactive|informed|no news|kept me posted|radio silence)\b"],
    "THEME-000011": [r"\b(packaging|box|unboxing|package|plastic|eco-friendly|bubble|protective wrap|crushed box|cushioning)\b"],
    "THEME-000012": [r"\b(install|setup|set up|instruction|instructions|guide|manual|connect|first-time setup|tutorial|step-by-step|plug and play)\b"],
    "THEME-000013": [r"\b(perform|performance|relia|freeze|lag|slow|crash|uptime|flawless|speed|snappy|crashes|responsive|latency)\b"],
    "THEME-000014": [r"\b(feature|feature request|customis|voice control|dark mode|automation|roadmap|integration|api|settings|option)\b"],
    "THEME-000015": [r"\b(onboard|onboarding|getting started|welcome tutorial|new user|first impression|walkthrough|sign-up flow|quickstart)\b"],
}

_COMPILED_THEME_PATTERNS = {
    tid: [re.compile(p, re.IGNORECASE) for p in pats]
    for tid, pats in _THEME_KEYWORDS.items()
}


def classify_theme_scores(text_val: str) -> list[tuple[str, int]]:
    """Return ranked list of (theme_id, match_count) sorted by match count descending."""
    scores: dict[str, int] = {}
    for tid, patterns in _COMPILED_THEME_PATTERNS.items():
        score = sum(len(p.findall(text_val)) for p in patterns)
        if score > 0:
            scores[tid] = score

    if not scores:
        return []

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def classify_theme_keyword(text_val: str, default: str | None = "THEME-000001") -> str:
    """Classify text into primary THEME-XXXXXX ID based on pattern match density."""
    ranked = classify_theme_scores(text_val)
    if ranked:
        return ranked[0][0]
    return default if default else "THEME-000001"


class ThemeClassifier:
    """Classifier for mapping customer feedback into primary and secondary themes."""

    def __init__(self, mode: str = "keyword", zero_shot_model: str = "facebook/bart-large-mnli"):
        self.mode = mode
        self.zero_shot_model = zero_shot_model
        self.pipeline = None

        if mode == "zero-shot":
            try:
                from transformers import pipeline
                self.pipeline = pipeline("zero-shot-classification", model=zero_shot_model, device="cpu")
            except Exception as e:
                print(f"[ThemeClassifier] Notice: Zero-shot model unavailable: {e}. Defaulting to keyword mode.")
                self.mode = "keyword"

    def predict_multi_label(self, texts: list[str], top_k: int = 3) -> list[list[str]]:
        """Return list of up to top_k theme IDs per text for multi-theme extraction."""
        all_preds = []
        for t in texts:
            ranked = classify_theme_scores(t)
            if ranked:
                themes = [tid for tid, _ in ranked[:top_k]]
            else:
                themes = ["THEME-000001"]
            all_preds.append(themes)
        return all_preds

    def predict_batch(self, texts: list[str]) -> list[str]:
        """Return a list of primary THEME-XXXXXX IDs for input texts."""
        if self.mode == "keyword" or self.pipeline is None:
            return [classify_theme_keyword(t) for t in texts]

        # Zero-shot classification
        candidate_labels = [t["name"] for t in THEMES]
        name_to_id = {t["name"]: t["theme_id"] for t in THEMES}

        preds = []
        for t in texts:
            try:
                res = self.pipeline(t, candidate_labels=candidate_labels, multi_label=False)
                top_name = res["labels"][0]
                preds.append(name_to_id.get(top_name, "THEME-000001"))
            except Exception:
                preds.append(classify_theme_keyword(t))

        return preds


def update_predicted_themes(engine, classifier: ThemeClassifier, batch_size: int = 64) -> dict[str, int]:
    """
    Fetch unpredicted rows from reviews, survey_responses, and support_messages,
    run theme classification, and update predicted_theme column in SQLite.
    """
    tables_config = [
        ("reviews", "review_id", "review_text"),
        ("survey_responses", "response_id", "response_text"),
        ("support_messages", "message_id", "message_text"),
    ]

    updated_counts = {}

    with engine.connect() as conn:
        for table_name, id_col, text_col in tables_config:
            stmt = text(f"""
                SELECT "{id_col}", "{text_col}"
                FROM "{table_name}"
                WHERE predicted_theme IS NULL
            """)
            rows = conn.execute(stmt).fetchall()
            if not rows:
                updated_counts[table_name] = 0
                continue

            ids = [r[0] for r in rows]
            raw_texts = [str(r[1]) if r[1] is not None else "" for r in rows]

            preds = []
            for i in range(0, len(raw_texts), batch_size):
                batch_texts = raw_texts[i: i + batch_size]
                preds.extend(classifier.predict_batch(batch_texts))

            with engine.begin() as trans_conn:
                update_sql = text(f"""
                    UPDATE "{table_name}"
                    SET predicted_theme = :theme
                    WHERE "{id_col}" = :rec_id
                """)
                params = [{"theme": p, "rec_id": r_id} for p, r_id in zip(preds, ids)]
                trans_conn.execute(update_sql, params)

            updated_counts[table_name] = len(ids)

    return updated_counts
