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
