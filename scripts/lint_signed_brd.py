#!/usr/bin/env python3
"""BRD signing-gate linter.

Closes reviewer finding #6: the "no scaffold without signed TDD; no
TDD without signed BRD" rule used to be enforced only by SKILL.md
prose. This script makes the gate programmatic.

A signed BRD has:
- A `## Signature` section.
- At least one row in the signature table where `Name`, `Date`, and
  `Signature` cells are all non-empty and non-placeholder.

The script is path-agnostic: pass any number of BRD paths, or a
directory and it will pick up every ``*brd*.md`` / ``*business-requirements*.md``
file (excluding ``templates/``).

Exit code 1 if any input BRD lacks a real signature.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable, List

from scripts.shared import (
    is_placeholder_cell,
    is_template_path,
    parse_tables_in_body,
    report_lint_result,
    section_body,
)

SIGNATURE_HEADER_RE = re.compile(r"^##\s*Signature\b", re.MULTILINE)


def is_signed(filepath: Path) -> bool:
    text = filepath.read_text(encoding="utf-8")
    sig_body = section_body(text, "Signature")
    if not sig_body:
        return False

    tables = parse_tables_in_body(sig_body)
    for headers_raw, rows in tables:
        headers = [c.lower() for c in headers_raw]
        try:
            name_idx = headers.index("name")
            date_idx = headers.index("date")
            sig_idx = headers.index("signature")
        except ValueError:
            continue
        for row in rows:
            for idx in (name_idx, date_idx, sig_idx):
                if idx >= len(row):
                    break
            else:
                if (
                    not is_placeholder_cell(row[name_idx])
                    and not is_placeholder_cell(row[date_idx])
                    and not is_placeholder_cell(row[sig_idx])
                ):
                    return True
    return False


def discover_brds(root: Path) -> List[Path]:
    candidates: List[Path] = []
    for pattern in ("*business-requirements*.md", "*brd*.md", "*BRD*.md"):
        candidates.extend(root.rglob(pattern))
    return [p for p in candidates if not is_template_path(p)]


def lint_paths(paths: Iterable[Path]) -> List[str]:
    errors: List[str] = []
    for p in paths:
        if not p.exists():
            errors.append(f"{p}: file not found")
            continue
        if is_template_path(p):
            continue
        if not is_signed(p):
            errors.append(
                f"{p}: BRD has no completed Signature block.\n"
                f"    -> remediation: complete the §Signature table "
                f"(Name + Date + Signature) before invoking /mart-tdd. "
                f"The 'no TDD without signed BRD' gate is enforced by CI."
            )
    return errors


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reject any unsigned BRD; auto-discovers BRDs under a directory."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="BRD files or directories to check. Default: ./docs/marts/",
    )
    args = parser.parse_args(argv)

    targets: List[Path] = []
    if not args.paths:
        default_root = Path("docs/marts")
        if default_root.exists():
            targets = discover_brds(default_root)
        else:
            print(
                "No BRD paths given and ./docs/marts/ does not exist — nothing to check."
            )
            return 0
    else:
        for raw in args.paths:
            p = Path(raw)
            if p.is_dir():
                targets.extend(discover_brds(p))
            else:
                targets.append(p)

    if not targets:
        print("Signed-BRD lint: no BRDs found (nothing to enforce).")
        return 0

    errors = lint_paths(targets)
    return report_lint_result(
        "SIGNED-BRD LINT",
        errors,
        context=f"{len(targets)} BRD(s) signed",
    )


if __name__ == "__main__":
    sys.exit(main())
