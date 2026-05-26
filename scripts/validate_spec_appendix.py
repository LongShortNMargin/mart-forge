#!/usr/bin/env python3
"""Validate that SPEC.md Appendix A contains only placeholders.

The public SPEC.md should define the Appendix A schema (column headers,
format description) but must NOT contain actual ledger entries -- those
belong to operator-private forks only.

Exit code 1 if populated entries are found, 0 if clean.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

SPEC_DEFAULT = "SPEC.md"

# ---------------------------------------------------------------------------
# Patterns that indicate real (non-placeholder) ledger entries
# ---------------------------------------------------------------------------
# ISO-8601 timestamps  e.g. 2024-03-15T10:30:00Z or 2024-03-15
TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2})", re.IGNORECASE)

# Ruling / decision entries  e.g. "RULING-001", "DEC-2024-03"
RULING_RE = re.compile(r"\b(?:RULING|DEC|DECISION|ENTRY)-\d{2,}", re.IGNORECASE)

# Monetary amounts  e.g. $1,234.56 or USD 500
MONETARY_RE = re.compile(r"(?:\$|USD|EUR|GBP)\s*[\d,]+(?:\.\d{2})?", re.IGNORECASE)

# Table rows that look populated: | <non-header content> | <content> | ...
# Heuristic: a markdown table row with 3+ cells where none are "---" and at
# least one cell contains a digit or timestamp-like string.
POPULATED_ROW_RE = re.compile(
    r"^\s*\|(?:[^|]+\|){2,}",  # at least 3 pipe-delimited cells
)

# Separator row (not a data row)
SEPARATOR_ROW_RE = re.compile(r"^\s*\|[\s\-:|]+\|")

# Placeholder markers
PLACEHOLDER_RE = re.compile(
    r"(?:TBD|TODO|placeholder|example|N/A|\.\.\.|<[^>]+>)",
    re.IGNORECASE,
)

REAL_ENTRY_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("timestamp", TIMESTAMP_RE),
    ("ruling_id", RULING_RE),
    ("monetary_amount", MONETARY_RE),
]


def find_appendix_a(lines: List[str]) -> Tuple[int, int]:
    """Return (start, end) line indices for Appendix A section.

    *start* is the heading line; *end* is the line before the next
    same-or-higher-level heading (or EOF).
    """
    start = -1
    heading_level = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        # Match markdown headings like ## Appendix A or # Appendix A
        m = re.match(r"^(#{1,6})\s+.*Appendix\s*A", stripped, re.IGNORECASE)
        if m:
            start = i
            heading_level = len(m.group(1))
            break

    if start < 0:
        return -1, -1

    # Find end of section
    end = len(lines)
    for i in range(start + 1, len(lines)):
        stripped = lines[i].strip()
        m = re.match(r"^(#{1,6})\s+", stripped)
        if m and len(m.group(1)) <= heading_level:
            end = i
            break

    return start, end


def check_appendix_content(lines: List[str], start: int, end: int) -> List[Tuple[int, str, str]]:
    """Scan Appendix A lines for real ledger entries.

    Returns list of (line_number, category, matched_text).
    """
    violations: List[Tuple[int, str, str]] = []

    for i in range(start + 1, end):
        line = lines[i]

        # Skip blank lines, headings, separator rows
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if SEPARATOR_ROW_RE.match(stripped):
            continue

        # Check if this looks like a populated table row
        if POPULATED_ROW_RE.match(stripped):
            # If the row is entirely placeholders, it's fine
            cells = [c.strip() for c in stripped.split("|") if c.strip()]
            all_placeholder = all(PLACEHOLDER_RE.search(c) for c in cells)
            if all_placeholder:
                continue

            # Check for real-entry patterns in the row
            for category, pattern in REAL_ENTRY_PATTERNS:
                m = pattern.search(stripped)
                if m:
                    violations.append((i + 1, category, m.group()))

        else:
            # Non-table prose -- still check for real entries
            for category, pattern in REAL_ENTRY_PATTERNS:
                m = pattern.search(stripped)
                if m:
                    # Allow if clearly in a format/schema description
                    if PLACEHOLDER_RE.search(stripped):
                        continue
                    violations.append((i + 1, category, m.group()))

    return violations


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate that SPEC.md Appendix A has no populated ledger entries."
    )
    parser.add_argument(
        "--spec",
        default=SPEC_DEFAULT,
        help=f"Path to SPEC.md (default: {SPEC_DEFAULT}).",
    )
    args = parser.parse_args()

    spec_path = Path(args.spec)
    if not spec_path.exists():
        print(f"SPEC.md not found at {spec_path} -- skipping validation.")
        sys.exit(0)

    text = spec_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    start, end = find_appendix_a(lines)
    if start < 0:
        print("No Appendix A section found in SPEC.md -- skipping validation.")
        sys.exit(0)

    violations = check_appendix_content(lines, start, end)

    if violations:
        print(f"SPEC APPENDIX VALIDATION FAILED -- {len(violations)} populated entry(ies) found:\n")
        for lineno, category, matched in violations:
            print(f"  {spec_path}:{lineno}  [{category}]  matched: {matched!r}")
        print()
        print("Appendix A must contain only placeholders in the public repo.")
        sys.exit(1)
    else:
        section_len = end - start
        print(f"Spec appendix validation passed -- Appendix A ({section_len} lines) is clean.")
        sys.exit(0)


if __name__ == "__main__":
    main()
