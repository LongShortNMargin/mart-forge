#!/usr/bin/env python3
"""Dogfood log validator for mart-forge CI.

Enforces the schema of `.skill-invocations.jsonl` and rejects any entry
that carries ``"reconstructed": true`` — the specific bypass shape from
the prior failed iteration that fabricated invocations to pass CI.

Exit code 1 on any failure, 0 if clean.

Usage:
    validate_dogfood.py [path-to-jsonl]
    (default: .skill-invocations.jsonl in cwd)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

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


def validate_line(line: str, line_no: int, filepath: Path) -> List[str]:
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

    return errors


def validate_file(filepath: Path) -> List[str]:
    """Validate every line in the file."""
    if not filepath.exists():
        # An absent file is acceptable; it means no skills have run yet.
        return []

    text = filepath.read_text(encoding="utf-8")
    if not text.strip():
        return []

    errors: List[str] = []
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        errors.extend(validate_line(raw_line, line_no, filepath))
    return errors


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the dogfood log; reject reconstructed=true entries."
    )
    parser.add_argument(
        "filepath",
        nargs="?",
        default=".skill-invocations.jsonl",
        help="Path to the JSONL log (default: .skill-invocations.jsonl).",
    )
    args = parser.parse_args(argv)

    filepath = Path(args.filepath)
    errors = validate_file(filepath)

    if errors:
        print(f"DOGFOOD VALIDATION FAILED — {len(errors)} error(s) in {filepath}:\n")
        for err in errors:
            print(f"  {err}")
        print()
        return 1

    if not filepath.exists() or not filepath.read_text(encoding="utf-8").strip():
        print(f"Dogfood validation passed — {filepath} is absent or empty (acceptable).")
    else:
        n_lines = sum(1 for line in filepath.read_text(encoding="utf-8").splitlines() if line.strip())
        print(f"Dogfood validation passed — {n_lines} entries in {filepath}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
