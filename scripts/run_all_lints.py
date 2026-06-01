#!/usr/bin/env python3
"""Run every mart-forge linter in sequence.

This is the umbrella entrypoint referenced by README and CI. It exits 1
on the first failure (so CI fails loudly) unless ``--continue-on-error``
is passed (for local triage).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class Step:
    name: str
    cmd: List[str]


def steps(repo_root: Path) -> List[Step]:
    return [
        Step(
            "validate_marketplace",
            [
                sys.executable,
                "scripts/validate_marketplace.py",
                ".claude-plugin/marketplace.json",
                "--repo-root",
                str(repo_root),
            ],
        ),
        Step(
            "confidentiality_scan",
            [sys.executable, "scripts/confidentiality_scan.py", "."],
        ),
        Step(
            "lint_brd_template",
            [
                sys.executable,
                "scripts/lint_brd.py",
                "templates/business-requirements.template.md",
            ],
        ),
        Step(
            "lint_tdd_template",
            [
                sys.executable,
                "scripts/lint_tdd.py",
                "templates/tech-design-doc.template.md",
            ],
        ),
        Step(
            "lint_layer_direction",
            [sys.executable, "scripts/lint_layer_direction.py", "templates/models/"],
        ),
        Step(
            "validate_dogfood",
            [
                sys.executable,
                "scripts/validate_dogfood.py",
                ".skill-invocations.jsonl",
                "--require-non-empty",
                "--check-semantics",
                "--repo-root",
                str(repo_root),
            ],
        ),
        Step(
            "lint_signed_brd_audit",
            [sys.executable, "scripts/lint_signed_brd.py"],
        ),
        Step(
            "lint_signed_tdd_audit",
            [sys.executable, "scripts/lint_signed_tdd.py"],
        ),
        Step(
            "lint_docs_freshness",
            [sys.executable, "scripts/lint_docs_freshness.py", "."],
        ),
    ]


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run every mart-forge linter.")
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Run every linter even when one fails (for local triage).",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Run only the named step(s); may be passed multiple times.",
    )
    args = parser.parse_args(argv)

    repo_root = Path.cwd().resolve()
    selected = steps(repo_root)
    if args.only:
        selected = [s for s in selected if s.name in set(args.only)]

    failures: List[str] = []
    for step in selected:
        print(f"\n=== {step.name} ===")
        result = subprocess.run(step.cmd, cwd=repo_root)
        if result.returncode != 0:
            failures.append(step.name)
            if not args.continue_on_error:
                print(f"\nFAILED at step: {step.name}")
                return 1

    if failures:
        print(f"\n{len(failures)} step(s) failed: {failures}")
        return 1
    print("\nAll linters passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
