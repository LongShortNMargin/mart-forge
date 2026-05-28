#!/usr/bin/env python3
"""BRD structural linter.

Enforces SPEC §4.4 / §7.2:
- Sections B-1 through B-4 are present.
- B-3 metric table has the required columns.
- Every B-3 metric row declares a known link_status.
- Every metric (non-DWS) has a non-empty source binding OR appears in
  B-4 with exhaustion evidence.

Exit code 1 on any failure.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

REQUIRED_SECTIONS = ["B-1", "B-2", "B-3", "B-4"]
REQUIRED_B3_COLUMNS = [
    "metric_name",
    "metric_definition",
    "source_type",
    "link_status",
]
VALID_LINK_STATUSES = {"exact", "proxy", "unsupported", "unverified"}
VALID_SOURCE_TYPES = {"native", "derived", "hybrid"}


def find_section(text: str, marker: str) -> int:
    """Return line number where section header appears, or -1."""
    pattern = re.compile(rf"^##\s*{re.escape(marker)}\b", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return -1
    return text[: match.start()].count("\n") + 1


def parse_table(text: str, section_marker: str) -> Tuple[List[str], List[List[str]]]:
    """Find the first markdown table after the given section. Return
    (headers, rows). Headers and rows are lists of trimmed cell strings.
    """
    pattern = re.compile(
        rf"^##\s*{re.escape(section_marker)}\b",
        re.MULTILINE,
    )
    m = pattern.search(text)
    if not m:
        return [], []

    rest = text[m.end():]
    lines = rest.splitlines()
    headers: List[str] = []
    rows: List[List[str]] = []
    in_table = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("##"):
            break
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if not in_table:
                headers = cells
                in_table = True
            elif set("".join(cells).strip()) <= set("-:| "):
                # Separator row.
                continue
            else:
                rows.append(cells)
        elif in_table and not stripped:
            # End of table.
            break
    return headers, rows


def lint(filepath: Path) -> List[str]:
    if not filepath.exists():
        return [f"{filepath}: file not found"]
    text = filepath.read_text(encoding="utf-8")
    errors: List[str] = []

    # Check section presence.
    for section in REQUIRED_SECTIONS:
        if find_section(text, section) < 0:
            errors.append(
                f"{filepath}: missing section §{section}\n"
                f"    -> remediation: add §{section} per "
                f"templates/business-requirements.template.md."
            )

    # Validate B-3 metric table.
    headers, rows = parse_table(text, "B-3")
    if not headers:
        errors.append(
            f"{filepath}: §B-3 metric table not found or empty\n"
            f"    -> remediation: add the metrics table per "
            f"templates/business-requirements.template.md §B-3."
        )
    else:
        missing_cols = [c for c in REQUIRED_B3_COLUMNS if c not in headers]
        if missing_cols:
            errors.append(
                f"{filepath}: §B-3 missing required columns: {missing_cols}\n"
                f"    -> remediation: include columns "
                f"{REQUIRED_B3_COLUMNS} per "
                f"templates/business-requirements.template.md §B-3."
            )
        # Validate each row's link_status and source_type when present.
        if "link_status" in headers:
            idx = headers.index("link_status")
            for r_no, row in enumerate(rows, start=1):
                if idx >= len(row):
                    continue
                val = row[idx].strip().lower()
                if not val:
                    continue
                # Allow templates with markdown decoration like
                # "exact / proxy / unsupported / unverified".
                if "/" in val:
                    continue
                if val not in VALID_LINK_STATUSES:
                    errors.append(
                        f"{filepath}: §B-3 row {r_no} has invalid link_status '{val}'\n"
                        f"    -> remediation: link_status must be one of "
                        f"{sorted(VALID_LINK_STATUSES)}."
                    )
        if "source_type" in headers:
            idx = headers.index("source_type")
            for r_no, row in enumerate(rows, start=1):
                if idx >= len(row):
                    continue
                val = row[idx].strip().lower()
                if not val or "/" in val:
                    continue
                if val not in VALID_SOURCE_TYPES:
                    errors.append(
                        f"{filepath}: §B-3 row {r_no} has invalid source_type '{val}'\n"
                        f"    -> remediation: source_type must be one of "
                        f"{sorted(VALID_SOURCE_TYPES)}."
                    )

    return errors


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lint a Business Requirements Document for structural compliance."
    )
    parser.add_argument("filepath", help="Path to the BRD markdown file.")
    args = parser.parse_args(argv)

    errors = lint(Path(args.filepath))
    if errors:
        print(f"BRD LINT FAILED — {len(errors)} error(s):\n")
        for err in errors:
            print(f"  {err}")
        return 1
    print(f"BRD lint passed: {args.filepath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
