#!/usr/bin/env python3
"""BRD structural linter.

Enforces SPEC §4.4 / §7.2:
- Sections B-1 through B-4 are present.
- B-3 metric table has the required columns.
- Every B-3 metric row declares a known link_status.
- Every B-3 metric row (per reviewer finding #4) has a non-empty
  source binding OR appears in §B-4 unsupported-metrics table with
  resource-exhaustion evidence.

Vocabulary cells that contain a `/` (e.g. ``exact / proxy / ...``) are
treated as legend strings — they pass the validator only when the file
is a template (``templates/*.template.md``) per reviewer finding #5.
A real BRD must commit to one canonical value per row.

Exit code 1 on any failure.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

REQUIRED_SECTIONS = ["B-1", "B-2", "B-3", "B-4"]
REQUIRED_B3_COLUMNS = [
    "metric_name",
    "metric_definition",
    "source_type",
    "link_status",
]
VALID_LINK_STATUSES = {"exact", "proxy", "unsupported", "unverified"}
VALID_SOURCE_TYPES = {"native", "derived", "hybrid"}

# Column used as evidence of a source binding on a B-3 row. If a row's
# metric is not listed in B-4 unsupported-metrics, this column must be
# non-empty.
B3_BINDING_COLUMN = "candidate_verification_evidence"

# B-4 unsupported-metrics table columns.
B4_UNSUPPORTED_REQUIRED_COLUMNS = [
    "metric_name",
    "Resource-Exhaustion Evidence",
]


def is_template_path(filepath: Path) -> bool:
    """Per reviewer finding #5, the legend/slash escape is allowed only
    on template files. A real BRD living in `docs/marts/<mart>/` must
    commit to a single canonical value per row.
    """
    name = filepath.name.lower()
    parts = {p.lower() for p in filepath.parts}
    return (
        ".template." in name
        or name.endswith(".template.md")
        or "templates" in parts
    )


def _is_placeholder(value: str) -> bool:
    """True for cells that are clearly placeholder content rather than
    a stakeholder commitment. Used to ignore empty template rows when
    deciding whether to enforce row-level invariants.
    """
    if not value:
        return True
    v = value.strip().lower()
    if not v:
        return True
    placeholders = {
        "todo",
        "_todo_",
        "_todo:_",
        "tbd",
        "_tbd_",
        "n/a",
        "—",
        "-",
    }
    if v in placeholders:
        return True
    if v.startswith("_todo") or v.startswith("_example"):
        return True
    return False


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
    return _parse_table_after(text, section_marker, table_index=0)


def parse_tables(
    text: str, section_marker: str
) -> List[Tuple[List[str], List[List[str]]]]:
    """Find every markdown table inside the given section."""
    pattern = re.compile(rf"^##\s*{re.escape(section_marker)}\b", re.MULTILINE)
    m = pattern.search(text)
    if not m:
        return []
    rest = text[m.end():]
    # Stop at the next `## ` header.
    next_pattern = re.compile(r"^##\s", re.MULTILINE)
    n = next_pattern.search(rest)
    section_body = rest[: n.start() if n else len(rest)]

    tables: List[Tuple[List[str], List[List[str]]]] = []
    headers: List[str] = []
    rows: List[List[str]] = []
    in_table = False
    for line in section_body.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if not in_table:
                headers = cells
                rows = []
                in_table = True
            elif set("".join(cells).strip()) <= set("-:| "):
                continue
            else:
                rows.append(cells)
        elif in_table and not stripped:
            tables.append((headers, rows))
            headers, rows = [], []
            in_table = False
    if in_table and headers:
        tables.append((headers, rows))
    return tables


def _parse_table_after(
    text: str, section_marker: str, *, table_index: int
) -> Tuple[List[str], List[List[str]]]:
    tables = parse_tables(text, section_marker)
    if table_index < len(tables):
        return tables[table_index]
    return [], []


def _row_dict(headers: List[str], row: List[str]) -> Dict[str, str]:
    return {h: (row[i] if i < len(row) else "") for i, h in enumerate(headers)}


def _collect_unsupported_metrics(text: str) -> set[str]:
    """Walk every table inside §B-4 and collect metric_name values from
    any table that looks like the unsupported-metrics table (it carries
    a ``Resource-Exhaustion Evidence`` column).
    """
    unsupported: set[str] = set()
    for headers, rows in parse_tables(text, "B-4"):
        if "metric_name" not in headers:
            continue
        if not any("exhaustion" in h.lower() for h in headers):
            continue
        idx_name = headers.index("metric_name")
        for row in rows:
            if idx_name >= len(row):
                continue
            name = row[idx_name].strip()
            if name and not _is_placeholder(name):
                unsupported.add(name.lower())
    return unsupported


def lint(filepath: Path) -> List[str]:
    if not filepath.exists():
        return [f"{filepath}: file not found"]
    text = filepath.read_text(encoding="utf-8")
    errors: List[str] = []
    allow_legend = is_template_path(filepath)

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
        return errors

    missing_cols = [c for c in REQUIRED_B3_COLUMNS if c not in headers]
    if missing_cols:
        errors.append(
            f"{filepath}: §B-3 missing required columns: {missing_cols}\n"
            f"    -> remediation: include columns "
            f"{REQUIRED_B3_COLUMNS} per "
            f"templates/business-requirements.template.md §B-3."
        )

    unsupported_metrics = _collect_unsupported_metrics(text)

    # Per-row checks. Skip rows whose every cell is placeholder content
    # (templates carry one such row by design).
    for r_no, row in enumerate(rows, start=1):
        row_map = _row_dict(headers, row)
        if all(_is_placeholder(v) for v in row_map.values()):
            continue

        # link_status validation.
        link_val = row_map.get("link_status", "").strip().lower()
        if link_val:
            is_legend = "/" in link_val
            if is_legend and not allow_legend:
                errors.append(
                    f"{filepath}: §B-3 row {r_no} link_status {link_val!r} looks "
                    f"like a legend; real BRDs must pick one value from "
                    f"{sorted(VALID_LINK_STATUSES)}.\n"
                    f"    -> remediation: commit to one canonical link_status; "
                    f"the slash legend is only allowed in templates/."
                )
            elif not is_legend and link_val not in VALID_LINK_STATUSES:
                errors.append(
                    f"{filepath}: §B-3 row {r_no} has invalid link_status "
                    f"{link_val!r}\n"
                    f"    -> remediation: link_status must be one of "
                    f"{sorted(VALID_LINK_STATUSES)}."
                )

        # source_type validation.
        st_val = row_map.get("source_type", "").strip().lower()
        if st_val:
            is_legend = "/" in st_val
            if is_legend and not allow_legend:
                errors.append(
                    f"{filepath}: §B-3 row {r_no} source_type {st_val!r} looks "
                    f"like a legend; real BRDs must pick one value from "
                    f"{sorted(VALID_SOURCE_TYPES)}.\n"
                    f"    -> remediation: commit to one canonical source_type; "
                    f"the slash legend is only allowed in templates/."
                )
            elif not is_legend and st_val not in VALID_SOURCE_TYPES:
                errors.append(
                    f"{filepath}: §B-3 row {r_no} has invalid source_type "
                    f"{st_val!r}\n"
                    f"    -> remediation: source_type must be one of "
                    f"{sorted(VALID_SOURCE_TYPES)}."
                )

        # ----- finding #4: per-row source binding check ----------------
        # In real BRDs every metric must either have a non-empty source
        # binding (B3_BINDING_COLUMN) OR appear in §B-4's unsupported
        # table with exhaustion evidence.
        if not allow_legend:
            metric_name = row_map.get("metric_name", "").strip()
            if metric_name and not _is_placeholder(metric_name):
                binding_val = row_map.get(B3_BINDING_COLUMN, "").strip()
                listed_unsupported = metric_name.lower() in unsupported_metrics
                if _is_placeholder(binding_val) and not listed_unsupported:
                    errors.append(
                        f"{filepath}: §B-3 row {r_no} metric {metric_name!r} has "
                        f"no source binding (column {B3_BINDING_COLUMN!r} is "
                        f"empty/placeholder) and is not declared unsupported in "
                        f"§B-4.\n"
                        f"    -> remediation: either fill the binding evidence "
                        f"on this row, or list the metric in §B-4 unsupported "
                        f"metrics with resource-exhaustion evidence."
                    )

    # ----- finding #4 (cont.): every B-4 unsupported metric must carry
    # resource-exhaustion evidence on its row.
    if not allow_legend:
        for b4_headers, b4_rows in parse_tables(text, "B-4"):
            if "metric_name" not in b4_headers:
                continue
            evidence_col = next(
                (h for h in b4_headers if "exhaustion" in h.lower()), None
            )
            if evidence_col is None:
                continue
            name_idx = b4_headers.index("metric_name")
            ev_idx = b4_headers.index(evidence_col)
            for r_no, row in enumerate(b4_rows, start=1):
                if name_idx >= len(row):
                    continue
                name_val = row[name_idx].strip()
                if not name_val or _is_placeholder(name_val):
                    continue
                ev_val = row[ev_idx].strip() if ev_idx < len(row) else ""
                if _is_placeholder(ev_val):
                    errors.append(
                        f"{filepath}: §B-4 unsupported metric {name_val!r} "
                        f"missing resource-exhaustion evidence.\n"
                        f"    -> remediation: every unsupported metric must "
                        f"document the investigation that established it "
                        f"cannot be sourced."
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
