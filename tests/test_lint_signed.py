"""Tests for the signing-gate linters (reviewer finding #6).

The "no scaffold without signed TDD; no TDD without signed BRD" rule
used to be enforced only by SKILL.md prose. These tests assert the
linters actually reject unsigned documents.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from scripts.lint_signed_brd import is_signed, lint_paths as brd_lint_paths
from scripts.lint_signed_tdd import lint_paths as tdd_lint_paths


SIGNATURE_UNSIGNED = textwrap.dedent(
    """
    ## Signature

    | Role | Name | Date | Signature |
    |------|------|------|-----------|
    | Stakeholder | ________________ | __________ | __________ |
    | Data Engineer | ________________ | __________ | __________ |
    """
).strip()

SIGNATURE_SIGNED = textwrap.dedent(
    """
    ## Signature

    | Role | Name | Date | Signature |
    |------|------|------|-----------|
    | Stakeholder | Jane Roe | 2026-06-01 | jroe |
    | Data Engineer | John Doe | 2026-06-01 | jdoe |
    """
).strip()


def _doc(body: str) -> str:
    return "# Doc\n\n## B-1: Version History\n\nstub\n\n" + body + "\n"


def _write(tmp_path: Path, body: str, *, name: str = "brd.md") -> Path:
    p = tmp_path / name
    p.write_text(_doc(body), encoding="utf-8")
    return p


class TestBRDSigning:
    def test_unsigned_brd_rejected(self, tmp_path: Path) -> None:
        marts = tmp_path / "docs" / "marts" / "example"
        marts.mkdir(parents=True)
        p = _write(marts, SIGNATURE_UNSIGNED, name="business-requirements.md")
        errors = brd_lint_paths([p])
        assert errors, "unsigned BRD must be rejected"
        assert any("Signature" in err for err in errors)

    def test_signed_brd_passes(self, tmp_path: Path) -> None:
        marts = tmp_path / "docs" / "marts" / "example"
        marts.mkdir(parents=True)
        p = _write(marts, SIGNATURE_SIGNED, name="business-requirements.md")
        errors = brd_lint_paths([p])
        assert errors == [], f"unexpected: {errors}"

    def test_missing_signature_section_rejected(self, tmp_path: Path) -> None:
        marts = tmp_path / "docs" / "marts" / "example"
        marts.mkdir(parents=True)
        p = marts / "business-requirements.md"
        p.write_text("# Doc\n\nNo signature here at all.\n", encoding="utf-8")
        errors = brd_lint_paths([p])
        assert errors

    def test_template_is_skipped(self, tmp_path: Path) -> None:
        # Templates always have placeholder signatures; the linter must
        # skip them.
        tmpl = tmp_path / "templates"
        tmpl.mkdir()
        p = _write(tmpl, SIGNATURE_UNSIGNED, name="business-requirements.template.md")
        errors = brd_lint_paths([p])
        assert errors == []


class TestTDDSigning:
    def test_unsigned_tdd_rejected(self, tmp_path: Path) -> None:
        marts = tmp_path / "docs" / "marts" / "example"
        marts.mkdir(parents=True)
        p = _write(marts, SIGNATURE_UNSIGNED, name="tech-design-doc.md")
        errors = tdd_lint_paths([p])
        assert errors
        assert any("scaffold without signed TDD" in err for err in errors)

    def test_signed_tdd_passes(self, tmp_path: Path) -> None:
        marts = tmp_path / "docs" / "marts" / "example"
        marts.mkdir(parents=True)
        p = _write(marts, SIGNATURE_SIGNED, name="tech-design-doc.md")
        errors = tdd_lint_paths([p])
        assert errors == []

    def test_template_tdd_is_skipped(self, tmp_path: Path) -> None:
        tmpl = tmp_path / "templates"
        tmpl.mkdir()
        p = _write(tmpl, SIGNATURE_UNSIGNED, name="tech-design-doc.template.md")
        errors = tdd_lint_paths([p])
        assert errors == []


class TestSignedPrimitive:
    """The internal helper exposed by lint_signed_brd."""

    def test_one_signed_row_is_enough(self, tmp_path: Path) -> None:
        body = textwrap.dedent(
            """
            ## Signature

            | Role | Name | Date | Signature |
            |------|------|------|-----------|
            | Stakeholder | Jane | 2026-06-01 | jroe |
            | Data Engineer | ____________ | __________ | __________ |
            """
        ).strip()
        p = _write(tmp_path, body, name="brd.md")
        assert is_signed(p)

    def test_all_placeholder_rows_fail(self, tmp_path: Path) -> None:
        p = _write(tmp_path, SIGNATURE_UNSIGNED, name="brd.md")
        assert not is_signed(p)
