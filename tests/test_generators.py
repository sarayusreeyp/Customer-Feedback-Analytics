"""
Unit and integration tests for Module 1 (Generators).
"""

from __future__ import annotations

import re
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from faker import Faker

from cfa.generators.schema import (
    PRODUCTS, CHANNELS, THEMES,
    REGIONS, SEGMENTS, LIFECYCLE_STATES,
    STAR_TO_SENTIMENT, response_rating_to_sentiment,
    ANOMALY_TYPES,
)
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
from cfa.generators.anomalies import (
    generate_review_anomalies, generate_response_anomalies,
    generate_message_anomalies, build_ground_truth,
)
from cfa.generators.generator import run, load_config

_SEED = 20261022


@pytest.fixture
def test_cfg():
    return {
        "seed": _SEED,
        "scale": "starter",
        "volumes": {
            "starter": {
                "customers": 50,
                "surveys": 5,
                "reviews": 100,
                "survey_responses": 100,
                "support_tickets": 20,
                "support_messages": 80,
                "anomalies_per_type": 20,
            }
        },
        "generation": {
            "multilingual_ratio": 0.05,
            "ambiguous_ratio": 0.03,
            "sentiment_distribution": {
                "positive": 0.34,
                "neutral": 0.33,
                "negative": 0.33,
            },
            "max_secondary_themes": 2,
        },
        "action_items": {
            "threshold_starter": 10,
        },
        "paths": {
            "raw_dir": "data/raw",
            "validated_dir": "data/validated",
            "excluded_dir": "data/excluded_anomalies",
            "evaluation_dir": "data/evaluation",
            "ground_truth_dir": "data/ground_truth",
            "db_file": "data/db/feedback.db",
        },
    }


def test_master_data_generation(test_cfg):
    rng = np.random.default_rng(_SEED)
    faker = Faker()
    Faker.seed(_SEED)

    prods = generate_products()
    assert len(prods) == 20
    assert prods["product_id"].nunique() == 20
    assert all(re.match(r"^PROD-\d{3}$", pid) for pid in prods["product_id"])

    chans = generate_channels()
    assert len(chans) == 6
    assert chans["channel_id"].nunique() == 6

    themes = generate_themes()
    assert len(themes) == 15
    assert themes["theme_id"].nunique() == 15

    sents = generate_sentiment_labels()
    assert len(sents) == 3
    assert sents["sentiment_id"].nunique() == 3
    assert set(sents["sentiment_label"]) == {"positive", "neutral", "negative"}

    custs = generate_customers(test_cfg["volumes"]["starter"]["customers"], rng, faker)
    assert len(custs) == 50
    assert custs["customer_id"].nunique() == 50
    assert all(re.match(r"^CUST-\d{4}-\d{6}$", cid) for cid in custs["customer_id"])
    assert custs["region"].isin(REGIONS).all()
    assert custs["segment"].isin(SEGMENTS).all()
    assert custs["lifecycle_state"].isin(LIFECYCLE_STATES).all()

    surveys = generate_surveys(
        test_cfg["volumes"]["starter"]["surveys"],
        rng, faker,
        prods["product_id"].tolist(),
        chans["channel_id"].tolist(),
    )
    assert len(surveys) == 5
    assert surveys["survey_id"].nunique() == 5
    assert all(re.match(r"^SUR-\d{4}-\d{6}$", sid) for sid in surveys["survey_id"])
    assert surveys["product_id"].isin(prods["product_id"]).all()
    assert surveys["channel_id"].isin(chans["channel_id"]).all()


def test_transactions_generation_and_sentiment_rules(test_cfg):
    rng = np.random.default_rng(_SEED)
    faker = Faker()
    Faker.seed(_SEED)

    prods = generate_products()
    chans = generate_channels()
    themes = generate_themes()
    custs = generate_customers(50, rng, faker)
    surveys = generate_surveys(5, rng, faker, prods["product_id"].tolist(), chans["channel_id"].tolist())

    # Reviews
    revs, rev_themes = generate_reviews(100, custs, prods, chans, themes, rng, test_cfg)
    assert len(revs) == 100
    assert revs["review_id"].nunique() == 100
    assert all(re.match(r"^REV-\d{4}-\d{6}$", rid) for rid in revs["review_id"])
    # Derived sentiment rule check
    for _, r in revs.iterrows():
        assert r["sentiment_label"] == STAR_TO_SENTIMENT[r["star_rating"]]
    assert revs["customer_id"].isin(custs["customer_id"]).all()
    assert revs["product_id"].isin(prods["product_id"]).all()
    assert revs["channel_id"].isin(chans["channel_id"]).all()
    assert not rev_themes.empty
    assert rev_themes["theme_id"].isin(themes["theme_id"]).all()

    # Survey Responses
    resps, resp_themes = generate_survey_responses(100, surveys, custs, themes, rng, test_cfg)
    assert len(resps) == 100
    for _, r in resps.iterrows():
        assert r["sentiment_label"] == response_rating_to_sentiment(r["rating"])
    assert resps["survey_id"].isin(surveys["survey_id"]).all()
    assert resps["customer_id"].isin(custs["customer_id"]).all()

    # Tickets & Messages
    tkts = generate_support_tickets(20, custs, chans, rng)
    assert len(tkts) == 20
    assert tkts["ticket_id"].nunique() == 20

    msgs, msg_themes = generate_support_messages(80, tkts, themes, rng, test_cfg)
    assert len(msgs) == 80
    assert msgs["ticket_id"].isin(tkts["ticket_id"]).all()
    assert msgs["sender_type"].isin(["customer", "agent"]).all()


def test_anomalies_and_ground_truth(test_cfg):
    rng = np.random.default_rng(_SEED)
    faker = Faker()
    Faker.seed(_SEED)

    prods = generate_products()
    chans = generate_channels()
    themes = generate_themes()
    custs = generate_customers(50, rng, faker)
    surveys = generate_surveys(5, rng, faker, prods["product_id"].tolist(), chans["channel_id"].tolist())
    revs, rev_themes = generate_reviews(50, custs, prods, chans, themes, rng, test_cfg)
    resps, resp_themes = generate_survey_responses(50, surveys, custs, themes, rng, test_cfg)
    tkts = generate_support_tickets(10, custs, chans, rng)
    msgs, msg_themes = generate_support_messages(50, tkts, themes, rng, test_cfg)

    rev_anom, rev_gt = generate_review_anomalies(20, revs, rng, faker, rev_themes, id_offset=50)
    resp_anom, resp_gt = generate_response_anomalies(20, resps, rng, faker, resp_themes)
    msg_anom, msg_gt = generate_message_anomalies(20, msgs, rng, faker, msg_themes)
    gt = build_ground_truth(rev_gt, resp_gt, msg_gt)

    assert "issue_type" in rev_anom.columns
    assert "issue_type" in resp_anom.columns
    assert "issue_type" in msg_anom.columns

    # Check clean raw tables have NO issue_type
    assert "issue_type" not in revs.columns
    assert "issue_type" not in resps.columns
    assert "issue_type" not in msgs.columns

    # Verify ground truth structure
    assert len(gt) == len(rev_anom) + len(resp_anom) + len(msg_anom)
    assert set(gt["issue_type"].unique()).issubset(set(ANOMALY_TYPES))
    assert "record_id" in gt.columns
    assert "correct_sentiment_label" in gt.columns


def test_action_items_generation():
    theme_counts = {
        "THEME-000001": 150,
        "THEME-000002": 80,
        "THEME-000003": 10,
    }
    threshold = 50
    rng = np.random.default_rng(_SEED)
    actions = generate_action_items(theme_counts, threshold, rng)

    # 10 is below threshold, so 2 action items generated
    assert len(actions) == 2
    assert "THEME-000001" in actions["theme_id"].values
    assert "THEME-000002" in actions["theme_id"].values
    assert "THEME-000003" not in actions["theme_id"].values
    
    # Check priority derivation
    row_1 = actions[actions["theme_id"] == "THEME-000001"].iloc[0]
    assert row_1["priority"] == "high"  # 150 >= 3*50
    row_2 = actions[actions["theme_id"] == "THEME-000002"].iloc[0]
    assert row_2["priority"] == "low"   # 80 < 2*50


def test_generator_module1_workflow(tmp_path, test_cfg):
    """Test full Module 1 generation, appending to raw, validation separation, and evaluation dataset."""
    cfg = test_cfg.copy()
    cfg["paths"] = {
        "raw_dir": str(tmp_path / "raw"),
        "validated_dir": str(tmp_path / "validated"),
        "excluded_dir": str(tmp_path / "excluded_anomalies"),
        "ground_truth_dir": str(tmp_path / "ground_truth"),
        "evaluation_dir": str(tmp_path / "evaluation"),
    }
    written = run(cfg)

    # 1. Verify raw data has normal + anomalies appended WITHOUT issue_type
    raw_rev = pd.read_csv(written["raw_reviews"])
    assert "issue_type" not in raw_rev.columns
    # Total raw reviews = 100 normal + 20 anomalies = 120
    assert len(raw_rev) == 120

    # 2. Verify validated data has only clean records
    val_rev = pd.read_csv(written["val_reviews"])
    assert len(val_rev) == 100
    assert "issue_type" not in val_rev.columns

    # 3. Verify excluded anomalies file exists and records excluded items
    excl_rev = pd.read_csv(written["excluded_reviews"])
    assert len(excl_rev) == 20
    assert "exclusion_reason" in excl_rev.columns

    # 4. Verify ground_truth directory has anomaly files with issue_type
    gt_rev = pd.read_csv(written["gt_reviews_anomalies"])
    assert "issue_type" in gt_rev.columns
    assert len(gt_rev) == 20

    # 5. Verify synthetic human-reviewed labeled dataset
    eval_df = pd.read_csv(written["human_reviewed_eval"])
    assert not eval_df.empty
    assert "sample_id" in eval_df.columns
    assert "ground_truth_sentiment" in eval_df.columns
    assert "ground_truth_theme_id" in eval_df.columns
    assert "review_status" in eval_df.columns
    assert (eval_df["review_status"] == "human_verified").all()

