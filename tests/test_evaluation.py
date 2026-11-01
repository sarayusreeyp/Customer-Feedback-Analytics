"""
Unit and integration tests for Module 6 (Evaluation).
"""

from pathlib import Path
import pytest
import pandas as pd

from cfa.db.seed import get_engine, init_db, load_raw_csvs_into_db
from cfa.evaluation.ground_truth import (
    load_ground_truth,
    get_evaluation_dataset,
    compute_anomaly_detection_metrics,
)
from cfa.evaluation.metrics import (
    compute_sentiment_classification_metrics,
    compute_theme_multilabel_metrics,
    run_evaluation
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def eval_test_db(tmp_path):
    """Seed a temporary database for evaluation testing."""
    db_file = tmp_path / "eval_test.db"
    engine = get_engine(db_file)
    init_db(engine)

    data_dir = _PROJECT_ROOT / "data" / "validated"
    if not (data_dir / "customers.csv").exists():
        data_dir = _PROJECT_ROOT / "data" / "raw"
    if not (data_dir / "customers.csv").exists():
        pytest.skip("data not generated yet.")

    load_raw_csvs_into_db(data_dir, engine)
    yield engine
    engine.dispose()


def test_load_ground_truth():
    """Verify ground truth file loads properly."""
    gt_path = _PROJECT_ROOT / "data" / "ground_truth" / "ground_truth.csv"
    if not gt_path.exists():
        pytest.skip("data/ground_truth/ground_truth.csv not generated yet.")

    df = load_ground_truth(gt_path)
    assert not df.empty
    assert "record_id" in df.columns
    assert "issue_type" in df.columns
    assert "correct_sentiment_label" in df.columns


def test_get_evaluation_dataset(eval_test_db):
    """Verify combining DB predictions and ground truth records."""
    gt_path = _PROJECT_ROOT / "data" / "ground_truth" / "ground_truth.csv"
    if not gt_path.exists():
        pytest.skip("data/ground_truth/ground_truth.csv not generated.")

    gt_df = load_ground_truth(gt_path)
    eval_df = get_evaluation_dataset(eval_test_db, gt_df)

    assert not eval_df.empty
    assert "true_sentiment" in eval_df.columns
    assert "predicted_sentiment" in eval_df.columns
    assert "is_anomaly" in eval_df.columns

    # Contains both clean baseline and anomaly subsets
    assert (eval_df["is_anomaly"] == False).sum() > 0
    assert (eval_df["is_anomaly"] == True).sum() > 0


def test_calculate_sentiment_metrics():
    """Verify accuracy, precision, recall, and macro F1 calculations."""
    y_true = pd.Series(["positive", "positive", "negative", "neutral"])
    y_pred = pd.Series(["positive", "negative", "negative", "neutral"])
    metrics = compute_sentiment_classification_metrics(y_true, y_pred)
    assert metrics["sample_count"] == 4
    assert metrics["accuracy"] == 0.75
    assert metrics["precision"] > 0.0
    assert metrics["recall"] > 0.0
    assert metrics["macro_f1"] > 0.0


def test_calculate_theme_multilabel_metrics():
    """Verify multi-label precision, recall, and F1 calculations for themes."""
    true_themes = [["THEME-000001", "THEME-000002"], ["THEME-000003"], ["THEME-000004"]]
    pred_themes = [["THEME-000001"], ["THEME-000003"], ["THEME-000005"]]
    metrics = compute_theme_multilabel_metrics(true_themes, pred_themes)
    assert metrics["sample_count"] == 3
    assert "multi_label_precision_macro" in metrics
    assert "multi_label_recall_macro" in metrics
    assert "multi_label_f1_macro" in metrics
    assert metrics["multi_label_precision_macro"] > 0.0


def test_run_evaluation_end_to_end(eval_test_db, tmp_path):
    """Verify evaluation runner exports model_evaluation_report.csv, .md, and data_evaluation_report.csv."""
    eval_path = _PROJECT_ROOT / "data" / "evaluation" / "human_reviewed_eval.csv"
    if not eval_path.exists():
        pytest.skip("data/evaluation/human_reviewed_eval.csv not generated.")

    out_dir = tmp_path / "eval_out"
    db_file = tmp_path / "eval_end_to_end.db"
    engine = get_engine(db_file)
    init_db(engine)
    data_dir = _PROJECT_ROOT / "data" / "validated"
    if not (data_dir / "customers.csv").exists():
        data_dir = _PROJECT_ROOT / "data" / "raw"
    load_raw_csvs_into_db(data_dir, engine)

    results_df, anom_df = run_evaluation(db_file, eval_path=eval_path, out_dir=out_dir)
    assert (out_dir / "model_evaluation_report.csv").exists()
    assert (out_dir / "model_evaluation_report.md").exists()
    assert not results_df.empty
    assert "sentiment_accuracy" in results_df.columns
    assert "theme_precision_multilabel" in results_df.columns
    assert "theme_recall_multilabel" in results_df.columns
    assert "theme_f1_multilabel" in results_df.columns

    from cfa.evaluation.data_audit import run_data_evaluation
    data_eval_results = run_data_evaluation(engine, _PROJECT_ROOT, out_dir=out_dir)
    assert (out_dir / "data_evaluation_report.csv").exists()
    assert (out_dir / "data_evaluation_report.md").exists()
    assert not data_eval_results.empty
    assert (data_eval_results["status"] == "PASS").all()


def test_anomaly_detection_metrics_evaluation():
    """Verify compute_anomaly_detection_metrics calculates recall properly."""
    gt_path = _PROJECT_ROOT / "data" / "ground_truth" / "ground_truth.csv"
    excl_path = _PROJECT_ROOT / "data" / "excluded_anomalies" / "all_excluded_anomalies.csv"
    if not gt_path.exists() or not excl_path.exists():
        pytest.skip("ground truth or excluded anomalies not generated.")

    anom_df = compute_anomaly_detection_metrics(gt_path, excl_path)
    assert not anom_df.empty
    assert "issue_type" in anom_df.columns
    assert "detection_recall" in anom_df.columns
    assert "total_injected" in anom_df.columns
    assert (anom_df["detection_recall"] >= 0.0).all()
