"""Scaffold workflow tests.

Tests the mart-forge scaffold command's hard gate enforcement
and successful skeleton generation from signed fixtures.
"""

import json
from pathlib import Path

import pytest

from mart_forge.scaffold import scaffold, _is_signed, _check_gates


@pytest.fixture
def mart_dir(tmp_path):
    return tmp_path / "test_mart"


@pytest.fixture
def signed_mart(mart_dir):
    mart_dir.mkdir()
    (mart_dir / "brd.md").write_text(
        "# Business Requirements\n\n## B-1 Scope\nGeneric test.\n\n"
        "Sign-off: APPROVED\nGrade: A\n"
    )
    (mart_dir / "tdd.md").write_text(
        "# Technical Design\n\n## T-1 Overview\nGeneric test.\n\n"
        "Sign-off: APPROVED\nGrade: A\n"
    )
    return mart_dir


class TestHardGateRejection:
    def test_rejects_missing_brd(self, mart_dir):
        mart_dir.mkdir()
        (mart_dir / "tdd.md").write_text("Sign-off: APPROVED\nGrade: A\n")
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"]
        assert any("BRD not found" in e for e in result["errors"])

    def test_rejects_unsigned_brd(self, mart_dir):
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text("# Draft BRD\nNo sign-off yet.\n")
        (mart_dir / "tdd.md").write_text("Sign-off: APPROVED\nGrade: A\n")
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"]
        assert any("BRD exists but is not signed off" in e for e in result["errors"])

    def test_rejects_missing_tdd(self, mart_dir):
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text("Sign-off: APPROVED\nGrade: A\n")
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"]
        assert any("TDD not found" in e for e in result["errors"])

    def test_rejects_unsigned_tdd(self, mart_dir):
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text("Sign-off: APPROVED\nGrade: A\n")
        (mart_dir / "tdd.md").write_text("# Draft TDD\nNo sign-off yet.\n")
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"]
        assert any("TDD exists but is not signed off" in e for e in result["errors"])

    def test_rejects_both_missing(self, mart_dir):
        mart_dir.mkdir()
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"]
        assert len(result["errors"]) == 2

    def test_no_files_created_on_rejection(self, mart_dir):
        mart_dir.mkdir()
        result = scaffold(mart_dir, "test-mart", "tst")
        assert result["files_created"] == []


class TestSuccessfulScaffold:
    def test_scaffold_succeeds_with_signed_docs(self, signed_mart):
        result = scaffold(signed_mart, "test-mart", "tst")
        assert result["success"]
        assert result["errors"] == []
        assert len(result["files_created"]) > 0

    def test_dbt_project_yml_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        dbt_project = signed_mart / "dbt_project.yml"
        assert dbt_project.exists()
        content = dbt_project.read_text()
        assert "test-mart" in content
        assert "model-paths" in content

    def test_profiles_yml_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        profiles = signed_mart / "profiles.yml"
        assert profiles.exists()
        content = profiles.read_text()
        assert "test-mart" in content
        assert "duckdb" in content

    def test_model_layer_dirs_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        for layer in ["ods", "dim", "dwd", "dws", "ads"]:
            assert (signed_mart / "models" / layer).is_dir()

    def test_schema_yml_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        schema = signed_mart / "models" / "schema.yml"
        assert schema.exists()
        content = schema.read_text()
        assert "tst_dim_date" in content

    def test_dashboard_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        app = signed_mart / "dashboard" / "app.py"
        assert app.exists()
        content = app.read_text()
        assert "test-mart" in content
        assert "streamlit" in content

    def test_scorecard_json_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        scorecard = signed_mart / "dqc_scorecard.json"
        assert scorecard.exists()
        data = json.loads(scorecard.read_text())
        assert data["mart"] == "test-mart"
        assert "controls" in data
        assert isinstance(data["controls"], list)

    def test_seeds_dir_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        assert (signed_mart / "seeds").is_dir()


class TestSignOffDetection:
    def test_grade_a_is_signed(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("# Doc\nGrade: A\n")
        assert _is_signed(doc)

    def test_approved_is_signed(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("# Doc\nAPPROVED by reviewer.\n")
        assert _is_signed(doc)

    def test_unsigned_doc(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("# Doc\nDraft version, not approved.\n")
        assert not _is_signed(doc)

    def test_missing_doc_not_signed(self, tmp_path):
        assert not _is_signed(tmp_path / "nonexistent.md")
