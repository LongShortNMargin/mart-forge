#!/usr/bin/env python3
"""Dogfood log validator for mart-forge CI.

For each example directory under ``examples/``, this script:

1. Checks that ``dogfood-log.jsonl`` exists.
2. Validates every line is valid JSON matching the expected schema:
   ``{timestamp, skill_name, input_artifact, output_artifact, checkpoint}``
3. Verifies that every non-log artifact file in the example directory has a
   corresponding entry in the log (either as ``input_artifact`` or
   ``output_artifact``).

Exit code 1 on any failure, 0 if all examples pass.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Set

LOG_FILENAME = "dogfood-log.jsonl"

REQUIRED_FIELDS = {"timestamp", "skill_name", "input_artifact", "output_artifact", "checkpoint"}

# Files that are expected but should not appear in artifact references
IGNORED_FILENAMES = {LOG_FILENAME, ".gitkeep", ".gitignore", "README.md"}


def validate_log_line(line: str, line_no: int, filepath: Path) -> List[str]:
    """Validate a single JSONL line. Return list of error messages."""
    errors: List[str] = []
    try:
        entry = json.loads(line)
    except json.JSONDecodeError as exc:
        errors.append(f"{filepath}:{line_no}: invalid JSON -- {exc}")
        return errors

    if not isinstance(entry, dict):
        errors.append(f"{filepath}:{line_no}: expected JSON object, got {type(entry).__name__}")
        return errors

    missing = REQUIRED_FIELDS - set(entry.keys())
    if missing:
        errors.append(f"{filepath}:{line_no}: missing required fields: {sorted(missing)}")

    return errors


def collect_referenced_artifacts(log_path: Path) -> Set[str]:
    """Read the log and return the set of all artifact filenames referenced."""
    artifacts: Set[str] = set()
    try:
        text = log_path.read_text(encoding="utf-8")
    except OSError:
        return artifacts

    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        for key in ("input_artifact", "output_artifact"):
            val = entry.get(key)
            if val:
                # Store just the basename so we can compare against dir listing
                artifacts.add(Path(val).name)
    return artifacts


def validate_example(example_dir: Path) -> List[str]:
    """Validate a single example directory. Return list of error strings."""
    errors: List[str] = []
    log_path = example_dir / LOG_FILENAME

    # 1. Log must exist
    if not log_path.exists():
        errors.append(f"{example_dir}: missing {LOG_FILENAME}")
        return errors

    # 2. Validate every line
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    if not lines:
        errors.append(f"{log_path}: file is empty")
        return errors

    for line_no, raw_line in enumerate(lines, start=1):
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        errors.extend(validate_log_line(raw_line, line_no, log_path))

    # 3. Every artifact file should have a log entry
    referenced = collect_referenced_artifacts(log_path)

    for item in sorted(example_dir.iterdir()):
        if not item.is_file():
            continue
        if item.name in IGNORED_FILENAMES:
            continue
        if item.name not in referenced:
            errors.append(
                f"{example_dir}: artifact file {item.name!r} has no entry in {LOG_FILENAME}"
            )

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate dogfood logs for every example directory."
    )
    parser.add_argument(
        "--examples-dir",
        default="examples",
        help="Root examples directory (default: examples).",
    )
    args = parser.parse_args()

    examples_root = Path(args.examples_dir)
    if not examples_root.is_dir():
        print(f"Examples directory not found: {examples_root}")
        # Not a failure -- repo may not have examples yet
        print("No examples to validate. Pass.")
        sys.exit(0)

    subdirs = sorted(
        d for d in examples_root.iterdir() if d.is_dir() and not d.name.startswith(".")
    )

    if not subdirs:
        print("No example subdirectories found. Pass.")
        sys.exit(0)

    all_errors: List[str] = []
    for subdir in subdirs:
        errors = validate_example(subdir)
        all_errors.extend(errors)

    if all_errors:
        print(f"DOGFOOD VALIDATION FAILED -- {len(all_errors)} error(s):\n")
        for err in all_errors:
            print(f"  {err}")
        print()
        sys.exit(1)
    else:
        print(f"Dogfood validation passed -- {len(subdirs)} example(s) checked.")
        sys.exit(0)


if __name__ == "__main__":
    main()
