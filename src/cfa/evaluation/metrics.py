"""
metrics.py — Compute evaluation metrics (Sentiment: Accuracy, Precision, Recall, Macro-F1;
Themes: Multi-label Precision, Recall, F1) evaluated directly against the human-reviewed benchmark,
and Anomaly Detection Recall against ground truth exceptions.

Outputs written to reports/:
  - reports/model_evaluation_report.csv
  - reports/model_evaluation_report.md
  - reports/anomaly_detection_report.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import pandas as pd
from sqlalchemy import text
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.preprocessing import MultiLabelBinarizer

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from cfa.db.seed import get_engine
from cfa.generators.schema import THEMES
from cfa.evaluation.ground_truth import compute_anomaly_detection_metrics


def compute_sentiment_classification_metrics(y_true: pd.Series, y_pred: pd.Series) -> dict:
    """Compute accuracy, macro precision, macro recall, and macro F1 for sentiment."""
    mask = y_true.notna() & y_pred.notna()
    if not mask.any():
        return {
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "macro_f1": 0.0,
            "sample_count": 0,
        }

    yt = y_true[mask].astype(str)
    yp = y_pred[mask].astype(str)

    acc = accuracy_score(yt, yp)
    p_mac, r_mac, f1_mac, _ = precision_recall_fscore_support(
        yt, yp, average="macro", zero_division=0
    )

    return {
        "accuracy": round(float(acc), 4),
        "precision": round(float(p_mac), 4),
        "recall": round(float(r_mac), 4),
        "macro_f1": round(float(f1_mac), 4),
        "sample_count": int(len(yt)),
    }


def compute_theme_multilabel_metrics(
    true_theme_lists: list[list[str]],
    pred_theme_lists: list[list[str]],
) -> dict:
    """
    Compute multi-label precision, recall, and F1 across the full 15-theme taxonomy.
    Computes both macro-averaged and micro-averaged metrics.
    """
    all_theme_ids = [t["theme_id"] for t in THEMES]
    mlb = MultiLabelBinarizer(classes=all_theme_ids)

    y_true = mlb.fit_transform(true_theme_lists)
    y_pred = mlb.transform(pred_theme_lists)

    # Macro metrics
    p_mac, r_mac, f1_mac, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )
    # Micro metrics
    p_mic, r_mic, f1_mic, _ = precision_recall_fscore_support(
        y_true, y_pred, average="micro", zero_division=0
    )

    return {
        "multi_label_precision_macro": round(float(p_mac), 4),
        "multi_label_recall_macro": round(float(r_mac), 4),
        "multi_label_f1_macro": round(float(f1_mac), 4),
        "multi_label_precision_micro": round(float(p_mic), 4),
        "multi_label_recall_micro": round(float(r_mic), 4),
        "multi_label_f1_micro": round(float(f1_mic), 4),
        "sample_count": len(true_theme_lists),
    }


def evaluate_human_reviewed_benchmark(
    engine,
    eval_csv_path: Path | str,
) -> tuple[pd.DataFrame, dict]:
    """
    Evaluates model predictions against the synthetic human-reviewed labeled dataset (human_reviewed_eval.csv).
    Produces detailed breakdowns:
      - All human-reviewed records
      - By ambiguity (Clear vs Sarcastic/Ambiguous)
      - By language (English vs Multilingual)
    """
    eval_csv_path = Path(eval_csv_path)
    if not eval_csv_path.exists():
        raise FileNotFoundError(f"Human-reviewed evaluation dataset not found at: {eval_csv_path}")

    eval_df = pd.read_csv(eval_csv_path)

    with engine.connect() as conn:
        rev_preds = pd.read_sql(
            text("SELECT review_id, predicted_sentiment, predicted_theme FROM reviews"), conn
        )
        rev_themes = pd.read_sql(
            text("SELECT review_id, theme_id FROM review_themes"), conn
        )

    # Build true multi-label theme list per review
    true_themes_map = rev_themes.groupby("review_id")["theme_id"].apply(list).to_dict()

    merged = pd.merge(
        eval_df, rev_preds, left_on="source_record_id", right_on="review_id", how="inner"
    )
    merged["true_theme_list"] = merged["source_record_id"].map(true_themes_map).apply(
        lambda x: x if isinstance(x, list) else []
    )
    merged["pred_theme_list"] = merged["predicted_theme"].apply(
        lambda x: [x] if pd.notna(x) and x else []
    )

    # Subsets to evaluate on human-reviewed benchmark
    subsets = {
        "all_human_reviewed": merged,
        "clear_records": merged[~merged["is_ambiguous"]],
        "ambiguous_or_sarcastic": merged[merged["is_ambiguous"]],
        "english_language": merged[merged["language"] == "en"],
        "multilingual": merged[merged["language"] != "en"],
    }

    report_rows = []
    for sub_name, df_sub in subsets.items():
        if df_sub.empty:
            continue

        sent_m = compute_sentiment_classification_metrics(
            df_sub["ground_truth_sentiment"], df_sub["predicted_sentiment"]
        )
        theme_m = compute_theme_multilabel_metrics(
            df_sub["true_theme_list"].tolist(), df_sub["pred_theme_list"].tolist()
        )

        report_rows.append({
            "subset": sub_name,
            "sample_count": sent_m["sample_count"],
            "sentiment_accuracy": sent_m["accuracy"],
            "sentiment_precision_macro": sent_m["precision"],
            "sentiment_recall_macro": sent_m["recall"],
            "sentiment_macro_f1": sent_m["macro_f1"],
            "theme_precision_multilabel": theme_m["multi_label_precision_macro"],
            "theme_recall_multilabel": theme_m["multi_label_recall_macro"],
            "theme_f1_multilabel": theme_m["multi_label_f1_macro"],
            "theme_f1_micro": theme_m["multi_label_f1_micro"],
        })

    results_df = pd.DataFrame(report_rows)
    return results_df, {
        "total_evaluated": len(merged),
        "source_dataset": str(eval_csv_path),
    }


def run_evaluation(
    db_path: Path | str,
    eval_path: Path | str = "data/evaluation/human_reviewed_eval.csv",
    gt_path: Path | str = "data/ground_truth/ground_truth.csv",
    excl_path: Path | str = "data/excluded_anomalies/all_excluded_anomalies.csv",
    out_dir: Path | str = "reports",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run model evaluation against the human-reviewed benchmark dataset
    and evaluate anomaly detection recall against ground truth exceptions.
    Saves:
      - reports/model_evaluation_report.csv
      - reports/model_evaluation_report.md
      - reports/anomaly_detection_report.csv
    """
    db_path = Path(db_path)
    eval_path = _PROJECT_ROOT / eval_path if not Path(eval_path).is_absolute() else Path(eval_path)
    gt_path = _PROJECT_ROOT / gt_path if not Path(gt_path).is_absolute() else Path(gt_path)
    excl_path = _PROJECT_ROOT / excl_path if not Path(excl_path).is_absolute() else Path(excl_path)
    out_dir = _PROJECT_ROOT / out_dir if not Path(out_dir).is_absolute() else Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    engine = get_engine(db_path)

    print(f"\n{'='*75}")
    print("  MODEL & SYSTEM EVALUATION REPORT")
    print(f"  Target DB: {db_path}")
    print(f"  Benchmark Dataset: {eval_path}")
    print(f"  Ground Truth Anomaly Index: {gt_path}")
    print(f"{'='*75}\n")

    # 1. Model Evaluation on Human Benchmark
    results_df, meta = evaluate_human_reviewed_benchmark(engine, eval_path)

    out_csv = out_dir / "model_evaluation_report.csv"
    results_df.to_csv(out_csv, index=False)

    # 2. Anomaly Detection Recall Evaluation
    anom_df = pd.DataFrame()
    if gt_path.exists():
        anom_df = compute_anomaly_detection_metrics(gt_path, excl_path)
        anom_csv = out_dir / "anomaly_detection_report.csv"
        anom_df.to_csv(anom_csv, index=False)
        print(f"[OK] Anomaly detection report saved to: {anom_csv}")

    # 3. Export Comprehensive Markdown Report
    out_md = out_dir / "model_evaluation_report.md"
    md_lines = [
        "# System & Model Evaluation Report",
        "",
        f"**Evaluated on Human-Reviewed Benchmark:** `{eval_path.name}` ({meta['total_evaluated']} verified records)",
        "",
        "### 1. Model Performance (Sentiment & Multi-Label Theme Classification)",
        "",
        "| Evaluation Subset | Samples | Sentiment Accuracy | Sentiment Precision (macro) | Sentiment Recall (macro) | Sentiment Macro-F1 | Theme Precision (multi-label) | Theme Recall (multi-label) | Theme Macro-F1 | Theme Micro-F1 |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for _, r in results_df.iterrows():
        md_lines.append(
            f"| **{r['subset']}** | {r['sample_count']} | {r['sentiment_accuracy']:.4f} | "
            f"{r['sentiment_precision_macro']:.4f} | {r['sentiment_recall_macro']:.4f} | "
            f"{r['sentiment_macro_f1']:.4f} | {r['theme_precision_multilabel']:.4f} | "
            f"{r['theme_recall_multilabel']:.4f} | {r['theme_f1_multilabel']:.4f} | "
            f"{r['theme_f1_micro']:.4f} |"
        )

    if not anom_df.empty:
        md_lines.extend([
            "",
            "---",
            "",
            "### 2. Validation Gate Anomaly Detection & Quarantine Recall",
            "",
            "| Injected Anomaly Type | Injected Volume | Quarantined By Gate | Detection Recall |",
            "| :--- | :---: | :---: | :---: |",
        ])
        for _, r in anom_df.iterrows():
            bold = "**" if r["issue_type"] == "OVERALL" else ""
            md_lines.append(
                f"| {bold}{r['issue_type']}{bold} | {r['total_injected']:,} | {r['total_quarantined']:,} | {bold}{r['detection_recall']*100:.1f}%{bold} |"
            )

    md_lines.append("")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    # Console output summary
    print(f"\n{'Subset':<24}  {'Samples':>7}  {'Sent Acc':>9}  {'Sent Prec':>10}  {'Sent Rec':>9}  {'Sent F1':>8}  {'Theme P':>8}  {'Theme R':>8}  {'Theme F1':>9}")
    print(f"{'-'*108}")
    for _, r in results_df.iterrows():
        print(f"  {r['subset']:<22}  {r['sample_count']:>7}  "
              f"{r['sentiment_accuracy']:>9.4f}  {r['sentiment_precision_macro']:>10.4f}  "
              f"{r['sentiment_recall_macro']:>9.4f}  {r['sentiment_macro_f1']:>8.4f}  "
              f"{r['theme_precision_multilabel']:>8.4f}  {r['theme_recall_multilabel']:>8.4f}  "
              f"{r['theme_f1_multilabel']:>9.4f}")
    print(f"{'-'*108}")

    if not anom_df.empty:
        print(f"\n{'-'*65}")
        print("  ANOMALY DETECTION RECALL (Module 2 Validation Gate vs Ground Truth)")
        print(f"{'-'*65}")
        for _, r in anom_df.iterrows():
            print(f"  {r['issue_type']:<28}  Injected: {r['total_injected']:>5} | Quarantined: {r['total_quarantined']:>5} | Recall: {r['detection_recall']*100:>5.1f}%")
        print(f"{'-'*65}\n")

    print(f"\n[OK] Model evaluation reports saved to:")
    print(f"  - {out_csv}")
    print(f"  - {out_md}\n")

    return results_df, anom_df


def main():
    parser = argparse.ArgumentParser(description="Evaluate model predictions and anomaly detection against ground truth")
    parser.add_argument("--db", default="data/db/feedback.db", help="Path to SQLite DB")
    parser.add_argument("--eval", default="data/evaluation/human_reviewed_eval.csv", help="Path to evaluation dataset")
    parser.add_argument("--gt", default="data/ground_truth/ground_truth.csv", help="Path to ground truth index")
    parser.add_argument("--excl", default="data/excluded_anomalies/all_excluded_anomalies.csv", help="Path to excluded anomalies")
    parser.add_argument("--out", default="reports", help="Output directory for reports")
    args = parser.parse_args()

    run_evaluation(args.db, args.eval, args.gt, args.excl, args.out)


if __name__ == "__main__":
    main()
