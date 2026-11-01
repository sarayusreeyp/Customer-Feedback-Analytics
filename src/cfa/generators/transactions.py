"""
transactions.py — Generate child/event entities.

Produces:
  reviews, review_themes (bridge)
  survey_responses, response_themes (bridge)
  support_tickets
  support_messages, message_themes (bridge)
  action_items (derived from theme mention counts)

Labelling rules (authoritative — mirrors validation checks):
  star_rating  1-2 → negative  |  3 → neutral  |  4-5 → positive
  response rating 1-4 → negative | 5-7 → neutral | 8-10 → positive
  sentiment_label is always derived from the numeric rating, never independently assigned.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from collections import defaultdict
from datetime import datetime, timedelta
from faker import Faker

from cfa.generators.schema import (
    THEME_WEIGHTS, SENTIMENT_LABELS,
    LANGUAGE_DISTRIBUTION,
    STAR_TO_SENTIMENT, response_rating_to_sentiment,
)
from cfa.generators.templates import (
    EN_REVIEW_TEMPLATES, SUPPORT_TEMPLATES,
    MULTILINGUAL_TEMPLATES, SARCASTIC_TEMPLATES,
)

# ── Constants ─────────────────────────────────────────────────────────────────

_NOW       = datetime(2026, 10, 30)
_YEAR_START = datetime(2026, 1, 1)

_LANG_KEYS  = list(LANGUAGE_DISTRIBUTION.keys())
_LANG_PROBS = [LANGUAGE_DISTRIBUTION[k] for k in _LANG_KEYS]


# ── ID helpers ────────────────────────────────────────────────────────────────

def _rev_id(i: int)               -> str: return f"REV-2026-{i:06d}"
def _tkt_id(i: int)               -> str: return f"TKT-2026-{i:06d}"
def _act_id(i: int)               -> str: return f"ACT-2026-{i:06d}"
def _resp_id(sur_id: str, i: int) -> str: return f"RESP-{sur_id}-{i:03d}"
def _msg_id(tkt_id: str, i: int)  -> str: return f"MSG-{tkt_id}-{i:03d}"


# ── Date helpers ──────────────────────────────────────────────────────────────

def _rand_dt(rng: np.random.Generator, lo: datetime, hi: datetime) -> datetime:
    delta_s = max(1, int((hi - lo).total_seconds()))
    return lo + timedelta(seconds=int(rng.integers(0, delta_s)))


# ── Sampling helpers ──────────────────────────────────────────────────────────

def _pick_language(rng: np.random.Generator) -> str:
    return str(rng.choice(_LANG_KEYS, p=_LANG_PROBS))


def _pick_star_rating(rng: np.random.Generator, pos: float, neu: float, neg: float) -> int:
    """Pick a 1-5 star rating consistent with the sentiment distribution."""
    sentiment = rng.choice(SENTIMENT_LABELS, p=[pos, neu, neg])
    if sentiment == "positive":
        return int(rng.choice([4, 5], p=[0.35, 0.65]))
    if sentiment == "neutral":
        return 3
    return int(rng.choice([1, 2], p=[0.45, 0.55]))


def _pick_response_rating(rng: np.random.Generator, pos: float, neu: float, neg: float) -> int:
    """Pick a 1-10 rating consistent with the sentiment distribution."""
    sentiment = rng.choice(SENTIMENT_LABELS, p=[pos, neu, neg])
    if sentiment == "positive":
        return int(rng.integers(8, 11))
    if sentiment == "neutral":
        return int(rng.integers(5, 8))
    return int(rng.integers(1, 5))


def _pick_themes(
    rng: np.random.Generator,
    theme_ids: list[str],
    max_secondary: int = 2,
) -> list[str]:
    """Return [primary_theme] + 0..max_secondary secondary themes (no repeats)."""
    primary = str(rng.choice(theme_ids, p=THEME_WEIGHTS))
    n_sec = int(rng.integers(0, max_secondary + 1))
    if n_sec == 0:
        return [primary]
    others = [t for t in theme_ids if t != primary]
    secondary = rng.choice(others, size=min(n_sec, len(others)), replace=False).tolist()
    return [primary] + secondary


def _get_text(
    rng: np.random.Generator,
    theme_id: str,
    sentiment: str,
    lang: str,
    product_name: str,
    category: str,
    ambiguous_ratio: float,
) -> tuple[str, bool]:
    """
    Return (text, is_ambiguous).
    ~ambiguous_ratio fraction of rows use a sarcastic template.
    Multilingual rows use language-specific pools (not theme-specific).
    """
    is_ambiguous = bool(rng.random() < ambiguous_ratio)

    if is_ambiguous:
        tmpl = SARCASTIC_TEMPLATES[int(rng.integers(0, len(SARCASTIC_TEMPLATES)))]
    elif lang != "en":
        pool = MULTILINGUAL_TEMPLATES[lang][sentiment]
        tmpl = pool[int(rng.integers(0, len(pool)))]
    else:
        pool = EN_REVIEW_TEMPLATES[theme_id][sentiment]
        tmpl = pool[int(rng.integers(0, len(pool)))]

    weeks  = int(rng.integers(1, 13))
    months = int(rng.integers(1, 13))
    text = tmpl.format(
        product_name=product_name,
        category=category,
        weeks=weeks,
        months=months,
    )
    return text, is_ambiguous


# ── Reviews ───────────────────────────────────────────────────────────────────

def generate_reviews(
    n: int,
    customers_df: pd.DataFrame,
    products_df: pd.DataFrame,
    channels_df: pd.DataFrame,
    themes_df: pd.DataFrame,
    rng: np.random.Generator,
    cfg: dict,
    id_offset: int = 0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns (reviews_df, review_themes_df).
    id_offset allows anomaly generation to continue numbering from n+1.
    """
    sentiment_dist = cfg["generation"]["sentiment_distribution"]
    pos = sentiment_dist["positive"]
    neu = sentiment_dist["neutral"]
    neg = sentiment_dist["negative"]
    max_sec = cfg["generation"]["max_secondary_themes"]
    amb_ratio = cfg["generation"]["ambiguous_ratio"]

    cust_ids    = customers_df["customer_id"].tolist()
    prod_rows   = products_df[["product_id", "name", "category"]].to_dict("records")
    chan_ids    = channels_df["channel_id"].tolist()
    theme_ids   = themes_df["theme_id"].tolist()

    reviews, bridges = [], []
    for i in range(1, n + 1):
        star    = _pick_star_rating(rng, pos, neu, neg)
        sent    = STAR_TO_SENTIMENT[star]
        lang    = _pick_language(rng)
        prod    = prod_rows[int(rng.integers(0, len(prod_rows)))]
        themes  = _pick_themes(rng, theme_ids, max_sec)
        text, is_amb = _get_text(
            rng, themes[0], sent, lang,
            prod["name"], prod["category"], amb_ratio,
        )
        rev_id = _rev_id(id_offset + i)
        dt = _rand_dt(rng, _YEAR_START, _NOW)

        reviews.append({
            "review_id":      rev_id,
            "customer_id":    cust_ids[int(rng.integers(0, len(cust_ids)))],
            "product_id":     prod["product_id"],
            "channel_id":     chan_ids[int(rng.integers(0, len(chan_ids)))],
            "review_text":    text,
            "star_rating":    star,
            "sentiment_label":sent,
            "language":       lang,
            "reviewed_at":    dt.isoformat(sep=" "),
            "is_ambiguous":   is_amb,
        })
        for theme_id in themes:
            bridges.append({"review_id": rev_id, "theme_id": theme_id})

    return pd.DataFrame(reviews), pd.DataFrame(bridges)


# ── Survey Responses ──────────────────────────────────────────────────────────

def generate_survey_responses(
    n: int,
    surveys_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    themes_df: pd.DataFrame,
    rng: np.random.Generator,
    cfg: dict,
    id_offset: int = 0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns (responses_df, response_themes_df).
    Responses are distributed evenly across surveys.
    submitted_at is within the survey's [start_date, end_date] window.
    """
    sentiment_dist = cfg["generation"]["sentiment_distribution"]
    pos = sentiment_dist["positive"]
    neu = sentiment_dist["neutral"]
    neg = sentiment_dist["negative"]
    max_sec   = cfg["generation"]["max_secondary_themes"]
    amb_ratio = cfg["generation"]["ambiguous_ratio"]

    cust_ids  = customers_df["customer_id"].tolist()
    theme_ids = themes_df["theme_id"].tolist()

    survey_list = surveys_df.to_dict("records")
    n_surveys   = len(survey_list)

    # Per-survey counter to build the RESP-<sur_id>-NNN pattern
    survey_counter: dict[str, int] = defaultdict(int)

    responses, bridges = [], []
    for i in range(n):
        global_idx = id_offset + i + 1
        survey  = survey_list[i % n_surveys]
        sur_id  = survey["survey_id"]
        survey_counter[sur_id] += 1

        rating = _pick_response_rating(rng, pos, neu, neg)
        sent   = response_rating_to_sentiment(rating)
        lang   = _pick_language(rng)
        themes = _pick_themes(rng, theme_ids, max_sec)

        # Use the same template pool as reviews (free-text feedback)
        # For multilingual, generic pool; for English, theme-specific
        text, is_amb = _get_text(
            rng, themes[0], sent, lang,
            survey.get("title", "our product"), "product", amb_ratio,
        )

        # submitted_at within [start_date, end_date]
        s_lo = datetime.fromisoformat(survey["start_date"])
        s_hi = min(datetime.fromisoformat(survey["end_date"]), _NOW)
        if s_hi <= s_lo:
            s_hi = s_lo + timedelta(days=1)
        submitted = _rand_dt(rng, s_lo, s_hi)

        resp_id = _resp_id(sur_id, survey_counter[sur_id])

        responses.append({
            "response_id":    resp_id,
            "survey_id":      sur_id,
            "customer_id":    cust_ids[int(rng.integers(0, len(cust_ids)))],
            "response_text":  text,
            "rating":         rating,
            "sentiment_label":sent,
            "language":       lang,
            "submitted_at":   submitted.isoformat(sep=" "),
            "is_ambiguous":   is_amb,
        })
        for theme_id in themes:
            bridges.append({"response_id": resp_id, "theme_id": theme_id})

    return pd.DataFrame(responses), pd.DataFrame(bridges)


# ── Support Tickets ───────────────────────────────────────────────────────────

_TICKET_SUBJECTS = [
    "Product not working as expected",
    "Request for refund",
    "Delivery issue — order not received",
    "Billing discrepancy on my account",
    "Technical setup help needed",
    "Wrong item received",
    "Product damaged on arrival",
    "Account access issue",
    "Return request for recent purchase",
    "Feature not working as described",
]

_TICKET_STATUS_WEIGHTS = [0.10, 0.20, 0.40, 0.30]  # open, in_progress, resolved, closed


def generate_support_tickets(
    n: int,
    customers_df: pd.DataFrame,
    channels_df: pd.DataFrame,
    rng: np.random.Generator,
    products_df: pd.DataFrame | None = None,
    id_offset: int = 0,
) -> pd.DataFrame:
    """Generate n SupportTicket records. resolved_at is None for open/in_progress."""
    from cfa.generators.schema import TICKET_STATUSES

    cust_ids = customers_df["customer_id"].tolist()
    chan_ids  = channels_df["channel_id"].tolist()
    prod_ids = products_df["product_id"].tolist() if products_df is not None and not products_df.empty else None

    rows = []
    for i in range(1, n + 1):
        created = _rand_dt(rng, _YEAR_START, _NOW)
        status  = rng.choice(TICKET_STATUSES, p=_TICKET_STATUS_WEIGHTS)
        subject = _TICKET_SUBJECTS[int(rng.integers(0, len(_TICKET_SUBJECTS)))]
        product_id = prod_ids[int(rng.integers(0, len(prod_ids)))] if prod_ids and rng.random() > 0.15 else None

        resolved_at = None
        if status in ("resolved", "closed"):
            max_resolve = min(created + timedelta(days=14), _NOW)
            if max_resolve > created:
                resolved_at = _rand_dt(rng, created, max_resolve).isoformat(sep=" ")

        rows.append({
            "ticket_id":   _tkt_id(id_offset + i),
            "customer_id": cust_ids[int(rng.integers(0, len(cust_ids)))],
            "channel_id":  chan_ids[int(rng.integers(0, len(chan_ids)))],
            "product_id":  product_id,
            "subject":     subject,
            "status":      status,
            "created_at":  created.isoformat(sep=" "),
            "resolved_at": resolved_at,
        })

    return pd.DataFrame(rows)


# ── Support Messages ──────────────────────────────────────────────────────────

def generate_support_messages(
    n: int,
    tickets_df: pd.DataFrame,
    themes_df: pd.DataFrame,
    rng: np.random.Generator,
    cfg: dict,
    id_offset: int = 0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate n SupportMessage records distributed across tickets.
    Returns (messages_df, message_themes_df).
    Each ticket gets a realistic conversation: customer → agent → customer → ...
    sent_at is after the ticket's created_at.
    """
    sentiment_dist = cfg["generation"]["sentiment_distribution"]
    pos = sentiment_dist["positive"]
    neu = sentiment_dist["neutral"]
    neg = sentiment_dist["negative"]
    max_sec   = cfg["generation"]["max_secondary_themes"]
    amb_ratio = cfg["generation"]["ambiguous_ratio"]

    theme_ids   = themes_df["theme_id"].tolist()
    ticket_list = tickets_df.to_dict("records")
    n_tickets   = len(ticket_list)

    # Per-ticket message counter
    ticket_counter: dict[str, int] = defaultdict(int)

    messages, bridges = [], []
    for i in range(n):
        ticket = ticket_list[i % n_tickets]
        tkt_id = ticket["ticket_id"]
        ticket_counter[tkt_id] += 1

        # Alternate sender: customer on odd messages, agent on even
        is_customer = (ticket_counter[tkt_id] % 2 == 1)
        sender_type = "customer" if is_customer else "agent"

        # Sentiment: customer negative early → positive late; agent always courteous
        if sender_type == "customer":
            sent_probs = [pos, neu, neg]
        else:
            # Agents lean neutral/positive
            sent_probs = [0.45, 0.45, 0.10]

        sent = rng.choice(SENTIMENT_LABELS, p=sent_probs)

        pool = SUPPORT_TEMPLATES[sender_type][sent]
        tmpl = pool[int(rng.integers(0, len(pool)))]
        text = tmpl.format(product_name="your product", category="product")
        is_amb = bool(rng.random() < amb_ratio)

        lang   = _pick_language(rng)
        themes = _pick_themes(rng, theme_ids, max_sec)

        created_at = datetime.fromisoformat(ticket["created_at"])
        sent_at = _rand_dt(
            rng,
            created_at,
            min(created_at + timedelta(days=10), _NOW),
        )

        msg_id = _msg_id(tkt_id, ticket_counter[tkt_id])
        messages.append({
            "message_id":    msg_id,
            "ticket_id":     tkt_id,
            "sender_type":   sender_type,
            "message_text":  text,
            "sentiment_label": sent,
            "language":      lang,
            "sent_at":       sent_at.isoformat(sep=" "),
            "is_ambiguous":  is_amb,
        })
        for theme_id in themes:
            bridges.append({"message_id": msg_id, "theme_id": theme_id})

    return pd.DataFrame(messages), pd.DataFrame(bridges)


# ── Action Items ──────────────────────────────────────────────────────────────

_ACTION_TITLES = {
    "THEME-000001": "Investigate and address product quality complaints",
    "THEME-000002": "Improve customer service response time and resolution rate",
    "THEME-000003": "Review pricing strategy and communicate value proposition",
    "THEME-000004": "Audit delivery partners and reduce shipping delays",
    "THEME-000005": "Redesign website/app UX based on user pain points",
    "THEME-000006": "Simplify return and refund process",
    "THEME-000007": "Improve inventory forecasting to reduce stockouts",
    "THEME-000008": "Upskill technical support team on product knowledge",
    "THEME-000009": "Fix billing system errors and improve invoice clarity",
    "THEME-000010": "Implement proactive order/status communication",
    "THEME-000011": "Review and improve packaging standards",
    "THEME-000012": "Rewrite installation guide and create video tutorials",
    "THEME-000013": "Investigate performance degradation reports",
    "THEME-000014": "Compile feature request backlog and share roadmap",
    "THEME-000015": "Redesign onboarding experience for new users",
}


def generate_action_items(
    theme_mention_counts: dict[str, int],
    threshold: int,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Create one ActionItem per theme whose total mention count >= threshold.
    Priority is derived from mention count (not randomly assigned):
      count >= 3×threshold → high
      count >= 2×threshold → medium
      else → low
    Status: open (new action items, all created today).
    """
    rows = []
    counter = 1
    for theme_id, count in sorted(theme_mention_counts.items()):
        if count < threshold:
            continue
        if count >= 3 * threshold:
            priority = "high"
        elif count >= 2 * threshold:
            priority = "medium"
        else:
            priority = "low"

        rows.append({
            "action_id":    _act_id(counter),
            "theme_id":     theme_id,
            "title":        _ACTION_TITLES.get(theme_id, f"Address issues for {theme_id}"),
            "priority":     priority,
            "status":       "open",
            "created_at":   "2026-10-30",
            "mention_count": count,
        })
        counter += 1

    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["action_id", "theme_id", "title", "priority", "status", "created_at", "mention_count"]
    )
