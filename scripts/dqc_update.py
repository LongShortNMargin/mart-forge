"""
DQC Scorecard Update Script

Reads dbt test results from target/run_results.json and generates/updates
dqc_scorecard.json with mechanically-linked test statuses.

The scorecard is never hand-edited — it reflects actual dbt test outcomes.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

CONTROL_CLASS_MAP = {
    "not_null": "pk_integrity",
    "unique": "pk_integrity",
    "relationships": "fk_integrity",
    "accepted_values": "accepted_ranges",
}

SINGULAR_TEST_PREFIXES = {
    "test_freshness": "freshness",
    "test_completeness": "completeness",
    "test_volume": "completeness",
    "test_duplicate": "duplicate_detection",
    "test_null_rate": "null_rate_threshold",
    "test_reconciliation": "business_reconciliation",
    "test_range": "accepted_ranges",
}


def classify_test(test_name: str) -> str:
    for prefix, control_class in SINGULAR_TEST_PREFIXES.items():
        if test_name.startswith(prefix):
            return control_class
    for keyword, control_class in CONTROL_CLASS_MAP.items():
        if keyword in test_name:
            return control_class
    return "unclassified"


def load_run_results(path: Path) -> list[dict]:
    if not path.exists():
        print(f"Warning: {path} not found. Run `dbt test` first.")
        return []
    data = json.loads(path.read_text())
    return data.get("results", [])


def build_scorecard(results: list[dict], mart_name: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    controls: dict[str, dict] = {}

    for result in results:
        test_name = result.get("unique_id", "").split(".")[-1]
        status = result.get("status", "error")
        dbt_status = "pass" if status == "pass" else "fail"

        control_class = classify_test(test_name)
        key = f"{control_class}_{test_name}"

        if control_class not in controls:
            controls[control_class] = {
                "class": control_class,
                "metric": test_name,
                "status": dbt_status,
                "linked_dbt_tests": [test_name],
                "last_dbt_run": now,
            }
        else:
            controls[control_class]["linked_dbt_tests"].append(test_name)
            if dbt_status == "fail":
                controls[control_class]["status"] = "fail"

    return {
        "mart": mart_name,
        "generated_at": now,
        "controls": list(controls.values()),
    }


def main():
    run_results_path = Path("target/run_results.json")
    scorecard_path = Path("dqc_scorecard.json")
    mart_name = "unknown"

    mart_yml = Path("mart.yml")
    if mart_yml.exists():
        import yaml

        config = yaml.safe_load(mart_yml.read_text())
        mart_name = config.get("mart", {}).get("name", "unknown")

    results = load_run_results(run_results_path)
    if not results:
        print("No test results found. Generating empty scorecard template.")
        scorecard = {
            "mart": mart_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "controls": [],
        }
    else:
        scorecard = build_scorecard(results, mart_name)

    scorecard_path.write_text(json.dumps(scorecard, indent=2))
    print(f"DQC scorecard written to {scorecard_path}")
    print(f"  Controls: {len(scorecard['controls'])}")

    fail_count = sum(1 for c in scorecard["controls"] if c["status"] == "fail")
    if fail_count:
        print(f"  FAILURES: {fail_count} controls failed")
        sys.exit(1)
    else:
        print("  All controls pass")


if __name__ == "__main__":
    main()
