"""
main.py — Single-command end-to-end workflow runner for Customer Feedback Analytics.

Executes all 6 modules sequentially:
  Step 1: Synthetic Data Generation (Module 1)
  Step 2: Database Schema & Seeding (Module 2)
  Step 3: Quality & Integrity Validation (Module 3)
  Step 4: Sentiment & Theme NLP Processing (Module 4)
  Step 5: Business Analytics & Service Priorities (Module 5)
  Step 6: Model Evaluation vs Ground Truth (Module 6)

Usage:
  python main.py
  python main.py --scale starter --seed 20261022
  python main.py --scale full
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
import yaml

_PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from cfa.generators.generator import run as run_generator, load_config
from cfa.db.seed import get_engine, load_raw_csvs_into_db, export_schema_sql
from cfa.validation.run_all import run_all_validations
from cfa.processing.pipeline import run_processing_pipeline
from cfa.analytics.report import generate_analytics_reports
from cfa.evaluation.metrics import run_evaluation
from cfa.evaluation.data_audit import run_data_evaluation


def run_full_pipeline(scale: str | None = None, seed: int | None = None, config_path: str = "configs/config.yaml"):
    start_time = time.time()
    cfg_file = _PROJECT_ROOT / config_path
    cfg = load_config(cfg_file)

    if scale:
        cfg["scale"] = scale
    if seed is not None:
        cfg["seed"] = seed

    selected_scale = cfg["scale"]
    selected_seed = cfg["seed"]

    paths = cfg.get("paths", {})
    raw_dir = _PROJECT_ROOT / paths.get("raw_dir", "data/raw")
    val_dir = _PROJECT_ROOT / paths.get("validated_dir", "data/validated")
    db_path = _PROJECT_ROOT / paths.get("db_file", "data/db/feedback.db")
    gt_path = _PROJECT_ROOT / paths.get("ground_truth_dir", "data/ground_truth") / "ground_truth.csv"
    eval_benchmark_path = _PROJECT_ROOT / paths.get("evaluation_dir", "data/evaluation") / "human_reviewed_eval.csv"
    reports_dir = _PROJECT_ROOT / paths.get("reports_dir", "reports")
    outcomes_dir = _PROJECT_ROOT / paths.get("outcomes_dir", "final_outcomes")
    reports_dir.mkdir(parents=True, exist_ok=True)
    outcomes_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*70)
    print("  CUSTOMER FEEDBACK ANALYTICS — END-TO-END PIPELINE RUNNER")
    print(f"  Scale: {selected_scale} | Seed: {selected_seed}")
    print(f"  Target DB: {db_path}")
    print(f"  Reports output: {reports_dir}")
    print(f"  Final Outcomes output: {outcomes_dir}")
    print("="*70)

    # ── STEP 1: Synthetic Data Generation ──────────────────────────────────────
    print("\n>>> [STEP 1/6] Running Data Generator & Validation Gate (Module 1)...")
    run_generator(cfg)

    # ── STEP 2: Database Seeding ───────────────────────────────────────────────
    print("\n>>> [STEP 2/6] Loading Validated Data into SQLite & Exporting Schema DDL (Module 2)...")
    engine = get_engine(db_path)
    counts = load_raw_csvs_into_db(val_dir, engine)
    schema_sql_path = _PROJECT_ROOT / "data" / "schema.sql"
    export_schema_sql(engine, schema_sql_path)
    print(f"Loaded {sum(counts.values()):,} total rows into SQLite.")

    # ── STEP 3: Quality & Integrity Validation ─────────────────────────────────
    print("\n>>> [STEP 3/6] Running Data Quality Gate Validations (Module 3)...")
    valid_ok = run_all_validations(db_path, seed=selected_seed)
    if not valid_ok:
        print("\n[ERROR] Data validation checks failed! Aborting pipeline.")
        sys.exit(1)

    # ── STEP 4: Processing Pipeline ────────────────────────────────────────────
    print("\n>>> [STEP 4/6] Executing Sentiment & Theme NLP Processing (Module 4)...")
    run_processing_pipeline(db_path, cfg)

    # ── STEP 5: Business Outcomes (Themes, Sentiment Shifts & Priorities) ───
    print("\n>>> [STEP 5/6] Generating Business Outcomes (final_outcomes/) (Module 5)...")
    generate_analytics_reports(db_path, output_dir=outcomes_dir)

    # ── STEP 6: Evaluation Reports (Model & Data Evaluation vs Criteria a-g) ──
    print("\n>>> [STEP 6/6] Generating Model & Data Evaluation Reports (Module 6)...")
    run_evaluation(db_path, eval_path=eval_benchmark_path, out_dir=reports_dir)
    run_data_evaluation(engine, _PROJECT_ROOT, out_dir=reports_dir, seed=selected_seed)

    elapsed = round(time.time() - start_time, 2)
    print("="*70)
    print(f"  END-TO-END WORKFLOW COMPLETED SUCCESSFULLY IN {elapsed}s")
    print("="*70)
    print("\nGenerated Evaluation Reports in reports/:")
    for f in sorted(reports_dir.glob("*.*")):
        if f.is_file():
            print(f"  - {f.name}")
    print("\nGenerated Final Business Outcomes in final_outcomes/:")
    for f in sorted(outcomes_dir.glob("*.csv")):
        print(f"  - {f.name}")
    print(f"\nDatabase: {db_path}")
    print(f"Schema DDL: {schema_sql_path}")
    print(f"Manifest: {_PROJECT_ROOT / 'data' / 'manifest.json'}\n")


def main():
    parser = argparse.ArgumentParser(description="Run complete Customer Feedback Analytics pipeline")
    parser.add_argument("--scale", choices=["starter", "full"], help="Data scale preset (starter or full)")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("--config", default="configs/config.yaml", help="Path to config.yaml")
    args = parser.parse_args()

    run_full_pipeline(scale=args.scale, seed=args.seed, config_path=args.config)


if __name__ == "__main__":
    main()
