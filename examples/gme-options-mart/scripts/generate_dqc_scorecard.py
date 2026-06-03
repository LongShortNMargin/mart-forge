#!/usr/bin/env python3
"""Generate dqc_scorecard.json from dbt's target/run_results.json.

Walks the 8 DQC control classes (PK, FK, Freshness, Volume, Ranges,
Duplicates, Null-Rate, Reconciliation) against the linked dbt tests
defined for the GME options mart, and emits a per-row scorecard in the
shape prescribed by skills/lifecycle/mart-dqc/SKILL.md.

The control rows are declared inline here (single source of truth for
the gme-options-mart audit), so a fresh `dbt test` followed by
`python scripts/generate_dqc_scorecard.py` reproduces the scorecard.

Usage:
    python scripts/generate_dqc_scorecard.py [--run-results PATH] [--out PATH]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

# control_class -> (id, table, linked dbt test short-names, rationale_if_na)
# A linked test entry is either a generic-test short name (test alias
# minus the `test.gme_options_mart.` prefix) OR a singular .sql filename
# without extension. The matcher accepts either an exact match or a
# prefix match against the dbt-uniquified short name.
CONTROL_ROWS = [
    # ---- PK Integrity -------------------------------------------------
    {
        "id": "pk_integrity_ods_chain_snapshot",
        "control_class": "PK Integrity",
        "table": "gme_ods_options_chain_snapshot",
        "linked_dbt_tests": [
            "not_null_gme_ods_options_chain_snapshot_trading_date",
            "not_null_gme_ods_options_chain_snapshot_expiry_date",
            "not_null_gme_ods_options_chain_snapshot_strike",
            "not_null_gme_ods_options_chain_snapshot_option_type",
            "pk_chain_snapshot_compound_unique",
        ],
    },
    {
        "id": "pk_integrity_ods_price_history",
        "control_class": "PK Integrity",
        "table": "gme_ods_price_history",
        "linked_dbt_tests": [
            "not_null_gme_ods_price_history_trading_date",
            "unique_gme_ods_price_history_trading_date",
        ],
    },
    {
        "id": "pk_integrity_dim_date",
        "control_class": "PK Integrity",
        "table": "dim_date",
        "linked_dbt_tests": [
            "not_null_dim_date_date_sk",
            "unique_dim_date_date_sk",
            "not_null_dim_date_calendar_date",
            "unique_dim_date_calendar_date",
        ],
    },
    {
        "id": "pk_integrity_dim_holidays",
        "control_class": "PK Integrity",
        "table": "dim_holidays",
        "linked_dbt_tests": [
            "not_null_dim_holidays_holiday_date",
            "unique_dim_holidays_holiday_date",
        ],
    },
    {
        "id": "pk_integrity_dwd_price_eod",
        "control_class": "PK Integrity",
        "table": "gme_dwd_price_eod",
        "linked_dbt_tests": [
            "not_null_gme_dwd_price_eod_trading_date",
            "unique_gme_dwd_price_eod_trading_date",
        ],
    },
    {
        "id": "pk_integrity_dws_dealer_gamma",
        "control_class": "PK Integrity",
        "table": "gme_dws_perf_dealer_gamma",
        "linked_dbt_tests": [
            "not_null_gme_dws_perf_dealer_gamma_trading_date",
            "unique_gme_dws_perf_dealer_gamma_trading_date",
        ],
    },
    {
        "id": "pk_integrity_dws_dealer_gamma_front_month",
        "control_class": "PK Integrity",
        "table": "gme_dws_perf_dealer_gamma_front_month",
        "linked_dbt_tests": [
            "not_null_gme_dws_perf_dealer_gamma_front_month_trading_date",
            "unique_gme_dws_perf_dealer_gamma_front_month_trading_date",
        ],
    },
    {
        "id": "pk_integrity_dws_implied_vol",
        "control_class": "PK Integrity",
        "table": "gme_dws_perf_implied_vol",
        "linked_dbt_tests": [
            "not_null_gme_dws_perf_implied_vol_trading_date",
            "unique_gme_dws_perf_implied_vol_trading_date",
        ],
    },
    # ---- FK Integrity -------------------------------------------------
    {
        "id": "fk_integrity_dwd_chain_date_sk",
        "control_class": "FK Integrity",
        "table": "gme_dwd_options_chain",
        "linked_dbt_tests": [
            "relationships_gme_dwd_options_chain_date_sk__date_sk__ref_dim_date_",
        ],
    },
    {
        "id": "fk_integrity_dwd_chain_expiry_date_sk",
        "control_class": "FK Integrity",
        "table": "gme_dwd_options_chain",
        "linked_dbt_tests": [
            "relationships_gme_dwd_options_chain_expiry_date_sk__date_sk__ref_dim_date_",
        ],
    },
    # ---- Freshness ----------------------------------------------------
    {
        "id": "freshness_ods_chain",
        "control_class": "Freshness",
        "table": "gme_ods_options_chain_snapshot",
        "linked_dbt_tests": [
            "freshness_chain",
        ],
    },
    {
        "id": "freshness_ods_price_history",
        "control_class": "Freshness",
        "table": "gme_ods_price_history",
        "linked_dbt_tests": [
            "freshness_price",
        ],
    },
    {
        "id": "freshness_ads_dashboard",
        "control_class": "Freshness",
        "table": "gme_ads_market_dashboard",
        "linked_dbt_tests": [
            "is_stale_freshness_contract",
        ],
    },
    # ---- Completeness / Volume ---------------------------------------
    {
        "id": "volume_ods_chain",
        "control_class": "Completeness / Volume",
        "table": "gme_ods_options_chain_snapshot",
        "linked_dbt_tests": [
            "volume_chain",
        ],
    },
    # ---- Accepted Ranges ---------------------------------------------
    {
        "id": "accepted_range_dwd_chain_open_interest",
        "control_class": "Accepted Ranges",
        "table": "gme_dwd_options_chain",
        "linked_dbt_tests": [
            "accepted_range_open_interest",
            "not_null_gme_dwd_options_chain_open_interest",
        ],
    },
    {
        "id": "accepted_range_dwd_chain_implied_volatility",
        "control_class": "Accepted Ranges",
        "table": "gme_dwd_options_chain",
        "linked_dbt_tests": [
            "accepted_range_implied_volatility",
        ],
    },
    {
        "id": "accepted_values_dwd_chain_option_type",
        "control_class": "Accepted Ranges",
        "table": "gme_dwd_options_chain",
        "linked_dbt_tests": [
            "accepted_values_gme_dwd_options_chain_option_type__call__put",
            "not_null_gme_dwd_options_chain_option_type",
        ],
    },
    {
        "id": "accepted_values_dwd_greeks_sign_dealer",
        "control_class": "Accepted Ranges",
        "table": "gme_dwd_options_chain_greeks",
        "linked_dbt_tests": [
            "accepted_values_gme_dwd_options_chain_greeks_sign_dealer___1__1",
            "not_null_gme_dwd_options_chain_greeks_sign_dealer",
        ],
    },
    {
        "id": "accepted_values_ods_chain_option_type",
        "control_class": "Accepted Ranges",
        "table": "gme_ods_options_chain_snapshot",
        "linked_dbt_tests": [
            "accepted_values_gme_ods_options_chain_snapshot_option_type__call__put",
        ],
    },
    {
        "id": "accepted_values_dws_dealer_gamma_scope_label",
        "control_class": "Accepted Ranges",
        "table": "gme_dws_perf_dealer_gamma",
        "linked_dbt_tests": [
            "accepted_values_gme_dws_perf_dealer_gamma_scope_label__full_chain",
        ],
    },
    {
        "id": "accepted_values_dws_dealer_gamma_front_month_scope_label",
        "control_class": "Accepted Ranges",
        "table": "gme_dws_perf_dealer_gamma_front_month",
        "linked_dbt_tests": [
            "accepted_values_gme_dws_perf_dealer_gamma_front_month_scope_label__front_month_only",
        ],
    },
    {
        "id": "accepted_values_dws_implied_vol_iv_rank_label",
        "control_class": "Accepted Ranges",
        "table": "gme_dws_perf_implied_vol",
        "linked_dbt_tests": [
            "accepted_values_gme_dws_perf_implied_vol_iv_rank_label__provisional__final",
        ],
    },
    {
        "id": "accepted_values_dim_macro_events_event_type",
        "control_class": "Accepted Ranges",
        "table": "dim_macro_events",
        "linked_dbt_tests": [
            "accepted_values_dim_macro_events_event_type__FOMC__CPI__EARNINGS",
            "not_null_dim_macro_events_event_type",
            "not_null_dim_macro_events_event_date",
        ],
    },
    {
        "id": "accepted_values_ads_iv_rank_link_status_active",
        "control_class": "Accepted Ranges",
        "table": "gme_ads_market_dashboard",
        "linked_dbt_tests": [
            "accepted_values_gme_ads_market_dashboard_iv_rank_link_status_active__unsupported__proxy",
        ],
    },
    # ---- Duplicate Detection -----------------------------------------
    {
        "id": "duplicate_detection_dwd_chain",
        "control_class": "Duplicate Detection",
        "table": "gme_dwd_options_chain",
        "linked_dbt_tests": [
            "dwd_chain_no_dupes",
        ],
    },
    # ---- Null-Rate Threshold -----------------------------------------
    {
        "id": "null_rate_dwd_chain_required",
        "control_class": "Null-Rate Threshold",
        "table": "gme_dwd_options_chain",
        "linked_dbt_tests": [
            "not_null_gme_dwd_options_chain_trading_date",
            "not_null_gme_dwd_options_chain_option_type",
            "not_null_gme_dwd_options_chain_open_interest",
        ],
    },
    {
        "id": "null_rate_dwd_greeks_required",
        "control_class": "Null-Rate Threshold",
        "table": "gme_dwd_options_chain_greeks",
        "linked_dbt_tests": [
            "not_null_gme_dwd_options_chain_greeks_trading_date",
            "not_null_gme_dwd_options_chain_greeks_sign_dealer",
        ],
    },
    {
        "id": "null_rate_dws_max_pain_strike",
        "control_class": "Null-Rate Threshold",
        "table": "gme_dws_perf_max_pain",
        "linked_dbt_tests": [
            "not_null_gme_dws_perf_max_pain_max_pain_strike",
        ],
    },
    {
        "id": "null_rate_ads_trading_date",
        "control_class": "Null-Rate Threshold",
        "table": "gme_ads_market_dashboard",
        "linked_dbt_tests": [
            "not_null_gme_ads_market_dashboard_trading_date",
        ],
    },
    # ---- Business Reconciliation -------------------------------------
    {
        "id": "business_recon_max_pain_in_strike_set",
        "control_class": "Business Reconciliation",
        "table": "gme_dws_perf_max_pain",
        "linked_dbt_tests": [
            "max_pain_in_strike_set",
            "max_pain_fixture_asymmetric_chain",
        ],
    },
    {
        "id": "business_recon_dealer_net_gamma_neq_net_gex",
        "control_class": "Business Reconciliation",
        "table": "gme_dws_perf_dealer_gamma_front_month",
        "linked_dbt_tests": [
            "dealer_net_gamma_neq_net_gex",
        ],
    },
    {
        "id": "business_recon_dealer_net_gamma_scope_distinct",
        "control_class": "Business Reconciliation",
        "table": "gme_dws_perf_dealer_gamma_front_month",
        "linked_dbt_tests": [
            "dealer_net_gamma_scope_distinct",
        ],
    },
    {
        "id": "business_recon_iv_rank_label_final",
        "control_class": "Business Reconciliation",
        "table": "gme_dws_perf_implied_vol",
        "linked_dbt_tests": [
            "iv_rank_implies_label_final",
            "iv_rank_fixture_synthetic_400d",
        ],
    },
    {
        "id": "business_recon_gex_zero_cross_in_strike_set",
        "control_class": "Business Reconciliation",
        "table": "gme_dws_perf_dealer_gamma_front_month",
        "linked_dbt_tests": [
            "gex_zero_cross_in_strike_set",
        ],
    },
    {
        "id": "business_recon_iv_rank_link_status_active_lifecycle",
        "control_class": "Business Reconciliation",
        "table": "gme_ads_market_dashboard",
        "linked_dbt_tests": [
            "iv_rank_lifecycle_predicate",
        ],
    },
    {
        "id": "business_recon_t1_6b_rate_floor",
        "control_class": "Business Reconciliation",
        "table": "gme_dws_perf_dealer_gamma",
        "linked_dbt_tests": [],
        "status_override": "not_applicable",
        "rationale": (
            "T1.6b parametric rate-sensitivity test (TDD §T-18 row "
            "business_recon_t1_6b_floor / §T-19 TC-14) is a Python test "
            "exercising the producer formula across r ∈ {0.03, 0.045, "
            "0.06} with a $1e6 denominator floor. It is not expressible "
            "as a single dbt test against the warehouse output (which "
            "is pinned to r=0.045 in dbt vars), and is therefore tracked "
            "as a CI-side check executed alongside dbt. See "
            "examples/gme-options-mart/tests/test_net_gex_rate_sensitivity.py "
            "follow-up tracked under Phase D OQ-2 (Fred 3M T-bill "
            "ingest) — the Python harness will land in the same dispatch."
        ),
    },
]


def normalize_unique_id(uid: str) -> str:
    """Strip the dbt project prefix and the trailing uniqueness hash."""
    prefix = "test.gme_options_mart."
    short = uid[len(prefix):] if uid.startswith(prefix) else uid
    # Generic tests have a trailing `.<10-char-hash>` segment; singular
    # tests do not. We compare on the hash-stripped form so callers can
    # write `not_null_foo_bar` without knowing the dbt hash.
    parts = short.split(".")
    if len(parts) > 1 and len(parts[-1]) == 10 and all(
        c.isalnum() for c in parts[-1]
    ):
        return ".".join(parts[:-1])
    return short


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-results",
        default="target/run_results.json",
        help="Path to dbt's run_results.json",
    )
    parser.add_argument(
        "--out",
        default="dqc_scorecard.json",
        help="Where to write the scorecard",
    )
    args = parser.parse_args()

    run_results_path = Path(args.run_results)
    if not run_results_path.exists():
        print(
            f"error: {run_results_path} not found — run "
            "`dbt seed && dbt run && dbt test` first.",
            file=sys.stderr,
        )
        return 1

    with run_results_path.open() as f:
        rr = json.load(f)

    test_status = {}
    for r in rr["results"]:
        short = normalize_unique_id(r["unique_id"])
        test_status[short] = r["status"]

    last_dbt_run = rr["metadata"]["generated_at"]

    rows = []
    summary = {
        "pass_count": 0,
        "warn_count": 0,
        "error_count": 0,
        "not_applicable_count": 0,
        "pending_count": 0,
    }
    missing_links = []

    for spec in CONTROL_ROWS:
        linked = spec["linked_dbt_tests"]
        status_override = spec.get("status_override")
        statuses = []
        for t in linked:
            if t in test_status:
                statuses.append(test_status[t])
            else:
                statuses.append("missing")
                missing_links.append((spec["id"], t))

        if status_override == "not_applicable":
            status = "not_applicable"
        elif not linked:
            status = "pending"
        elif "missing" in statuses:
            status = "pending"
        elif any(s in ("error", "fail") for s in statuses):
            status = "error"
        elif any(s == "warn" for s in statuses):
            status = "warn"
        else:
            status = "pass"

        row = {
            "id": spec["id"],
            "control_class": spec["control_class"],
            "table": spec["table"],
            "status": status,
            "linked_dbt_tests": linked,
            "last_dbt_run": last_dbt_run,
            "rationale": spec.get("rationale"),
            "attempts": [],
        }
        rows.append(row)
        summary[f"{status}_count"] += 1

    out = {
        "schema_version": "1.0",
        "mart": "gme-options-mart",
        "phase": "D_dqc_complete",
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "last_dbt_run": last_dbt_run,
        "controls": rows,
        "summary": summary,
        "totals": {
            "planned": len(rows),
            "passed": summary["pass_count"],
            "failed": summary["error_count"],
        },
    }

    with Path(args.out).open("w") as f:
        json.dump(out, f, indent=2)
        f.write("\n")

    print("DQC Run Complete")
    print(f"  pass:           {summary['pass_count']}")
    print(f"  warn:           {summary['warn_count']}")
    print(f"  error:          {summary['error_count']}")
    print(f"  not_applicable: {summary['not_applicable_count']}")
    print(f"  pending:        {summary['pending_count']}")
    print(f"  total rows:     {len(rows)}")
    if missing_links:
        print()
        print("Missing test links (control → expected test):")
        for cid, t in missing_links:
            print(f"  {cid:60s}  {t}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
