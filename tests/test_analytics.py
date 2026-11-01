"""
Unit and integration tests for Module 5 (Analytics).
"""

from pathlib import Path
import pytest
import pandas as pd

from cfa.db.seed import get_engine, init_db, load_raw_csvs_into_db
from cfa.analytics.trend_analysis import compute_sentiment_trends, detect_sentiment_inflection_points
from cfa.analytics.theme_frequency import compute_theme_frequencies
from cfa.analytics.priority_scoring import compute_service_priorities, sync_live_action_items_from_priorities
from cfa.analytics.report import generate_analytics_reports

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def analytics_test_db(tmp_path):
    """Seed a temporary database for analytics testing."""
    db_file = tmp_path / "analytics_test.db"
    engine = get_engine(db_file)
    init_db(engine)

    raw_dir = _PROJECT_ROOT / "data" / "raw"
    if not (raw_dir / "customers.csv").exists():
        pytest.skip("data/raw not generated yet.")

    load_raw_csvs_into_db(raw_dir, engine)
    yield engine
    engine.dispose()


def test_sentiment_trends_computation(analytics_test_db):
    """Verify sentiment trends aggregation, Net Sentiment Score (NSS), and lineage traceability."""
    trends_df, lineage_df = compute_sentiment_trends(analytics_test_db, freq="W")
    assert not trends_df.empty
    assert "period" in trends_df.columns
    assert "net_sentiment_score" in trends_df.columns
    assert "total_feedback" in trends_df.columns
    assert "sample_source_record_ids" in trends_df.columns
    assert trends_df["total_feedback"].sum() > 0

    # Lineage check
    assert not lineage_df.empty
    assert "record_id" in lineage_df.columns
    assert "period" in lineage_df.columns

    # Test monthly grouping
    monthly_df, _ = compute_sentiment_trends(analytics_test_db, freq="M")
    assert not monthly_df.empty
    assert len(monthly_df) <= len(trends_df)


def test_sentiment_inflection_detection():
    """Verify inflection point detection identifies periods with significant shift."""
    mock_trends = pd.DataFrame({
        "period": ["2026-W01", "2026-W02", "2026-W03"],
        "net_sentiment_score": [10.0, 35.0, 30.0],  # +25 jump between W01 and W02
    })
    inflections = detect_sentiment_inflection_points(mock_trends, threshold=15.0)
    assert len(inflections) == 1
    assert inflections.iloc[0]["period"] == "2026-W02"
    assert inflections.iloc[0]["nss_change"] == 25.0


def test_theme_frequency_computation(analytics_test_db):
    """Verify theme occurrences and percentage shares across feedback sources."""
    freq_df = compute_theme_frequencies(analytics_test_db)
    assert not freq_df.empty
    assert len(freq_df) == 15  # All 15 taxonomy themes present
    assert "percentage_share" in freq_df.columns
    assert "total_count" in freq_df.columns

    # Percentage shares must sum to ~100%
    assert abs(freq_df["percentage_share"].sum() - 100.0) < 0.5


def test_service_priorities_computation(analytics_test_db):
    """Verify priority score ranking and urgency assignment."""
    prio_df = compute_service_priorities(analytics_test_db)
    assert not prio_df.empty
    assert len(prio_df) == 15
    assert "priority_score" in prio_df.columns
    assert "priority_rank" in prio_df.columns
    assert "recommended_urgency" in prio_df.columns

    # Ranks should be 1 through 15 in descending order of priority_score
    assert prio_df["priority_rank"].tolist() == list(range(1, 16))
    assert prio_df["priority_score"].is_monotonic_decreasing

    # Top items should have Critical or High urgency
    assert prio_df.iloc[0]["recommended_urgency"] in ["Critical", "High"]


def test_analytics_report_generation(analytics_test_db, tmp_path):
    """Verify end-to-end report exporter generates all required CSV files."""
    db_file = tmp_path / "report_test.db"
    engine = get_engine(db_file)
    init_db(engine)
    data_dir = _PROJECT_ROOT / "data" / "validated"
    if not (data_dir / "customers.csv").exists():
        data_dir = _PROJECT_ROOT / "data" / "raw"
    load_raw_csvs_into_db(data_dir, engine)

    out_dir = tmp_path / "outcomes_out"
    reports = generate_analytics_reports(db_file, output_dir=out_dir)

    assert (out_dir / "sentiment_shifts.csv").exists()
    assert (out_dir / "sentiment_shifts_lineage.csv").exists()
    assert (out_dir / "recurring_themes.csv").exists()
    assert (out_dir / "service_priorities.csv").exists()
    assert (out_dir / "analytics_summary.md").exists()
    assert "sentiment_shifts" in reports
    assert "sentiment_shifts_lineage" in reports
    assert "recurring_themes" in reports
    assert "service_priorities" in reports


def test_product_filtered_sentiment_trends(analytics_test_db):
    """Verify sentiment trends can be filtered by product_id."""
    trends_df, lineage_df = compute_sentiment_trends(analytics_test_db, freq="W", product_id="PROD-001")
    if not trends_df.empty:
        assert all(lineage_df["product_id"] == "PROD-001")


def test_sync_live_action_items(analytics_test_db):
    """Verify live action items are created from priorities and synced to DB."""
    prio_df = compute_service_priorities(analytics_test_db)
    actions = sync_live_action_items_from_priorities(analytics_test_db, prio_df, threshold=1)
    assert not actions.empty
    assert "action_id" in actions.columns
    assert "priority" in actions.columns
