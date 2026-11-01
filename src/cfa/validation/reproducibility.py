"""
reproducibility.py — Validates deterministic seed reproducibility and checksum matching.

Runs generator data generation logic twice with the same seed in-memory,
comparing row counts and SHA-256 data checksums.
"""

from __future__ import annotations

import hashlib
import numpy as np
import pandas as pd
from faker import Faker

from cfa.generators.master_data import (
    generate_products, generate_channels, generate_themes,
    generate_sentiment_labels,
    generate_customers, generate_surveys,
)
from cfa.generators.transactions import (
    generate_reviews, generate_survey_responses,
    generate_support_tickets, generate_support_messages,
    generate_action_items,
)


def _compute_df_checksum(df: pd.DataFrame) -> str:
    """Compute a deterministic hash of a dataframe's tabular content."""
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(csv_bytes).hexdigest()


def check_seed_reproducibility(seed: int = 20261022, sample_volume: int = 100) -> dict:
    """
    Run data generation twice with the given seed.
    Returns comparison result with pass/fail status and table checksums.
    """
    cfg = {
        "generation": {
            "multilingual_ratio": 0.05,
            "ambiguous_ratio": 0.03,
            "sentiment_distribution": {"positive": 0.34, "neutral": 0.33, "negative": 0.33},
            "max_secondary_themes": 2,
        }
    }

    def _generate_pass():
        rng = np.random.default_rng(seed)
        faker = Faker()
        Faker.seed(seed)

        prods = generate_products()
        chans = generate_channels()
        themes = generate_themes()
        sents = generate_sentiment_labels()
        custs = generate_customers(sample_volume, rng, faker)
        survs = generate_surveys(5, rng, faker, prods["product_id"].tolist(), chans["channel_id"].tolist())

        revs, rev_themes = generate_reviews(sample_volume, custs, prods, chans, themes, rng, cfg)
        resps, resp_themes = generate_survey_responses(sample_volume, survs, custs, themes, rng, cfg)
        tkts = generate_support_tickets(20, custs, chans, rng)
        msgs, msg_themes = generate_support_messages(sample_volume, tkts, themes, rng, cfg)

        tables = {
            "products": prods,
            "channels": chans,
            "themes": themes,
            "sentiment_labels": sents,
            "customers": custs,
            "surveys": survs,
            "reviews": revs,
            "survey_responses": resps,
            "support_tickets": tkts,
            "support_messages": msgs,
            "review_themes": rev_themes,
            "response_themes": resp_themes,
            "message_themes": msg_themes,
        }
        return {k: (_compute_df_checksum(v), len(v)) for k, v in tables.items()}

    run1 = _generate_pass()
    run2 = _generate_pass()

    mismatches = []
    for table_name in run1:
        hash1, count1 = run1[table_name]
        hash2, count2 = run2[table_name]
        if hash1 != hash2 or count1 != count2:
            mismatches.append({
                "table": table_name,
                "run1": (count1, hash1),
                "run2": (count2, hash2),
            })

    return {
        "is_reproducible": len(mismatches) == 0,
        "seed": seed,
        "tables_checked": list(run1.keys()),
        "mismatches": mismatches,
    }
