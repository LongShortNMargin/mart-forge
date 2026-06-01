"""Tests for scripts.validate_dogfood.

The critical case here is the `"reconstructed": true` rejection — the
specific bypass shape that defeated the prior iteration of mart-forge.
This is exercised in `TestAdversarial::test_rejects_reconstructed_entry`.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from scripts.validate_dogfood import validate_file


def _entry(**overrides) -> dict:
    base = {
        "timestamp": "2026-05-28T12:00:00Z",
        "skill_name": "commit",
        "input_artifact": "src/a.py",
        "output_artifact": "abc123def",
        "checkpoint": "commit",
        "reconstructed": False,
    }
    base.update(overrides)
    return base


def _write_log(tmp_path: Path, *entries: dict) -> Path:
    p = tmp_path / "log.jsonl"
    p.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")
    return p


class TestHappyPath:
    def test_valid_single_entry(self, tmp_path: Path) -> None:
        log = _write_log(tmp_path, _entry())
        assert validate_file(log) == []

    def test_valid_multiple_entries(self, tmp_path: Path) -> None:
        log = _write_log(tmp_path, _entry(), _entry(skill_name="land"))
        assert validate_file(log) == []

    def test_empty_file_is_acceptable(self, tmp_path: Path) -> None:
        p = tmp_path / "log.jsonl"
        p.write_text("", encoding="utf-8")
        assert validate_file(p) == []

    def test_missing_file_is_acceptable(self, tmp_path: Path) -> None:
        # A repo with no skills yet invoked has no log. That is fine.
        p = tmp_path / "log.jsonl"
        assert validate_file(p) == []

    def test_blank_lines_skipped(self, tmp_path: Path) -> None:
        p = tmp_path / "log.jsonl"
        p.write_text("\n\n" + json.dumps(_entry()) + "\n\n", encoding="utf-8")
        assert validate_file(p) == []


class TestMissingFields:
    @pytest.mark.parametrize(
        "drop",
        ["timestamp", "skill_name", "input_artifact", "output_artifact", "checkpoint", "reconstructed"],
    )
    def test_missing_required_field(self, tmp_path: Path, drop: str) -> None:
        e = _entry()
        del e[drop]
        log = _write_log(tmp_path, e)
        errors = validate_file(log)
        assert errors
        assert any(drop in err for err in errors)


class TestInvalidJson:
    def test_invalid_json_line_rejected(self, tmp_path: Path) -> None:
        p = tmp_path / "log.jsonl"
        p.write_text("{not valid json\n", encoding="utf-8")
        errors = validate_file(p)
        assert errors
        assert "invalid JSON" in errors[0]

    def test_non_object_rejected(self, tmp_path: Path) -> None:
        p = tmp_path / "log.jsonl"
        p.write_text('"a string"\n', encoding="utf-8")
        errors = validate_file(p)
        assert errors
        assert "expected JSON object" in errors[0]


class TestReconstructedTypeChecks:
    def test_string_reconstructed_rejected(self, tmp_path: Path) -> None:
        log = _write_log(tmp_path, _entry(reconstructed="false"))
        errors = validate_file(log)
        assert any("must be a boolean" in err for err in errors)

    def test_integer_reconstructed_rejected(self, tmp_path: Path) -> None:
        log = _write_log(tmp_path, _entry(reconstructed=0))
        errors = validate_file(log)
        assert any("must be a boolean" in err for err in errors)


class TestAdversarial:
    """Bypass attempts the validator MUST still reject."""

    def test_rejects_reconstructed_entry(self, tmp_path: Path) -> None:
        """The single most important test in the suite.

        Prior iteration shipped a dogfood log with `"reconstructed": true`
        and passed CI without actually invoking the skills. This test
        defeats that bypass.
        """
        log = _write_log(tmp_path, _entry(reconstructed=True))
        errors = validate_file(log)
        assert errors
        assert any("'reconstructed': true" in err for err in errors)
        assert any("forbidden" in err for err in errors)

    def test_mixed_log_with_one_reconstructed_still_fails(self, tmp_path: Path) -> None:
        """A log with 99 honest entries and 1 reconstructed entry fails.
        The whole log must be real."""
        log = _write_log(
            tmp_path,
            _entry(),
            _entry(skill_name="land"),
            _entry(skill_name="push", reconstructed=True),
            _entry(skill_name="commit"),
        )
        errors = validate_file(log)
        assert any("'reconstructed': true" in err for err in errors)

    def test_reconstructed_uppercase_value_not_a_loophole(self, tmp_path: Path) -> None:
        """`"reconstructed": "true"` (string, not boolean) is still
        rejected — by the type check, not the reject-true check, but
        the bypass-prevention property holds."""
        log = _write_log(tmp_path, _entry(reconstructed="true"))
        errors = validate_file(log)
        assert errors  # caught by type check

    def test_remediation_hint_present(self, tmp_path: Path) -> None:
        """Every rejection must include a remediation hint pointing the
        author at the right next step."""
        log = _write_log(tmp_path, _entry(reconstructed=True))
        errors = validate_file(log)
        assert any("remediation" in err for err in errors)


class TestRequireNonEmpty:
    """Reviewer finding #2: a missing or whitespace-only log used to
    pass. With --require-non-empty CI rejects this."""

    def test_missing_file_rejected(self, tmp_path: Path) -> None:
        p = tmp_path / "log.jsonl"
        errors = validate_file(p, require_non_empty=True)
        assert errors, "absent log must fail when --require-non-empty"
        assert any("required to exist" in err for err in errors)

    def test_empty_file_rejected(self, tmp_path: Path) -> None:
        p = tmp_path / "log.jsonl"
        p.write_text("", encoding="utf-8")
        errors = validate_file(p, require_non_empty=True)
        assert errors
        assert any("empty" in err for err in errors)

    def test_whitespace_only_file_rejected(self, tmp_path: Path) -> None:
        p = tmp_path / "log.jsonl"
        p.write_text("\n\n   \n", encoding="utf-8")
        errors = validate_file(p, require_non_empty=True)
        assert errors

    def test_single_entry_satisfies_non_empty(self, tmp_path: Path) -> None:
        log = _write_log(tmp_path, _entry())
        # Disable semantics here — repo_root is tmp_path, not the
        # mart-forge tree, so the catalog is empty. We only exercise
        # the non-empty gate.
        errors = validate_file(log, require_non_empty=True)
        assert errors == []

    def test_default_still_permissive_for_first_commit(self, tmp_path: Path) -> None:
        # On the bootstrap branch the flag is off; absence remains OK.
        p = tmp_path / "log.jsonl"
        assert validate_file(p) == []


class TestSemanticVerification:
    """Reviewer finding #3: a fabricated entry with reconstructed=false
    used to slide through because the validator never checked
    skill_name, artifact paths, or timestamp sanity.

    The adversarial probe at the end is the critical case.
    """

    def _make_repo_with_skill(self, tmp_path: Path, skill_name: str) -> Path:
        skill_dir = tmp_path / "skills" / "lifecycle" / skill_name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: stub\n---\n",
            encoding="utf-8",
        )
        # plausible artifact path
        (tmp_path / "README.md").write_text("# test\n", encoding="utf-8")
        return tmp_path

    def test_real_skill_with_path_artifacts_passes(self, tmp_path: Path) -> None:
        repo = self._make_repo_with_skill(tmp_path, "mart-brd")
        log = _write_log(
            tmp_path,
            _entry(
                skill_name="mart-brd",
                input_artifact="README.md",
                output_artifact="README.md",
            ),
        )
        errors = validate_file(log, check_semantics=True, repo_root=repo)
        assert errors == [], f"unexpected errors: {errors}"

    def test_unknown_skill_name_rejected(self, tmp_path: Path) -> None:
        repo = self._make_repo_with_skill(tmp_path, "mart-brd")
        log = _write_log(
            tmp_path,
            _entry(
                skill_name="totally-not-a-skill",
                input_artifact="README.md",
                output_artifact="README.md",
            ),
        )
        errors = validate_file(log, check_semantics=True, repo_root=repo)
        assert errors, "unknown skill_name must be rejected"
        assert any("not in the on-disk skill catalog" in err for err in errors)

    def test_nonexistent_input_artifact_rejected(self, tmp_path: Path) -> None:
        repo = self._make_repo_with_skill(tmp_path, "mart-brd")
        log = _write_log(
            tmp_path,
            _entry(
                skill_name="mart-brd",
                input_artifact="nonexistent/path/to/file.md",
                output_artifact="README.md",
            ),
        )
        errors = validate_file(log, check_semantics=True, repo_root=repo)
        assert errors
        assert any("input_artifact" in err and "does not" in err for err in errors)

    def test_nonexistent_output_artifact_rejected(self, tmp_path: Path) -> None:
        repo = self._make_repo_with_skill(tmp_path, "mart-brd")
        log = _write_log(
            tmp_path,
            _entry(
                skill_name="mart-brd",
                input_artifact="README.md",
                output_artifact="fake-sha-1234567",
            ),
        )
        errors = validate_file(log, check_semantics=True, repo_root=repo)
        assert errors
        assert any("output_artifact" in err for err in errors)

    def test_future_timestamp_rejected(self, tmp_path: Path) -> None:
        repo = self._make_repo_with_skill(tmp_path, "mart-brd")
        log = _write_log(
            tmp_path,
            _entry(
                skill_name="mart-brd",
                timestamp="2099-01-01T00:00:00Z",
                input_artifact="README.md",
                output_artifact="README.md",
            ),
        )
        errors = validate_file(log, check_semantics=True, repo_root=repo)
        assert errors
        assert any("future" in err for err in errors)

    def test_malformed_timestamp_rejected(self, tmp_path: Path) -> None:
        repo = self._make_repo_with_skill(tmp_path, "mart-brd")
        log = _write_log(
            tmp_path,
            _entry(
                skill_name="mart-brd",
                timestamp="not-a-timestamp",
                input_artifact="README.md",
                output_artifact="README.md",
            ),
        )
        errors = validate_file(log, check_semantics=True, repo_root=repo)
        assert errors
        assert any("ISO-8601" in err for err in errors)

    def test_adversarial_fabricated_entry_rejected(self, tmp_path: Path) -> None:
        """The reviewer's exact bypass case: reconstructed=false, fake
        skill_name, nonexistent artifacts. Before #3 this passed.
        """
        repo = self._make_repo_with_skill(tmp_path, "mart-brd")
        log = _write_log(
            tmp_path,
            _entry(
                skill_name="totally-not-a-skill",
                input_artifact="path/that/does/not/exist.md",
                output_artifact="path/that/does/not/exist.md",
                reconstructed=False,
            ),
        )
        errors = validate_file(log, check_semantics=True, repo_root=repo)
        assert errors, (
            "finding #3 regression: fabricated entry with reconstructed=false slipped through"
        )
        # All three semantic checks should fire on a fully-faked entry.
        text = " ".join(errors)
        assert "skill_name" in text
        assert "input_artifact" in text or "output_artifact" in text
