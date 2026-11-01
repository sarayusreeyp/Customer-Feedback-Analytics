"""
Unit and integration tests for Module 2 (Database).
"""

import os
from pathlib import Path
import pytest
from sqlalchemy import text, inspect

from cfa.db.models import metadata
from cfa.db.seed import get_engine, init_db, load_raw_csvs_into_db
from cfa.db.queries import (
    get_all_unprocessed_texts,
    get_theme_mention_counts,
    get_sentiment_trends_by_product
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def temp_db(tmp_path):
    """Create a fresh temporary SQLite database for testing."""
    db_file = tmp_path / "test_feedback.db"
    engine = get_engine(db_file)
    init_db(engine)
    yield engine
    engine.dispose()


def test_schema_creation(temp_db):
    """Verify all tables and foreign keys are created properly."""
    inspector = inspect(temp_db)
    table_names = inspector.get_table_names()

    expected_tables = {
        "customers", "products", "channels", "themes", "sentiment_labels", "surveys",
        "reviews", "survey_responses", "support_tickets", "support_messages",
        "action_items", "status_history", "review_themes", "response_themes", "message_themes"
    }

    assert expected_tables.issubset(set(table_names))

    # Verify foreign key existence on reviews
    fks = inspector.get_foreign_keys("reviews")
    referred_tables = {fk["referred_table"] for fk in fks}
    assert {"customers", "products", "channels"}.issubset(referred_tables)


def test_seed_from_raw_csvs(temp_db):
    """Test loading data into database."""
    data_dir = _PROJECT_ROOT / "data" / "validated"
    if not (data_dir / "customers.csv").exists():
        data_dir = _PROJECT_ROOT / "data" / "raw"
    if not (data_dir / "customers.csv").exists():
        pytest.skip("Data CSV files not generated yet. Run generator first.")

    counts = load_raw_csvs_into_db(data_dir, temp_db)

    assert counts.get("customers", 0) > 0
    assert counts.get("products", 0) == 20
    assert counts.get("channels", 0) == 6
    assert counts.get("themes", 0) == 15
    assert counts.get("reviews", 0) > 0
    assert counts.get("review_themes", 0) > 0

    with temp_db.connect() as conn:
        res = conn.execute(text("SELECT count(*) FROM reviews")).scalar()
        assert res == counts["reviews"]


def test_query_helpers(temp_db):
    """Test queries against seeded database."""
    data_dir = _PROJECT_ROOT / "data" / "validated"
    if not (data_dir / "customers.csv").exists():
        data_dir = _PROJECT_ROOT / "data" / "raw"
    if not (data_dir / "customers.csv").exists():
        pytest.skip("Data CSV files not generated yet.")

    load_raw_csvs_into_db(data_dir, temp_db)

    with temp_db.connect() as conn:
        texts = get_all_unprocessed_texts(conn, limit=10)
        assert len(texts["reviews"]) == 10
        assert "review_text" in texts["reviews"].columns

        theme_counts = get_theme_mention_counts(conn)
        assert not theme_counts.empty
        assert "total_count" in theme_counts.columns
        assert theme_counts["total_count"].sum() > 0

        product_trends = get_sentiment_trends_by_product(conn)
        assert not product_trends.empty
        assert "product_name" in product_trends.columns
