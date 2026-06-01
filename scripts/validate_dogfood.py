#!/usr/bin/env python3
"""Dogfood log validator for mart-forge CI.

Enforces the schema of `.skill-invocations.jsonl` and rejects entries
that look fabricated. Closes reviewer findings #2 and #3 from EMB-321:

#2 — A missing or whitespace-only log used to pass. With
``--require-non-empty`` (default on in CI for any branch other than
the initial bootstrap) the absence of entries is treated as failure.

#3 — Semantic verification: ``skill_name`` is checked against the
on-disk skill catalog (``./skills/{group}/{name}/SKILL.md``), the
``input_artifact`` / ``output_artifact`` fields are checked against
the working tree or git, and obvious-future timestamps are rejected.

Exit code 1 on any failure, 0 if clean.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Set

REQUIRED_FIELDS = {
    "timestamp",
    "skill_name",
    "input_artifact",
    "output_artifact",
    "checkpoint",
    "reconstructed",
}

# Reject `"reconstructed": true` everywhere. The field exists in the
# schema for forward compatibility, but the only acceptable value in a
# real log is `false`.
RECONSTRUCTED_REJECT_VALUE = True

# Allowed clock skew when comparing entry timestamps against "now". An
# entry more than this far into the future is rejected as fabricated.
FUTURE_SKEW_TOLERANCE = _dt.timedelta(minutes=5)

# Git SHA shape used for output_artifact references. Tags, branches and
# arbitrary refs are also accepted via `git rev-parse --verify`.
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")


def _now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _parse_iso(ts: str) -> Optional[_dt.datetime]:
    try:
        # Accept both 'Z' and '+00:00' shapes.
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        dt = _dt.datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_dt.timezone.utc)
        return dt
    except ValueError:
        return None


def discover_skill_catalog(repo_root: Path) -> Set[str]:
    """Return the set of valid skill names by walking `./skills/`.

    A skill is a directory `skills/<group>/<name>/` that contains
    `SKILL.md`. The skill's name is `<name>`. This mirrors the manifest
    in `.claude-plugin/marketplace.json`.
    """
    catalog: Set[str] = set()
    skills_root = repo_root / "skills"
    if not skills_root.exists():
        return catalog
    for group_dir in skills_root.iterdir():
        if not group_dir.is_dir():
            continue
        for skill_dir in group_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                catalog.add(skill_dir.name)
    return catalog


def _git_ref_exists(repo_root: Path, ref: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{}}"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def _artifact_resolves(
    artifact: str, repo_root: Path, *, allow_git: bool = True
) -> bool:
    """An artifact is valid if it points at an existing path in the work
    tree, OR (when `allow_git`) at a git-resolvable ref/SHA, OR at a
    branch-like ref that is plausibly tracked in git history.
    """
    if not artifact or not isinstance(artifact, str):
        return False
    # Path-resolution: relative path inside the repo.
    p = repo_root / artifact
    if p.exists():
        return True
    if not allow_git:
        return False
    # Git-resolution: SHA or named ref. Skip the network — local refs only.
    if SHA_RE.match(artifact) and _git_ref_exists(repo_root, artifact):
        return True
    # Branch / tag with slashes (e.g. "phase-zero/agent-bootstrap").
    if "/" in artifact and _git_ref_exists(repo_root, artifact):
        return True
    return False


def _is_git_sha(artifact: str) -> bool:
    return isinstance(artifact, str) and bool(SHA_RE.match(artifact))


def _commit_touches_path(repo_root: Path, sha: str, path: str) -> Optional[bool]:
    """Return True if the commit `sha` changed `path` relative to its
    parent, False if the diff is empty, and None if the answer cannot
    be determined (no parent / git unavailable).

    Used by the M1 hardening: a dogfood entry where `output_artifact` is
    a commit SHA must show that the commit actually touched
    `input_artifact`. Without this check the entry only proves the SHA
    exists, not that the recorded skill produced any change.
    """
    try:
        parent = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"{sha}^"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if parent.returncode != 0:
            # Root commit (no parent) — accept; there is no prior state
            # to diff against, and rejecting the bootstrap commit would
            # make the gate unbootstrappable.
            return None
        diff = subprocess.run(
            ["git", "diff", "--name-only", f"{sha}^..{sha}", "--", path],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if diff.returncode != 0:
            return None
        return bool(diff.stdout.strip())
    except (subprocess.SubprocessError, FileNotFoundError):
        return None


def validate_line(
    line: str,
    line_no: int,
    filepath: Path,
    *,
    skill_catalog: Optional[Set[str]] = None,
    repo_root: Optional[Path] = None,
    check_semantics: bool = False,
) -> List[str]:
    """Return a list of error messages for a single JSONL line."""
    errors: List[str] = []
    try:
        entry = json.loads(line)
    except json.JSONDecodeError as exc:
        errors.append(
            f"{filepath}:{line_no}: invalid JSON — {exc}\n"
            f"    -> remediation: every line of the dogfood log must be a single JSON object."
        )
        return errors

    if not isinstance(entry, dict):
        errors.append(
            f"{filepath}:{line_no}: expected JSON object, got {type(entry).__name__}\n"
            f"    -> remediation: rewrite the line as a JSON object with the required fields."
        )
        return errors

    missing = REQUIRED_FIELDS - set(entry.keys())
    if missing:
        errors.append(
            f"{filepath}:{line_no}: missing required fields: {sorted(missing)}\n"
            f"    -> remediation: add the missing fields; required schema is "
            f"{{timestamp, skill_name, input_artifact, output_artifact, checkpoint, reconstructed}}."
        )

    if entry.get("reconstructed", None) is RECONSTRUCTED_REJECT_VALUE:
        errors.append(
            f"{filepath}:{line_no}: entry carries 'reconstructed': true, which is forbidden.\n"
            f"    -> remediation: a dogfood log entry must record a REAL skill invocation. "
            f"If the skill was not actually invoked, document the gap in "
            f"docs/exec-plans/active/*.md and delete this fabricated line."
        )

    if "reconstructed" in entry and not isinstance(entry["reconstructed"], bool):
        errors.append(
            f"{filepath}:{line_no}: 'reconstructed' must be a boolean (got {type(entry['reconstructed']).__name__}).\n"
            f"    -> remediation: set 'reconstructed': false for genuine invocations."
        )

    # ----- Semantic verification (reviewer finding #3) -------------------
    if check_semantics and repo_root is not None:
        # 1. skill_name must exist in the on-disk catalog. If the catalog
        #    is empty (e.g. running outside a checkout) we skip the
        #    check rather than fail spuriously.
        sname = entry.get("skill_name")
        if isinstance(sname, str) and skill_catalog:
            if sname not in skill_catalog:
                errors.append(
                    f"{filepath}:{line_no}: 'skill_name' {sname!r} is not in the "
                    f"on-disk skill catalog ({len(skill_catalog)} known skills under "
                    f"./skills/).\n"
                    f"    -> remediation: a dogfood entry must reference a real skill. "
                    f"Either invoke an existing skill or add the new skill to "
                    f"./skills/{{lifecycle,workflow,duckdb,quality}}/<name>/ first."
                )

        # 2. Future-timestamp guard.
        ts = entry.get("timestamp")
        if isinstance(ts, str):
            dt = _parse_iso(ts)
            if dt is None:
                errors.append(
                    f"{filepath}:{line_no}: 'timestamp' {ts!r} is not ISO-8601.\n"
                    f"    -> remediation: use UTC ISO-8601 like '2026-06-02T12:00:00Z'."
                )
            elif dt > _now() + FUTURE_SKEW_TOLERANCE:
                errors.append(
                    f"{filepath}:{line_no}: 'timestamp' {ts!r} is in the future.\n"
                    f"    -> remediation: dogfood entries cannot be pre-dated; "
                    f"use the actual invocation time."
                )

        # 3. Artifact paths / refs must resolve. input_artifact is
        #    commonly a branch name, output_artifact is commonly a SHA;
        #    both shapes are accepted.
        in_art = entry.get("input_artifact")
        if isinstance(in_art, str) and not _artifact_resolves(in_art, repo_root):
            errors.append(
                f"{filepath}:{line_no}: 'input_artifact' {in_art!r} does not "
                f"resolve as a path or git ref in the current repo.\n"
                f"    -> remediation: point input_artifact at a file path "
                f"under the repo, or at a real branch/tag/SHA."
            )
        out_art = entry.get("output_artifact")
        if isinstance(out_art, str) and not _artifact_resolves(out_art, repo_root):
            errors.append(
                f"{filepath}:{line_no}: 'output_artifact' {out_art!r} does not "
                f"resolve as a path or git ref in the current repo.\n"
                f"    -> remediation: point output_artifact at a real path or "
                f"git ref (SHA / branch / tag)."
            )

        # 4. M1: change-witness check. The reviewer's bypass was
        #    'real-skill + identical existing path as BOTH artifacts'
        #    — the entry was field-shape-valid but proved nothing.
        #    A real invocation must show evidence of change:
        #
        #    - input_artifact and output_artifact cannot be the same
        #      string (string equality is the lower bound: identical
        #      paths or identical SHAs both imply no change).
        #    - When output_artifact is a git SHA, the commit must
        #      touch input_artifact (or be a root commit, which has
        #      no prior state to diff against).
        if isinstance(in_art, str) and isinstance(out_art, str) and in_art == out_art:
            errors.append(
                f"{filepath}:{line_no}: 'input_artifact' and 'output_artifact' "
                f"are identical ({in_art!r}).\n"
                f"    -> remediation: a real skill invocation must show a "
                f"change between input and output. If the skill mutated a "
                f"file in place, set output_artifact to the commit SHA that "
                f"records the change; if the skill produced a new file, "
                f"point output_artifact at the new path."
            )

        if (
            isinstance(in_art, str)
            and isinstance(out_art, str)
            and _is_git_sha(out_art)
            and _git_ref_exists(repo_root, out_art)
        ):
            # input_artifact may be a path (most common) or a SHA. Only
            # check the diff when input_artifact looks like a path that
            # exists or once existed in the tree.
            input_is_path = (repo_root / in_art).exists() or "/" in in_art
            if input_is_path and not _is_git_sha(in_art):
                touched = _commit_touches_path(repo_root, out_art, in_art)
                if touched is False:
                    errors.append(
                        f"{filepath}:{line_no}: commit {out_art!r} does not "
                        f"touch 'input_artifact' {in_art!r}.\n"
                        f"    -> remediation: point output_artifact at the "
                        f"commit that actually changed input_artifact, or "
                        f"point input_artifact at the file the skill "
                        f"actually edited. An entry with no diff between "
                        f"input and output records no work."
                    )

    return errors


def validate_file(
    filepath: Path,
    *,
    require_non_empty: bool = False,
    check_semantics: bool = False,
    repo_root: Optional[Path] = None,
) -> List[str]:
    """Validate every line in the file.

    `require_non_empty=True` is the CI-default contract: a missing or
    whitespace-only log is a failure. The flag exists so the first-commit
    bootstrap path (when no skill has yet run) can pass with the default
    off.
    """
    if not filepath.exists():
        if require_non_empty:
            return [
                f"{filepath}: dogfood log is required to exist and contain >= 1 entry "
                f"(--require-non-empty).\n"
                f"    -> remediation: invoke at least one mart-forge skill and record "
                f"the invocation, or run with --require-non-empty disabled only on "
                f"the initial bootstrap branch."
            ]
        return []

    text = filepath.read_text(encoding="utf-8")
    if not text.strip():
        if require_non_empty:
            return [
                f"{filepath}: dogfood log is empty (--require-non-empty)."
            ]
        return []

    if repo_root is None and check_semantics:
        repo_root = filepath.parent.resolve()
    skill_catalog = (
        discover_skill_catalog(repo_root) if (check_semantics and repo_root) else set()
    )

    errors: List[str] = []
    entry_count = 0
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        entry_count += 1
        errors.extend(
            validate_line(
                raw_line,
                line_no,
                filepath,
                skill_catalog=skill_catalog,
                repo_root=repo_root,
                check_semantics=check_semantics,
            )
        )

    if require_non_empty and entry_count == 0:
        errors.append(
            f"{filepath}: dogfood log contains no entries (--require-non-empty)."
        )

    return errors


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the dogfood log; reject reconstructed=true entries, "
            "and (with --require-non-empty / --check-semantics) reject "
            "absent/empty logs and fabricated entries."
        )
    )
    parser.add_argument(
        "filepath",
        nargs="?",
        default=".skill-invocations.jsonl",
        help="Path to the JSONL log (default: .skill-invocations.jsonl).",
    )
    parser.add_argument(
        "--require-non-empty",
        action="store_true",
        help="Treat an absent or empty log as failure (CI default for "
             "non-bootstrap branches).",
    )
    parser.add_argument(
        "--check-semantics",
        action="store_true",
        help="Cross-check skill_name against ./skills/, verify "
             "input/output artifacts resolve, and reject future timestamps.",
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repo root for semantic resolution (default: directory containing the log).",
    )
    args = parser.parse_args(argv)

    filepath = Path(args.filepath)
    repo_root = Path(args.repo_root).resolve() if args.repo_root else None
    errors = validate_file(
        filepath,
        require_non_empty=args.require_non_empty,
        check_semantics=args.check_semantics,
        repo_root=repo_root,
    )

    if errors:
        print(f"DOGFOOD VALIDATION FAILED — {len(errors)} error(s) in {filepath}:\n")
        for err in errors:
            print(f"  {err}")
        print()
        return 1

    if not filepath.exists() or not filepath.read_text(encoding="utf-8").strip():
        print(
            f"Dogfood validation passed — {filepath} is absent or empty "
            f"(allowed because --require-non-empty was not set)."
        )
    else:
        n_lines = sum(
            1 for line in filepath.read_text(encoding="utf-8").splitlines() if line.strip()
        )
        print(f"Dogfood validation passed — {n_lines} entries in {filepath}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
