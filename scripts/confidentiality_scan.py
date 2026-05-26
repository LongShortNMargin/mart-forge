#!/usr/bin/env python3
"""Confidentiality scanner for mart-forge CI.

Scans repository files for banned patterns that would leak private paths,
internal project names, user identifiers, or operator data into the
public open-source repo.

Exit code 1 if any violation is found, 0 if clean.
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# ---------------------------------------------------------------------------
# File extensions to scan
# ---------------------------------------------------------------------------
SCAN_EXTENSIONS = {
    ".py", ".md", ".yml", ".yaml", ".json", ".sql", ".csv", ".txt", ".toml",
}

# ---------------------------------------------------------------------------
# Banned patterns grouped by category
# ---------------------------------------------------------------------------
BANNED_PATTERNS: List[Tuple[str, re.Pattern]] = [
    # Private paths
    ("private_path", re.compile(r"/Users/\w+")),
    ("private_path", re.compile(r"Google\s*Drive")),
    ("private_path", re.compile(r"C:\\Users\\\w+")),
    # Internal project names
    ("internal_project", re.compile(r"\bShopee\b")),
    ("internal_project", re.compile(r"\bChatbot\s*Mart\b")),
    ("internal_project", re.compile(r"\bDragonRook\b")),
    ("internal_project", re.compile(r"\bEmberlock\b")),
    ("internal_project", re.compile(r"\bIBKR\b")),
    # User identifiers
    ("user_id", re.compile(r"vuduclong0309")),
    # Operator data
    ("operator_data", re.compile(r"position[_\s]?size", re.IGNORECASE)),
    ("operator_data", re.compile(r"cost[_\s]?basis", re.IGNORECASE)),
    ("operator_data", re.compile(r"account[_\s]?id(?:entifier)?", re.IGNORECASE)),
]

# ---------------------------------------------------------------------------
# Self-reference exclusion: skip this script to avoid false positives from
# the pattern definitions above.
# ---------------------------------------------------------------------------
EXCLUDED_FILENAMES = {"confidentiality_scan.py", "SPEC.md"}


def is_scannable(path: Path) -> bool:
    """Return True if the file extension is in the scan set."""
    return path.suffix.lower() in SCAN_EXTENSIONS


def scan_file(filepath: Path) -> List[Tuple[str, int, str, str]]:
    """Scan a single file and return a list of violations.

    Each violation is (filepath_str, line_number, category, matched_text).
    """
    violations: List[Tuple[str, int, str, str]] = []
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return violations

    for line_no, line in enumerate(text.splitlines(), start=1):
        for category, pattern in BANNED_PATTERNS:
            match = pattern.search(line)
            if match:
                violations.append(
                    (str(filepath), line_no, category, match.group())
                )
    return violations


def scan_directory(root: str) -> List[Tuple[str, int, str, str]]:
    """Walk *root* and scan every eligible file (excluding self)."""
    all_violations: List[Tuple[str, int, str, str]] = []
    root_path = Path(root).resolve()

    for dirpath, _dirnames, filenames in os.walk(root_path):
        # Skip hidden directories (e.g. .git)
        rel_dir = Path(dirpath).relative_to(root_path)
        if any(part.startswith(".") for part in rel_dir.parts):
            continue

        for fname in filenames:
            filepath = Path(dirpath) / fname

            if filepath.name in EXCLUDED_FILENAMES:
                continue

            if not is_scannable(filepath):
                continue

            all_violations.extend(scan_file(filepath))

    return all_violations


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan repository for confidential / private references."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Root directory to scan (default: current directory).",
    )
    args = parser.parse_args()

    violations = scan_directory(args.directory)

    if violations:
        print(f"CONFIDENTIALITY SCAN FAILED -- {len(violations)} violation(s) found:\n")
        for fpath, lineno, category, matched in violations:
            print(f"  {fpath}:{lineno}  [{category}]  matched: {matched!r}")
        print()
        sys.exit(1)
    else:
        print("Confidentiality scan passed -- no violations found.")
        sys.exit(0)


if __name__ == "__main__":
    main()
