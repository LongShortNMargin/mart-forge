"""Tests for scripts.lint_layer_direction — main() and lint() edge cases.

Covers the CLI entry-point, upward reference detection, placeholder ref
skipping, and directory-not-found handling.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.lint_layer_direction import extract_layer, lint, main


class TestExtractLayer:
    @pytest.mark.parametrize(
        "name, expected",
        [
            ("gme_ods_raw.sql", "ods"),
            ("gme_dim_broker.sql", "dim"),
            ("gme_dwd_trades.sql", "dwd"),
            ("gme_dws_summary.sql", "dws"),
            ("gme_ads_dashboard.sql", "ads"),
            ("dim_broker.sql", "dim"),
            ("dim_something", "dim"),
            ("random_file.sql", None),
        ],
    )
    def test_layers(self, name: str, expected: str | None) -> None:
        assert extract_layer(name) == expected


class TestLint:
    def test_clean_models(self, tmp_path: Path) -> None:
        (tmp_path / "gme_ods_raw.sql").write_text(
            "SELECT * FROM source", encoding="utf-8"
        )
        (tmp_path / "gme_dwd_trades.sql").write_text(
            "SELECT * FROM {{ ref('gme_ods_raw') }}", encoding="utf-8"
        )
        assert lint(tmp_path) == []

    def test_upward_ref_detected(self, tmp_path: Path) -> None:
        (tmp_path / "gme_ads_dashboard.sql").write_text(
            "SELECT 1", encoding="utf-8"
        )
        (tmp_path / "gme_ods_raw.sql").write_text(
            "SELECT * FROM {{ ref('gme_ads_dashboard') }}", encoding="utf-8"
        )
        errors = lint(tmp_path)
        assert len(errors) == 1
        assert "references upward" in errors[0]

    def test_placeholder_refs_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "gme_ods_raw.sql").write_text(
            "SELECT * FROM {{ ref('<mart_prefix>_ads_report') }}", encoding="utf-8"
        )
        assert lint(tmp_path) == []

    def test_todo_placeholder_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "gme_ods_raw.sql").write_text(
            "SELECT * FROM {{ ref('_TODO_ads_report') }}", encoding="utf-8"
        )
        assert lint(tmp_path) == []

    def test_directory_not_found(self) -> None:
        errors = lint(Path("/nonexistent/models"))
        assert len(errors) == 1
        assert "directory not found" in errors[0]

    def test_no_sql_files(self, tmp_path: Path) -> None:
        (tmp_path / "readme.md").write_text("no sql", encoding="utf-8")
        assert lint(tmp_path) == []

    def test_files_without_layer_prefix_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "utils.sql").write_text(
            "SELECT * FROM {{ ref('gme_ads_dashboard') }}", encoding="utf-8"
        )
        (tmp_path / "gme_ads_dashboard.sql").write_text("SELECT 1", encoding="utf-8")
        assert lint(tmp_path) == []

    def test_same_layer_ref_allowed(self, tmp_path: Path) -> None:
        (tmp_path / "gme_dwd_a.sql").write_text(
            "SELECT * FROM {{ ref('gme_dwd_b') }}", encoding="utf-8"
        )
        (tmp_path / "gme_dwd_b.sql").write_text("SELECT 1", encoding="utf-8")
        assert lint(tmp_path) == []

    def test_downstream_ref_allowed(self, tmp_path: Path) -> None:
        (tmp_path / "gme_ads_report.sql").write_text(
            "SELECT * FROM {{ ref('gme_dws_summary') }}", encoding="utf-8"
        )
        (tmp_path / "gme_dws_summary.sql").write_text("SELECT 1", encoding="utf-8")
        assert lint(tmp_path) == []

    def test_unknown_ref_model_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "gme_ods_raw.sql").write_text(
            "SELECT * FROM {{ ref('some_unknown_model') }}", encoding="utf-8"
        )
        assert lint(tmp_path) == []


class TestMainCLI:
    def test_clean_returns_zero(self, tmp_path: Path) -> None:
        (tmp_path / "gme_ods_raw.sql").write_text("SELECT 1", encoding="utf-8")
        assert main([str(tmp_path)]) == 0

    def test_failure_returns_one(self, tmp_path: Path) -> None:
        (tmp_path / "gme_ads_report.sql").write_text("SELECT 1", encoding="utf-8")
        (tmp_path / "gme_ods_raw.sql").write_text(
            "SELECT * FROM {{ ref('gme_ads_report') }}", encoding="utf-8"
        )
        assert main([str(tmp_path)]) == 1

    def test_default_directory(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        models = tmp_path / "templates" / "models"
        models.mkdir(parents=True)
        (models / "gme_ods_raw.sql").write_text("SELECT 1", encoding="utf-8")
        assert main([]) == 0

    def test_empty_directory(self, tmp_path: Path) -> None:
        assert main([str(tmp_path)]) == 0
