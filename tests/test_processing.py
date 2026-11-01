"""
Unit and integration tests for Module 4 (Processing).
"""

from pathlib import Path
import pytest
from sqlalchemy import text

from cfa.db.seed import get_engine, init_db, load_raw_csvs_into_db
from cfa.processing.sentiment import SentimentClassifier, update_predicted_sentiment
from cfa.processing.theme_classifier import ThemeClassifier, update_predicted_themes
from cfa.processing.pipeline import run_processing_pipeline

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def processed_test_db(tmp_path):
    """Seed a sample temporary DB for testing predictions."""
    db_file = tmp_path / "proc_test.db"
    engine = get_engine(db_file)
    init_db(engine)

    raw_dir = _PROJECT_ROOT / "data" / "raw"
    if not (raw_dir / "customers.csv").exists():
        pytest.skip("data/raw not generated yet.")

    load_raw_csvs_into_db(raw_dir, engine)
    yield engine
    engine.dispose()


def test_sentiment_classifier_predictions():
    """Verify sentiment classifier outputs valid sentiment labels, confidence, and flags sarcasm."""
    clf = SentimentClassifier(use_model=False)  # use robust fast rule-based classifier
    texts = [
        "The build quality is excellent and works flawlessly!",
        "Terrible and disappointing experience. It broke within days.",
        "It arrived on time. The packaging was okay.",
        "Oh wow, yet another product that works exactly as advertised. Five stars for effort."  # Sarcasm test
    ]
    preds = clf.predict_batch(texts)
    assert len(preds) == 4
    assert preds[0] == "positive"
    assert preds[1] == "negative"
    assert preds[2] == "neutral"
    assert preds[3] == "negative"  # correctly detected as sarcastic negative tone

    details = clf.predict_batch_with_details(texts)
    assert details[3]["is_sarcastic"] is True
    assert details[0]["confidence"] > 0.70


def test_theme_classifier_predictions():
    """Verify theme classifier maps feedback to valid taxonomy theme IDs and handles multi-theme ranking."""
    clf = ThemeClassifier(mode="keyword")
    texts = [
        "The shipping was delayed and the delivery tracking was slow.",
        "There is a billing discrepancy on my recent invoice charge.",
        "Customer service agent was rude and unhelpful on the phone. Also the shipping took weeks."
    ]
    preds = clf.predict_batch(texts)
    assert len(preds) == 3
    assert preds[0] == "THEME-000004"  # Delivery & Shipping
    assert preds[1] == "THEME-000009"  # Account & Billing
    assert preds[2] == "THEME-000002"  # Customer Service primary

    # Multi-label test
    multi = clf.predict_multi_label([texts[2]], top_k=2)
    assert len(multi[0]) == 2
    assert "THEME-000002" in multi[0]
    assert "THEME-000004" in multi[0]


def test_update_sentiment_and_theme_in_db(processed_test_db):
    """Verify that columns in the SQLite database get properly updated."""
    sentiment_clf = SentimentClassifier(use_model=False)
    theme_clf = ThemeClassifier(mode="keyword")

    sent_counts = update_predicted_sentiment(processed_test_db, sentiment_clf, batch_size=50)
    theme_counts = update_predicted_themes(processed_test_db, theme_clf, batch_size=50)

    assert sent_counts["reviews"] > 0
    assert theme_counts["reviews"] > 0

    with processed_test_db.connect() as conn:
        null_sent = conn.execute(text("SELECT count(*) FROM reviews WHERE predicted_sentiment IS NULL")).scalar()
        null_theme = conn.execute(text("SELECT count(*) FROM reviews WHERE predicted_theme IS NULL")).scalar()
        assert null_sent == 0
        assert null_theme == 0


def test_processing_pipeline_orchestration(tmp_path):
    """Verify the pipeline orchestrator executes without errors on sample data."""
    db_file = tmp_path / "pipe_test.db"
    engine = get_engine(db_file)
    init_db(engine)

    # Insert a minimal sample to test orchestration rapidly
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO customers (customer_id, name, email, region, segment, created_at, lifecycle_state)
            VALUES ('CUST-2026-000001', 'Test User', 'test@example.com', 'North', 'B2C', '2026-01-01', 'active');
        """))
        conn.execute(text("""
            INSERT INTO products (product_id, name, category)
            VALUES ('PROD-001', 'SmartHome Hub', 'Smart Home');
        """))
        conn.execute(text("""
            INSERT INTO channels (channel_id, name, type)
            VALUES ('CHAN-001', 'Website', 'digital');
        """))
        conn.execute(text("""
            INSERT INTO reviews (review_id, customer_id, product_id, channel_id, review_text, star_rating, sentiment_label, language, reviewed_at, is_ambiguous)
            VALUES ('REV-2026-000001', 'CUST-2026-000001', 'PROD-001', 'CHAN-001', 'Fast shipping and great quality product!', 5, 'positive', 'en', '2026-02-01', 0);
        """))

    res = run_processing_pipeline(db_file, cfg={"processing": {"theme_mode": "keyword"}})
    assert "sentiment_updated" in res
    assert "theme_updated" in res
    assert res["sentiment_updated"].get("reviews", 0) == 1
    assert res["theme_updated"].get("reviews", 0) == 1
