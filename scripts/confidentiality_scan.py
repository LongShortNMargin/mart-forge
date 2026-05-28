#!/usr/bin/env python3
"""Confidentiality scanner for mart-forge CI.

Scans repository files for banned patterns that would leak private paths,
internal project names, user identifiers, or operator data into the
public open-source repo.

Exit code 1 if any violation is found; 0 if clean.

Each violation prints:
  <file>:<line>:<col>  [<category>]  matched: <text>
  -> remediation: <remediation hint>
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Iterable, List, NamedTuple, Tuple

SCAN_EXTENSIONS = {
    ".py", ".md", ".yml", ".yaml", ".json", ".sql", ".csv", ".txt",
    ".toml", ".sh", ".jsonl", ".cfg", ".ini",
}

# Files the scanner excludes from its own scan. The scanner file itself is
# excluded because it must define the patterns it is rejecting. Other
# entries must each justify their exclusion in a comment beside them.
EXCLUDED_FILENAMES = {
    "confidentiality_scan.py",        # this file defines the patterns
    "test_confidentiality.py",        # tests assert against the patterns
}


class BannedPattern(NamedTuple):
    category: str
    pattern: re.Pattern[str]
    remediation: str


# Each category groups related strings. Adding a new banned string is a
# two-step process: add the pattern here, and add a positive test in
# tests/test_confidentiality.py asserting the scanner catches it.
BANNED_PATTERNS: List[BannedPattern] = [
    # --- private paths ----------------------------------------------------
    BannedPattern(
        "private_path",
        re.compile(r"/Users/\w+"),
        "Replace with '~' or '<home>' in examples.",
    ),
    BannedPattern(
        "private_path",
        re.compile(r"Google\s*Drive", re.IGNORECASE),
        "Refer to cloud-drive paths generically as '<cloud-drive>'.",
    ),
    BannedPattern(
        "private_path",
        re.compile(r"C:\\Users\\\w+"),
        "Replace Windows user paths with '<home>'.",
    ),

    # --- internal project identifiers -------------------------------------
    BannedPattern(
        "internal_project",
        re.compile(r"\bShopee\b"),
        "Do not name third-party companies; use a generic placeholder.",
    ),
    BannedPattern(
        "internal_project",
        re.compile(r"\bChatbot\s*Mart\b"),
        "Internal mart name. Use a generic example like 'orders-mart'.",
    ),
    BannedPattern(
        "internal_project",
        re.compile(r"\bDragonRook\b"),
        "Private mono-repo name. Do not reference in public artifacts.",
    ),
    BannedPattern(
        "internal_project",
        re.compile(r"\bEmberlock(?:_\w+)?\b"),
        "Private archive name. Do not reference.",
    ),

    # --- internal agent / persona names -----------------------------------
    BannedPattern(
        "internal_persona",
        re.compile(r"\bArgent\b"),
        "Private agent persona. Use generic 'reviewer' or 'maintainer'.",
    ),
    BannedPattern(
        "internal_persona",
        re.compile(r"\bSilver\s+Chainbind\b"),
        "Private persona name. Do not reference.",
    ),
    BannedPattern(
        "internal_persona",
        re.compile(r"\bGhost\s+Operator\b"),
        "Private operator alias. Do not reference.",
    ),

    # --- internal program names -------------------------------------------
    BannedPattern(
        "internal_program",
        re.compile(r"\bDROOK\b"),
        "Private orchestration program. Do not reference.",
    ),
    BannedPattern(
        "internal_program",
        re.compile(r"\bFHAG\b"),
        "Private program. Do not reference.",
    ),
    BannedPattern(
        "internal_program",
        re.compile(r"\bSCAS\b"),
        "Private program. Do not reference.",
    ),
    BannedPattern(
        "internal_program",
        re.compile(r"\bDaPES\b"),
        "Private program. Do not reference.",
    ),
    BannedPattern(
        "internal_program",
        re.compile(r"\bFLQP\b"),
        "Private protocol. Do not reference.",
    ),
    BannedPattern(
        "internal_program",
        re.compile(r"\bCelestial\s+Ordinance\b"),
        "Private protocol name. Do not reference.",
    ),
    BannedPattern(
        "internal_program",
        re.compile(r"\bBurry\s+catalyst\b", re.IGNORECASE),
        "Private framing term. Do not reference.",
    ),

    # --- user identifiers -------------------------------------------------
    BannedPattern(
        "user_id",
        re.compile(r"vuduclong0309"),
        "Personal Google email handle. Do not commit.",
    ),
    BannedPattern(
        "user_id",
        re.compile(r"longshortnmargin", re.IGNORECASE),
        "Operator's public org handle is banned in examples per CLAUDE.md. Use 'your-org' as a placeholder.",
    ),

    # --- operator data ----------------------------------------------------
    BannedPattern(
        "operator_data",
        re.compile(r"\bposition[_\s]?size\b", re.IGNORECASE),
        "Trading-position data must not appear. Replace with generic 'measure'.",
    ),
    BannedPattern(
        "operator_data",
        re.compile(r"\bcost[_\s]?basis\b", re.IGNORECASE),
        "Trading-position data must not appear.",
    ),
    BannedPattern(
        "operator_data",
        re.compile(r"\baccount[_\s]?id(?:entifier)?\b", re.IGNORECASE),
        "Account identifier. Use generic 'entity_id'.",
    ),

    # --- secrets ----------------------------------------------------------
    BannedPattern(
        "secret",
        re.compile(r"AKIA[0-9A-Z]{16}"),
        "AWS access key. Rotate immediately if committed.",
    ),
    BannedPattern(
        "secret",
        re.compile(r"AIza[0-9A-Za-z_-]{35}"),
        "Google API key. Rotate immediately if committed.",
    ),
    BannedPattern(
        "secret",
        re.compile(r"ghp_[0-9A-Za-z]{36,}"),
        "GitHub personal access token. Rotate immediately if committed.",
    ),
]


class Violation(NamedTuple):
    filepath: str
    line_number: int
    column: int
    category: str
    matched: str
    remediation: str


def is_scannable(path: Path) -> bool:
    return path.suffix.lower() in SCAN_EXTENSIONS


def scan_file(filepath: Path) -> List[Violation]:
    violations: List[Violation] = []
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return violations

    for line_no, line in enumerate(text.splitlines(), start=1):
        for bp in BANNED_PATTERNS:
            match = bp.pattern.search(line)
            if match:
                violations.append(
                    Violation(
                        filepath=str(filepath),
                        line_number=line_no,
                        column=match.start() + 1,
                        category=bp.category,
                        matched=match.group(),
                        remediation=bp.remediation,
                    )
                )
    return violations


def iter_files(root: Path) -> Iterable[Path]:
    for dirpath, _dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)
        if any(part.startswith(".") for part in rel_dir.parts if part != "."):
            # Skip hidden directories like .git, but allow root.
            continue
        for fname in filenames:
            filepath = Path(dirpath) / fname
            if filepath.name in EXCLUDED_FILENAMES:
                continue
            if not is_scannable(filepath):
                continue
            yield filepath


def scan_directory(root: str) -> List[Violation]:
    all_violations: List[Violation] = []
    root_path = Path(root).resolve()
    for filepath in iter_files(root_path):
        all_violations.extend(scan_file(filepath))
    return all_violations


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scan repository for confidential / private references."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Root directory to scan (default: current directory).",
    )
    args = parser.parse_args(argv)

    violations = scan_directory(args.directory)

    if violations:
        print(f"CONFIDENTIALITY SCAN FAILED — {len(violations)} violation(s) found:\n")
        for v in violations:
            print(f"  {v.filepath}:{v.line_number}:{v.column}  [{v.category}]  matched: {v.matched!r}")
            print(f"    -> remediation: {v.remediation}")
        print()
        return 1

    print("Confidentiality scan passed — no violations found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
