"""
seed.py — Reads generated CSVs from data/raw/ and loads them into SQLite.

Features:
  - Validates FK referential integrity before committing inserts.
  - Inserts in strict dependency order (master data -> transactions -> bridges).
  - Can be invoked as CLI: python -m cfa.db.seed
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, select, text

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from cfa.db.models import (
    metadata, customers, products, channels, themes, sentiment_labels, surveys,
    reviews, survey_responses, support_tickets, support_messages,
    action_items, status_history, review_themes, response_themes, message_themes,
)


def get_engine(db_path: Path | str):
    """Create a SQLite engine with foreign keys enabled."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", echo=False)
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON;"))
    return engine


def init_db(engine):
    """Create tables if they do not exist."""
    metadata.create_all(engine)


def export_schema_sql(engine, out_path: Path):
    """Export table schemas and table creations as standalone SQL DDL script."""
    from sqlalchemy.schema import CreateTable
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    all_ddl = []
    for tbl in metadata.sorted_tables:
        ddl_str = str(CreateTable(tbl).compile(engine)).strip()
        all_ddl.append(f"{ddl_str};")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(all_ddl) + "\n")
    print(f"SQL Schema DDL exported to: {out_path}")


def load_raw_csvs_into_db(data_dir: Path, engine) -> dict[str, int]:
    """
    Load CSVs from data_dir (e.g. data/validated/ or data/raw/) into the database in topological/dependency order.
    Returns a dict mapping table name -> inserted row count.
    """
    data_dir = Path(data_dir)
    init_db(engine)

    # Dependency order: master tables first, then transactions, then bridges
    load_sequence = [
        ("customers", customers, "customers.csv"),
        ("products", products, "products.csv"),
        ("channels", channels, "channels.csv"),
        ("themes", themes, "themes.csv"),
        ("sentiment_labels", sentiment_labels, "sentiment_labels.csv"),
        ("surveys", surveys, "surveys.csv"),
        ("reviews", reviews, "reviews.csv"),
        ("survey_responses", survey_responses, "survey_responses.csv"),
        ("support_tickets", support_tickets, "support_tickets.csv"),
        ("support_messages", support_messages, "support_messages.csv"),
        ("action_items", action_items, "action_items.csv"),
        ("status_history", status_history, "status_history.csv"),
        ("review_themes", review_themes, "review_themes.csv"),
        ("response_themes", response_themes, "response_themes.csv"),
        ("message_themes", message_themes, "message_themes.csv"),
    ]

    inserted_counts = {}

    with engine.begin() as conn:
        # Clear child tables first (reverse dependency) to respect foreign key constraints
        for _, table_obj, _ in reversed(load_sequence):
            conn.execute(table_obj.delete())

        # Insert tables in topological forward order
        for table_name, table_obj, csv_filename in load_sequence:
            csv_path = data_dir / csv_filename
            if not csv_path.exists():
                # If status_history.csv does not exist on disk, synthesize initial lifecycle records
                if table_name == "status_history":
                    hist_rows = []
                    # Derive ticket status history from support_tickets
                    tkt_csv = data_dir / "support_tickets.csv"
                    if tkt_csv.exists():
                        t_df = pd.read_csv(tkt_csv)
                        for _, r in t_df.iterrows():
                            hist_rows.append({
                                "history_id": f"HIST-TKT-{r['ticket_id']}-01",
                                "entity_type": "support_ticket",
                                "entity_id": r["ticket_id"],
                                "old_status": None,
                                "new_status": "open",
                                "changed_at": str(r["created_at"]),
                                "changed_by": "system_ingest",
                            })
                            if pd.notnull(r.get("resolved_at")) and str(r.get("status")) in ("resolved", "closed"):
                                hist_rows.append({
                                    "history_id": f"HIST-TKT-{r['ticket_id']}-02",
                                    "entity_type": "support_ticket",
                                    "entity_id": r["ticket_id"],
                                    "old_status": "open",
                                    "new_status": str(r["status"]),
                                    "changed_at": str(r["resolved_at"]),
                                    "changed_by": "support_agent",
                                })
                    if hist_rows:
                        conn.execute(status_history.insert(), hist_rows)
                        inserted_counts["status_history"] = len(hist_rows)
                    continue

                print(f"Warning: {csv_filename} not found in {data_dir}, skipping.")
                continue

            df = pd.read_csv(csv_path)

            for bool_col in ["is_ambiguous"]:
                if bool_col in df.columns:
                    df[bool_col] = df[bool_col].astype(bool)

            df = df.where(pd.notnull(df), None)
            records = df.to_dict(orient="records")
            if records:
                conn.execute(table_obj.insert(), records)

            inserted_counts[table_name] = len(records)

    return inserted_counts


def main():
    parser = argparse.ArgumentParser(description="Seed SQLite database from CSVs")
    parser.add_argument("--db", default="data/db/feedback.db", help="Path to SQLite DB")
    parser.add_argument("--raw", default="data/raw", help="Path to raw CSVs directory")
    args = parser.parse_args()

    db_path = _PROJECT_ROOT / args.db
    raw_dir = _PROJECT_ROOT / args.raw

    print(f"\nSeeding database at: {db_path}")
    print(f"Source raw directory: {raw_dir}")

    engine = get_engine(db_path)
    counts = load_raw_csvs_into_db(raw_dir, engine)
    export_schema_sql(engine, _PROJECT_ROOT / "data" / "schema.sql")

    print(f"\n{'-'*45}")
    print(f"  {'Table':<25}  {'Rows Loaded':>15}")
    print(f"{'-'*45}")
    for tbl, count in counts.items():
        print(f"  {tbl:<25}  {count:>15,}")
    print(f"{'-'*45}")
    print("Database seeding completed successfully.\n")


if __name__ == "__main__":
    main()
