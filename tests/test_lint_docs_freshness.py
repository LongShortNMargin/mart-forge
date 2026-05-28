"""Tests for scripts.lint_docs_freshness."""

from __future__ import annotations

from pathlib import Path

from scripts.lint_docs_freshness import lint


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestHappyPath:
    def test_resolvable_links_pass(self, tmp_path: Path) -> None:
        _write(tmp_path / "README.md", "See [SPEC.md](SPEC.md).\n")
        _write(tmp_path / "SPEC.md", "# Spec\n")
        assert lint(tmp_path) == []

    def test_external_urls_skipped(self, tmp_path: Path) -> None:
        _write(tmp_path / "doc.md", "See [example](https://example.com).\n")
        assert lint(tmp_path) == []

    def test_anchor_only_skipped(self, tmp_path: Path) -> None:
        _write(tmp_path / "doc.md", "[Section](#some-section).\n")
        assert lint(tmp_path) == []


class TestDanglingLinks:
    def test_dangling_link_caught(self, tmp_path: Path) -> None:
        _write(tmp_path / "doc.md", "See [missing](does_not_exist.md).\n")
        errors = lint(tmp_path)
        assert errors
        assert any("dangling link" in err for err in errors)
        assert any("remediation" in err for err in errors)


class TestStaleSpecNames:
    def test_spec_v2_md_rejected(self, tmp_path: Path) -> None:
        _write(tmp_path / "old.md", "See SPEC_V2.md for the old version.\n")
        errors = lint(tmp_path)
        assert errors
        assert any("SPEC_V2.md" in err for err in errors)

    def test_spec_feedback_rejected(self, tmp_path: Path) -> None:
        _write(tmp_path / "old.md", "Feedback in SPEC_FEEDBACK.md.\n")
        errors = lint(tmp_path)
        assert errors
        assert any("SPEC_FEEDBACK.md" in err for err in errors)

    def test_spec_iteration_2_rejected(self, tmp_path: Path) -> None:
        _write(tmp_path / "old.md", "Use SPEC_ITERATION_2.md.\n")
        errors = lint(tmp_path)
        assert errors


class TestAdversarial:
    def test_link_in_code_fence_still_flagged(self, tmp_path: Path) -> None:
        # Markdown links inside code fences are arguably ambiguous; we
        # still flag them because they often slip through cut-paste.
        _write(tmp_path / "doc.md", "```\nSee [missing](missing.md)\n```\n")
        errors = lint(tmp_path)
        assert any("dangling link" in err for err in errors)
