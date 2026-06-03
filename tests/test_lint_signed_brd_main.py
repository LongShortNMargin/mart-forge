"""Tests for scripts.lint_signed_brd — main(), discover_brds(), and
is_signed / _is_placeholder_cell edge cases.

Extends the existing test_lint_signed.py with coverage for the CLI
entry-point, auto-discovery, and tricky signing scenarios.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from scripts.lint_signed_brd import (
    _is_placeholder_cell,
    _is_template,
    discover_brds,
    is_signed,
    main,
)


SIGNED_BODY = textwrap.dedent(
    """\
    # BRD

    ## Signature

    | Role | Name | Date | Signature |
    |------|------|------|-----------|
    | Stakeholder | Jane Roe | 2026-06-01 | jroe |
    """
)

UNSIGNED_BODY = textwrap.dedent(
    """\
    # BRD

    ## Signature

    | Role | Name | Date | Signature |
    |------|------|------|-----------|
    | Stakeholder | __________ | __________ | __________ |
    """
)


class TestIsPlaceholderCell:
    @pytest.mark.parametrize(
        "value",
        ["", "  ", "___", "----", "TBD", "tbd", "TODO", "_TODO_", "—", "-"],
    )
    def test_placeholders(self, value: str) -> None:
        assert _is_placeholder_cell(value) is True

    @pytest.mark.parametrize(
        "value",
        ["Jane", "2026-06-01", "jroe", "Dr. Smith"],
    )
    def test_real_values(self, value: str) -> None:
        assert _is_placeholder_cell(value) is False


class TestIsTemplate:
    def test_template_in_name(self) -> None:
        assert _is_template(Path("foo.template.md")) is True

    def test_templates_in_path(self) -> None:
        assert _is_template(Path("templates/brd.md")) is True

    def test_normal_file(self) -> None:
        assert _is_template(Path("docs/business-requirements.md")) is False


class TestIsSignedEdgeCases:
    def test_no_signature_section(self, tmp_path: Path) -> None:
        p = tmp_path / "brd.md"
        p.write_text("# BRD\n\nNo signature here.\n", encoding="utf-8")
        assert is_signed(p) is False

    def test_signature_section_no_table(self, tmp_path: Path) -> None:
        body = "# BRD\n\n## Signature\n\nNo table here.\n"
        p = tmp_path / "brd.md"
        p.write_text(body, encoding="utf-8")
        assert is_signed(p) is False

    def test_table_missing_required_columns(self, tmp_path: Path) -> None:
        body = textwrap.dedent(
            """\
            # BRD

            ## Signature

            | Role | Person | When |
            |------|--------|------|
            | Stakeholder | Jane | 2026-06-01 |
            """
        )
        p = tmp_path / "brd.md"
        p.write_text(body, encoding="utf-8")
        assert is_signed(p) is False

    def test_row_with_too_few_cells(self, tmp_path: Path) -> None:
        body = textwrap.dedent(
            """\
            # BRD

            ## Signature

            | Role | Name | Date | Signature |
            |------|------|------|-----------|
            | Stakeholder | Jane |
            """
        )
        p = tmp_path / "brd.md"
        p.write_text(body, encoding="utf-8")
        assert is_signed(p) is False

    def test_signature_section_bounded_by_next_header(self, tmp_path: Path) -> None:
        body = textwrap.dedent(
            """\
            # BRD

            ## Signature

            | Role | Name | Date | Signature |
            |------|------|------|-----------|
            | Stakeholder | Jane | 2026-06-01 | jroe |

            ## Appendix

            Other stuff.
            """
        )
        p = tmp_path / "brd.md"
        p.write_text(body, encoding="utf-8")
        assert is_signed(p) is True

    def test_empty_table_after_header(self, tmp_path: Path) -> None:
        body = textwrap.dedent(
            """\
            # BRD

            ## Signature

            | Role | Name | Date | Signature |
            |------|------|------|-----------|
            """
        )
        p = tmp_path / "brd.md"
        p.write_text(body, encoding="utf-8")
        assert is_signed(p) is False


class TestDiscoverBrds:
    def test_finds_brd_files(self, tmp_path: Path) -> None:
        d = tmp_path / "docs" / "marts"
        d.mkdir(parents=True)
        (d / "business-requirements.md").write_text(SIGNED_BODY, encoding="utf-8")
        result = discover_brds(tmp_path)
        assert len(result) == 1

    def test_finds_brd_variants(self, tmp_path: Path) -> None:
        d = tmp_path / "sub"
        d.mkdir()
        (d / "my-brd.md").write_text(SIGNED_BODY, encoding="utf-8")
        (d / "project-BRD.md").write_text(SIGNED_BODY, encoding="utf-8")
        result = discover_brds(tmp_path)
        assert len(result) == 2

    def test_excludes_templates(self, tmp_path: Path) -> None:
        d = tmp_path / "templates"
        d.mkdir()
        (d / "business-requirements.template.md").write_text(
            UNSIGNED_BODY, encoding="utf-8"
        )
        result = discover_brds(tmp_path)
        assert result == []

    def test_empty_dir(self, tmp_path: Path) -> None:
        result = discover_brds(tmp_path)
        assert result == []


class TestMainCLI:
    def test_no_args_no_docs_marts(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        assert main([]) == 0

    def test_no_args_with_signed_brd(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        d = tmp_path / "docs" / "marts" / "m1"
        d.mkdir(parents=True)
        (d / "business-requirements.md").write_text(SIGNED_BODY, encoding="utf-8")
        assert main([]) == 0

    def test_no_args_with_unsigned_brd(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        d = tmp_path / "docs" / "marts" / "m1"
        d.mkdir(parents=True)
        (d / "business-requirements.md").write_text(UNSIGNED_BODY, encoding="utf-8")
        assert main([]) == 1

    def test_explicit_file_signed(self, tmp_path: Path) -> None:
        p = tmp_path / "brd.md"
        p.write_text(SIGNED_BODY, encoding="utf-8")
        assert main([str(p)]) == 0

    def test_explicit_file_unsigned(self, tmp_path: Path) -> None:
        p = tmp_path / "brd.md"
        p.write_text(UNSIGNED_BODY, encoding="utf-8")
        assert main([str(p)]) == 1

    def test_explicit_file_not_found(self, tmp_path: Path) -> None:
        p = tmp_path / "nonexistent.md"
        assert main([str(p)]) == 1

    def test_explicit_directory_arg(self, tmp_path: Path) -> None:
        d = tmp_path / "marts"
        d.mkdir()
        (d / "business-requirements.md").write_text(SIGNED_BODY, encoding="utf-8")
        assert main([str(d)]) == 0

    def test_explicit_directory_no_brds(self, tmp_path: Path) -> None:
        d = tmp_path / "empty"
        d.mkdir()
        assert main([str(d)]) == 0

    def test_no_args_docs_marts_empty(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        d = tmp_path / "docs" / "marts"
        d.mkdir(parents=True)
        assert main([]) == 0
