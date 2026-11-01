"""
pk_fk_checks.py — Primary key uniqueness and foreign key integrity checks.

Validates that:
  - All primary keys across all tables are non-null and strictly unique.
  - All foreign key relationships point to existing parent IDs in the referenced tables.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import inspect, text


def check_pk_uniqueness(engine) -> list[dict]:
    """
    Check that all tables with primary keys have no duplicates and no NULL PKs.
    Returns a list of violation dicts (empty if all pass).
    """
    inspector = inspect(engine)
    violations = []

    with engine.connect() as conn:
        for table_name in inspector.get_table_names():
            pk_constraint = inspector.get_pk_constraint(table_name)
            pk_cols = pk_constraint.get("constrained_columns", [])
            if not pk_cols:
                continue

            cols_str = ", ".join(f'"{col}"' for col in pk_cols)
            query = f"""
                SELECT {cols_str}, COUNT(*) as cnt
                FROM "{table_name}"
                GROUP BY {cols_str}
                HAVING COUNT(*) > 1
                   OR { ' OR '.join(f'"{col}" IS NULL' for col in pk_cols) }
            """
            result = conn.execute(text(query)).fetchall()
            if result:
                violations.append({
                    "table": table_name,
                    "pk_columns": pk_cols,
                    "violation_count": len(result),
                    "details": [dict(r._mapping) for r in result[:5]],
                })

    return violations


def check_fk_integrity(engine) -> list[dict]:
    """
    Check that every foreign key in child tables references an existing row in the parent table.
    Uses SQLite PRAGMA foreign_key_check() as well as manual orphan queries.
    Returns a list of violation dicts (empty if all pass).
    """
    inspector = inspect(engine)
    violations = []

    with engine.connect() as conn:
        # SQLite built-in foreign key check
        pragma_results = conn.execute(text("PRAGMA foreign_key_check;")).fetchall()
        if pragma_results:
            for row in pragma_results:
                table, rowid, parent, fkid = row
                violations.append({
                    "type": "pragma_fk_failure",
                    "table": table,
                    "rowid": rowid,
                    "parent_table": parent,
                    "fkid": fkid,
                })

        # Explicit JOIN verification for orphan detection
        for child_table in inspector.get_table_names():
            for fk in inspector.get_foreign_keys(child_table):
                parent_table = fk["referred_table"]
                constrained = fk["constrained_columns"]
                referred = fk["referred_columns"]

                if not parent_table or not constrained or not referred:
                    continue

                join_conditions = " AND ".join(
                    f'child."{c}" = parent."{r}"'
                    for c, r in zip(constrained, referred)
                )
                child_null_check = " OR ".join(f'child."{c}" IS NOT NULL' for c in constrained)

                query = f"""
                    SELECT child."{constrained[0]}" as orphan_id
                    FROM "{child_table}" child
                    LEFT JOIN "{parent_table}" parent
                    ON {join_conditions}
                    WHERE parent."{referred[0]}" IS NULL
                      AND ({child_null_check})
                    LIMIT 5
                """
                orphans = conn.execute(text(query)).fetchall()
                if orphans:
                    violations.append({
                        "type": "orphan_foreign_key",
                        "child_table": child_table,
                        "parent_table": parent_table,
                        "foreign_keys": constrained,
                        "orphan_count": len(orphans),
                        "sample_orphans": [r[0] for r in orphans],
                    })

    return violations
