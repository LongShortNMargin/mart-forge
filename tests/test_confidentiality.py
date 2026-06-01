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
        # excluded by relative path (not basename — see finding #9).
        from scripts.confidentiality_scan import EXCLUDED_PATHS

        assert "scripts/confidentiality_scan.py" in EXCLUDED_PATHS


class TestDotDirScanning:
    """Reviewer finding #1: dot-prefixed directories at any depth used to
    be silently skipped, so banned strings in `.claude/`, `.claude-plugin/`,
    and `.github/` slipped past CI.

    The scanner now uses an explicit allow-list (`ALLOWED_DOT_DIR_SKIPS`);
    any dot-dir not on that list is walked.
    """

    @pytest.mark.parametrize(
        "rel_dir",
        [
            ".claude/skills/source-discovery",
            ".claude-plugin",
            ".github/workflows",
        ],
    )
    def test_banned_string_in_dot_dir_is_caught(
        self, tmp_path: Path, rel_dir: str
    ) -> None:
        dot_dir = tmp_path / rel_dir
        dot_dir.mkdir(parents=True)
        (dot_dir / "leaked.md").write_text(
            "This file accidentally names Shopee in the prose.\n",
            encoding="utf-8",
        )
        violations = scan_directory(str(tmp_path))
        assert violations, (
            f"finding #1 regression: scanner missed banned string in {rel_dir}"
        )
        assert any(v.category == "internal_project" for v in violations)

    def test_git_dir_still_skipped(self, tmp_path: Path) -> None:
        git_dir = tmp_path / ".git" / "objects"
        git_dir.mkdir(parents=True)
        # .git is on the allow-list so its files are never scanned.
        (git_dir / "fake.txt").write_text("Shopee\n", encoding="utf-8")
        assert scan_directory(str(tmp_path)) == []

    def test_pycache_still_skipped(self, tmp_path: Path) -> None:
        pyc = tmp_path / "__pycache__"
        pyc.mkdir()
        (pyc / "fake.py").write_text("# DROOK\n", encoding="utf-8")
        assert scan_directory(str(tmp_path)) == []

    def test_yaml_workflow_in_github_dir_scanned(self, tmp_path: Path) -> None:
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "framework-ci.yml").write_text(
            "# CI for Shopee data warehouse\n",
            encoding="utf-8",
        )
        violations = scan_directory(str(tmp_path))
        assert violations
        assert any(v.category == "internal_project" for v in violations)


class TestRelativePathExclusion:
    """Reviewer finding #9: EXCLUDED_FILENAMES used to match basename
    only, so `templates/confidentiality_scan.py` (or any file with that
    name anywhere in the tree) bypassed the scan. Exclusion now matches
    the relative path so only the real scanner file is exempt.
    """

    def test_decoy_file_with_scanner_basename_is_still_scanned(
        self, tmp_path: Path
    ) -> None:
        decoy_dir = tmp_path / "templates"
        decoy_dir.mkdir()
        (decoy_dir / "confidentiality_scan.py").write_text(
            "# decoy named like the scanner, leaks Shopee\n",
            encoding="utf-8",
        )
        violations = scan_directory(str(tmp_path))
        assert violations, "finding #9 regression: basename-match bypass still works"

    def test_real_scanner_path_still_excluded(self, tmp_path: Path) -> None:
        # Create the actual relative path the scanner uses for itself.
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "confidentiality_scan.py").write_text(
            "# pretend this is the scanner — banned strings inside should not fire\n"
            "# DROOK FHAG vuduclong0309\n",
            encoding="utf-8",
        )
        assert scan_directory(str(tmp_path)) == []


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

    def test_lowercase_internal_persona_caught(self, tmp_path: Path) -> None:
        # L1: every internal_persona / internal_program pattern is now
        # case-insensitive. `argent` and `ARGENT` are caught the same
        # way `Argent` was before.
        for variant in ("argent", "ARGENT", "Argent"):
            _write(tmp_path, "a.md", f"reviewer is {variant}\n")
            violations = scan_file(tmp_path / "a.md")
            assert any(
                v.category == "internal_persona" for v in violations
            ), f"L1 regression: {variant!r} not caught"

    def test_lowercase_internal_program_caught(self, tmp_path: Path) -> None:
        for variant in ("drook", "DROOK", "fhag", "FHAG"):
            _write(tmp_path, "a.md", f"system: {variant}\n")
            violations = scan_file(tmp_path / "a.md")
            assert any(
                v.category == "internal_program" for v in violations
            ), f"L1 regression: {variant!r} not caught"


class TestPublicOrgAllowList:
    """B2: the public GitHub org slug `LongShortNMargin` is allowed
    in three narrow install-surface files. Everywhere else, the slug
    still trips the scanner. The orchestrator spec clarification
    (EMB-322, 2026-06-01) governs this carve-out.
    """

    def test_slug_allowed_in_marketplace_json(self, tmp_path: Path) -> None:
        cp_dir = tmp_path / ".claude-plugin"
        cp_dir.mkdir()
        (cp_dir / "marketplace.json").write_text(
            '{"owner": {"name": "LongShortNMargin"}}\n', encoding="utf-8"
        )
        assert scan_directory(str(tmp_path)) == []

    def test_slug_allowed_in_readme(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "README.md",
            "Install via /plugin marketplace add LongShortNMargin/mart-forge\n",
        )
        assert scan_directory(str(tmp_path)) == []

    def test_slug_allowed_in_marketplace_md(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "MARKETPLACE.md",
            "Add LongShortNMargin/mart-forge to the community directory.\n",
        )
        assert scan_directory(str(tmp_path)) == []

    def test_slug_blocked_in_a_random_skill_body(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "skills" / "lifecycle" / "demo"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: demo\n---\nrun git clone https://github.com/LongShortNMargin/x\n",
            encoding="utf-8",
        )
        violations = scan_directory(str(tmp_path))
        assert violations, "B2 regression: slug must still trip outside install surfaces"
        assert any(v.category == "user_id" for v in violations)

    def test_slug_blocked_in_docs(self, tmp_path: Path) -> None:
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "notes.md").write_text(
            "Reference: LongShortNMargin internal handle\n", encoding="utf-8"
        )
        violations = scan_directory(str(tmp_path))
        assert any(v.category == "user_id" for v in violations)

    def test_other_banned_strings_in_allowed_path_still_caught(
        self, tmp_path: Path
    ) -> None:
        # The allow-list only forgives the public-org slug. A different
        # banned string in README.md must still fail.
        _write(tmp_path, "README.md", "internal: DROOK\n")
        violations = scan_directory(str(tmp_path))
        assert any(v.category == "internal_program" for v in violations)
