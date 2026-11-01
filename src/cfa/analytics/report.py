"""
report.py — Module 5 analytics report runner and exporter.

Computes:
  1. Sentiment trend timeline -> final_outcomes/sentiment_shifts.csv
  2. Granular record traceability lineage -> final_outcomes/sentiment_shifts_lineage.csv
  3. Recurring theme frequencies -> final_outcomes/recurring_themes.csv
  4. Ranked service priorities -> final_outcomes/service_priorities.csv
  5. Syncs live action items to SQLite database and logs state history.
  6. Consolidated markdown report -> final_outcomes/analytics_summary.md

Usage:
  python -m cfa.analytics.report
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from cfa.db.seed import get_engine
from cfa.analytics.trend_analysis import compute_sentiment_trends, detect_sentiment_inflection_points
from cfa.analytics.theme_frequency import compute_theme_frequencies
from cfa.analytics.priority_scoring import compute_service_priorities, sync_live_action_items_from_priorities


def generate_analytics_reports(
    db_path: Path | str,
    output_dir: Path | str = "final_outcomes"
) -> dict[str, pd.DataFrame]:
    """Execute all analytics calculations and save tabular reports to CSV and Markdown."""
    db_path = Path(db_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    engine = get_engine(db_path)

    print(f"\n{'='*65}")
    print("  CUSTOMER FEEDBACK ANALYTICS OUTCOMES GENERATOR")
    print(f"  Database: {db_path}")
    print(f"  Outcomes directory: {output_dir}")
    print(f"{'='*65}\n")

    # 1. Sentiment Trends with Traceability Lineage
    print("1. Computing Sentiment Shifts & Traceability Lineage...")
    trends_df, lineage_df = compute_sentiment_trends(engine, freq="W")
    trend_csv = output_dir / "sentiment_shifts.csv"
    trends_df.to_csv(trend_csv, index=False)
    lineage_csv = output_dir / "sentiment_shifts_lineage.csv"
    lineage_df.to_csv(lineage_csv, index=False)
    inflections_df = detect_sentiment_inflection_points(trends_df)
    print(f"   [OK] Saved: {trend_csv} ({len(trends_df)} weekly periods)")
    print(f"   [OK] Saved: {lineage_csv} ({len(lineage_df)} source event traces)")
    if not inflections_df.empty:
        print(f"   [INFO] Detected {len(inflections_df)} sentiment inflection point(s)")

    # 2. Recurring Theme Frequency Breakdown
    print("\n2. Computing Recurring Themes...")
    themes_df = compute_theme_frequencies(engine)
    theme_csv = output_dir / "recurring_themes.csv"
    themes_df.to_csv(theme_csv, index=False)
    print(f"   [OK] Saved: {theme_csv} ({len(themes_df)} themes analyzed)")

    # 3. Service Priorities & Live Action Items Sync
    print("\n3. Calculating Service Priorities & Syncing Action Items...")
    priorities_df = compute_service_priorities(engine)
    priority_csv = output_dir / "service_priorities.csv"
    priorities_df.to_csv(priority_csv, index=False)
    print(f"   [OK] Saved: {priority_csv} ({len(priorities_df)} prioritized themes)")

    actions_df = sync_live_action_items_from_priorities(engine, priorities_df, threshold=50)
    if not actions_df.empty:
        actions_csv = output_dir / "live_action_items.csv"
        actions_df.to_csv(actions_csv, index=False)
        print(f"   [OK] Synced {len(actions_df)} live action items to DB & {actions_csv}")

    # 4. Generate Markdown Summary Report
    summary_md_path = output_dir / "analytics_summary.md"
    top5 = priorities_df.head(5)
    md_content = f"""# Customer Feedback Analytics — Executive Summary

**Generated At**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Target Database**: `{db_path.name}`

---

## 1. Top Service Priorities (Highest Friction & Negative Sentiment)

| Rank | Urgency | Theme | Total Mentions | Negative Mentions | Negative Ratio | Priority Score |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: |
"""
    for _, r in top5.iterrows():
        md_content += f"| #{r['priority_rank']} | **{r['recommended_urgency']}** | {r['theme_name']} | {r['total_mentions']:,} | {r['negative_mentions']:,} | {r['negative_ratio']*100:.1f}% | {r['priority_score']:.1f} |\n"

    md_content += f"""
---

## 2. Sentiment Trends Overview

- **Weekly Periods Analyzed**: {len(trends_df)}
- **Total Feedback Events Tracked**: {len(lineage_df):,}
- **Inflection Points Detected ($\Delta NSS \ge 10$)**: {len(inflections_df)}

All trends are strictly linked to source records via `sentiment_shifts_lineage.csv`.
"""
    with open(summary_md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"   [OK] Generated Executive Summary: {summary_md_path}")

    # Print Top 5 Action Priorities to Console
    print(f"\n{'-'*65}")
    print("  TOP 5 SERVICE PRIORITIES (Ranked by Friction & Negative Impact)")
    print(f"{'-'*65}")
    for _, r in top5.iterrows():
        print(f"  #{r['priority_rank']} [{r['recommended_urgency']:<8}] {r['theme_name']:<28} "
              f"Score: {r['priority_score']:>7.1f} | Neg Ratio: {r['negative_ratio']*100:>5.1f}%")
    print(f"{'-'*65}\n")

    return {
        "sentiment_shifts": trends_df,
        "sentiment_shifts_lineage": lineage_df,
        "recurring_themes": themes_df,
        "service_priorities": priorities_df,
        "live_action_items": actions_df,
    }


def main():
    parser = argparse.ArgumentParser(description="Run analytics and generate summary reports")
    parser.add_argument("--db", default="data/db/feedback.db", help="Path to SQLite DB")
    parser.add_argument("--out", default="final_outcomes", help="Output directory for reports")
    args = parser.parse_args()

    db_path = _PROJECT_ROOT / args.db
    out_dir = _PROJECT_ROOT / args.out
    generate_analytics_reports(db_path, out_dir)


if __name__ == "__main__":
    main()
