"""Tests for scripts.confidentiality_scan.

Covers:
- The happy path (a clean directory produces no violations).
- One positive test per banned-pattern category (the scanner DOES catch
  the banned string).
- Adversarial bypass attempts (split words, capitalization tricks, etc.)
  in a dedicated `TestAdversarial` class.
- The scanner excludes itself from scanning so the patterns it defines
  do not trigger.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from scripts.confidentiality_scan import scan_directory, scan_file


def _write(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return p


class TestHappyPath:
    def test_clean_dir_returns_no_violations(self, tmp_path: Path) -> None:
        _write(tmp_path, "readme.md", "# Clean repo\n\nNothing private here.\n")
        assert scan_directory(str(tmp_path)) == []

    def test_external_urls_are_ignored(self, tmp_path: Path) -> None:
        _write(tmp_path, "doc.md", "See https://example.com for details.\n")
        assert scan_directory(str(tmp_path)) == []


class TestBannedCategories:
    @pytest.mark.parametrize(
        "name,body,category",
        [
            ("a.md", "Path is /Users/jane/dev/foo.\n", "private_path"),
            ("a.md", "See Google Drive folder.\n", "private_path"),
            ("a.md", "Shopee data warehouse pattern.\n", "internal_project"),
            ("a.md", "From Chatbot Mart docs.\n", "internal_project"),
            ("a.md", "Per DragonRook standard.\n", "internal_project"),
            ("a.md", "See Emberlock_Kingdom/.\n", "internal_project"),
            ("a.md", "Argent reviewer signs off.\n", "internal_persona"),
            ("a.md", "Silver Chainbind operator.\n", "internal_persona"),
            ("a.md", "Ghost Operator era.\n", "internal_persona"),
            ("a.md", "DROOK orchestration.\n", "internal_program"),
            ("a.md", "FHAG pipeline.\n", "internal_program"),
            ("a.md", "SCAS release flow.\n", "internal_program"),
            ("a.md", "DaPES briefing.\n", "internal_program"),
            ("a.md", "FLQP cap.\n", "internal_program"),
            ("a.md", "Celestial Ordinance gate.\n", "internal_program"),
            ("a.md", "Burry catalyst playbook.\n", "internal_program"),
            ("a.md", "Email vuduclong0309@example.com\n", "user_id"),
            ("a.md", "github.com/LongShortNMargin/foo\n", "user_id"),
            ("a.md", "Track position_size column.\n", "operator_data"),
            ("a.md", "field: cost_basis decimal\n", "operator_data"),
            ("a.md", "Provide an account identifier.\n", "operator_data"),
        ],
    )
    def test_scanner_catches_category(
        self, tmp_path: Path, name: str, body: str, category: str
    ) -> None:
        _write(tmp_path, name, body)
        violations = scan_directory(str(tmp_path))
        assert violations, f"Expected at least one violation for {category!r}"
        assert any(v.category == category for v in violations)

    def test_scanner_catches_secret_aws_key(self, tmp_path: Path) -> None:
        _write(tmp_path, "leaked.md", "key=AKIAIOSFODNN7EXAMPLE\n")
        violations = scan_directory(str(tmp_path))
        assert any(v.category == "secret" for v in violations)


class TestRemediationHints:
    def test_every_violation_carries_remediation(self, tmp_path: Path) -> None:
        _write(tmp_path, "a.md", "Per DragonRook standard.\n")
        violations = scan_directory(str(tmp_path))
        assert violations
        for v in violations:
            assert v.remediation, "every violation must carry a non-empty remediation hint"


class TestSelfExclusion:
    def test_scanner_excludes_itself(self) -> None:
        # The scanner file contains every banned pattern; if it were
        # scanned, the whole suite would explode. Confirm the file is
        # excluded by name.
        from scripts.confidentiality_scan import EXCLUDED_FILENAMES

        assert "confidentiality_scan.py" in EXCLUDED_FILENAMES


class TestAdversarial:
    """Bypass attempts the scanner MUST still reject."""

    def test_capitalisation_variants_caught(self, tmp_path: Path) -> None:
        for variant in ("LongShortNMargin", "LONGSHORTNMARGIN", "longshortnmargin"):
            _write(tmp_path, "a.md", f"text {variant} more text\n")
            violations = scan_file(tmp_path / "a.md")
            assert violations, f"Failed to catch {variant!r}"

    def test_banned_string_inside_code_block(self, tmp_path: Path) -> None:
        body = """
        Some intro text.

        ```python
        # this is a comment that says Shopee
        ```
        """
        _write(tmp_path, "a.md", body)
        violations = scan_directory(str(tmp_path))
        assert any(v.category == "internal_project" for v in violations)

    def test_banned_string_inside_json_value(self, tmp_path: Path) -> None:
        body = '{"reviewer": "Argent", "ok": true}\n'
        _write(tmp_path, "a.json", body)
        violations = scan_directory(str(tmp_path))
        assert any(v.category == "internal_persona" for v in violations)

    def test_excluded_file_extensions_skipped(self, tmp_path: Path) -> None:
        # A .bin file is not scanned; banned strings inside it do not
        # fail the scan. This protects compiled artifacts from random
        # false positives.
        _write(tmp_path, "a.bin", "Shopee\n")
        violations = scan_directory(str(tmp_path))
        assert violations == []
