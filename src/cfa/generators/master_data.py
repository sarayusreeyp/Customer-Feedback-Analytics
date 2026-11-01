"""
master_data.py — Generate fixed/parent entities.

Produces: Customer, Product, Channel, Survey, Theme DataFrames.
All IDs are deterministic (counter-based, zero-padded).
No FK dependencies on other generated tables.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from faker import Faker

from cfa.generators.schema import (
    PRODUCTS, CHANNELS, THEMES, SENTIMENT_LABELS_MASTER,
    REGIONS, REGION_WEIGHTS,
    SEGMENTS, SEGMENT_WEIGHTS,
    SURVEY_TYPES, LIFECYCLE_STATES,
    CUSTOMER_LIFECYCLE_WEIGHTS,
)


# ── ID helpers ────────────────────────────────────────────────────────────────

def _cust_id(i: int) -> str:  return f"CUST-2026-{i:06d}"
def _sur_id(i: int) -> str:   return f"SUR-2026-{i:06d}"


# ── Date helpers ──────────────────────────────────────────────────────────────

_EPOCH = datetime(2024, 1, 1)
_NOW   = datetime(2026, 10, 30)
_SURVEY_START_RANGE = (datetime(2026, 1, 1), datetime(2026, 8, 1))


def _rand_dt(rng: np.random.Generator, lo: datetime, hi: datetime) -> datetime:
    """Return a random datetime between lo and hi (inclusive)."""
    delta_s = int((hi - lo).total_seconds())
    return lo + timedelta(seconds=int(rng.integers(0, delta_s + 1)))


# ── Generators ────────────────────────────────────────────────────────────────

def generate_products() -> pd.DataFrame:
    """Return the fixed 20-product catalogue."""
    return pd.DataFrame(PRODUCTS)


def generate_channels() -> pd.DataFrame:
    """Return the fixed 6-channel list."""
    return pd.DataFrame(CHANNELS)


def generate_themes() -> pd.DataFrame:
    """Return the fixed 15-theme taxonomy."""
    return pd.DataFrame(THEMES)


def generate_sentiment_labels() -> pd.DataFrame:
    """Return the fixed sentiment labels master table."""
    return pd.DataFrame(SENTIMENT_LABELS_MASTER)


def generate_customers(n: int, rng: np.random.Generator, faker: Faker) -> pd.DataFrame:
    """
    Generate n Customer records.

    ID pattern : CUST-2026-000001
    created_at : random date between 2024-01-01 and 2026-10-30
    """
    lifecycle_states = list(CUSTOMER_LIFECYCLE_WEIGHTS.keys())
    lifecycle_weights = list(CUSTOMER_LIFECYCLE_WEIGHTS.values())

    rows = []
    for i in range(1, n + 1):
        created_at = _rand_dt(rng, _EPOCH, _NOW).date()
        rows.append({
            "customer_id":     _cust_id(i),
            "name":            faker.name(),
            "email":           faker.unique.email(),
            "region":          rng.choice(REGIONS, p=REGION_WEIGHTS),
            "segment":         rng.choice(SEGMENTS, p=SEGMENT_WEIGHTS),
            "created_at":      str(created_at),
            "lifecycle_state": rng.choice(lifecycle_states, p=lifecycle_weights),
        })

    return pd.DataFrame(rows)


def generate_surveys(
    n: int,
    rng: np.random.Generator,
    faker: Faker,
    product_ids: list[str],
    channel_ids: list[str],
) -> pd.DataFrame:
    """
    Generate n Survey records.

    ID pattern  : SUR-2026-000001
    start_date  : random within Q1-Q3 2026
    end_date    : start_date + 30 to 90 days (capped at 2026-10-30)
    lifecycle   : derived from end_date vs today
    """
    lo, hi = _SURVEY_START_RANGE
    rows = []

    for i in range(1, n + 1):
        s_type  = rng.choice(SURVEY_TYPES)
        prod_id = rng.choice(product_ids)
        chan_id = rng.choice(channel_ids)

        start = _rand_dt(rng, lo, hi).date()
        duration_days = int(rng.integers(30, 91))
        end = min(
            start + timedelta(days=duration_days),
            _NOW.date(),
        )

        # Lifecycle derived from dates
        if end < _NOW.date():
            state = "closed"
        elif start <= _NOW.date():
            state = "active"
        else:
            state = "draft"

        rows.append({
            "survey_id":       _sur_id(i),
            "title":           f"{s_type} Survey — {faker.bs().title()}",
            "survey_type":     s_type,
            "product_id":      prod_id,
            "channel_id":      chan_id,
            "start_date":      str(start),
            "end_date":        str(end),
            "lifecycle_state": state,
        })

    return pd.DataFrame(rows)
