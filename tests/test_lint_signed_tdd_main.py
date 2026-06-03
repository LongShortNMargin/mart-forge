"""Tests for scripts.lint_signed_tdd — main() and discover_tdds().

Extends the existing test_lint_signed.py (which covers lint_paths and
is_signed primitives) with coverage for the CLI entry-point and the
auto-discovery logic.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from scripts.lint_signed_tdd import discover_tdds, main


SIGNED_BODY = textwrap.dedent(
    """\
    # TDD

    ## Signature

    | Role | Name | Date | Signature |
    |------|------|------|-----------|
    | Engineer | Alice | 2026-06-01 | alice |
    """
)

UNSIGNED_BODY = textwrap.dedent(
    """\
    # TDD

    ## Signature

    | Role | Name | Date | Signature |
    |------|------|------|-----------|
    | Engineer | __________ | __________ | __________ |
    """
)


class TestDiscoverTdds:
    def test_discovers_tdd_by_name(self, tmp_path: Path) -> None:
        d = tmp_path / "docs" / "marts" / "m1"
        d.mkdir(parents=True)
        (d / "tech-design-doc.md").write_text(SIGNED_BODY, encoding="utf-8")
        result = discover_tdds(tmp_path)
        assert len(result) == 1
        assert result[0].name == "tech-design-doc.md"

    def test_discovers_tdd_variants(self, tmp_path: Path) -> None:
        d = tmp_path / "sub"
        d.mkdir()
        (d / "my-tdd.md").write_text(SIGNED_BODY, encoding="utf-8")
        (d / "project-TDD-v2.md").write_text(SIGNED_BODY, encoding="utf-8")
        result = discover_tdds(tmp_path)
        assert len(result) == 2

    def test_excludes_templates(self, tmp_path: Path) -> None:
        d = tmp_path / "templates"
        d.mkdir()
        (d / "tech-design-doc.template.md").write_text(UNSIGNED_BODY, encoding="utf-8")
        result = discover_tdds(tmp_path)
        assert result == []

    def test_empty_dir(self, tmp_path: Path) -> None:
        result = discover_tdds(tmp_path)
        assert result == []


class TestMainCLI:
    def test_no_args_no_docs_marts_returns_zero(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        assert main([]) == 0

    def test_no_args_with_docs_marts_signed(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        d = tmp_path / "docs" / "marts" / "m1"
        d.mkdir(parents=True)
        (d / "tech-design-doc.md").write_text(SIGNED_BODY, encoding="utf-8")
        assert main([]) == 0

    def test_no_args_with_docs_marts_unsigned(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        d = tmp_path / "docs" / "marts" / "m1"
        d.mkdir(parents=True)
        (d / "tech-design-doc.md").write_text(UNSIGNED_BODY, encoding="utf-8")
        assert main([]) == 1

    def test_explicit_file_signed(self, tmp_path: Path) -> None:
        p = tmp_path / "tdd.md"
        p.write_text(SIGNED_BODY, encoding="utf-8")
        assert main([str(p)]) == 0

    def test_explicit_file_unsigned(self, tmp_path: Path) -> None:
        p = tmp_path / "tdd.md"
        p.write_text(UNSIGNED_BODY, encoding="utf-8")
        assert main([str(p)]) == 1

    def test_explicit_file_not_found(self, tmp_path: Path) -> None:
        p = tmp_path / "nonexistent.md"
        assert main([str(p)]) == 1

    def test_explicit_directory_arg(self, tmp_path: Path) -> None:
        d = tmp_path / "marts"
        d.mkdir()
        (d / "tech-design-doc.md").write_text(SIGNED_BODY, encoding="utf-8")
        assert main([str(d)]) == 0

    def test_explicit_directory_no_tdds(self, tmp_path: Path) -> None:
        d = tmp_path / "empty"
        d.mkdir()
        assert main([str(d)]) == 0

    def test_no_args_docs_marts_empty(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        d = tmp_path / "docs" / "marts"
        d.mkdir(parents=True)
        assert main([]) == 0
