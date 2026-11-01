"""
ground_truth.py — Load, join ground truth labels, and evaluate anomaly quarantine gates.

Features:
  - Loads ground_truth.csv from data/ground_truth/
  - Matches excluded anomalies from the validation gate against ground truth to calculate detection recall.
  - Keeps ground truth strictly separate from model inference features (no data leakage).
"""

from __future__ import annotations

import pandas as pd
from pathlib import Path
from sqlalchemy import text


def load_ground_truth(gt_path: Path | str) -> pd.DataFrame:
    """Load the ground truth index CSV."""
    gt_path = Path(gt_path)
    if not gt_path.exists():
        raise FileNotFoundError(f"Ground truth file not found at: {gt_path}")
    return pd.read_csv(gt_path)


def compute_anomaly_detection_metrics(
    gt_path: Path | str,
    excluded_path: Path | str
) -> pd.DataFrame:
    """
    Evaluates how effectively the Module 2 validation gate quarantined injected anomalies.
    Compares data/ground_truth/ground_truth.csv with data/excluded_anomalies/all_excluded_anomalies.csv.
    Returns DataFrame: [issue_type, total_injected, total_quarantined, detection_recall]
    """
    gt_df = load_ground_truth(gt_path)
    excl_path = Path(excluded_path)

    if not excl_path.exists():
        empty_res = []
        for itype in gt_df["issue_type"].unique():
            cnt = len(gt_df[gt_df["issue_type"] == itype])
            empty_res.append({
                "issue_type": itype,
                "total_injected": cnt,
                "total_quarantined": 0,
                "detection_recall": 0.0,
            })
        return pd.DataFrame(empty_res)

    excl_df = pd.read_csv(excl_path)
    quarantined_ids = set(excl_df["record_id"].dropna().unique())

    gt_df["was_quarantined"] = gt_df["record_id"].isin(quarantined_ids)

    rows = []
    for itype, group in gt_df.groupby("issue_type"):
        total_inj = len(group)
        total_quar = int(group["was_quarantined"].sum())
        recall = round(total_quar / total_inj, 4) if total_inj > 0 else 0.0
        rows.append({
            "issue_type": itype,
            "total_injected": total_inj,
            "total_quarantined": total_quar,
            "detection_recall": recall,
        })

    # Overall summary row
    overall_inj = len(gt_df)
    overall_quar = int(gt_df["was_quarantined"].sum())
    overall_recall = round(overall_quar / overall_inj, 4) if overall_inj > 0 else 0.0
    rows.append({
        "issue_type": "OVERALL",
        "total_injected": overall_inj,
        "total_quarantined": overall_quar,
        "detection_recall": overall_recall,
    })

    return pd.DataFrame(rows)


def get_evaluation_dataset(engine, gt_df: pd.DataFrame) -> pd.DataFrame:
    """
    Joins ground truth records with predicted values from the database.
    Also queries clean records to evaluate baseline model accuracy.
    Returns DataFrame: [record_id, entity_type, issue_type, true_sentiment,
                        predicted_sentiment, true_theme, predicted_theme, is_anomaly]
    """
    with engine.connect() as conn:
        q_rev = """
            SELECT review_id as record_id, 'review' as entity_type,
                   sentiment_label as true_sentiment, predicted_sentiment,
                   predicted_theme
            FROM reviews
        """
        q_resp = """
            SELECT response_id as record_id, 'survey_response' as entity_type,
                   sentiment_label as true_sentiment, predicted_sentiment,
                   predicted_theme
            FROM survey_responses
        """
        q_msg = """
            SELECT message_id as record_id, 'support_message' as entity_type,
                   sentiment_label as true_sentiment, predicted_sentiment,
                   predicted_theme
            FROM support_messages
        """
        df_rev = pd.read_sql(text(q_rev), conn)
        df_resp = pd.read_sql(text(q_resp), conn)
        df_msg = pd.read_sql(text(q_msg), conn)

    db_records = pd.concat([df_rev, df_resp, df_msg], ignore_index=True)

    # Clean records baseline
    clean_eval = db_records.copy()
    clean_eval["issue_type"] = "clean"
    clean_eval["is_anomaly"] = False
    clean_eval["true_theme"] = None

    # Merge anomalies from ground_truth.csv
    anom_eval = gt_df.copy()
    anom_eval = anom_eval.rename(columns={
        "correct_sentiment_label": "true_sentiment",
        "correct_theme_id": "true_theme",
    })
    anom_eval["is_anomaly"] = True

    merged_anom = pd.merge(
        anom_eval,
        db_records[["record_id", "predicted_sentiment", "predicted_theme"]],
        on="record_id",
        how="left"
    )

    combined = pd.concat([
        clean_eval,
        merged_anom[["record_id", "entity_type", "issue_type", "true_sentiment",
                     "predicted_sentiment", "true_theme", "predicted_theme", "is_anomaly"]]
    ], ignore_index=True)

    return combined
