"""Scaffold workflow tests.

Tests structural contract validation, rejection of incomplete/undergraded
BRD/TDD, name sanitization, and generation of a complete runnable dbt
skeleton with SQL models, DQC assets, dashboard, and pipeline scripts.

Two scaffold paths:
  fixture=True  → CI smoke-fixture using built-in order/revenue templates.
  fixture=False → General contract-driven path (impl_contract.yml required).
"""

import json
import subprocess
from pathlib import Path

import pytest
import yaml

from mart_forge.scaffold import scaffold, _is_signed, _has_proxy_stamp, _validate_brd, _validate_tdd


VALID_BRD = """\
# Business Requirements — Test Mart

## B-1. Scope

This mart covers order processing for the generic test domain.

## B-2. Business Questions

| ID | Question | Priority |
|----|----------|----------|
| Q-1 | What is total daily revenue? | High |
| Q-2 | How many orders per day? | High |

## B-3. Metric Catalog

| Metric | source_type | link_status | Definition |
|--------|-------------|-------------|------------|
| M-1 Revenue | native | exact | Sum of order amounts from source |
| M-2 Order Count | derived | proxy | Count of distinct orders, advisory comparison only |

## B-4. Source-Link Evidence

| Metric | Source | Link | Evidence |
|--------|--------|------|----------|
| M-1 | orders.csv | exact | Field mapping: amount -> revenue |
| M-2 | calculated | proxy | Derived from count of ODS records |

Sign-off: APPROVED
Grade: A
"""

VALID_TDD = """\
# Technical Design Document — Test Mart

## T-1. Version History
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-01-01 | Test | Initial |

## T-2. Design Reasoning
Grain: one row per order line per day.

## T-3. Table Summary
| Table Name | Layer | Purpose | Grain | Materialization |
|------------|-------|---------|-------|-----------------|
| tst_ods_csv_sample | ODS | Raw ingestion | one row per record per pull_date | incremental |

## T-4. Data Architecture Diagram
ODS -> DWD -> DWS -> ADS, DIM referenced by DWD.

## T-5. Column Specification
Per-table specs follow in T-6 through T-11.

## T-6. ODS Table Design

| Field | Value |
|-------|-------|
| Source | csv_provider |
| Grain | One row per record per pull_date |
| Logical Partition | pull_date |
| Incremental Strategy | delete+insert |
| Unique Key | ['pull_date', 'record_id'] |
| Backfill | Full reload per partition |
| Restatement | Re-pull same partition date |
| Provenance Columns | provider, pull_ts_utc, quote_ts_utc, run_id |

Idempotence: Re-running same partition produces identical output.

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|------------|---------------|-------------|-------------|
| record_id | VARCHAR | Source record identifier | ORD-001 | source.record_id -> pass-through | csv |
| pull_date | DATE | Logical partition date | 2020-01-01 | source.pull_date -> pass-through | csv |
| amount | DECIMAL | Order amount | 99.50 | source.amount -> pass-through | csv |
| provider | VARCHAR | Source identifier | csv_provider | not_applicable — direct field | csv |

## T-7. Dimension Table Design

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|------------|---------------|-------------|-------------|
| date_sk | INTEGER | Surrogate key | 1 | row_number() over (order by calendar_date) | Generated |
| calendar_date | DATE | Calendar date | 2020-01-01 | not_applicable — direct field from seed | dim_date.csv |

## T-8. Fact Table Design (DWD)

| column_name | data_type | definition | example_value | calculation | data_source | source_type |
|-------------|-----------|------------|---------------|-------------|-------------|-------------|
| order_line_sk | VARCHAR | Surrogate key | abc123 | md5(record_id || pull_date) | derived | derived |
| date_key | INTEGER | FK to dim_date | 1 | coalesce(dim_date.date_sk, -1) | dim_date | native |
| amount | DECIMAL | Order amount | 99.50 | not_applicable — pass-through from ODS | ods | native |

Provenance columns: provider, pull_ts_utc, quote_ts_utc, run_id

## T-9. Count Aggregation Design (DWS)

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|------------|---------------|-------------|-------------|
| date_key | INTEGER | FK to dim_date | 1 | not_applicable — pass-through | DWD |
| order_count | BIGINT | Daily order count | 3 | COUNT(DISTINCT record_id) | DWD aggregation |
| daily_revenue | DECIMAL | Total daily revenue | 325.75 | SUM(amount) | DWD aggregation |

## T-10. Performance Aggregation Design (DWS)

not_applicable rationale: No performance/ratio metrics required for this basic order mart. All metrics are count and sum aggregations covered in T-9. Signed off.

## T-11. Presentation Table Design (ADS)

| column_name | data_type | definition | example_value | calculation | data_source | BRD_ref | link_status |
|-------------|-----------|------------|---------------|-------------|-------------|---------|-------------|
| calendar_date | DATE | Date context | 2020-01-01 | dim_date.calendar_date via join | dim_date | - | exact |
| order_count | BIGINT | Daily orders | 3 | dws.order_count via join | DWS | M-2 | proxy |
| daily_revenue | DECIMAL | Daily revenue | 325.75 | dws.daily_revenue via join | DWS | M-1 | exact |

## T-12. Physical Design
Column-level specs provided in T-6 through T-11.

## T-13. Implementation Specification
dbt model configuration per naming conventions.

## T-14. DQC Plan
All 8 control classes addressed per control catalog.

## T-15. Test Inventory
| Test Name | Type | Target Model |
|-----------|------|-------------|
| not_null_record_id | generic | ods |

## T-16. Operations
Daily at 06:00 UTC.

## T-17. Known Limitations
No external data sources for reconciliation.

Sign-off: APPROVED
Grade: A
"""


# -- case_volume BRD/TDD for the general contract-driven path -----------------

CASE_VOLUME_BRD = """\
# Business Requirements — Case Support Mart

## B-1. Scope

This mart tracks support case volume for the operations dashboard.

## B-2. Business Questions

| ID | Question | Priority |
|----|----------|----------|
| Q-1 | How many support cases per day? | High |

## B-3. Metric Catalog

| Metric | source_type | link_status | Definition |
|--------|-------------|-------------|------------|
| M-1 Case Volume | native | exact | Count of distinct support cases per day |

## B-4. Source-Link Evidence

| Metric | Source | Link | Evidence |
|--------|--------|------|----------|
| M-1 | case_system | exact | Direct field mapping: case_id -> count |

[ARGENT-PROXY 2026-05-20T10:00:00Z]
Sign-off: APPROVED
Grade: A
"""

CASE_VOLUME_TDD = """\
# Technical Design Document — Case Support Mart

## T-1. Version History
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-05-20 | Operator | Initial |

## T-2. Design Reasoning
Grain: one row per case per day.

## T-3. Table Summary
| Table Name | Layer | Purpose | Grain | Materialization |
|------------|-------|---------|-------|-----------------|
| cas_ods_cases | ODS | Raw ingestion | one row per case per pull_date | incremental |

## T-4. Data Architecture Diagram
ODS -> DWD -> DWS -> ADS, DIM referenced by DWD.

## T-5. Column Specification
Per-table specs follow in T-6 through T-11.

## T-6. ODS Table Design

| Field | Value |
|-------|-------|
| Source | case_system |
| Grain | One row per case per pull_date |
| Logical Partition | pull_date |
| Incremental Strategy | delete+insert |
| Unique Key | ['pull_date', 'record_id'] |
| Backfill | Full reload per partition |
| Restatement | Re-pull same partition date |
| Provenance Columns | provider, pull_ts_utc, quote_ts_utc, run_id |

Idempotence: Re-running same partition produces identical output.

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|------------|---------------|-------------|-------------|
| record_id | VARCHAR | Case identifier | CASE-001 | source.case_id -> pass-through | case_system |
| pull_date | DATE | Logical partition date | 2026-01-01 | source.pull_date -> pass-through | case_system |
| case_type | VARCHAR | Case category | billing | source.type -> pass-through | case_system |
| provider | VARCHAR | Source identifier | case_api | not_applicable — direct field | case_system |

## T-7. Dimension Table Design

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|------------|---------------|-------------|-------------|
| date_sk | INTEGER | Surrogate key | 1 | row_number() over (order by calendar_date) | Generated |
| calendar_date | DATE | Calendar date | 2026-01-01 | not_applicable — direct field from seed | dim_date.csv |

## T-8. Fact Table Design (DWD)

| column_name | data_type | definition | example_value | calculation | data_source | source_type |
|-------------|-----------|------------|---------------|-------------|-------------|-------------|
| case_sk | VARCHAR | Surrogate key | abc123 | md5(record_id || pull_date) | derived | derived |
| date_key | INTEGER | FK to dim_date | 1 | coalesce(dim_date.date_sk, -1) | dim_date | native |
| case_type | VARCHAR | Case category | billing | not_applicable — pass-through from ODS | ods | native |

Provenance columns: provider, pull_ts_utc, quote_ts_utc, run_id

## T-9. Count Aggregation Design (DWS)

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|------------|---------------|-------------|-------------|
| date_key | INTEGER | FK to dim_date | 1 | not_applicable — pass-through | DWD |
| case_volume | BIGINT | Daily case count | 42 | COUNT(DISTINCT record_id) | DWD aggregation |

## T-10. Performance Aggregation Design (DWS)

not_applicable rationale: No performance/ratio metrics required for this case volume mart. The only metric is a count aggregation covered in T-9. Signed off.

## T-11. Presentation Table Design (ADS)

| column_name | data_type | definition | example_value | calculation | data_source | BRD_ref | link_status |
|-------------|-----------|------------|---------------|-------------|-------------|---------|-------------|
| calendar_date | DATE | Date context | 2026-01-01 | dim_date.calendar_date via join | dim_date | - | exact |
| case_volume | BIGINT | Daily case count | 42 | dws.case_volume via join | DWS | M-1 | exact |

## T-12. Physical Design
Column-level specs provided in T-6 through T-11.

## T-13. Implementation Specification
dbt model configuration per naming conventions.

## T-14. DQC Plan
All 8 control classes addressed per control catalog.

## T-15. Test Inventory
| Test Name | Type | Target Model |
|-----------|------|-------------|
| not_null_record_id | generic | ods |

## T-16. Operations
Daily at 06:00 UTC.

## T-17. Known Limitations
No external data sources for reconciliation.

[ARGENT-PROXY 2026-05-20T10:00:00Z]
Sign-off: APPROVED
Grade: A
"""

CASE_VOLUME_CONTRACT = {
    "models": {
        "ods": {
            "name": "cas_ods_cases",
            "sql": (
                "{{ config(materialized='table') }}\n"
                "select\n"
                "    record_id,\n"
                "    cast(pull_date as date) as pull_date,\n"
                "    case_type,\n"
                "    provider,\n"
                "    cast(pull_ts_utc as timestamp) as pull_ts_utc,\n"
                "    cast(quote_ts_utc as timestamp) as quote_ts_utc,\n"
                "    run_id\n"
                "from {{ ref('raw_case_data') }}\n"
            ),
        },
        "dim": {"name": "cas_dim_date"},
        "dwd": {
            "name": "cas_dwd_cases_di",
            "sql": (
                "{{ config(materialized='table') }}\n"
                "with ods as (\n"
                "    select record_id, pull_date, case_type, provider,\n"
                "           pull_ts_utc, quote_ts_utc, run_id\n"
                "    from {{ ref('cas_ods_cases') }}\n"
                "),\n"
                "with_keys as (\n"
                "    select\n"
                "        md5(cast(record_id as varchar) || '|' || cast(pull_date as varchar)) as case_sk,\n"
                "        coalesce(d.date_sk, -1) as date_key,\n"
                "        s.record_id, s.case_type, s.provider,\n"
                "        s.pull_ts_utc, s.quote_ts_utc, s.run_id\n"
                "    from ods s\n"
                "    left join {{ ref('cas_dim_date') }} d on s.pull_date = d.calendar_date\n"
                ")\n"
                "select case_sk, date_key, record_id, case_type, provider,\n"
                "       pull_ts_utc, quote_ts_utc, run_id\n"
                "from with_keys\n"
            ),
        },
        "dws": {
            "name": "cas_dws_daily_cases_1d",
            "sql": (
                "{{ config(materialized='table') }}\n"
                "select\n"
                "    date_key,\n"
                "    count(distinct record_id) as case_volume,\n"
                "    current_timestamp as calculated_at\n"
                "from {{ ref('cas_dwd_cases_di') }}\n"
                "group by date_key\n"
            ),
        },
        "ads": {
            "name": "cas_ads_case_dashboard",
            "sql": (
                "{{ config(materialized='table') }}\n"
                "select\n"
                "    dt.calendar_date,\n"
                "    dt.day_name,\n"
                "    dt.is_business_day,\n"
                "    s.case_volume,\n"
                "    s.calculated_at\n"
                "from {{ ref('cas_dws_daily_cases_1d') }} s\n"
                "inner join {{ ref('cas_dim_date') }} dt on s.date_key = dt.date_sk\n"
            ),
        },
    },
    "metrics": [
        {"id": "M-1", "name": "Case Volume", "ads_column": "case_volume"},
    ],
    "visualizations": [
        {
            "metric_id": "M-1",
            "chart_type": "line",
            "x_column": "calendar_date",
            "y_column": "case_volume",
            "model": "cas_ads_case_dashboard",
            "title": "Case Volume Trend",
        },
    ],
    "seeds": [
        {"name": "raw_case_data", "path": "seeds/raw_case_data.csv"},
    ],
}

CASE_SEED_CSV = """\
record_id,pull_date,case_type,provider,pull_ts_utc,quote_ts_utc,run_id
CASE-001,2026-01-01,billing,case_api,2026-01-01 06:00:00,2026-01-01 05:55:00,run-001
CASE-002,2026-01-01,technical,case_api,2026-01-01 06:00:00,2026-01-01 05:55:00,run-001
CASE-003,2026-01-02,billing,case_api,2026-01-02 06:00:00,2026-01-02 05:55:00,run-002
CASE-004,2026-01-02,billing,case_api,2026-01-02 06:00:00,2026-01-02 05:55:00,run-002
CASE-005,2026-01-02,technical,case_api,2026-01-02 06:00:00,2026-01-02 05:55:00,run-002
"""


@pytest.fixture
def mart_dir(tmp_path):
    return tmp_path / "test_mart"


@pytest.fixture
def signed_mart(mart_dir):
    mart_dir.mkdir()
    (mart_dir / "brd.md").write_text(VALID_BRD)
    (mart_dir / "tdd.md").write_text(VALID_TDD)
    return mart_dir


@pytest.fixture
def case_volume_mart(mart_dir):
    """Mart directory for general contract-driven path with case_volume."""
    mart_dir.mkdir()
    (mart_dir / "brd.md").write_text(CASE_VOLUME_BRD)
    (mart_dir / "tdd.md").write_text(CASE_VOLUME_TDD)
    (mart_dir / "impl_contract.yml").write_text(
        yaml.dump(CASE_VOLUME_CONTRACT, default_flow_style=False, sort_keys=False)
    )
    seeds_dir = mart_dir / "seeds"
    seeds_dir.mkdir()
    (seeds_dir / "raw_case_data.csv").write_text(CASE_SEED_CSV)
    return mart_dir


class TestPlaceholderRejection:
    """Minimal approval-token documents must be rejected."""

    def test_rejects_token_only_brd(self, mart_dir):
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(
            "# BRD\n\nSign-off: APPROVED\nGrade: A\n"
        )
        (mart_dir / "tdd.md").write_text(VALID_TDD)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"], "Scaffold accepted a token-only BRD"
        assert any("B-" in e for e in result["errors"])

    def test_rejects_token_only_tdd(self, mart_dir):
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(
            "# TDD\n\nSign-off: APPROVED\nGrade: A\n"
        )
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"], "Scaffold accepted a token-only TDD"
        assert any("T-" in e for e in result["errors"])

    def test_rejects_partial_brd_missing_sections(self, mart_dir):
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(
            "# BRD\n\n## B-1. Scope\nSome scope text here.\n\nSign-off: APPROVED\nGrade: A\n"
        )
        (mart_dir / "tdd.md").write_text(VALID_TDD)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"], "Scaffold accepted BRD missing B-2..B-4"

    def test_rejects_brd_with_unverified(self, mart_dir):
        mart_dir.mkdir()
        brd_with_unverified = VALID_BRD.replace("exact", "unverified")
        (mart_dir / "brd.md").write_text(brd_with_unverified)
        (mart_dir / "tdd.md").write_text(VALID_TDD)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"], "Scaffold accepted BRD with unverified link_status"
        assert any("unverified" in e.lower() for e in result["errors"])

    def test_rejects_tdd_with_unverified(self, mart_dir):
        mart_dir.mkdir()
        tdd_with_unverified = VALID_TDD.replace("exact", "unverified")
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(tdd_with_unverified)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"], "Scaffold accepted TDD with unverified"

    def test_rejects_brd_missing_source_type(self, mart_dir):
        mart_dir.mkdir()
        brd_no_source = (
            VALID_BRD
            .replace("source_type", "category")
            .replace("native", "field")
            .replace("derived", "field")
        )
        (mart_dir / "brd.md").write_text(brd_no_source)
        (mart_dir / "tdd.md").write_text(VALID_TDD)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"], "Scaffold accepted BRD without source_type classification"


class TestGradeBRejection:
    """Grade B and below must be rejected."""

    def test_rejects_grade_b_brd(self, mart_dir):
        mart_dir.mkdir()
        grade_b_brd = VALID_BRD.replace("Grade: A", "Grade: B")
        (mart_dir / "brd.md").write_text(grade_b_brd)
        (mart_dir / "tdd.md").write_text(VALID_TDD)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"], "Scaffold accepted Grade B BRD"

    def test_rejects_grade_b_tdd(self, mart_dir):
        mart_dir.mkdir()
        grade_b_tdd = VALID_TDD.replace("Grade: A", "Grade: B")
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(grade_b_tdd)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"], "Scaffold accepted Grade B TDD"

    def test_rejects_grade_c(self, mart_dir):
        mart_dir.mkdir()
        grade_c_brd = VALID_BRD.replace("Grade: A", "Grade: C")
        (mart_dir / "brd.md").write_text(grade_c_brd)
        (mart_dir / "tdd.md").write_text(VALID_TDD)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"], "Scaffold accepted Grade C"


class TestBareContentRejection:
    """Bare heading vocabulary and bare N/A tokens must fail."""

    def test_rejects_brd_bare_headings(self, mart_dir):
        mart_dir.mkdir()
        bare_brd = (
            "# BRD\n\n"
            "## B-1\n\n"
            "## B-2\n\n"
            "## B-3\n\n"
            "## B-4\n\n"
            "Sign-off: APPROVED\nGrade: A\n"
        )
        (mart_dir / "brd.md").write_text(bare_brd)
        (mart_dir / "tdd.md").write_text(VALID_TDD)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"], "Scaffold accepted BRD with bare section headings"

    def test_rejects_tdd_bare_na(self, mart_dir):
        mart_dir.mkdir()
        bare_na_tdd = VALID_TDD.replace(
            "not_applicable rationale: No performance/ratio metrics required "
            "for this basic order mart. All metrics are count and sum "
            "aggregations covered in T-9. Signed off.",
            "not_applicable"
        )
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(bare_na_tdd)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"], "Scaffold accepted TDD with bare not_applicable (no rationale)"
        assert any("bare" in e.lower() or "rationale" in e.lower() for e in result["errors"])


class TestHardGateRejection:
    def test_rejects_missing_brd(self, mart_dir):
        mart_dir.mkdir()
        (mart_dir / "tdd.md").write_text(VALID_TDD)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"]
        assert any("BRD not found" in e for e in result["errors"])

    def test_rejects_unsigned_brd(self, mart_dir):
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text("# Draft BRD\nNo sign-off yet.\n")
        (mart_dir / "tdd.md").write_text(VALID_TDD)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"]
        assert any("not signed off" in e for e in result["errors"])

    def test_rejects_missing_tdd(self, mart_dir):
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(VALID_BRD)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"]
        assert any("TDD not found" in e for e in result["errors"])

    def test_rejects_unsigned_tdd(self, mart_dir):
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text("# Draft TDD\nNo sign-off yet.\n")
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"]
        assert any("not signed off" in e for e in result["errors"])

    def test_rejects_both_missing(self, mart_dir):
        mart_dir.mkdir()
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"]
        assert len(result["errors"]) >= 2

    def test_no_files_created_on_rejection(self, mart_dir):
        mart_dir.mkdir()
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert result["files_created"] == []


class TestSuccessfulScaffold:
    """Fixture scaffold path — CI smoke with built-in templates."""

    def test_scaffold_succeeds(self, signed_mart):
        result = scaffold(signed_mart, "test-mart", "tst", fixture=True)
        assert result["success"], f"Scaffold failed: {result['errors']}"
        assert result["errors"] == []
        assert len(result["files_created"]) > 0

    def test_dbt_project_yml_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst", fixture=True)
        dbt_project = signed_mart / "dbt_project.yml"
        assert dbt_project.exists()
        content = dbt_project.read_text()
        assert "test_mart" in content
        assert "model-paths" in content

    def test_dbt_project_name_sanitized(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst", fixture=True)
        content = (signed_mart / "dbt_project.yml").read_text()
        assert "test-mart" not in content, "dbt_project.yml has unsanitized kebab-case name"
        assert "test_mart" in content

    def test_profiles_yml_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst", fixture=True)
        profiles = signed_mart / "profiles.yml"
        assert profiles.exists()
        content = profiles.read_text()
        assert "test_mart" in content
        assert "duckdb" in content

    def test_model_sql_files_created_with_semantic_names(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst", fixture=True)
        expected_models = {
            "ods": "tst_ods_csv_sample.sql",
            "dim": "tst_dim_date.sql",
            "dwd": "tst_dwd_daily_sample_di.sql",
            "dws": "tst_dws_daily_revenue_1d.sql",
            "ads": "tst_ads_exec_dashboard.sql",
        }
        for layer, filename in expected_models.items():
            model_path = signed_mart / "models" / layer / filename
            assert model_path.exists(), f"Missing model: models/{layer}/{filename}"

    def test_model_refs_are_resolved(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst", fixture=True)
        dwd = (signed_mart / "models" / "dwd" / "tst_dwd_daily_sample_di.sql").read_text()
        assert "ref('tst_ods_csv_sample')" in dwd
        assert "ref('tst_dim_date')" in dwd
        assert "{prefix}" not in dwd

        dws = (signed_mart / "models" / "dws" / "tst_dws_daily_revenue_1d.sql").read_text()
        assert "ref('tst_dwd_daily_sample_di')" in dws

        ads = (signed_mart / "models" / "ads" / "tst_ads_exec_dashboard.sql").read_text()
        assert "ref('tst_dws_daily_revenue_1d')" in ads
        assert "ref('tst_dim_date')" in ads

    def test_model_sql_no_select_star(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst", fixture=True)
        for layer in ["ods", "dim", "dwd", "dws", "ads"]:
            for sql_file in (signed_mart / "models" / layer).glob("*.sql"):
                content = sql_file.read_text()
                in_comment = False
                for line in content.splitlines():
                    stripped = line.strip()
                    if "{#" in stripped:
                        in_comment = True
                    if in_comment:
                        if "#}" in stripped:
                            in_comment = False
                        continue
                    if stripped.startswith("--") or stripped.startswith("{"):
                        continue
                    assert "select *" not in stripped.lower(), \
                        f"{sql_file.name} uses SELECT *: {stripped}"

    def test_schema_yml_references_all_models(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst", fixture=True)
        schema = signed_mart / "models" / "schema.yml"
        assert schema.exists()
        content = schema.read_text()
        assert "tst_ods_csv_sample" in content
        assert "tst_dim_date" in content
        assert "tst_dwd_daily_sample_di" in content
        assert "tst_dws_daily_revenue_1d" in content
        assert "tst_ads_exec_dashboard" in content
        assert "raw_sample_data" in content
        assert "dim_date" in content

    def test_both_seeds_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst", fixture=True)
        assert (signed_mart / "seeds" / "raw_sample_data.csv").exists()
        assert (signed_mart / "seeds" / "dim_date.csv").exists()

    def test_dashboard_created_with_db_connection(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst", fixture=True)
        app = signed_mart / "dashboard" / "app.py"
        assert app.exists()
        content = app.read_text()
        assert "test-mart" in content
        assert "duckdb" in content
        assert "get_connection" in content
        assert "load_ads_data" in content
        assert "tst_ads_exec_dashboard" in content
        assert "scorecard" in content.lower()
        assert "provenance" in content.lower()

    def test_scorecard_json_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst", fixture=True)
        scorecard = signed_mart / "dqc_scorecard.json"
        assert scorecard.exists()
        data = json.loads(scorecard.read_text())
        assert data["mart"] == "test-mart"
        assert isinstance(data["controls"], list)

    def test_dqc_update_script_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst", fixture=True)
        dqc_script = signed_mart / "scripts" / "dqc_update.py"
        assert dqc_script.exists()
        content = dqc_script.read_text()
        assert "scorecard" in content.lower()

    def test_pipeline_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst", fixture=True)
        pipeline = signed_mart / ".github" / "workflows" / "daily.yml"
        assert pipeline.exists()
        content = pipeline.read_text()
        assert "test-mart" in content

    def test_pipeline_dqc_script_exists(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst", fixture=True)
        pipeline = signed_mart / ".github" / "workflows" / "daily.yml"
        content = pipeline.read_text()
        if "scripts/dqc_update.py" in content:
            assert (signed_mart / "scripts" / "dqc_update.py").exists()

    def test_singular_test_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst", fixture=True)
        test_file = signed_mart / "tests" / "test_tst_ods_no_duplicate_keys.sql"
        assert test_file.exists()
        content = test_file.read_text()
        assert "ref('tst_ods_csv_sample')" in content
        assert "record_id" in content


class TestDbtIntegration:
    """End-to-end: fixture scaffold then dbt parse/seed/run/test."""

    def test_scaffold_and_dbt_pipeline(self, signed_mart):
        result = scaffold(signed_mart, "test-mart", "tst", fixture=True)
        assert result["success"], f"Scaffold failed: {result['errors']}"

        for step in ["parse", "seed", "run", "test"]:
            cmd = ["dbt", step, "--profiles-dir", ".", "--target", "ci"]
            r = subprocess.run(
                cmd, cwd=str(signed_mart),
                capture_output=True, text=True, timeout=120,
            )
            assert r.returncode == 0, (
                f"dbt {step} failed (rc={r.returncode}):\n"
                f"STDOUT:\n{r.stdout[-2000:]}\n"
                f"STDERR:\n{r.stderr[-2000:]}"
            )


class TestSignOffDetection:
    def test_grade_a_is_signed(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("# Doc\nGrade: A\n")
        assert _is_signed(doc)

    def test_approved_alone_not_signed(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("# Doc\nAPPROVED by reviewer.\n")
        assert not _is_signed(doc)

    def test_grade_a_with_approved_is_signed(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("# Doc\nAPPROVED by reviewer.\nGrade: A\n")
        assert _is_signed(doc)

    def test_grade_b_not_signed(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("# Doc\nGrade: B\n")
        assert not _is_signed(doc)

    def test_grade_b_with_approved_not_signed(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("# Doc\nGrade: B\nAPPROVED\n")
        assert not _is_signed(doc)

    def test_unsigned_doc(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("# Doc\nDraft version, not approved.\n")
        assert not _is_signed(doc)

    def test_missing_doc_not_signed(self, tmp_path):
        assert not _is_signed(tmp_path / "nonexistent.md")


class TestDesignBypassRejection:
    """Exact negative regression: long N/A prose for required layers,
    empty ADS column header, and token text for T-12/T-16 must be rejected."""

    BYPASS_TDD = """\
# Technical Design Document — Test Mart

## T-1. Version History
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-01-01 | Test | Initial |

## T-2. Design Reasoning
Grain: one row per order line per day.

## T-3. Table Summary
| Table Name | Layer | Purpose | Grain | Materialization |
|------------|-------|---------|-------|-----------------|
| tst_ods_csv_sample | ODS | Raw ingestion | one row per record per pull_date | incremental |

## T-4. Data Architecture Diagram
ODS -> DWD -> DWS -> ADS, DIM referenced by DWD.

## T-5. Column Specification
Per-table specs follow in T-6 through T-11.

## T-6. ODS Table Design

not_applicable rationale: This layer will be implemented in a later iteration after source discovery confirms the ingestion pattern. Signed off by design authority.

## T-7. Dimension Table Design

not_applicable rationale: Date dimension will be sourced from an enterprise calendar service rather than local seed. Out of scope for this design iteration. Signed off.

## T-8. Fact Table Design (DWD)

not_applicable rationale: The fact grain depends on the ODS layer finalization. This section is deferred to the next design increment pending source confirmation. Signed off by design authority.

## T-9. Count Aggregation Design (DWS)

not_applicable rationale: Count aggregations require a finalized DWD layer. This section is deferred pending the fact table design. Reviewed and signed off.

## T-10. Performance Aggregation Design (DWS)

not_applicable rationale: No performance/ratio metrics required for this basic order mart. All metrics are count and sum aggregations covered in T-9. Signed off.

## T-11. Presentation Table Design (ADS)

| column_name | data_type | definition | example_value | calculation | data_source | BRD_ref | link_status |
|-------------|-----------|------------|---------------|-------------|-------------|---------|-------------|

## T-12. Physical Design
TBD

## T-13. Implementation Specification
dbt model configuration per naming conventions.

## T-14. DQC Plan
All 8 control classes addressed per control catalog.

## T-15. Test Inventory
| Test Name | Type | Target Model |
|-----------|------|-------------|
| not_null_record_id | generic | ods |

## T-16. Operations
TBD

## T-17. Known Limitations
No external data sources for reconciliation.

Sign-off: APPROVED
Grade: A
"""

    def test_rejects_na_required_layers(self, mart_dir):
        """ODS (T-6) and DWD (T-8) are required layers and cannot be N/A."""
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(self.BYPASS_TDD)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"], "Scaffold accepted TDD with N/A for required layers"
        error_text = " ".join(result["errors"])
        assert "T-6" in error_text, "Missing rejection for T-6 (ODS) N/A"
        assert "T-8" in error_text, "Missing rejection for T-8 (DWD) N/A"

    def test_rejects_empty_ads_column_header(self, mart_dir):
        """ADS (T-11) with column header but no data rows must be rejected."""
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(self.BYPASS_TDD)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"]
        assert any("T-11" in e for e in result["errors"]), "Missing rejection for T-11 (ADS) empty data"

    def test_rejects_token_t12_t16(self, mart_dir):
        """T-12 and T-16 with token text ('TBD') must be rejected."""
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(self.BYPASS_TDD)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"]
        error_text = " ".join(result["errors"])
        assert "T-12" in error_text, "Missing rejection for T-12 token text"
        assert "T-16" in error_text, "Missing rejection for T-16 token text"

    def test_no_models_emitted_on_bypass(self, mart_dir):
        """No files should be created when bypass TDD is rejected."""
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(self.BYPASS_TDD)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"]
        assert result["files_created"] == []


class TestContractBinding:
    """Contract file must be generated and reflect BRD/TDD signed design."""

    def test_mart_contract_created(self, signed_mart):
        result = scaffold(signed_mart, "test-mart", "tst", fixture=True)
        assert result["success"]
        contract_path = signed_mart / "mart_contract.json"
        assert contract_path.exists()
        assert "mart_contract.json" in result["files_created"]

    def test_contract_metrics_match_brd(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst", fixture=True)
        contract = json.loads((signed_mart / "mart_contract.json").read_text())
        metrics = contract["metrics"]
        assert len(metrics) == 2
        m1 = next(m for m in metrics if m["id"] == "M-1")
        m2 = next(m for m in metrics if m["id"] == "M-2")
        assert m1["link_status"] == "exact"
        assert m2["link_status"] == "proxy"
        assert m1["ads_column"] == "daily_revenue"
        assert m2["ads_column"] == "order_count"

    def test_contract_rejects_metric_mismatch(self, mart_dir):
        """TDD link_status must match BRD link_status for each metric."""
        mart_dir.mkdir()
        mismatched_tdd = VALID_TDD.replace(
            "| order_count | BIGINT | Daily orders | 3 | dws.order_count via join | DWS | M-2 | proxy |",
            "| order_count | BIGINT | Daily orders | 3 | dws.order_count via join | DWS | M-2 | exact |",
        )
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(mismatched_tdd)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"]
        assert any("mismatch" in e.lower() for e in result["errors"])

    def test_dashboard_uses_contracted_metrics(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst", fixture=True)
        dash = (signed_mart / "dashboard" / "app.py").read_text()
        assert "CONTRACTED_METRICS" in dash
        assert '"M-1"' in dash
        assert '"M-2"' in dash
        assert "Avg Order Value" not in dash

    def test_dashboard_no_unsupported_on_error(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst", fixture=True)
        dash = (signed_mart / "dashboard" / "app.py").read_text()
        assert "render_error_badge" in dash
        assert "Data unavailable" in dash


class TestMetricMappingValidation:
    """BRD metrics must map to ADS columns with consistent link_status."""

    def test_rejects_missing_metric_mapping(self, mart_dir):
        mart_dir.mkdir()
        tdd_no_mapping = VALID_TDD.replace(
            "| order_count | BIGINT | Daily orders | 3 | dws.order_count via join | DWS | M-2 | proxy |",
            "| order_count | BIGINT | Daily orders | 3 | dws.order_count via join | DWS | - | proxy |",
        )
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(tdd_no_mapping)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"]
        assert any("M-2" in e and "no mapping" in e.lower() for e in result["errors"])


class TestContractEnforcement:
    """Regression tests for Codex review blockers 1-5 (2026-05-24)."""

    def test_rejects_approved_without_grade_a(self, mart_dir):
        """Blocker 1: Removing Grade: A from both docs (keeping APPROVED) must fail."""
        mart_dir.mkdir()
        brd_no_grade = VALID_BRD.replace("Grade: A", "").replace("APPROVED", "APPROVED")
        tdd_no_grade = VALID_TDD.replace("Grade: A", "").replace("APPROVED", "APPROVED")
        (mart_dir / "brd.md").write_text(brd_no_grade)
        (mart_dir / "tdd.md").write_text(tdd_no_grade)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"], "Scaffold accepted docs without Grade: A"
        assert any("not signed off" in e.lower() for e in result["errors"])

    def test_rejects_brd_ref_dash(self, mart_dir):
        """Blocker 2: Replacing both ADS BRD_ref with '-' must fail."""
        mart_dir.mkdir()
        tdd_no_refs = VALID_TDD.replace("| M-2 |", "| - |").replace("| M-1 |", "| - |")
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(tdd_no_refs)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"], "Scaffold accepted ADS with all BRD_ref set to '-'"
        assert any("no mapping" in e.lower() for e in result["errors"])

    def test_rejects_invalid_link_status_bogus(self, mart_dir):
        """Blocker 3: Invalid link_status 'bogus' in BRD must fail."""
        mart_dir.mkdir()
        brd_bogus = VALID_BRD.replace("| M-1 Revenue | native | exact |",
                                       "| M-1 Revenue | native | bogus |")
        tdd_bogus = VALID_TDD.replace("| daily_revenue | DECIMAL | Daily revenue | 325.75 | dws.daily_revenue via join | DWS | M-1 | exact |",
                                       "| daily_revenue | DECIMAL | Daily revenue | 325.75 | dws.daily_revenue via join | DWS | M-1 | bogus |")
        (mart_dir / "brd.md").write_text(brd_bogus)
        (mart_dir / "tdd.md").write_text(tdd_bogus)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"], "Scaffold accepted invalid link_status 'bogus'"
        assert any("invalid link_status" in e.lower() for e in result["errors"])

    def test_rejects_invalid_source_type(self, mart_dir):
        """Blocker 3 extension: Invalid source_type must also fail."""
        mart_dir.mkdir()
        brd_bad_st = VALID_BRD.replace("| M-1 Revenue | native | exact |",
                                        "| M-1 Revenue | magical | exact |")
        (mart_dir / "brd.md").write_text(brd_bad_st)
        (mart_dir / "tdd.md").write_text(VALID_TDD)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"], "Scaffold accepted invalid source_type 'magical'"
        assert any("invalid source_type" in e.lower() for e in result["errors"])

    def test_rejects_unbound_ads_column(self, mart_dir):
        """Blocker 4: ADS binding column not produced by fixture must fail on fixture path."""
        mart_dir.mkdir()
        tdd_wrong_col = VALID_TDD.replace(
            "| daily_revenue | DECIMAL | Daily revenue | 325.75 | dws.daily_revenue via join | DWS | M-1 | exact |",
            "| case_volume | DECIMAL | Daily revenue | 325.75 | dws.daily_revenue via join | DWS | M-1 | exact |",
        )
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(tdd_wrong_col)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"], "Fixture scaffold accepted ADS column 'case_volume' not in fixture template"
        assert any("case_volume" in e for e in result["errors"])
        assert any("fixture" in e.lower() for e in result["errors"])

    def test_dashboard_chart_contract_bound(self, signed_mart):
        """Blocker 5: Dashboard trend chart must use contract metrics, not hardcoded columns."""
        scaffold(signed_mart, "test-mart", "tst", fixture=True)
        dash = (signed_mart / "dashboard" / "app.py").read_text()
        assert "Metric Trends" in dash, "Dashboard should show 'Metric Trends' not 'Revenue Trend'"
        assert "Revenue Trend" not in dash, "Dashboard has hardcoded 'Revenue Trend' header"
        assert "for metric in CONTRACTED_METRICS" in dash, "Dashboard chart not iterating over contract"

    def test_rejects_empty_ads_column_binding(self, mart_dir):
        """Blocker 2 extension: ADS column binding of '-' for a mapped metric must fail."""
        mart_dir.mkdir()
        tdd_dash_col = VALID_TDD.replace(
            "| daily_revenue | DECIMAL | Daily revenue | 325.75 | dws.daily_revenue via join | DWS | M-1 | exact |",
            "| - | DECIMAL | Daily revenue | 325.75 | dws.daily_revenue via join | DWS | M-1 | exact |",
        )
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(tdd_dash_col)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"], "Scaffold accepted metric with empty ADS column binding"
        assert any("empty ads column" in e.lower() for e in result["errors"])

    def test_rejects_tdd_invalid_link_status(self, mart_dir):
        """Blocker 3 extension: Invalid link_status in TDD T-11 must fail."""
        mart_dir.mkdir()
        tdd_bogus = VALID_TDD.replace(
            "| daily_revenue | DECIMAL | Daily revenue | 325.75 | dws.daily_revenue via join | DWS | M-1 | exact |",
            "| daily_revenue | DECIMAL | Daily revenue | 325.75 | dws.daily_revenue via join | DWS | M-1 | bogus |",
        )
        brd_bogus = VALID_BRD.replace("| M-1 Revenue | native | exact |",
                                       "| M-1 Revenue | native | bogus |")
        (mart_dir / "brd.md").write_text(brd_bogus)
        (mart_dir / "tdd.md").write_text(tdd_bogus)
        result = scaffold(mart_dir, "test-mart", "tst", fixture=True)
        assert not result["success"]
        errors_text = " ".join(result["errors"])
        assert "invalid link_status" in errors_text.lower()


class TestNameSanitization:
    def test_kebab_to_snake(self, signed_mart):
        result = scaffold(signed_mart, "my-test-mart", "tst", fixture=True)
        assert result["success"]
        content = (signed_mart / "dbt_project.yml").read_text()
        assert "my_test_mart" in content
        assert "my-test-mart" not in content

    def test_already_clean_name(self, signed_mart):
        result = scaffold(signed_mart, "clean_name", "tst", fixture=True)
        assert result["success"]
        content = (signed_mart / "dbt_project.yml").read_text()
        assert "clean_name" in content


# ===========================================================================
# General contract-driven scaffold path tests
# ===========================================================================

class TestProxyStampDetection:
    """ARGENT-PROXY stamp detection."""

    def test_detects_proxy_stamp(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("# Doc\n[ARGENT-PROXY 2026-05-20T10:00:00Z]\nGrade: A\n")
        assert _has_proxy_stamp(doc)

    def test_rejects_missing_stamp(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("# Doc\nGrade: A\n")
        assert not _has_proxy_stamp(doc)

    def test_rejects_malformed_stamp(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("# Doc\n[ARGENT-PROXY sometime]\nGrade: A\n")
        assert not _has_proxy_stamp(doc)


class TestGeneralContractScaffold:
    """General contract-driven scaffold with case_volume metric."""

    def test_case_volume_scaffold_succeeds(self, case_volume_mart):
        result = scaffold(case_volume_mart, "case-mart", "cas")
        assert result["success"], f"General scaffold failed: {result['errors']}"
        assert result["errors"] == []
        assert len(result["files_created"]) > 0

    def test_case_volume_ads_sql_uses_case_volume(self, case_volume_mart):
        scaffold(case_volume_mart, "case-mart", "cas")
        ads_sql = (case_volume_mart / "models" / "ads" / "cas_ads_case_dashboard.sql").read_text()
        assert "case_volume" in ads_sql

    def test_case_volume_output_no_fixture_fields(self, case_volume_mart):
        """Output must NOT contain daily_revenue or order_count fixture fields."""
        scaffold(case_volume_mart, "case-mart", "cas")

        ads_sql = (case_volume_mart / "models" / "ads" / "cas_ads_case_dashboard.sql").read_text()
        assert "daily_revenue" not in ads_sql, "ADS SQL contains fixture field daily_revenue"
        assert "order_count" not in ads_sql, "ADS SQL contains fixture field order_count"

        schema = (case_volume_mart / "models" / "schema.yml").read_text()
        assert "daily_revenue" not in schema, "schema.yml contains fixture field daily_revenue"
        assert "order_count" not in schema, "schema.yml contains fixture field order_count"

        dash = (case_volume_mart / "dashboard" / "app.py").read_text()
        assert "daily_revenue" not in dash, "Dashboard contains fixture field daily_revenue"
        assert "order_count" not in dash, "Dashboard contains fixture field order_count"

    def test_case_volume_dashboard_uses_case_volume(self, case_volume_mart):
        scaffold(case_volume_mart, "case-mart", "cas")
        dash = (case_volume_mart / "dashboard" / "app.py").read_text()
        assert "case_volume" in dash
        assert "CONTRACTED_METRICS" in dash
        assert '"M-1"' in dash
        assert "cas_ads_case_dashboard" in dash

    def test_contract_json_fixture_disabled(self, case_volume_mart):
        scaffold(case_volume_mart, "case-mart", "cas")
        contract = json.loads((case_volume_mart / "mart_contract.json").read_text())
        assert contract["fixture"]["enabled"] is False
        metrics = contract["metrics"]
        assert len(metrics) == 1
        assert metrics[0]["ads_column"] == "case_volume"

    def test_schema_yml_uses_contract_model_names(self, case_volume_mart):
        scaffold(case_volume_mart, "case-mart", "cas")
        schema = (case_volume_mart / "models" / "schema.yml").read_text()
        assert "cas_ods_cases" in schema
        assert "cas_dim_date" in schema
        assert "cas_dwd_cases_di" in schema
        assert "cas_dws_daily_cases_1d" in schema
        assert "cas_ads_case_dashboard" in schema
        assert "case_volume" in schema

    def test_dim_model_is_framework_provided(self, case_volume_mart):
        scaffold(case_volume_mart, "case-mart", "cas")
        dim_sql = (case_volume_mart / "models" / "dim" / "cas_dim_date.sql").read_text()
        assert "ref('dim_date')" in dim_sql
        assert "unknown_member" in dim_sql

    def test_dim_date_seed_included(self, case_volume_mart):
        scaffold(case_volume_mart, "case-mart", "cas")
        assert (case_volume_mart / "seeds" / "dim_date.csv").exists()

    def test_user_seed_copied(self, case_volume_mart):
        scaffold(case_volume_mart, "case-mart", "cas")
        assert (case_volume_mart / "seeds" / "raw_case_data.csv").exists()


class TestGeneralContractNegatives:
    """Rejection tests for the general contract-driven path."""

    def test_rejects_missing_contract(self, mart_dir):
        """No impl_contract.yml → must fail without generating files."""
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(CASE_VOLUME_BRD)
        (mart_dir / "tdd.md").write_text(CASE_VOLUME_TDD)
        result = scaffold(mart_dir, "case-mart", "cas")
        assert not result["success"]
        assert any("impl_contract.yml" in e.lower() for e in result["errors"])
        assert result["files_created"] == []

    def test_rejects_missing_proxy_stamp_brd(self, mart_dir):
        """BRD without ARGENT-PROXY stamp → must fail."""
        mart_dir.mkdir()
        brd_no_stamp = CASE_VOLUME_BRD.replace("[ARGENT-PROXY 2026-05-20T10:00:00Z]\n", "")
        (mart_dir / "brd.md").write_text(brd_no_stamp)
        (mart_dir / "tdd.md").write_text(CASE_VOLUME_TDD)
        (mart_dir / "impl_contract.yml").write_text(
            yaml.dump(CASE_VOLUME_CONTRACT, default_flow_style=False, sort_keys=False)
        )
        result = scaffold(mart_dir, "case-mart", "cas")
        assert not result["success"]
        assert any("argent-proxy" in e.lower() for e in result["errors"])
        assert result["files_created"] == []

    def test_rejects_missing_proxy_stamp_tdd(self, mart_dir):
        """TDD without ARGENT-PROXY stamp → must fail."""
        mart_dir.mkdir()
        tdd_no_stamp = CASE_VOLUME_TDD.replace("[ARGENT-PROXY 2026-05-20T10:00:00Z]\n", "")
        (mart_dir / "brd.md").write_text(CASE_VOLUME_BRD)
        (mart_dir / "tdd.md").write_text(tdd_no_stamp)
        (mart_dir / "impl_contract.yml").write_text(
            yaml.dump(CASE_VOLUME_CONTRACT, default_flow_style=False, sort_keys=False)
        )
        result = scaffold(mart_dir, "case-mart", "cas")
        assert not result["success"]
        assert any("argent-proxy" in e.lower() for e in result["errors"])

    def test_rejects_contract_metric_mismatch(self, mart_dir):
        """Contract ads_column not matching TDD T-11 column → must fail."""
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(CASE_VOLUME_BRD)
        (mart_dir / "tdd.md").write_text(CASE_VOLUME_TDD)
        bad_contract = dict(CASE_VOLUME_CONTRACT)
        bad_contract = json.loads(json.dumps(CASE_VOLUME_CONTRACT))
        bad_contract["metrics"] = [
            {"id": "M-1", "name": "Case Volume", "ads_column": "wrong_column"},
        ]
        (mart_dir / "impl_contract.yml").write_text(
            yaml.dump(bad_contract, default_flow_style=False, sort_keys=False)
        )
        result = scaffold(mart_dir, "case-mart", "cas")
        assert not result["success"]
        assert any("does not match" in e.lower() for e in result["errors"])

    def test_rejects_contract_missing_visualizations(self, mart_dir):
        """Contract without visualizations → must fail."""
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(CASE_VOLUME_BRD)
        (mart_dir / "tdd.md").write_text(CASE_VOLUME_TDD)
        bad_contract = json.loads(json.dumps(CASE_VOLUME_CONTRACT))
        del bad_contract["visualizations"]
        (mart_dir / "impl_contract.yml").write_text(
            yaml.dump(bad_contract, default_flow_style=False, sort_keys=False)
        )
        result = scaffold(mart_dir, "case-mart", "cas")
        assert not result["success"]
        assert any("visualizations" in e.lower() for e in result["errors"])

    def test_rejects_contract_missing_models(self, mart_dir):
        """Contract without models → must fail."""
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(CASE_VOLUME_BRD)
        (mart_dir / "tdd.md").write_text(CASE_VOLUME_TDD)
        bad_contract = json.loads(json.dumps(CASE_VOLUME_CONTRACT))
        del bad_contract["models"]
        (mart_dir / "impl_contract.yml").write_text(
            yaml.dump(bad_contract, default_flow_style=False, sort_keys=False)
        )
        result = scaffold(mart_dir, "case-mart", "cas")
        assert not result["success"]
        assert any("models" in e.lower() for e in result["errors"])

    def test_rejects_incomplete_visualization(self, mart_dir):
        """Visualization missing required fields → must fail."""
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(CASE_VOLUME_BRD)
        (mart_dir / "tdd.md").write_text(CASE_VOLUME_TDD)
        bad_contract = json.loads(json.dumps(CASE_VOLUME_CONTRACT))
        bad_contract["visualizations"] = [{"metric_id": "M-1"}]
        (mart_dir / "impl_contract.yml").write_text(
            yaml.dump(bad_contract, default_flow_style=False, sort_keys=False)
        )
        seeds_dir = mart_dir / "seeds"
        seeds_dir.mkdir(exist_ok=True)
        (seeds_dir / "raw_case_data.csv").write_text(CASE_SEED_CSV)
        result = scaffold(mart_dir, "case-mart", "cas")
        assert not result["success"]
        assert any("visualization" in e.lower() and "missing" in e.lower() for e in result["errors"])


class TestDynamicVisualizationBinding:
    """Dashboard must use contract-driven visualization definitions."""

    def test_dashboard_uses_visualization_defs(self, case_volume_mart):
        scaffold(case_volume_mart, "case-mart", "cas")
        dash = (case_volume_mart / "dashboard" / "app.py").read_text()
        assert "VISUALIZATION_DEFS" in dash
        assert "section_visualizations" in dash
        assert "chart_type" in dash
        assert "Case Volume Trend" in dash

    def test_dashboard_no_hardcoded_fixture_charts(self, case_volume_mart):
        scaffold(case_volume_mart, "case-mart", "cas")
        dash = (case_volume_mart / "dashboard" / "app.py").read_text()
        assert "Revenue Trend" not in dash
        assert "order_count" not in dash
        assert "daily_revenue" not in dash

    def test_dashboard_chart_type_binding(self, case_volume_mart):
        """Visualization chart_type=line should produce st.line_chart."""
        scaffold(case_volume_mart, "case-mart", "cas")
        dash = (case_volume_mart / "dashboard" / "app.py").read_text()
        assert "st.line_chart" in dash
        assert "st.bar_chart" in dash  # bar chart support in code


class TestOperationalUnavailableSemantics:
    """Operational data errors must show 'unavailable'/'error', never 'unsupported'."""

    def test_fixture_dashboard_error_is_unavailable(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst", fixture=True)
        dash = (signed_mart / "dashboard" / "app.py").read_text()
        assert "Data unavailable" in dash
        assert "render_error_badge" in dash

    def test_general_dashboard_error_is_unavailable(self, case_volume_mart):
        scaffold(case_volume_mart, "case-mart", "cas")
        dash = (case_volume_mart / "dashboard" / "app.py").read_text()
        assert "Data unavailable" in dash
        assert "render_error_badge" in dash

    def test_general_dashboard_no_unsupported_in_error_path(self, case_volume_mart):
        """The 'unsupported' link_status label must not appear in error handling paths."""
        scaffold(case_volume_mart, "case-mart", "cas")
        dash = (case_volume_mart / "dashboard" / "app.py").read_text()
        error_section = dash[dash.find("def render_error_badge"):]
        error_fn_end = error_section.find("\ndef ")
        if error_fn_end > 0:
            error_fn = error_section[:error_fn_end]
        else:
            error_fn = error_section[:200]
        assert "unsupported" not in error_fn.lower()


class TestFixtureIsNotGeneralRoute:
    """Regression: fixture-only behavior must not be the general route."""

    def test_general_path_rejects_without_contract(self, mart_dir):
        """Default scaffold (no --fixture) with fixture docs must fail."""
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(VALID_TDD)
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"], "General scaffold accepted fixture docs without proxy stamp or contract"

    def test_fixture_flag_required_for_fixture_behavior(self, signed_mart):
        """Fixture scaffold requires explicit fixture=True."""
        result_general = scaffold(signed_mart, "test-mart", "tst")
        assert not result_general["success"], "General scaffold succeeded without contract"

        mart_dir2 = signed_mart.parent / "test_mart_2"
        mart_dir2.mkdir()
        (mart_dir2 / "brd.md").write_text(VALID_BRD)
        (mart_dir2 / "tdd.md").write_text(VALID_TDD)
        result_fixture = scaffold(mart_dir2, "test-mart", "tst", fixture=True)
        assert result_fixture["success"], f"Fixture scaffold failed: {result_fixture['errors']}"


class TestDbtIntegrationGeneral:
    """End-to-end: general contract scaffold then dbt parse/seed/run/test."""

    def test_case_volume_dbt_pipeline(self, case_volume_mart):
        result = scaffold(case_volume_mart, "case-mart", "cas")
        assert result["success"], f"Scaffold failed: {result['errors']}"

        for step in ["parse", "seed", "run", "test"]:
            cmd = ["dbt", step, "--profiles-dir", ".", "--target", "ci"]
            r = subprocess.run(
                cmd, cwd=str(case_volume_mart),
                capture_output=True, text=True, timeout=120,
            )
            assert r.returncode == 0, (
                f"dbt {step} failed (rc={r.returncode}):\n"
                f"STDOUT:\n{r.stdout[-2000:]}\n"
                f"STDERR:\n{r.stderr[-2000:]}"
            )
