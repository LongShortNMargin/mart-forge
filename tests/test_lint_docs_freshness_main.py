"""Tests for scripts.lint_docs_freshness — main() and lint() edge cases.

Covers the CLI entry-point, dangling link detection, stale spec filename
detection, and directory-not-found handling.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.lint_docs_freshness import is_external_link, lint, main


class TestIsExternalLink:
    @pytest.mark.parametrize(
        "url",
        [
            "http://example.com",
            "https://example.com",
            "mailto:a@b.com",
            "#anchor",
        ],
    )
    def test_external(self, url: str) -> None:
        assert is_external_link(url) is True

    @pytest.mark.parametrize(
        "url",
        ["./foo.md", "../bar.md", "SPEC.md", "docs/ref.md"],
    )
    def test_not_external(self, url: str) -> None:
        assert is_external_link(url) is False


class TestLint:
    def test_clean_directory(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text(
            "# Hello\n\nSee [SPEC](SPEC.md).\n", encoding="utf-8"
        )
        (tmp_path / "SPEC.md").write_text("# Spec\n", encoding="utf-8")
        assert lint(tmp_path) == []

    def test_dangling_link_detected(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text(
            "# Hello\n\nSee [missing](nonexistent.md).\n", encoding="utf-8"
        )
        errors = lint(tmp_path)
        assert len(errors) == 1
        assert "dangling link" in errors[0]

    def test_stale_spec_filename(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text(
            "# Hello\n\nSee SPEC_V2.md for details.\n", encoding="utf-8"
        )
        errors = lint(tmp_path)
        assert len(errors) == 1
        assert "stale spec filename" in errors[0]

    @pytest.mark.parametrize(
        "banned",
        ["SPEC_V2.md", "SPEC_FEEDBACK.md", "SPEC_ITERATION_3.md", "SPEC_DRAFT.md"],
    )
    def test_all_banned_patterns(self, tmp_path: Path, banned: str) -> None:
        (tmp_path / "doc.md").write_text(
            f"See {banned} for details.\n", encoding="utf-8"
        )
        errors = lint(tmp_path)
        assert errors

    def test_external_links_ignored(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text(
            "[Google](https://google.com)\n", encoding="utf-8"
        )
        assert lint(tmp_path) == []

    def test_anchor_only_link_ignored(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text(
            "See [below](#section).\n", encoding="utf-8"
        )
        assert lint(tmp_path) == []

    def test_link_with_anchor_to_existing_file(self, tmp_path: Path) -> None:
        (tmp_path / "SPEC.md").write_text("# Spec\n", encoding="utf-8")
        (tmp_path / "README.md").write_text(
            "See [spec](SPEC.md#section).\n", encoding="utf-8"
        )
        assert lint(tmp_path) == []

    def test_directory_not_found(self) -> None:
        errors = lint(Path("/nonexistent/path"))
        assert len(errors) == 1
        assert "directory not found" in errors[0]

    def test_no_markdown_files(self, tmp_path: Path) -> None:
        (tmp_path / "data.txt").write_text("not markdown", encoding="utf-8")
        assert lint(tmp_path) == []


class TestMainCLI:
    def test_clean_dir_returns_zero(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Ok\n", encoding="utf-8")
        assert main([str(tmp_path)]) == 0

    def test_failure_returns_one(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text(
            "# Hello\n\nSee [bad](missing.md).\n", encoding="utf-8"
        )
        assert main([str(tmp_path)]) == 1

    def test_default_directory(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "README.md").write_text("# Ok\n", encoding="utf-8")
        assert main([]) == 0
