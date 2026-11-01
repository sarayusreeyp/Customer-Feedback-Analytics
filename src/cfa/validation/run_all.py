"""
run_all.py — Orchestrates all data validation checks.

Runs:
  1. PK uniqueness checks
  2. FK referential integrity checks
  3. Enum & pattern conformance checks
  4. Derived sentiment reconciliation & arithmetic reconciliation checks
  5. Date ordering & temporal integrity checks
  6. Lifecycle state consistency checks
  7. Semantic duplicate record checks
  8. Deterministic seed reproducibility test
  9. Exports machine-readable validation summary (reports/validation_summary.json)

Usage:
  python -m cfa.validation.run_all
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from cfa.db.seed import get_engine
from cfa.validation.pk_fk_checks import check_pk_uniqueness, check_fk_integrity
from cfa.validation.enum_checks import (
    check_allowed_enums,
    check_derived_rules_reconciliation,
    check_date_ordering,
    check_lifecycle_consistency,
    check_database_duplicates,
)
from cfa.validation.reproducibility import check_seed_reproducibility


def run_all_validations(
    db_path: Path | str,
    seed: int = 20261022,
    export_summary: bool = True
) -> bool:
    engine = get_engine(db_path)

    print(f"\n{'='*65}")
    print(f"  DATA QUALITY & VALIDATION REPORT")
    print(f"  Target DB: {db_path}")
    print(f"{'='*65}\n")

    results: dict = {
        "timestamp": datetime.now().isoformat(),
        "database": str(db_path),
        "seed": seed,
        "checks": {},
        "overall_status": "PASS",
    }
    all_passed = True

    # 1. Primary Key Uniqueness
    print("1. Checking Primary Key Uniqueness...", end=" ")
    pk_violations = check_pk_uniqueness(engine)
    if not pk_violations:
        print("[PASS]")
        results["checks"]["pk_uniqueness"] = {"status": "PASS", "violations": 0}
    else:
        print("[FAIL]")
        all_passed = False
        results["checks"]["pk_uniqueness"] = {"status": "FAIL", "violations": len(pk_violations), "details": pk_violations}
        for v in pk_violations:
            print(f"   - Table {v['table']}: {v['violation_count']} PK violations on {v['pk_columns']}")

    # 2. Foreign Key Referential Integrity
    print("2. Checking Foreign Key Integrity...", end=" ")
    fk_violations = check_fk_integrity(engine)
    if not fk_violations:
        print("[PASS]")
        results["checks"]["fk_integrity"] = {"status": "PASS", "violations": 0}
    else:
        print("[FAIL]")
        all_passed = False
        results["checks"]["fk_integrity"] = {"status": "FAIL", "violations": len(fk_violations), "details": fk_violations}
        for v in fk_violations:
            print(f"   - {v}")

    # 3. Enum & Pattern Conformance
    print("3. Checking Enums & Format Patterns...", end=" ")
    enum_violations = check_allowed_enums(engine)
    if not enum_violations:
        print("[PASS]")
        results["checks"]["enum_and_patterns"] = {"status": "PASS", "violations": 0}
    else:
        print("[FAIL]")
        all_passed = False
        results["checks"]["enum_and_patterns"] = {"status": "FAIL", "violations": len(enum_violations), "details": enum_violations}
        for v in enum_violations:
            print(f"   - Table {v['table']}, Col {v['column']}: invalid values found")

    # 4. Derived Rules & Arithmetic Reconciliation
    print("4. Checking Derived Rules & Arithmetic Reconciliation...", end=" ")
    rule_violations = check_derived_rules_reconciliation(engine)
    if not rule_violations:
        print("[PASS]")
        results["checks"]["derived_rules_and_arithmetic"] = {"status": "PASS", "violations": 0}
    else:
        print("[FAIL]")
        all_passed = False
        results["checks"]["derived_rules_and_arithmetic"] = {"status": "FAIL", "violations": len(rule_violations), "details": rule_violations}
        for v in rule_violations:
            print(f"   - Table {v['table']}: {v['mismatch_count']} mismatches in rule '{v['rule']}'")

    # 5. Date Ordering & Temporal Consistency
    print("5. Checking Date Ordering & Temporal Integrity...", end=" ")
    date_violations = check_date_ordering(engine)
    if not date_violations:
        print("[PASS]")
        results["checks"]["date_ordering"] = {"status": "PASS", "violations": 0}
    else:
        print("[FAIL]")
        all_passed = False
        results["checks"]["date_ordering"] = {"status": "FAIL", "violations": len(date_violations), "details": date_violations}
        for v in date_violations:
            print(f"   - Table {v['table']}: {v['violation_count']} date order violations ({v['rule']})")

    # 6. Lifecycle Consistency
    print("6. Checking Lifecycle Transitions...", end=" ")
    lifecycle_violations = check_lifecycle_consistency(engine)
    if not lifecycle_violations:
        print("[PASS]")
        results["checks"]["lifecycle_transitions"] = {"status": "PASS", "violations": 0}
    else:
        print("[FAIL]")
        all_passed = False
        results["checks"]["lifecycle_transitions"] = {"status": "FAIL", "violations": len(lifecycle_violations), "details": lifecycle_violations}
        for v in lifecycle_violations:
            print(f"   - Table {v['table']}: {v['violation_count']} lifecycle violations ({v['rule']})")

    # 7. Semantic Duplicate Records
    print("7. Checking Semantic Duplicate Records in Database...", end=" ")
    dup_violations = check_database_duplicates(engine)
    if not dup_violations:
        print("[PASS]")
        results["checks"]["database_duplicates"] = {"status": "PASS", "violations": 0}
    else:
        print("[FAIL]")
        all_passed = False
        results["checks"]["database_duplicates"] = {"status": "FAIL", "violations": len(dup_violations), "details": dup_violations}
        for v in dup_violations:
            print(f"   - Table {v['table']}: {v['duplicate_clusters']} duplicate key groups ({v['columns']})")

    # 8. Reproducibility Check
    print("8. Checking Deterministic Seed Reproducibility...", end=" ")
    repro = check_seed_reproducibility(seed=seed, sample_volume=100)
    if repro["is_reproducible"]:
        print("[PASS]")
        results["checks"]["reproducibility"] = {"status": "PASS", "seed": seed, "tables_verified": len(repro["tables_checked"])}
    else:
        print("[FAIL]")
        all_passed = False
        results["checks"]["reproducibility"] = {"status": "FAIL", "mismatches": repro["mismatches"]}
        for m in repro["mismatches"]:
            print(f"   - Checksum mismatch in table {m['table']}")

    results["overall_status"] = "PASS" if all_passed else "FAIL"

    # Export Summary Report
    if export_summary:
        summary_dir = _PROJECT_ROOT / "reports"
        summary_dir.mkdir(parents=True, exist_ok=True)
        summary_file = summary_dir / "validation_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"\nValidation summary written to: {summary_file}")

    print(f"\n{'-'*65}")
    if all_passed:
        print("  OVERALL STATUS: ALL CHECKS PASSED (Data is compliant & integral)")
    else:
        print("  OVERALL STATUS: VALIDATION FAILURES DETECTED")
    print(f"{'-'*65}\n")

    return all_passed


def main():
    parser = argparse.ArgumentParser(description="Run all data quality and validation checks")
    parser.add_argument("--db", default="data/db/feedback.db", help="Path to SQLite database")
    parser.add_argument("--seed", type=int, default=20261022, help="Seed to test reproducibility")
    args = parser.parse_args()

    db_path = _PROJECT_ROOT / args.db
    success = run_all_validations(db_path, seed=args.seed)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
