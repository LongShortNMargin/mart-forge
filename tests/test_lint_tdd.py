"""Tests for scripts.lint_tdd.

The most important property: a derived-column row that puts prose
('derived', 'computed', 'see model') in the `calculation` column is
rejected. This was a recurring pattern in prior iterations.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from scripts.lint_tdd import lint


def _good_tdd(prefix: str = "ord") -> str:
    sections = ["# TDD: example\n"]
    for i in range(1, 22):
        sections.append(f"## T-{i}: Section\n\nContent.\n")
    # Replace T-8 with a real schema table.
    t8 = (
        "## T-8: Table Schema Detail\n\n"
        "| column_name | data_type | definition | example_value | calculation | data_source |\n"
        "|---|---|---|---|---|---|\n"
        f"| {prefix}_id | INTEGER | id | 1 | pass-through from src.id | source.t |\n"
    )
    t9 = (
        "## T-9: ODS Table Columns\n\n"
        "| Property | Value |\n"
        "|---|---|\n"
        "| source | provider.api |\n"
        "| grain | one row per day |\n"
        "| logical_partition | event_date |\n"
        "| incremental_strategy | delete+insert |\n"
        "| unique_key | event_date |\n"
        "| backfill | dbt run --vars |\n"
        "| restatement | delete+insert replaces |\n"
        "| provenance_columns | provider, pull_ts_utc, run_id |\n"
    )
    body = "".join(sections)
    body = body.replace("## T-8: Section\n\nContent.\n", t8)
    body = body.replace("## T-9: Section\n\nContent.\n", t9)
    return body


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "tdd.md"
    p.write_text(content, encoding="utf-8")
    return p


class TestHappyPath:
    def test_well_formed_tdd_passes(self, tmp_path: Path) -> None:
        p = _write(tmp_path, _good_tdd())
        assert lint(p) == []


class TestMissingSections:
    @pytest.mark.parametrize("missing", ["T-1", "T-8", "T-15", "T-21"])
    def test_missing_section_rejected(self, tmp_path: Path, missing: str) -> None:
        body = _good_tdd().replace(f"## {missing}: ", f"## NOT-{missing}: ")
        p = _write(tmp_path, body)
        errors = lint(p)
        assert any(f"§{missing}" in err for err in errors)


class TestT8Columns:
    def test_missing_required_column_rejected(self, tmp_path: Path) -> None:
        body = _good_tdd().replace(
            "| column_name | data_type | definition | example_value | calculation | data_source |",
            "| column_name | data_type | definition | example_value | calculation |",
        ).replace(
            "|---|---|---|---|---|---|",
            "|---|---|---|---|---|",
        ).replace(
            "| ord_id | INTEGER | id | 1 | pass-through from src.id | source.t |",
            "| ord_id | INTEGER | id | 1 | pass-through from src.id |",
        )
        p = _write(tmp_path, body)
        errors = lint(p)
        assert any("data_source" in err for err in errors)


class TestT9OdsContract:
    @pytest.mark.parametrize("field", [
        "source", "grain", "logical_partition", "incremental_strategy",
        "unique_key", "backfill", "restatement", "provenance_columns",
    ])
    def test_missing_t9_field_rejected(self, tmp_path: Path, field: str) -> None:
        body = _good_tdd()
        # Remove the row containing the field.
        body = "\n".join(
            line for line in body.splitlines() if not line.lstrip().startswith(f"| {field} ")
        )
        p = _write(tmp_path, body)
        errors = lint(p)
        assert any(field in err for err in errors)


class TestAdversarial:
    def test_prose_in_calculation_rejected(self, tmp_path: Path) -> None:
        body = _good_tdd().replace("pass-through from src.id", "derived")
        p = _write(tmp_path, body)
        errors = lint(p)
        assert errors
        assert any("calculation" in err.lower() for err in errors)
        assert any("prose placeholder" in err.lower() or "derived" in err.lower() for err in errors)

    @pytest.mark.parametrize("prose", ["computed", "see model", "TBD", "TODO"])
    def test_other_prose_placeholders_rejected(self, tmp_path: Path, prose: str) -> None:
        body = _good_tdd().replace("pass-through from src.id", prose)
        p = _write(tmp_path, body)
        errors = lint(p)
        assert errors
        assert any("calculation" in err.lower() for err in errors)
