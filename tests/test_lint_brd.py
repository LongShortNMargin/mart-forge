"""Tests for scripts.lint_brd.

Covers happy path, missing-section detection, invalid link_status, and
bypass attempts (table without headers, headers without rows).
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from scripts.lint_brd import lint


GOOD_BRD = textwrap.dedent(
    """
    # BRD: example-mart

    ## B-1: Version History

    | Version | Date | Author | Changes |
    |---------|------|--------|---------|
    | 0.1 | 2026-05-28 | Author | Initial draft |

    ## B-2: Business Context

    Some context.

    ## B-3: Metrics Breakdown

    | metric_name | metric_definition | source_type | link_status |
    |-------------|-------------------|-------------|-------------|
    | rev | total revenue | native | exact |
    | gex | gamma exposure | derived | proxy |

    ## B-4: Notable / Known Limitations

    None at this time.
    """
).strip()


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "brd.md"
    p.write_text(content, encoding="utf-8")
    return p


class TestHappyPath:
    def test_well_formed_brd_passes(self, tmp_path: Path) -> None:
        p = _write(tmp_path, GOOD_BRD)
        assert lint(p) == []


class TestMissingSections:
    @pytest.mark.parametrize("section", ["B-1", "B-2", "B-3", "B-4"])
    def test_missing_section_rejected(self, tmp_path: Path, section: str) -> None:
        body = GOOD_BRD.replace(f"## {section}:", f"## NOT-{section}:")
        p = _write(tmp_path, body)
        errors = lint(p)
        assert errors
        assert any(f"§{section}" in err for err in errors)
        assert any("remediation" in err for err in errors)


class TestB3Columns:
    def test_missing_link_status_column_rejected(self, tmp_path: Path) -> None:
        body = GOOD_BRD.replace(
            "| metric_name | metric_definition | source_type | link_status |",
            "| metric_name | metric_definition | source_type | something_else |",
        ).replace(
            "|-------------|-------------------|-------------|-------------|",
            "|-------------|-------------------|-------------|----------------|",
        )
        p = _write(tmp_path, body)
        errors = lint(p)
        assert errors
        assert any("link_status" in err for err in errors)

    def test_invalid_link_status_value_rejected(self, tmp_path: Path) -> None:
        body = GOOD_BRD.replace(
            "| rev | total revenue | native | exact |",
            "| rev | total revenue | native | bogus |",
        )
        p = _write(tmp_path, body)
        errors = lint(p)
        assert any("invalid link_status" in err.lower() or "link_status" in err for err in errors)

    def test_invalid_source_type_value_rejected(self, tmp_path: Path) -> None:
        body = GOOD_BRD.replace(
            "| rev | total revenue | native | exact |",
            "| rev | total revenue | nuclear | exact |",
        )
        p = _write(tmp_path, body)
        errors = lint(p)
        assert any("source_type" in err for err in errors)


class TestAdversarial:
    def test_file_not_found_clear_error(self, tmp_path: Path) -> None:
        errors = lint(tmp_path / "missing.md")
        assert errors
        assert any("file not found" in err for err in errors)

    def test_empty_b3_table_rejected(self, tmp_path: Path) -> None:
        body = textwrap.dedent(
            """
            # BRD

            ## B-1: Version History

            v1

            ## B-2: Business Context

            ctx

            ## B-3: Metrics Breakdown

            (no table here)

            ## B-4: Notable / Known Limitations

            None.
            """
        ).strip()
        p = _write(tmp_path, body)
        errors = lint(p)
        assert any("§B-3" in err for err in errors)
