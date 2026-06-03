"""Tests for scripts.run_all_lints.

Covers the umbrella linter runner: step construction, selective execution
with --only, --continue-on-error behaviour, and normal fail-fast.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.run_all_lints import Step, main, steps


class TestSteps:
    def test_steps_returns_non_empty_list(self) -> None:
        result = steps(Path("/fake/root"))
        assert len(result) > 0
        assert all(isinstance(s, Step) for s in result)

    def test_all_steps_have_name_and_cmd(self) -> None:
        for s in steps(Path("/fake/root")):
            assert s.name
            assert len(s.cmd) >= 1

    def test_known_step_names_present(self) -> None:
        names = {s.name for s in steps(Path("/fake"))}
        expected = {
            "validate_marketplace",
            "sync_local_skills_check",
            "confidentiality_scan",
            "lint_brd_template",
            "lint_tdd_template",
            "lint_layer_direction",
            "validate_dogfood",
            "lint_signed_brd_audit",
            "lint_signed_tdd_audit",
            "lint_docs_freshness",
        }
        assert expected == names

    def test_repo_root_appears_in_relevant_steps(self) -> None:
        root = Path("/my/repo")
        for s in steps(root):
            if s.name in {"validate_marketplace", "sync_local_skills_check", "validate_dogfood"}:
                assert str(root) in s.cmd, f"{s.name} should embed repo_root"


class TestMainAllPass:
    """All subprocess.run calls return rc=0."""

    @patch("scripts.run_all_lints.subprocess.run")
    def test_all_pass_returns_zero(self, mock_run) -> None:
        mock_run.return_value.returncode = 0
        assert main([]) == 0

    @patch("scripts.run_all_lints.subprocess.run")
    def test_all_pass_runs_all_steps(self, mock_run) -> None:
        mock_run.return_value.returncode = 0
        main([])
        assert mock_run.call_count == len(steps(Path.cwd().resolve()))


class TestMainFailFast:
    """Default behaviour: stop at the first failure."""

    @patch("scripts.run_all_lints.subprocess.run")
    def test_first_failure_returns_one(self, mock_run) -> None:
        mock_run.return_value.returncode = 1
        assert main([]) == 1

    @patch("scripts.run_all_lints.subprocess.run")
    def test_first_failure_stops_early(self, mock_run) -> None:
        mock_run.return_value.returncode = 1
        main([])
        assert mock_run.call_count == 1


class TestMainContinueOnError:
    @patch("scripts.run_all_lints.subprocess.run")
    def test_continue_runs_all_steps_despite_failure(self, mock_run) -> None:
        mock_run.return_value.returncode = 1
        result = main(["--continue-on-error"])
        assert result == 1
        assert mock_run.call_count == len(steps(Path.cwd().resolve()))


class TestMainOnly:
    @patch("scripts.run_all_lints.subprocess.run")
    def test_only_runs_selected_steps(self, mock_run) -> None:
        mock_run.return_value.returncode = 0
        main(["--only", "confidentiality_scan"])
        assert mock_run.call_count == 1

    @patch("scripts.run_all_lints.subprocess.run")
    def test_only_multiple(self, mock_run) -> None:
        mock_run.return_value.returncode = 0
        main(["--only", "confidentiality_scan", "--only", "lint_brd_template"])
        assert mock_run.call_count == 2

    @patch("scripts.run_all_lints.subprocess.run")
    def test_only_nonexistent_runs_nothing(self, mock_run) -> None:
        mock_run.return_value.returncode = 0
        result = main(["--only", "no_such_step"])
        assert result == 0
        assert mock_run.call_count == 0
