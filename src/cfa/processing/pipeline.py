"""
pipeline.py — Module 4 consolidated processing orchestrator.

Runs both sentiment inference and theme classification on all raw texts,
populating `predicted_sentiment` and `predicted_theme` in the database.

Usage:
  python -m cfa.processing.pipeline
  python -m cfa.processing.pipeline --db data/db/feedback.db
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import yaml

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from cfa.db.seed import get_engine
from cfa.processing.sentiment import SentimentClassifier, update_predicted_sentiment
from cfa.processing.theme_classifier import ThemeClassifier, update_predicted_themes


def run_processing_pipeline(db_path: Path | str, cfg: dict | None = None) -> dict:
    """Run full processing pipeline (Sentiment + Theme prediction)."""
    db_path = Path(db_path)
    engine = get_engine(db_path)

    batch_size = 32  # default matches config.yaml; overridden below if cfg is provided
    sentiment_model = "distilbert-base-uncased-finetuned-sst-2-english"
    theme_mode = "keyword"
    zero_shot_model = "facebook/bart-large-mnli"

    if cfg and "processing" in cfg:
        p_cfg = cfg["processing"]
        batch_size = p_cfg.get("batch_size", batch_size)
        sentiment_model = p_cfg.get("sentiment_model", sentiment_model)
        theme_mode = p_cfg.get("theme_mode", theme_mode)
        zero_shot_model = p_cfg.get("zero_shot_model", zero_shot_model)

    print(f"\n{'='*60}")
    print("  FEEDBACK PROCESSING PIPELINE")
    print(f"  Target DB: {db_path}")
    print(f"  Sentiment model: {sentiment_model}")
    print(f"  Theme mode: {theme_mode}")
    print(f"{'='*60}\n")

    # 1. Sentiment Prediction
    print("1. Running Sentiment Analysis Inference...")
    # use_model=False ensures rapid, reliable local execution; set use_model=True if GPU/full transformer run is desired
    use_hf = cfg.get("processing", {}).get("use_hf_transformer", False) if cfg else False
    sentiment_clf = SentimentClassifier(model_name=sentiment_model, use_model=use_hf)
    sent_updated = update_predicted_sentiment(engine, sentiment_clf, batch_size=batch_size)
    for tbl, count in sent_updated.items():
        print(f"   - {tbl}: {count:,} records updated with predicted sentiment")

    # 2. Theme Classification
    print("\n2. Running Theme Classification...")
    theme_clf = ThemeClassifier(mode=theme_mode, zero_shot_model=zero_shot_model)
    theme_updated = update_predicted_themes(engine, theme_clf, batch_size=batch_size)
    for tbl, count in theme_updated.items():
        print(f"   - {tbl}: {count:,} records updated with predicted theme")

    print(f"\n{'-'*60}")
    print("Processing pipeline completed successfully.\n")

    return {
        "sentiment_updated": sent_updated,
        "theme_updated": theme_updated,
    }


def main():
    parser = argparse.ArgumentParser(description="Run feedback processing pipeline")
    parser.add_argument("--db", default="data/db/feedback.db", help="Path to SQLite DB")
    parser.add_argument("--config", default="configs/config.yaml", help="Path to config.yaml")
    args = parser.parse_args()

    cfg_path = _PROJECT_ROOT / args.config
    cfg = None
    if cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

    db_path = _PROJECT_ROOT / args.db
    run_processing_pipeline(db_path, cfg)


if __name__ == "__main__":
    main()
