#!/usr/bin/env python3
"""Docs freshness linter.

Catches two failure modes:
1. Cross-references to files that no longer exist (dangling links).
2. References to stale spec filenames (SPEC_V2.md, SPEC_FEEDBACK.md,
   etc.) that violate the single-living-spec rule (DESIGN.md §3).

Detection:
- Walks every markdown file under the given root.
- Extracts inline markdown links [text](path) where path is a relative
  file path (not a URL).
- For each link, checks the file exists.
- Also greps every markdown file for banned spec-filename patterns.

Exit code 1 on any failure.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List

# Markdown link: [text](path)
LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

# Banned spec-filename patterns (per DESIGN.md §3).
BANNED_FILENAMES = [
    re.compile(r"\bSPEC_V\d+\.md\b"),
    re.compile(r"\bSPEC_FEEDBACK\.md\b"),
    re.compile(r"\bSPEC_ITERATION_\d+\.md\b"),
    re.compile(r"\bSPEC_DRAFT\.md\b"),
]


def is_external_link(target: str) -> bool:
    return (
        target.startswith("http://")
        or target.startswith("https://")
        or target.startswith("mailto:")
        or target.startswith("#")
    )


def lint(root: Path) -> List[str]:
    errors: List[str] = []
    if not root.exists():
        return [f"{root}: directory not found"]

    md_files = list(root.rglob("*.md"))

    for md in md_files:
        text = md.read_text(encoding="utf-8", errors="replace")

        # Check for banned spec filenames.
        for line_no, line in enumerate(text.splitlines(), start=1):
            for pattern in BANNED_FILENAMES:
                m = pattern.search(line)
                if m:
                    errors.append(
                        f"{md}:{line_no}: stale spec filename reference {m.group()!r}\n"
                        f"    -> remediation: per DESIGN.md §3, there is only one SPEC.md. "
                        f"Remove the versioned filename and point to SPEC.md."
                    )

        # Check inline links resolve.
        for line_no, line in enumerate(text.splitlines(), start=1):
            for m in LINK_PATTERN.finditer(line):
                target = m.group(2).strip()
                if is_external_link(target):
                    continue
                # Strip any anchor fragment.
                target_no_anchor = target.split("#")[0]
                if not target_no_anchor:
                    continue
                # Resolve relative to the markdown file's directory.
                resolved = (md.parent / target_no_anchor).resolve()
                if not resolved.exists():
                    errors.append(
                        f"{md}:{line_no}: dangling link to {target!r}\n"
                        f"    -> remediation: update or remove the link. "
                        f"If the target was renamed, point to the new path."
                    )
    return errors


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check markdown freshness: no dangling links, no stale spec filenames."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Root directory to walk (default: current directory).",
    )
    args = parser.parse_args(argv)

    errors = lint(Path(args.directory))
    if errors:
        print(f"DOCS FRESHNESS LINT FAILED — {len(errors)} issue(s):\n")
        for err in errors:
            print(f"  {err}")
        return 1
    print(f"Docs freshness lint passed: {args.directory}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
