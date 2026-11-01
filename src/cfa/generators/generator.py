"""
generator.py — Module 1 entry point.

Usage
-----
  python -m cfa.generators.generator                        # starter scale, seed from config
  python -m cfa.generators.generator --scale full
  python -m cfa.generators.generator --scale starter --seed 20261022
  python -m cfa.generators.generator --config configs/config.yaml

Outputs written to paths defined in config.yaml:
  data/raw/            — clean entity CSVs
  data/anomalies/      — anomaly CSVs (include issue_type column)
  data/ground_truth/   — ground_truth.csv
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from faker import Faker

# ── Resolve project root (src/cfa/generators/generator.py → 3 levels up) ─────
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

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
from cfa.validation.validate_raw import (
    validate_reviews, validate_survey_responses, validate_support_messages,
    validate_theme_bridge,
)
import json
from datetime import datetime


# ── Config loading ─────────────────────────────────────────────────────────────

def load_config(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── CSV writing ────────────────────────────────────────────────────────────────

def _save(df: pd.DataFrame, directory: Path, filename: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    dest = directory / filename
    df.to_csv(dest, index=False)
    return dest


def _checksum(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


# ── Theme mention aggregation ──────────────────────────────────────────────────

def _count_theme_mentions(
    rev_themes: pd.DataFrame,
    resp_themes: pd.DataFrame,
    msg_themes: pd.DataFrame,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for df, col in [
        (rev_themes,  "theme_id"),
        (resp_themes, "theme_id"),
        (msg_themes,  "theme_id"),
    ]:
        if df.empty:
            continue
        for theme_id, cnt in df[col].value_counts().items():
            counts[str(theme_id)] = counts.get(str(theme_id), 0) + int(cnt)
    return counts


# ── Main ───────────────────────────────────────────────────────────────────────

def run(cfg: dict) -> dict[str, Path]:
    """
    Generate all data for the given config.
    Returns a mapping of {label: csv_path} for checksumming / reporting.
    """
    seed  = int(cfg["seed"])
    scale = cfg["scale"]
    vols  = cfg["volumes"][scale]
    paths = cfg["paths"]
    threshold = cfg["action_items"][f"threshold_{scale}"]

    raw_dir   = _PROJECT_ROOT / paths.get("raw_dir", "data/raw")
    val_dir   = _PROJECT_ROOT / paths.get("validated_dir", "data/validated")
    excl_dir  = _PROJECT_ROOT / paths.get("excluded_dir", "data/excluded_anomalies")
    gt_dir    = _PROJECT_ROOT / paths.get("ground_truth_dir", "data/ground_truth")
    eval_dir  = _PROJECT_ROOT / paths.get("evaluation_dir", "data/evaluation")

    rng   = np.random.default_rng(seed)
    faker = Faker()
    Faker.seed(seed)

    print(f"\n{'='*60}")
    print(f"  CFA Generator  |  scale={scale}  |  seed={seed}")
    print(f"{'='*60}")

    # ── 1. Master data ─────────────────────────────────────────────────────────
    products  = generate_products()
    channels  = generate_channels()
    themes    = generate_themes()
    sentiment_labels_df = generate_sentiment_labels()
    customers = generate_customers(vols["customers"], rng, faker)
    surveys   = generate_surveys(
        vols["surveys"], rng, faker,
        products["product_id"].tolist(),
        channels["channel_id"].tolist(),
    )

    product_ids  = products["product_id"].tolist()
    channel_ids  = channels["channel_id"].tolist()

    # ── 2. Transactions ────────────────────────────────────────────────────────
    reviews, rev_themes = generate_reviews(
        vols["reviews"], customers, products, channels, themes, rng, cfg,
    )
    responses, resp_themes = generate_survey_responses(
        vols["survey_responses"], surveys, customers, themes, rng, cfg,
    )
    tickets = generate_support_tickets(
        vols["support_tickets"], customers, channels, rng, products_df=products,
    )
    messages, msg_themes = generate_support_messages(
        vols["support_messages"], tickets, themes, rng, cfg,
    )

    # ── 3. Action items (derived) ───────────────────────────────────────────────
    theme_counts = _count_theme_mentions(rev_themes, resp_themes, msg_themes)
    action_items = generate_action_items(theme_counts, threshold, rng)

    # ── 4. Anomalies ────────────────────────────────────────────────────────────
    n_anom = vols["anomalies_per_type"]
    rev_id_offset  = vols["reviews"]
    resp_id_offset = 0   # responses use per-survey counters starting at 900
    msg_id_offset  = 0   # messages use per-ticket counters starting at 900

    rev_anom, rev_gt = generate_review_anomalies(
        n_anom, reviews, rng, faker, rev_themes, id_offset=rev_id_offset,
    )
    resp_anom, resp_gt = generate_response_anomalies(
        n_anom, responses, rng, faker, resp_themes, id_offset=resp_id_offset,
    )
    msg_anom, msg_gt = generate_message_anomalies(
        n_anom, messages, rng, faker, msg_themes, id_offset=msg_id_offset,
    )
    ground_truth = build_ground_truth(rev_gt, resp_gt, msg_gt)

    # ── 5. Raw Data Assembly (Normal + Anomalies without issue_type) ────────────
    # In module 1, anomalies are appended to normal raw data without the issue_type column
    raw_reviews = pd.concat([reviews, rev_anom.drop(columns=["issue_type"])], ignore_index=True)
    raw_responses = pd.concat([responses, resp_anom.drop(columns=["issue_type"])], ignore_index=True)
    raw_messages = pd.concat([messages, msg_anom.drop(columns=["issue_type"])], ignore_index=True)

    # ── 6. Validation Gate & Anomaly Exclusion ─────────────────────────────────
    # Raw data goes through validation: valid data is separated for SQLite ingestion,
    # and excluded anomalies are saved to a separate file for verification.
    val_reviews, excl_reviews = validate_reviews(raw_reviews)
    val_responses, excl_responses = validate_survey_responses(raw_responses)
    val_messages, excl_messages = validate_support_messages(raw_messages)

    # Bridge-table validation: filter out any theme assignments outside the 15-item taxonomy.
    # validate_theme_bridge() is called explicitly here so that out_of_taxonomy_theme entries
    # are caught directly on the bridge tables, not just indirectly through parent-ID filtering.
    allowed_theme_ids: set[str] = set(themes["theme_id"].tolist())
    val_rev_themes,  _ = validate_theme_bridge(rev_themes,  allowed_theme_ids)
    val_resp_themes, _ = validate_theme_bridge(resp_themes, allowed_theme_ids)
    val_msg_themes,  _ = validate_theme_bridge(msg_themes,  allowed_theme_ids)

    # Filter validated theme bridges to only rows belonging to validated parent transactions
    val_rev_themes = val_rev_themes[val_rev_themes["review_id"].isin(val_reviews["review_id"])].copy()
    val_resp_themes = val_resp_themes[val_resp_themes["response_id"].isin(val_responses["response_id"])].copy()
    val_msg_themes = val_msg_themes[val_msg_themes["message_id"].isin(val_messages["message_id"])].copy()

    # Reconcile validated action items against validated bridge counts so database arithmetic passes
    val_theme_counts = _count_theme_mentions(val_rev_themes, val_resp_themes, val_msg_themes)
    val_action_items = generate_action_items(val_theme_counts, threshold, rng)

    excl_reviews_out = excl_reviews.copy()
    excl_reviews_out["entity_type"] = "review"
    excl_responses_out = excl_responses.copy()
    excl_responses_out["entity_type"] = "survey_response"
    excl_messages_out = excl_messages.copy()
    excl_messages_out["entity_type"] = "support_message"

    all_excluded = pd.concat([
        excl_reviews_out.rename(columns={"review_id": "record_id"}),
        excl_responses_out.rename(columns={"response_id": "record_id"}),
        excl_messages_out.rename(columns={"message_id": "record_id"}),
    ], ignore_index=True)

    # ── 7. Synthetic Human-Reviewed Labeled Dataset for Model Evaluation ───────
    # Certified benchmark set across sentiment classes, languages, and ambiguous examples
    eval_sample_n = min(300, len(val_reviews))
    eval_candidates = val_reviews.sample(n=eval_sample_n, random_state=int(rng.integers(0, 1_000_000))).copy()
    # Map primary theme for each review in evaluation set (use validated bridge for accuracy)
    eval_candidates["primary_theme_id"] = eval_candidates["review_id"].map(
        val_rev_themes.drop_duplicates(subset=["review_id"]).set_index("review_id")["theme_id"]
    ).fillna("THEME-000001")
    eval_dataset = pd.DataFrame({
        "sample_id": [f"EVAL-{i+1:05d}" for i in range(len(eval_candidates))],
        "source_record_id": eval_candidates["review_id"].tolist(),
        "entity_type": "review",
        "text": eval_candidates["review_text"].tolist(),
        "language": eval_candidates["language"].tolist(),
        "is_ambiguous": eval_candidates["is_ambiguous"].tolist(),
        "ground_truth_sentiment": eval_candidates["sentiment_label"].tolist(),
        "ground_truth_theme_id": eval_candidates["primary_theme_id"].tolist(),
        "review_status": "human_verified",
        "verified_by": "expert_evaluator",
        "confidence": 1.0,
    })

    # ── 8. Write Datasets to Disk ───────────────────────────────────────────────
    written: dict[str, Path] = {}

    # raw/ (contains normal data + appended unlabelled anomalies)
    for name, df in [
        ("customers",        customers),
        ("products",         products),
        ("channels",         channels),
        ("themes",           themes),
        ("sentiment_labels", sentiment_labels_df),
        ("surveys",          surveys),
        ("reviews",          raw_reviews),
        ("survey_responses", raw_responses),
        ("support_tickets",  tickets),
        ("support_messages", raw_messages),
        ("review_themes",    rev_themes),
        ("response_themes",  resp_themes),
        ("message_themes",   msg_themes),
        ("action_items",     action_items),
    ]:
        written[f"raw_{name}"] = _save(df, raw_dir, f"{name}.csv")

    # validated/ (clean data that will go into SQLite db)
    for name, df in [
        ("customers",        customers),
        ("products",         products),
        ("channels",         channels),
        ("themes",           themes),
        ("sentiment_labels", sentiment_labels_df),
        ("surveys",          surveys),
        ("reviews",          val_reviews),
        ("survey_responses", val_responses),
        ("support_tickets",  tickets),
        ("support_messages", val_messages),
        ("review_themes",    val_rev_themes),
        ("response_themes",  val_resp_themes),
        ("message_themes",   val_msg_themes),
        ("action_items",     val_action_items),
    ]:
        written[f"val_{name}"] = _save(df, val_dir, f"{name}.csv")

    # excluded_anomalies/ (excluded records for validation verification)
    written["excluded_reviews"] = _save(excl_reviews, excl_dir, "excluded_reviews.csv")
    written["excluded_responses"] = _save(excl_responses, excl_dir, "excluded_responses.csv")
    written["excluded_messages"] = _save(excl_messages, excl_dir, "excluded_messages.csv")
    written["excluded_all"] = _save(all_excluded, excl_dir, "all_excluded_anomalies.csv")

    # ground_truth/ (separate reference anomalies with issue_type + ground_truth.csv)
    written["gt_reviews_anomalies"] = _save(rev_anom, gt_dir, "reviews_anomalies.csv")
    written["gt_responses_anomalies"] = _save(resp_anom, gt_dir, "responses_anomalies.csv")
    written["gt_messages_anomalies"] = _save(msg_anom, gt_dir, "messages_anomalies.csv")
    written["ground_truth"] = _save(ground_truth, gt_dir, "ground_truth.csv")

    # evaluation/ (synthetic human-reviewed labeled dataset)
    written["human_reviewed_eval"] = _save(eval_dataset, eval_dir, "human_reviewed_eval.csv")

    # ── 6. Manifest & Provenance Export ─────────────────────────────────────────
    def _to_rel_path(p: Path) -> str:
        try:
            return str(p.relative_to(_PROJECT_ROOT)).replace("\\", "/")
        except ValueError:
            # If path is not inside _PROJECT_ROOT (e.g. running in temp dir in tests), return relative to its own parent data root
            return p.name

    manifest_data = {
        "generated_at": datetime.now().isoformat(),
        "seed": seed,
        "scale": scale,
        "files": {
            label: {
                "rows": len(pd.read_csv(p)),
                "sha256": _checksum(p),
                "relative_path": _to_rel_path(p)
            }
            for label, p in written.items()
        }
    }
    manifest_path = raw_dir.parent / "manifest.json" if (raw_dir.parent / "manifest.json").parent.exists() else _PROJECT_ROOT / "data" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest_data, mf, indent=2)

    # ── 7. Summary ─────────────────────────────────────────────────────────────
    print(f"\n{'-'*60}")
    print(f"  {'File':<32}  {'Rows':>8}  {'SHA-256':>16}")
    print(f"{'-'*60}")
    for label, path in written.items():
        cnt = manifest_data["files"][label]["rows"]
        chk = manifest_data["files"][label]["sha256"]
        print(f"  {label:<32}  {cnt:>8,}  {chk}")
    print(f"{'-'*60}")
    print(f"\nManifest exported to: {manifest_path}")
    print(f"All files written to {_PROJECT_ROOT}\n")

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="CFA synthetic data generator")
    parser.add_argument("--config", default="configs/config.yaml",
                        help="Path to config.yaml (default: configs/config.yaml)")
    parser.add_argument("--scale",  choices=["starter", "full"],
                        help="Override scale from config")
    parser.add_argument("--seed",   type=int,
                        help="Override random seed from config")
    args = parser.parse_args()

    config_path = _PROJECT_ROOT / args.config
    cfg = load_config(config_path)
    if args.scale:
        cfg["scale"] = args.scale
    if args.seed is not None:
        cfg["seed"] = args.seed

    run(cfg)


if __name__ == "__main__":
    main()
