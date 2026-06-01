#!/usr/bin/env python3
"""TDD signing-gate linter.

Mirror of `lint_signed_brd.py` for Technical Design Documents. The
"no scaffold without signed TDD" rule (CLAUDE.md non-negotiable #1) is
enforced here.

A signed TDD has:
- A `## Signature` section.
- At least one row in the signature table where `Name`, `Date`, and
  `Signature` cells are non-empty and non-placeholder.

Exit code 1 if any input TDD lacks a real signature.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, List

# Reuse the BRD signing primitives; the signature shape is identical.
from scripts.lint_signed_brd import (
    _is_template,
    is_signed,
    lint_paths as _lint_paths_for_doctype,
)


def discover_tdds(root: Path) -> List[Path]:
    candidates: List[Path] = []
    for pattern in ("*tech-design*.md", "*tdd*.md", "*TDD*.md"):
        candidates.extend(root.rglob(pattern))
    return [p for p in candidates if not _is_template(p)]


def lint_paths(paths: Iterable[Path]) -> List[str]:
    errors: List[str] = []
    for p in paths:
        if not p.exists():
            errors.append(f"{p}: file not found")
            continue
        if _is_template(p):
            continue
        if not is_signed(p):
            errors.append(
                f"{p}: TDD has no completed Signature block.\n"
                f"    -> remediation: complete the §Signature table "
                f"(Name + Date + Signature) before invoking /mart-bootstrap. "
                f"The 'no scaffold without signed TDD' gate is enforced by CI."
            )
    return errors


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reject any unsigned TDD; auto-discovers TDDs under a directory."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="TDD files or directories to check. Default: ./docs/marts/",
    )
    args = parser.parse_args(argv)

    targets: List[Path] = []
    if not args.paths:
        default_root = Path("docs/marts")
        if default_root.exists():
            targets = discover_tdds(default_root)
        else:
            print(
                "No TDD paths given and ./docs/marts/ does not exist — nothing to check."
            )
            return 0
    else:
        for raw in args.paths:
            p = Path(raw)
            if p.is_dir():
                targets.extend(discover_tdds(p))
            else:
                targets.append(p)

    if not targets:
        print("Signed-TDD lint: no TDDs found (nothing to enforce).")
        return 0

    errors = lint_paths(targets)
    if errors:
        print(
            f"SIGNED-TDD LINT FAILED — {len(errors)} unsigned TDD(s) found:\n"
        )
        for err in errors:
            print(f"  {err}")
        return 1
    print(f"Signed-TDD lint passed — {len(targets)} TDD(s) signed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
