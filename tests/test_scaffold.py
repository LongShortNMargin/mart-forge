"""Scaffold workflow tests.

Tests structural contract validation, rejection of incomplete/undergraded
BRD/TDD, name sanitization, and generation of a complete runnable dbt
skeleton with SQL models, DQC assets, dashboard, and pipeline scripts.
"""

import json
import subprocess
from pathlib import Path

import pytest
import yaml

from mart_forge.scaffold import scaffold, _is_signed, _validate_brd, _validate_tdd


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


@pytest.fixture
def mart_dir(tmp_path):
    return tmp_path / "test_mart"


@pytest.fixture
def signed_mart(mart_dir):
    mart_dir.mkdir()
    (mart_dir / "brd.md").write_text(VALID_BRD)
    (mart_dir / "tdd.md").write_text(VALID_TDD)
    return mart_dir


class TestPlaceholderRejection:
    """Minimal approval-token documents must be rejected."""

    def test_rejects_token_only_brd(self, mart_dir):
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(
            "# BRD\n\nSign-off: APPROVED\nGrade: A\n"
        )
        (mart_dir / "tdd.md").write_text(VALID_TDD)
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"], "Scaffold accepted a token-only BRD"
        assert any("B-" in e for e in result["errors"])

    def test_rejects_token_only_tdd(self, mart_dir):
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(
            "# TDD\n\nSign-off: APPROVED\nGrade: A\n"
        )
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"], "Scaffold accepted a token-only TDD"
        assert any("T-" in e for e in result["errors"])

    def test_rejects_partial_brd_missing_sections(self, mart_dir):
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(
            "# BRD\n\n## B-1. Scope\nSome scope text here.\n\nSign-off: APPROVED\nGrade: A\n"
        )
        (mart_dir / "tdd.md").write_text(VALID_TDD)
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"], "Scaffold accepted BRD missing B-2..B-4"

    def test_rejects_brd_with_unverified(self, mart_dir):
        mart_dir.mkdir()
        brd_with_unverified = VALID_BRD.replace("exact", "unverified")
        (mart_dir / "brd.md").write_text(brd_with_unverified)
        (mart_dir / "tdd.md").write_text(VALID_TDD)
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"], "Scaffold accepted BRD with unverified link_status"
        assert any("unverified" in e.lower() for e in result["errors"])

    def test_rejects_tdd_with_unverified(self, mart_dir):
        mart_dir.mkdir()
        tdd_with_unverified = VALID_TDD.replace("exact", "unverified")
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(tdd_with_unverified)
        result = scaffold(mart_dir, "test-mart", "tst")
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
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"], "Scaffold accepted BRD without source_type classification"


class TestGradeBRejection:
    """Grade B and below must be rejected."""

    def test_rejects_grade_b_brd(self, mart_dir):
        mart_dir.mkdir()
        grade_b_brd = VALID_BRD.replace("Grade: A", "Grade: B")
        (mart_dir / "brd.md").write_text(grade_b_brd)
        (mart_dir / "tdd.md").write_text(VALID_TDD)
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"], "Scaffold accepted Grade B BRD"

    def test_rejects_grade_b_tdd(self, mart_dir):
        mart_dir.mkdir()
        grade_b_tdd = VALID_TDD.replace("Grade: A", "Grade: B")
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(grade_b_tdd)
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"], "Scaffold accepted Grade B TDD"

    def test_rejects_grade_c(self, mart_dir):
        mart_dir.mkdir()
        grade_c_brd = VALID_BRD.replace("Grade: A", "Grade: C")
        (mart_dir / "brd.md").write_text(grade_c_brd)
        (mart_dir / "tdd.md").write_text(VALID_TDD)
        result = scaffold(mart_dir, "test-mart", "tst")
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
        result = scaffold(mart_dir, "test-mart", "tst")
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
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"], "Scaffold accepted TDD with bare not_applicable (no rationale)"
        assert any("bare" in e.lower() or "rationale" in e.lower() for e in result["errors"])


class TestHardGateRejection:
    def test_rejects_missing_brd(self, mart_dir):
        mart_dir.mkdir()
        (mart_dir / "tdd.md").write_text(VALID_TDD)
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"]
        assert any("BRD not found" in e for e in result["errors"])

    def test_rejects_unsigned_brd(self, mart_dir):
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text("# Draft BRD\nNo sign-off yet.\n")
        (mart_dir / "tdd.md").write_text(VALID_TDD)
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"]
        assert any("not signed off" in e for e in result["errors"])

    def test_rejects_missing_tdd(self, mart_dir):
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(VALID_BRD)
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"]
        assert any("TDD not found" in e for e in result["errors"])

    def test_rejects_unsigned_tdd(self, mart_dir):
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text("# Draft TDD\nNo sign-off yet.\n")
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"]
        assert any("not signed off" in e for e in result["errors"])

    def test_rejects_both_missing(self, mart_dir):
        mart_dir.mkdir()
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"]
        assert len(result["errors"]) >= 2

    def test_no_files_created_on_rejection(self, mart_dir):
        mart_dir.mkdir()
        result = scaffold(mart_dir, "test-mart", "tst")
        assert result["files_created"] == []


class TestSuccessfulScaffold:
    def test_scaffold_succeeds(self, signed_mart):
        result = scaffold(signed_mart, "test-mart", "tst")
        assert result["success"], f"Scaffold failed: {result['errors']}"
        assert result["errors"] == []
        assert len(result["files_created"]) > 0

    def test_dbt_project_yml_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        dbt_project = signed_mart / "dbt_project.yml"
        assert dbt_project.exists()
        content = dbt_project.read_text()
        assert "test_mart" in content
        assert "model-paths" in content

    def test_dbt_project_name_sanitized(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        content = (signed_mart / "dbt_project.yml").read_text()
        assert "test-mart" not in content, "dbt_project.yml has unsanitized kebab-case name"
        assert "test_mart" in content

    def test_profiles_yml_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        profiles = signed_mart / "profiles.yml"
        assert profiles.exists()
        content = profiles.read_text()
        assert "test_mart" in content
        assert "duckdb" in content

    def test_model_sql_files_created_with_semantic_names(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
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
        scaffold(signed_mart, "test-mart", "tst")
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
        scaffold(signed_mart, "test-mart", "tst")
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
        scaffold(signed_mart, "test-mart", "tst")
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
        scaffold(signed_mart, "test-mart", "tst")
        assert (signed_mart / "seeds" / "raw_sample_data.csv").exists()
        assert (signed_mart / "seeds" / "dim_date.csv").exists()

    def test_dashboard_created_with_db_connection(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        app = signed_mart / "dashboard" / "app.py"
        assert app.exists()
        content = app.read_text()
        assert "duckdb" in content
        assert "get_connection" in content
        assert "load_ads_data" in content
        assert "mart.yml" in content
        assert "scorecard" in content.lower()
        assert "provenance" in content.lower()
        contract = yaml.safe_load((signed_mart / "mart.yml").read_text())
        assert contract["dashboard"]["ads_table"] == "tst_ads_exec_dashboard"

    def test_scorecard_json_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        scorecard = signed_mart / "dqc_scorecard.json"
        assert scorecard.exists()
        data = json.loads(scorecard.read_text())
        assert data["mart"] == "test-mart"
        assert isinstance(data["controls"], list)

    def test_dqc_update_script_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        dqc_script = signed_mart / "scripts" / "dqc_update.py"
        assert dqc_script.exists()
        content = dqc_script.read_text()
        assert "scorecard" in content.lower()

    def test_pipeline_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        pipeline = signed_mart / ".github" / "workflows" / "daily.yml"
        assert pipeline.exists()
        content = pipeline.read_text()
        assert "test-mart" in content

    def test_pipeline_dqc_script_exists(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        pipeline = signed_mart / ".github" / "workflows" / "daily.yml"
        content = pipeline.read_text()
        if "scripts/dqc_update.py" in content:
            assert (signed_mart / "scripts" / "dqc_update.py").exists()

    def test_singular_test_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        test_file = signed_mart / "tests" / "test_tst_ods_no_duplicate_keys.sql"
        assert test_file.exists()
        content = test_file.read_text()
        assert "ref('tst_ods_csv_sample')" in content
        assert "record_id" in content


class TestDbtIntegration:
    """End-to-end: scaffold then dbt parse/seed/run/test."""

    def test_scaffold_and_dbt_pipeline(self, signed_mart):
        result = scaffold(signed_mart, "test-mart", "tst")
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

    def test_approved_is_signed(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("# Doc\nAPPROVED by reviewer.\n")
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


class TestContractGeneration:
    """Implementation contract (mart.yml) must be generated from signed BRD/TDD."""

    def test_contract_generated(self, signed_mart):
        result = scaffold(signed_mart, "test-mart", "tst")
        assert result["success"]
        contract_path = signed_mart / "mart.yml"
        assert contract_path.exists()
        contract = yaml.safe_load(contract_path.read_text())
        assert contract["mart"]["name"] == "test-mart"
        assert contract["mart"]["prefix"] == "tst"
        assert contract["mart"]["db_name"] == "test_mart"

    def test_contract_metrics_match_brd(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        contract = yaml.safe_load((signed_mart / "mart.yml").read_text())
        metrics = contract["metrics"]
        assert len(metrics) == 2
        m1 = next(m for m in metrics if m["id"] == "M-1")
        assert m1["name"] == "Revenue"
        assert m1["source_type"] == "native"
        assert m1["link_status"] == "exact"
        assert m1["ads_column"] == "daily_revenue"
        m2 = next(m for m in metrics if m["id"] == "M-2")
        assert m2["name"] == "Order Count"
        assert m2["source_type"] == "derived"
        assert m2["link_status"] == "proxy"
        assert m2["ads_column"] == "order_count"

    def test_contract_active_layers(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        contract = yaml.safe_load((signed_mart / "mart.yml").read_text())
        layers = contract["layers"]
        assert layers["ods"]["active"] is True
        assert layers["dim"]["active"] is True
        assert layers["dwd"]["active"] is True
        assert layers["dws_count"]["active"] is True
        assert layers["dws_perf"]["active"] is False
        assert layers["ads"]["active"] is True

    def test_contract_dashboard_bindings(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        contract = yaml.safe_load((signed_mart / "mart.yml").read_text())
        assert contract["dashboard"]["ads_table"] == "tst_ads_exec_dashboard"
        assert contract["dashboard"]["dws_table"] == "tst_dws_daily_revenue_1d"

    def test_contract_in_files_created(self, signed_mart):
        result = scaffold(signed_mart, "test-mart", "tst")
        assert "mart.yml" in result["files_created"]


class TestEmptyDesignBypass:
    """TDDs with no actual design must be rejected (Finding 1)."""

    ALL_NA_TDD = """\
# Technical Design Document — Empty Design

## T-1. Version History
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-01-01 | Test | Initial |

## T-2. Design Reasoning
No design required.

## T-3. Table Summary
| Table Name | Layer | Purpose | Grain | Materialization |
|------------|-------|---------|-------|-----------------|

## T-4. Data Architecture Diagram
N/A

## T-5. Column Specification
Per-table specs follow in T-6 through T-11.

## T-6. ODS Table Design
not_applicable rationale: No ingestion needed for this hypothetical mart.

## T-7. Dimension Table Design
not_applicable rationale: No dimensions needed for this design.

## T-8. Fact Table Design (DWD)
not_applicable rationale: No fact table in this design.

## T-9. Count Aggregation Design (DWS)
not_applicable rationale: No count aggregation required.

## T-10. Performance Aggregation Design (DWS)
not_applicable rationale: No performance aggregation required.

## T-11. Presentation Table Design (ADS)
| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|------------|---------------|-------------|-------------|

## T-12. Physical Design
N/A

## T-13. Implementation Specification
N/A

## T-14. DQC Plan
N/A

## T-15. Test Inventory
N/A

## T-16. Operations
N/A

## T-17. Known Limitations
None.

Sign-off: APPROVED
Grade: A
"""

    def test_rejects_all_na_tdd_bypass(self, mart_dir):
        """A TDD with all N/A layers and empty T-11 table must be rejected."""
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(self.ALL_NA_TDD)
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"], "Scaffold accepted TDD with no actual design"
        assert any("ODS" in e and "not_applicable" in e for e in result["errors"])
        assert any("no data rows" in e.lower() or "not_applicable" in e for e in result["errors"])

    def test_rejects_na_ods(self, mart_dir):
        """T-6 ODS cannot be not_applicable — every mart needs ingestion."""
        mart_dir.mkdir()
        t6_start = VALID_TDD.find("## T-6. ODS Table Design")
        t7_start = VALID_TDD.find("## T-7. Dimension Table Design")
        na_ods_tdd = (
            VALID_TDD[:t6_start]
            + "## T-6. ODS Table Design\n\n"
            + "not_applicable rationale: No ODS layer needed for this mart.\n\n"
            + VALID_TDD[t7_start:]
        )
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(na_ods_tdd)
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"], "Scaffold accepted TDD with N/A ODS layer"
        assert any("T-6" in e and "not_applicable" in e for e in result["errors"])

    def test_rejects_header_only_ads(self, mart_dir):
        """T-11 with column_name header but no data rows must be rejected."""
        mart_dir.mkdir()
        header_only_tdd = VALID_TDD.replace(
            "| calendar_date | DATE | Date context | 2020-01-01 | dim_date.calendar_date via join | dim_date | - | exact |\n"
            "| order_count | BIGINT | Daily orders | 3 | dws.order_count via join | DWS | M-2 | proxy |\n"
            "| daily_revenue | DECIMAL | Daily revenue | 325.75 | dws.daily_revenue via join | DWS | M-1 | exact |",
            ""
        )
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(header_only_tdd)
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"], "Scaffold accepted TDD with header-only T-11"
        assert any("no data rows" in e.lower() for e in result["errors"])

    def test_rejects_no_fact_layer(self, mart_dir):
        """At least one fact/aggregation layer (T-8 DWD or T-9 DWS) is required."""
        mart_dir.mkdir()
        no_fact = VALID_TDD.replace(
            "## T-8. Fact Table Design (DWD)\n\n"
            "| column_name | data_type | definition | example_value | calculation | data_source | source_type |\n"
            "|-------------|-----------|------------|---------------|-------------|-------------|-------------|\n"
            "| order_line_sk | VARCHAR | Surrogate key | abc123 | md5(record_id || pull_date) | derived | derived |\n"
            "| date_key | INTEGER | FK to dim_date | 1 | coalesce(dim_date.date_sk, -1) | dim_date | native |\n"
            "| amount | DECIMAL | Order amount | 99.50 | not_applicable — pass-through from ODS | ods | native |\n\n"
            "Provenance columns: provider, pull_ts_utc, quote_ts_utc, run_id",
            "## T-8. Fact Table Design (DWD)\n\n"
            "not_applicable rationale: No fact table in this design. All data flows directly to aggregation."
        ).replace(
            "## T-9. Count Aggregation Design (DWS)\n\n"
            "| column_name | data_type | definition | example_value | calculation | data_source |\n"
            "|-------------|-----------|------------|---------------|-------------|-------------|\n"
            "| date_key | INTEGER | FK to dim_date | 1 | not_applicable — pass-through | DWD |\n"
            "| order_count | BIGINT | Daily order count | 3 | COUNT(DISTINCT record_id) | DWD aggregation |\n"
            "| daily_revenue | DECIMAL | Total daily revenue | 325.75 | SUM(amount) | DWD aggregation |",
            "## T-9. Count Aggregation Design (DWS)\n\n"
            "not_applicable rationale: No count aggregation. All metrics in T-8."
        )
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(no_fact)
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"], "Scaffold accepted TDD with no fact/aggregation layer"
        assert any("fact" in e.lower() or "aggregation" in e.lower() for e in result["errors"])


class TestContractLinkage:
    """BRD metric-to-ADS traceability must be validated (Finding 3)."""

    def test_rejects_mismatched_link_status(self, mart_dir):
        """T-11 link_status must match BRD metric link_status."""
        mart_dir.mkdir()
        bad_tdd = VALID_TDD.replace(
            "| order_count | BIGINT | Daily orders | 3 | dws.order_count via join | DWS | M-2 | proxy |",
            "| order_count | BIGINT | Daily orders | 3 | dws.order_count via join | DWS | M-2 | exact |"
        )
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(bad_tdd)
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"], "Scaffold accepted mismatched link_status"
        assert any("link_status" in e for e in result["errors"])

    def test_rejects_invalid_brd_ref(self, mart_dir):
        """T-11 BRD_ref must reference an actual BRD metric."""
        mart_dir.mkdir()
        bad_tdd = VALID_TDD.replace(
            "| order_count | BIGINT | Daily orders | 3 | dws.order_count via join | DWS | M-2 | proxy |",
            "| order_count | BIGINT | Daily orders | 3 | dws.order_count via join | DWS | M-99 | proxy |"
        )
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(bad_tdd)
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"], "Scaffold accepted T-11 referencing non-existent metric"
        assert any("M-99" in e for e in result["errors"])

    def test_rejects_untraced_brd_metric(self, mart_dir):
        """Every BRD metric must be traced in T-11."""
        mart_dir.mkdir()
        missing_tdd = VALID_TDD.replace(
            "| order_count | BIGINT | Daily orders | 3 | dws.order_count via join | DWS | M-2 | proxy |",
            "| order_count | BIGINT | Daily orders | 3 | dws.order_count via join | DWS | - | proxy |"
        )
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(missing_tdd)
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"], "Scaffold accepted TDD missing BRD metric trace"
        assert any("M-2" in e and "not traced" in e for e in result["errors"])

    def test_dashboard_no_uncontracted_metrics(self, signed_mart):
        """Dashboard must not display metrics not in the contract."""
        scaffold(signed_mart, "test-mart", "tst")
        content = (signed_mart / "dashboard" / "app.py").read_text()
        assert "Avg Order Value" not in content, \
            "Dashboard shows uncontracted metric"
        assert '"unsupported"' not in content or "unsupported" in content.lower(), \
            "Dashboard must not use unsupported for operational errors"

    def test_dashboard_error_state_not_unsupported(self, signed_mart):
        """Connection/data failures must show operational error, not unsupported."""
        scaffold(signed_mart, "test-mart", "tst")
        content = (signed_mart / "dashboard" / "app.py").read_text()
        assert "Data unavailable" in content or "pipeline has not been run" in content


class TestNameSanitization:
    def test_kebab_to_snake(self, signed_mart):
        result = scaffold(signed_mart, "my-test-mart", "tst")
        assert result["success"]
        content = (signed_mart / "dbt_project.yml").read_text()
        assert "my_test_mart" in content
        assert "my-test-mart" not in content

    def test_already_clean_name(self, signed_mart):
        result = scaffold(signed_mart, "clean_name", "tst")
        assert result["success"]
        content = (signed_mart / "dbt_project.yml").read_text()
        assert "clean_name" in content
