#!/usr/bin/env python3
"""Post-dbt-test DQC scorecard updater.

Reads dbt's ``target/run_results.json``, maps each test to a DQC control
class, and updates ``dqc_scorecard.json`` with current pass/fail status.

Designed to run as a post-hook after ``dbt test``.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Canonical DQC control classes
# ---------------------------------------------------------------------------
CONTROL_CLASSES = {
    "pk_integrity",
    "fk_integrity",
    "freshness",
    "completeness",
    "accepted_ranges",
    "duplicate_detection",
    "null_rate",
    "business_reconciliation",
}

# ---------------------------------------------------------------------------
# Heuristic mapping: regex on test name -> control class
# ---------------------------------------------------------------------------
TEST_CLASS_MAP: List[tuple] = [
    (re.compile(r"unique|primary_key|pk_integrity", re.IGNORECASE), "pk_integrity"),
    (re.compile(r"relationships|fk_integrity|foreign_key", re.IGNORECASE), "fk_integrity"),
    (re.compile(r"freshness|recency|stale", re.IGNORECASE), "freshness"),
    (re.compile(r"not_null|completeness|missing", re.IGNORECASE), "completeness"),
    (re.compile(r"accepted_values|accepted_range|range_check", re.IGNORECASE), "accepted_ranges"),
    (re.compile(r"duplicate|dedup|duplicate_detection", re.IGNORECASE), "duplicate_detection"),
    (re.compile(r"null_rate|null_pct|null_ratio", re.IGNORECASE), "null_rate"),
    (re.compile(r"reconcil|recon|business_reconciliation", re.IGNORECASE), "business_reconciliation"),
]


def classify_test(test_name: str) -> Optional[str]:
    """Map a dbt test name to a DQC control class, or None if unclassified."""
    for pattern, cls in TEST_CLASS_MAP:
        if pattern.search(test_name):
            return cls
    return None


def map_dbt_status(status: str) -> str:
    """Normalise dbt result status to DQC status vocabulary."""
    s = status.lower()
    if s == "pass":
        return "pass"
    elif s == "fail":
        return "fail"
    elif s in ("warn", "warning"):
        return "warn"
    else:
        return "error"


def load_json(path: Path) -> Any:
    """Load a JSON file or return None if it does not exist."""
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def build_empty_scorecard() -> Dict[str, Any]:
    """Return a fresh scorecard skeleton with one entry per control class."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "version": "1.0",
        "generated_at": now,
        "controls": {
            cls: {
                "status": "unknown",
                "last_dbt_run": None,
                "linked_dbt_tests": [],
            }
            for cls in sorted(CONTROL_CLASSES)
        },
    }


def update_scorecard(
    scorecard: Dict[str, Any],
    run_results: Dict[str, Any],
) -> Dict[str, Any]:
    """Merge dbt run results into the scorecard and return the updated copy."""
    now = datetime.now(timezone.utc).isoformat()
    controls = scorecard.setdefault("controls", {})

    # Ensure every canonical class exists
    for cls in CONTROL_CLASSES:
        controls.setdefault(cls, {
            "status": "unknown",
            "last_dbt_run": None,
            "linked_dbt_tests": [],
        })

    # Track per-class worst status for this run
    class_statuses: Dict[str, List[str]] = {cls: [] for cls in CONTROL_CLASSES}

    for result in run_results.get("results", []):
        unique_id: str = result.get("unique_id", "")
        test_name = unique_id.split(".")[-1] if unique_id else ""
        status = map_dbt_status(result.get("status", "error"))

        cls = classify_test(test_name) or classify_test(unique_id)
        if cls is None:
            continue

        class_statuses[cls].append(status)

        # Update linked tests (deduplicate)
        linked = controls[cls].setdefault("linked_dbt_tests", [])
        if unique_id and unique_id not in linked:
            linked.append(unique_id)

    # Resolve final status per class (worst-of)
    severity = {"pass": 0, "warn": 1, "fail": 2, "error": 3}

    for cls, statuses in class_statuses.items():
        if not statuses:
            continue
        worst = max(statuses, key=lambda s: severity.get(s, 3))
        controls[cls]["status"] = worst
        controls[cls]["last_dbt_run"] = now

    scorecard["generated_at"] = now
    return scorecard


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Update DQC scorecard from dbt run results."
    )
    parser.add_argument(
        "--target-path",
        default="target/run_results.json",
        help="Path to dbt run_results.json (default: target/run_results.json).",
    )
    parser.add_argument(
        "--scorecard-path",
        default="dqc_scorecard.json",
        help="Path to dqc_scorecard.json (default: dqc_scorecard.json).",
    )
    args = parser.parse_args()

    target_path = Path(args.target_path)
    scorecard_path = Path(args.scorecard_path)

    # Load dbt results
    run_results = load_json(target_path)
    if run_results is None:
        print(f"ERROR: dbt run results not found at {target_path}", file=sys.stderr)
        sys.exit(1)

    # Load or create scorecard
    scorecard = load_json(scorecard_path)
    if scorecard is None:
        print(f"Scorecard not found at {scorecard_path} -- creating new one.")
        scorecard = build_empty_scorecard()

    # Update
    scorecard = update_scorecard(scorecard, run_results)

    # Write back
    scorecard_path.parent.mkdir(parents=True, exist_ok=True)
    with scorecard_path.open("w", encoding="utf-8") as fh:
        json.dump(scorecard, fh, indent=2)
        fh.write("\n")

    print(f"DQC scorecard updated: {scorecard_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
