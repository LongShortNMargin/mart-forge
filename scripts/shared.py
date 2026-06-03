"""Shared utilities for mart-forge linters.

Consolidates duplicated markdown-parsing, template-detection,
placeholder-detection, and CLI-reporting helpers that were previously
copy-pasted across lint_brd, lint_tdd, lint_signed_brd, and
lint_signed_tdd.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Markdown section helpers
# ---------------------------------------------------------------------------

_SECTION_HEADER_CACHE: Dict[str, re.Pattern[str]] = {}


def _section_re(marker: str) -> re.Pattern[str]:
    if marker not in _SECTION_HEADER_CACHE:
        _SECTION_HEADER_CACHE[marker] = re.compile(
            rf"^##\s*{re.escape(marker)}\b", re.MULTILINE
        )
    return _SECTION_HEADER_CACHE[marker]


_NEXT_SECTION_RE = re.compile(r"^##\s", re.MULTILINE)


def find_section(text: str, marker: str) -> int:
    """Return line number where ``## <marker>`` appears, or -1."""
    match = _section_re(marker).search(text)
    if not match:
        return -1
    return text[: match.start()].count("\n") + 1


def section_body(text: str, marker: str) -> str:
    """Return the text under ``## <marker>`` until the next ``## `` or EOF."""
    m = _section_re(marker).search(text)
    if not m:
        return ""
    start = m.end()
    n = _NEXT_SECTION_RE.search(text, pos=start)
    return text[start : n.start() if n else len(text)]


# ---------------------------------------------------------------------------
# Markdown table parsing
# ---------------------------------------------------------------------------

_SEPARATOR_CHARS = frozenset("-:| ")


def _is_separator_row(cells: List[str]) -> bool:
    return set("".join(cells).strip()) <= _SEPARATOR_CHARS


def parse_tables_in_body(body: str) -> List[Tuple[List[str], List[List[str]]]]:
    """Parse every markdown table found in *body*.

    Returns a list of ``(headers, rows)`` tuples. Headers and rows are
    lists of trimmed cell strings.
    """
    tables: List[Tuple[List[str], List[List[str]]]] = []
    headers: List[str] = []
    rows: List[List[str]] = []
    in_table = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if not in_table:
                headers = cells
                rows = []
                in_table = True
            elif _is_separator_row(cells):
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


def parse_tables(
    text: str, section_marker: str
) -> List[Tuple[List[str], List[List[str]]]]:
    """Find every markdown table inside the given section."""
    body = section_body(text, section_marker)
    return parse_tables_in_body(body)


def parse_first_table(
    text: str, section_marker: str
) -> Tuple[List[str], List[List[str]]]:
    """Return the first markdown table in a section, or ``([], [])``."""
    tables = parse_tables(text, section_marker)
    return tables[0] if tables else ([], [])


def first_table_in_body(
    body: str,
) -> Tuple[List[str], List[List[str]]]:
    """Return the first table found in a raw text body."""
    tables = parse_tables_in_body(body)
    return tables[0] if tables else ([], [])


# ---------------------------------------------------------------------------
# Row-to-dict helper
# ---------------------------------------------------------------------------


def row_to_dict(headers: List[str], row: List[str]) -> Dict[str, str]:
    """Map column headers to row values, defaulting missing cells to ``""``."""
    return {h: (row[i] if i < len(row) else "") for i, h in enumerate(headers)}


# ---------------------------------------------------------------------------
# Template / placeholder detection
# ---------------------------------------------------------------------------

_PLACEHOLDER_VALUES = frozenset({
    "todo",
    "_todo_",
    "_todo:_",
    "tbd",
    "_tbd_",
    "n/a",
    "\u2014",  # em-dash
    "-",
})


def is_template_path(filepath: Path) -> bool:
    """True when *filepath* looks like a template file, not a real doc."""
    name = filepath.name.lower()
    parts = {p.lower() for p in filepath.parts}
    return (
        ".template." in name
        or name.endswith(".template.md")
        or "templates" in parts
    )


def is_placeholder(value: str) -> bool:
    """True for cells that are clearly placeholder content."""
    if not value:
        return True
    v = value.strip().lower()
    if not v:
        return True
    if v in _PLACEHOLDER_VALUES:
        return True
    if v.startswith("_todo") or v.startswith("_example"):
        return True
    return False


_SIGNATURE_PLACEHOLDER_CELLS = frozenset({
    "",
    "__________",
    "_________",
    "________________",
    "_______________",
    "_TODO_",
    "TODO",
    "tbd",
    "TBD",
    "\u2014",
    "-",
    "_____",
    "____",
})


def is_placeholder_cell(value: str) -> bool:
    """True for signature-table cells that are placeholder content."""
    v = value.strip()
    if not v:
        return True
    stripped = v.strip("_- ")
    if not stripped:
        return True
    if v.upper() in {"TBD", "TODO"}:
        return True
    return v in _SIGNATURE_PLACEHOLDER_CELLS


# ---------------------------------------------------------------------------
# CLI error-reporting
# ---------------------------------------------------------------------------


def report_lint_result(label: str, errors: List[str], *, context: str = "") -> int:
    """Print errors in the standard mart-forge linter format.

    Returns 1 when errors exist, 0 otherwise.
    """
    if errors:
        print(f"{label} FAILED \u2014 {len(errors)} error(s):\n")
        for err in errors:
            print(f"  {err}")
        return 1
    print(f"{label} passed{': ' + context if context else '.'}")
    return 0
