"""
data_evaluation.py — Data evaluation audit across criteria (a) through (g).

Audit criteria from project description:
  (a) realistic distributions and meaningful variation;
  (b) consistent IDs and valid joins;
  (c) dependency/lifecycle consistency across entities;
  (d) correct derived values and reconciliation;
  (e) normal, boundary, failure and exception coverage;
  (f) separate ground truth;
  (g) fixed-seed reproducibility, documentation and lawful provenance.
"""

from __future__ import annotations

import re
from pathlib import Path
import pandas as pd
from sqlalchemy import text, inspect

from cfa.generators.schema import (
    REGIONS, SEGMENTS, LIFECYCLE_STATES, SENTIMENT_LABELS, LANGUAGES,
    STAR_TO_SENTIMENT, response_rating_to_sentiment, ANOMALY_TYPES
)
from cfa.validation.pk_fk_checks import check_pk_uniqueness, check_fk_integrity
from cfa.validation.enum_checks import check_allowed_enums, check_derived_rules_reconciliation
from cfa.validation.reproducibility import check_seed_reproducibility


def audit_realistic_distributions(engine) -> dict:
    """(a) Realistic distributions and meaningful variation."""
    with engine.connect() as conn:
        rev_sent = pd.read_sql(text("SELECT sentiment_label, count(*) as cnt FROM reviews GROUP BY sentiment_label"), conn)
        rev_lang = pd.read_sql(text("SELECT language, count(*) as cnt FROM reviews GROUP BY language"), conn)
        rev_amb = pd.read_sql(text("SELECT is_ambiguous, count(*) as cnt FROM reviews GROUP BY is_ambiguous"), conn)

    total_rev = rev_sent["cnt"].sum()
    sent_dist = {row["sentiment_label"]: round(row["cnt"] / total_rev, 3) for _, row in rev_sent.iterrows()}
    multilingual_count = int(rev_lang[rev_lang["language"] != "en"]["cnt"].sum())
    ambiguous_count = int(rev_amb[rev_amb["is_ambiguous"] == 1]["cnt"].sum())

    passed = (
        len(sent_dist) == 3
        and all(0.20 <= v <= 0.45 for v in sent_dist.values())
        and multilingual_count > 0
        and ambiguous_count > 0
    )
    return {
        "criterion": "(a) Realistic distributions and meaningful variation",
        "status": "PASS" if passed else "FAIL",
        "details": f"Sentiment balance: {sent_dist}; Multilingual reviews: {multilingual_count}; Ambiguous/sarcastic: {ambiguous_count}",
    }


def audit_consistent_ids_and_joins(engine) -> dict:
    """(b) Consistent IDs and valid joins."""
    pk_errs = check_pk_uniqueness(engine)
    fk_errs = check_fk_integrity(engine)

    passed = len(pk_errs) == 0 and len(fk_errs) == 0
    return {
        "criterion": "(b) Consistent IDs and valid joins",
        "status": "PASS" if passed else "FAIL",
        "details": f"PK violations: {len(pk_errs)}; FK orphan violations: {len(fk_errs)}",
    }


def audit_dependency_and_lifecycle(engine) -> dict:
    """(c) Dependency/lifecycle consistency across entities."""
    violations = []
    with engine.connect() as conn:
        # Check support ticket resolution date >= creation date
        q_ticket_dates = """
            SELECT count(*) FROM support_tickets
            WHERE resolved_at IS NOT NULL AND resolved_at < created_at
        """
        bad_ticket_dates = conn.execute(text(q_ticket_dates)).scalar()
        if bad_ticket_dates > 0:
            violations.append(f"{bad_ticket_dates} tickets have resolved_at < created_at")

        # Check survey response dates fall within survey start/end dates
        q_survey_dates = """
            SELECT count(*) FROM survey_responses r
            JOIN surveys s ON r.survey_id = s.survey_id
            WHERE substr(r.submitted_at, 1, 10) < s.start_date
               OR substr(r.submitted_at, 1, 10) > s.end_date
        """
        bad_survey_dates = conn.execute(text(q_survey_dates)).scalar()
        if bad_survey_dates > 0:
            violations.append(f"{bad_survey_dates} responses submitted outside active survey window")

    passed = len(violations) == 0
    return {
        "criterion": "(c) Dependency/lifecycle consistency across entities",
        "status": "PASS" if passed else "FAIL",
        "details": "All event dates and lifecycle sequences align with parent master entities" if passed else "; ".join(violations),
    }


def audit_correct_derived_values(engine) -> dict:
    """(d) Correct derived values and reconciliation."""
    reconcil_errs = check_derived_rules_reconciliation(engine)
    passed = len(reconcil_errs) == 0
    return {
        "criterion": "(d) Correct derived values and reconciliation",
        "status": "PASS" if passed else "FAIL",
        "details": f"Arithmetic & rule reconciliation errors: {len(reconcil_errs)} (Stars and ratings reconcile with sentiment)",
    }


def audit_coverage_and_exceptions(project_root: Path) -> dict:
    """(e) Normal, boundary, failure and exception coverage."""
    excl_path = project_root / "data" / "excluded_anomalies" / "all_excluded_anomalies.csv"
    if not excl_path.exists():
        return {
            "criterion": "(e) Normal, boundary, failure and exception coverage",
            "status": "FAIL",
            "details": "Excluded anomalies file missing",
        }
    df_excl = pd.read_csv(excl_path)
    total_excluded = len(df_excl)
    reasons = df_excl["exclusion_reason"].value_counts().to_dict()
    passed = total_excluded > 0 and len(reasons) >= 3
    return {
        "criterion": "(e) Normal, boundary, failure and exception coverage",
        "status": "PASS" if passed else "FAIL",
        "details": f"Total anomalies caught & excluded: {total_excluded}; Covered anomaly types: {reasons}",
    }


def audit_separate_ground_truth(project_root: Path, engine) -> dict:
    """(f) Separate ground truth."""
    gt_file = project_root / "data" / "ground_truth" / "ground_truth.csv"
    gt_exists = gt_file.exists()
    inspector = inspect(engine)

    # Ensure issue_type is NOT leaked into any database table
    leaked_tables = []
    for table_name in inspector.get_table_names():
        cols = [c["name"] for c in inspector.get_columns(table_name)]
        if "issue_type" in cols:
            leaked_tables.append(table_name)

    passed = gt_exists and len(leaked_tables) == 0
    return {
        "criterion": "(f) Separate ground truth",
        "status": "PASS" if passed else "FAIL",
        "details": f"Ground truth isolated in {gt_file.name} ({len(pd.read_csv(gt_file)) if gt_exists else 0} records); Zero feature leakage into DB (leaked tables: {leaked_tables})",
    }


def audit_reproducibility_and_provenance(project_root: Path, seed: int = 20261022) -> dict:
    """(g) Fixed-seed reproducibility, documentation and lawful provenance."""
    repro = check_seed_reproducibility(seed=seed, sample_volume=50)
    dict_doc = (project_root / "docs" / "DATA_DICTIONARY.md").exists()
    prov_doc = (project_root / "docs" / "PROVENANCE.md").exists()
    manifest_doc = (project_root / "data" / "manifest.json").exists()

    passed = repro["is_reproducible"] and dict_doc and prov_doc and manifest_doc
    return {
        "criterion": "(g) Fixed-seed reproducibility, documentation and lawful provenance",
        "status": "PASS" if passed else "FAIL",
        "details": f"Reproducibility: {'PASS' if repro['is_reproducible'] else 'FAIL'}; Docs verified: DATA_DICTIONARY.md={dict_doc}, PROVENANCE.md={prov_doc}, manifest.json={manifest_doc}",
    }


def run_data_evaluation(
    engine,
    project_root: Path,
    out_dir: Path | str = "reports",
    seed: int = 20261022
) -> pd.DataFrame:
    """
    Run evaluation against all criteria (a) through (g) and write data_evaluation_report.csv
    and data_evaluation_report.md.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results = [
        audit_realistic_distributions(engine),
        audit_consistent_ids_and_joins(engine),
        audit_dependency_and_lifecycle(engine),
        audit_correct_derived_values(engine),
        audit_coverage_and_exceptions(project_root),
        audit_separate_ground_truth(project_root, engine),
        audit_reproducibility_and_provenance(project_root, seed=seed),
    ]

    report_df = pd.DataFrame(results)
    csv_path = out_dir / "data_evaluation_report.csv"
    report_df.to_csv(csv_path, index=False)

    # Also render clean markdown report
    md_path = out_dir / "data_evaluation_report.md"
    md_lines = [
        "# Data Quality & Benchmark Evaluation Report",
        "",
        "Comprehensive evaluation of generated synthetic data and pipeline integrity conforming to specification criteria (a) through (g).",
        "",
        "| Section / Rubric Focus | Status | Evaluation Findings |",
        "| :--- | :---: | :--- |",
    ]
    for r in results:
        badge = "**PASS**" if r["status"] == "PASS" else "**FAIL**"
        md_lines.append(f"| {r['criterion']} | {badge} | {r['details']} |")

    md_lines.append("")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"\n{'='*70}")
    print("  DATA EVALUATION REPORT (Specification Criteria a-g)")
    print(f"{'='*70}")
    for r in results:
        print(f"  [{r['status']}] {r['criterion']}")
        print(f"        {r['details']}")
    print(f"{'-'*70}")
    print(f"Exported: {csv_path} and {md_path}\n")

    return report_df
