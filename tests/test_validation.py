"""
Unit and integration tests for Module 3 (Validation).
"""

from pathlib import Path
import pytest
from sqlalchemy import text

from cfa.db.seed import get_engine, init_db, load_raw_csvs_into_db
from cfa.validation.pk_fk_checks import check_pk_uniqueness, check_fk_integrity
from cfa.validation.enum_checks import (
    check_allowed_enums,
    check_derived_rules_reconciliation,
    check_date_ordering,
    check_lifecycle_consistency,
    check_database_duplicates,
)
from cfa.validation.reproducibility import check_seed_reproducibility

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def seeded_db(tmp_path):
    """Create and seed a temporary database from validated clean data."""
    db_file = tmp_path / "val_feedback.db"
    engine = get_engine(db_file)
    init_db(engine)
    data_dir = _PROJECT_ROOT / "data" / "validated"
    if not (data_dir / "customers.csv").exists():
        data_dir = _PROJECT_ROOT / "data" / "raw"
    if not (data_dir / "customers.csv").exists():
        pytest.skip("data not populated yet.")
    load_raw_csvs_into_db(data_dir, engine)
    yield engine
    engine.dispose()


def test_validation_pk_uniqueness(seeded_db):
    """PK checks should pass on valid database."""
    violations = check_pk_uniqueness(seeded_db)
    assert violations == []


def test_validation_fk_integrity(seeded_db):
    """FK checks should pass on valid database."""
    violations = check_fk_integrity(seeded_db)
    assert violations == []


def test_validation_enum_and_patterns(seeded_db):
    """Enum and regex pattern checks should pass."""
    violations = check_allowed_enums(seeded_db)
    assert violations == []


def test_validation_derived_rules(seeded_db):
    """Derived rules (star/rating -> sentiment_label and arithmetic counts) must reconcile."""
    violations = check_derived_rules_reconciliation(seeded_db)
    assert violations == []


def test_validation_date_ordering(seeded_db):
    """Date ordering and temporal sequences must pass on clean data."""
    violations = check_date_ordering(seeded_db)
    assert violations == []


def test_validation_lifecycle_consistency(seeded_db):
    """Lifecycle states must pass on clean data."""
    violations = check_lifecycle_consistency(seeded_db)
    assert violations == []


def test_validation_database_duplicates(seeded_db):
    """Clean database must have no duplicate submissions."""
    violations = check_database_duplicates(seeded_db)
    assert violations == []


def test_validation_reproducibility():
    """Reproducibility test should pass when executed with same seed."""
    result = check_seed_reproducibility(seed=20261022, sample_volume=50)
    assert result["is_reproducible"] is True
    assert result["mismatches"] == []


def test_validation_detects_deliberate_fk_violation(seeded_db):
    """Verify that validation correctly flags a simulated corruption."""
    with seeded_db.begin() as conn:
        # Temporarily disable foreign keys to inject an orphan row
        conn.execute(text("PRAGMA foreign_keys = OFF;"))
        conn.execute(text("""
            INSERT INTO reviews (
                review_id, customer_id, product_id, channel_id,
                review_text, star_rating, sentiment_label, language, reviewed_at, is_ambiguous
            ) VALUES (
                'REV-9999-999999', 'NON_EXISTENT_CUST', 'PROD-001', 'CHAN-001',
                'Fake review', 5, 'positive', 'en', '2026-10-30', 0
            )
        """))

    violations = check_fk_integrity(seeded_db)
    assert len(violations) > 0
    assert any(v.get("child_table") == "reviews" or v.get("table") == "reviews" for v in violations)
