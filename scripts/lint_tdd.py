#!/usr/bin/env python3
"""TDD structural linter.

Enforces SPEC §4.5 / §7.3:
- Sections T-1 through T-21 are present.
- T-8 schema-detail rows have all 6 required columns.
- T-9 ODS contract carries all 8 required fields per ODS table.
- `calculation` cells for derived columns contain SQL, not prose
  placeholders.

Exit code 1 on any failure.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

from scripts.shared import (
    find_section,
    first_table_in_body,
    report_lint_result,
    section_body,
)

REQUIRED_SECTIONS = [f"T-{i}" for i in range(1, 22)]

T8_REQUIRED_COLUMNS = [
    "column_name",
    "data_type",
    "definition",
    "example_value",
    "calculation",
    "data_source",
]

T9_CONTRACT_FIELDS = [
    "source",
    "grain",
    "logical_partition",
    "incremental_strategy",
    "unique_key",
    "backfill",
    "restatement",
    "provenance_columns",
]

PROSE_PLACEHOLDERS = {
    "derived",
    "computed",
    "see model",
    "see above",
    "see below",
    "tbd",
    "todo",
}


def lint(filepath: Path) -> List[str]:
    if not filepath.exists():
        return [f"{filepath}: file not found"]
    text = filepath.read_text(encoding="utf-8")
    errors: List[str] = []

    # Check all section markers.
    for section in REQUIRED_SECTIONS:
        if find_section(text, section) < 0:
            errors.append(
                f"{filepath}: missing section §{section}\n"
                f"    -> remediation: add §{section} per "
                f"templates/tech-design-doc.template.md."
            )

    # Validate T-8 column shape on every table inside T-8.
    t8 = section_body(text, "T-8")
    if t8:
        headers, rows = first_table_in_body(t8)
        if headers:
            missing = [c for c in T8_REQUIRED_COLUMNS if c not in headers]
            if missing:
                errors.append(
                    f"{filepath}: §T-8 schema detail table missing columns: {missing}\n"
                    f"    -> remediation: T-8 rows must have all 6 columns: "
                    f"{T8_REQUIRED_COLUMNS} (see templates/tech-design-doc.template.md §T-8)."
                )

    # Validate T-9 ODS contract fields.
    t9 = section_body(text, "T-9")
    missing_t9 = [f for f in T9_CONTRACT_FIELDS if f not in t9]
    if missing_t9:
        errors.append(
            f"{filepath}: §T-9 ODS contract missing fields: {missing_t9}\n"
            f"    -> remediation: ODS contract MUST declare "
            f"{T9_CONTRACT_FIELDS} (see templates/tech-design-doc.template.md §T-9)."
        )

    # Validate T-8 calculation cells: derived rows must not carry prose
    # placeholders. We detect by checking any cell value that matches a
    # banned placeholder exactly (case-insensitive, after trimming).
    if t8:
        headers, rows = first_table_in_body(t8)
        if headers and "calculation" in headers:
            idx = headers.index("calculation")
            for r_no, row in enumerate(rows, start=1):
                if idx >= len(row):
                    continue
                val = row[idx].strip().lower()
                if not val:
                    continue
                if val in PROSE_PLACEHOLDERS:
                    errors.append(
                        f"{filepath}: §T-8 row {r_no} `calculation` is a prose placeholder ({val!r})\n"
                        f"    -> remediation: derived columns require actual SQL/formula; native columns "
                        f"use 'pass-through from <provider>.<field>'."
                    )

    return errors


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lint a Technical Design Document for structural compliance."
    )
    parser.add_argument("filepath", help="Path to the TDD markdown file.")
    args = parser.parse_args(argv)

    errors = lint(Path(args.filepath))
    return report_lint_result("TDD LINT", errors, context=args.filepath)


if __name__ == "__main__":
    sys.exit(main())
