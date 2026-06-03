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
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Set, Tuple

SCAN_EXTENSIONS = {
    ".py", ".md", ".yml", ".yaml", ".json", ".sql", ".csv", ".txt",
    ".toml", ".sh", ".jsonl", ".cfg", ".ini",
}

# Paths the scanner excludes from its own scan. Each entry is matched
# against the file's path relative to the scan root (POSIX separators),
# not just the basename — a `templates/confidentiality_scan.py` placed
# anywhere in the tree is still scanned. The scanner file itself is
# excluded because it must define the patterns it is rejecting.
EXCLUDED_PATHS = {
    "scripts/confidentiality_scan.py",  # this file defines the patterns
    "tests/test_confidentiality.py",    # tests assert against the patterns
}


# Per-context allow-list for the public GitHub org slug. The slug is
# permitted in three narrow public-discovery surfaces and rejected
# everywhere else. The orchestrator's round-3 ruling (EMB-322,
# 2026-06-01) requires NARROW context predicates, not file-wide
# allowance — without them the README is one prose edit away from
# leaking the slug onto a contributor line, badge, or quoted excerpt.
#
# The allowed contexts are:
#
#   - ``.claude-plugin/marketplace.json`` — the line must be the
#     ``"name": "LongShortNMargin"`` entry inside the top-level
#     ``"owner": { ... }`` object. Other JSON contexts in the same
#     file are not allowed.
#   - ``README.md`` — the line must be inside a fenced code block
#     whose info string starts with ``bash``, ``shell``, or
#     ``console``, AND must contain ``/plugin marketplace add `` or
#     ``git clone https://github.com/``. Prose lines, info strings
#     of other shapes (``text``, ``python`` ...), and code lines
#     without an install command are all rejected.
#   - ``MARKETPLACE.md`` — the line must be inside a section whose
#     H2 heading is ``## Submission steps``, ``## How to submit``, or
#     ``## Submitting to the marketplace`` (case-insensitive). The
#     file is otherwise treated like any other doc.
#
# See ``_public_org_allowed_lines`` and its three per-file helpers
# for the implementation. ``_is_public_org_allowed_at`` is what
# ``scan_file`` calls per match.
PUBLIC_ORG_SLUG_RE = re.compile(r"longshortnmargin", re.IGNORECASE)

# Files for which a context predicate is defined. Anything not in this
# map is treated as "slug is banned, period".
PUBLIC_ORG_PREDICATE_PATHS = {
    ".claude-plugin/marketplace.json",
    "README.md",
    "MARKETPLACE.md",
}

# Allowed H2 headings for MARKETPLACE.md (compared case-insensitively).
# The file is generated and the heading may stabilize under different
# wording; any of these is acceptable as the submission section.
_MARKETPLACE_MD_ALLOWED_SECTIONS = {
    "submission steps",
    "how to submit",
    "submitting to the marketplace",
}

# Fenced-block info strings that count as a shell-like context for the
# README install allowance. The match is case-insensitive and uses
# ``startswith`` — ``console`` and ``bash`` are both common in plugin
# READMEs; ``text`` and ``python`` are deliberately excluded.
_README_SHELL_FENCE_PREFIXES = ("bash", "shell", "console")

# Tokens an install line must contain to qualify for the allowance.
# ``in`` substring check, so ``/plugin marketplace add LongShortNMargin``
# counts (no trailing space required after the value).
_README_INSTALL_LINE_MARKERS = (
    "/plugin marketplace add ",
    "git clone https://github.com/",
)

# Dot-prefixed directory names allowed to be skipped during the walk.
# Anything not on this allow-list — most importantly `.claude/`,
# `.claude-plugin/`, `.github/` — must be scanned. This is the fix for
# the reviewer finding "confidentiality_scan silently skips every
# dot-prefixed directory at any depth": prior code did
# `any(part.startswith(".") for part in rel_dir.parts)`, which
# excluded the agent-authored skill files most likely to leak codenames.
ALLOWED_DOT_DIR_SKIPS = {
    ".git",
    ".venv",
    ".pytest_cache",
    "__pycache__",   # never starts with ".", listed for symmetry
    "node_modules",  # idem
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".eggs",
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
    # L1: every internal_project / internal_persona / internal_program
    # pattern uses re.IGNORECASE so case-variants (`ARGENT`, `shopee`,
    # `drook`) cannot smuggle the term past the scanner.
    BannedPattern(
        "internal_project",
        re.compile(r"\bShopee\b", re.IGNORECASE),
        "Do not name third-party companies; use a generic placeholder.",
    ),
    BannedPattern(
        "internal_project",
        re.compile(r"\bChatbot\s*Mart\b", re.IGNORECASE),
        "Internal mart name. Use a generic example like 'orders-mart'.",
    ),
    BannedPattern(
        "internal_project",
        re.compile(r"\bDragonRook\b", re.IGNORECASE),
        "Private mono-repo name. Do not reference in public artifacts.",
    ),
    BannedPattern(
        "internal_project",
        re.compile(r"\bEmberlock(?:_\w+)?\b", re.IGNORECASE),
        "Private archive name. Do not reference.",
    ),

    # --- internal agent / persona names -----------------------------------
    BannedPattern(
        "internal_persona",
        re.compile(r"\bArgent\b", re.IGNORECASE),
        "Private agent persona. Use generic 'reviewer' or 'maintainer'.",
    ),
    BannedPattern(
        "internal_persona",
        re.compile(r"\bSilver\s+Chainbind\b", re.IGNORECASE),
        "Private persona name. Do not reference.",
    ),
    BannedPattern(
        "internal_persona",
        re.compile(r"\bGhost\s+Operator\b", re.IGNORECASE),
        "Private operator alias. Do not reference.",
    ),

    # --- internal program names -------------------------------------------
    BannedPattern(
        "internal_program",
        re.compile(r"\bDROOK\b", re.IGNORECASE),
        "Private orchestration program. Do not reference.",
    ),
    BannedPattern(
        "internal_program",
        re.compile(r"\bFHAG\b", re.IGNORECASE),
        "Private program. Do not reference.",
    ),
    BannedPattern(
        "internal_program",
        re.compile(r"\bSCAS\b", re.IGNORECASE),
        "Private program. Do not reference.",
    ),
    BannedPattern(
        "internal_program",
        re.compile(r"\bDaPES\b", re.IGNORECASE),
        "Private program. Do not reference.",
    ),
    BannedPattern(
        "internal_program",
        re.compile(r"\bFLQP\b", re.IGNORECASE),
        "Private protocol. Do not reference.",
    ),
    BannedPattern(
        "internal_program",
        re.compile(r"\bCelestial\s+Ordinance\b", re.IGNORECASE),
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
    BannedPattern(
        "secret",
        re.compile(r"xox[bpas]-[0-9A-Za-z\-]{10,}"),
        "Slack token. Rotate immediately if committed.",
    ),
    BannedPattern(
        "secret",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----"),
        "PEM private key. Remove and rotate immediately.",
    ),
    BannedPattern(
        "secret",
        re.compile(r"sk-[0-9A-Za-z]{20,}"),
        "OpenAI / generic secret key. Rotate immediately if committed.",
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


def _readme_allowed_lines(text: str) -> Set[int]:
    """Return README.md line numbers (1-indexed) where the public-org
    slug is permitted.

    A line is allowed iff:

    1. It is inside a fenced code block (``\\`\\`\\``` ... ``\\`\\`\\```` or
       ``~~~`` ... ``~~~``) whose info string starts with ``bash``,
       ``shell``, or ``console`` (case-insensitive).
    2. It contains ``/plugin marketplace add `` or
       ``git clone https://github.com/``.

    The fence line itself is never allowed; only lines strictly between
    the opening and closing fence count.
    """
    allowed: Set[int] = set()
    in_fence = False
    fence_marker: str = ""
    info_is_shell = False
    fence_open_re = re.compile(r"^(`{3,}|~{3,})\s*([A-Za-z0-9_+\-]*)")
    for idx, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        m = fence_open_re.match(stripped)
        if m:
            marker = m.group(1)[:3]  # collapse "````+" to "```" / "~~~"
            if not in_fence:
                in_fence = True
                fence_marker = marker
                info = (m.group(2) or "").lower()
                info_is_shell = any(
                    info.startswith(prefix)
                    for prefix in _README_SHELL_FENCE_PREFIXES
                )
            elif stripped.startswith(fence_marker):
                in_fence = False
                fence_marker = ""
                info_is_shell = False
            # The fence line itself is never an install-command line.
            continue
        if in_fence and info_is_shell:
            if any(marker in line for marker in _README_INSTALL_LINE_MARKERS):
                allowed.add(idx)
    return allowed


def _marketplace_md_allowed_lines(text: str) -> Set[int]:
    """Return MARKETPLACE.md line numbers where the public-org slug is
    permitted.

    A line is allowed iff it falls under an H2 heading whose text
    (after the ``## `` prefix, trimmed and lowercased) is one of
    ``_MARKETPLACE_MD_ALLOWED_SECTIONS``. The heading line itself is
    not counted as an allowed line — the slug should never appear in
    a heading.
    """
    allowed: Set[int] = set()
    in_allowed_section = False
    h2_re = re.compile(r"^##\s+(.+?)\s*$")
    h_any_re = re.compile(r"^(#{1,6})\s+")
    for idx, line in enumerate(text.splitlines(), start=1):
        # An H2 heading both closes the previous section and opens the
        # next one. An H1 also closes any current allowed section
        # (everything beneath an H1 is a new top-level scope).
        h_match = h_any_re.match(line)
        if h_match:
            level = len(h_match.group(1))
            if level <= 2:
                m = h2_re.match(line)
                if m and m.group(1).strip().lower() in _MARKETPLACE_MD_ALLOWED_SECTIONS:
                    in_allowed_section = True
                else:
                    in_allowed_section = False
            # H3+ headings stay inside the current section.
            continue
        if in_allowed_section:
            allowed.add(idx)
    return allowed


def _marketplace_json_allowed_lines(text: str) -> Set[int]:
    """Return marketplace.json line numbers where the public-org slug is
    permitted.

    A line is allowed iff:

    1. It matches the literal form
       ``"name": "<slug>"`` (whitespace flexible, trailing comma OK), and
    2. It appears at the immediate-child depth of the top-level
       ``"owner": { ... }`` object.

    The JSON is parsed once to validate that ``owner.name`` is in fact
    the public-org slug — if the structure is malformed or owner.name
    is a different value, no line is allowed. The per-line check is
    then a regex + brace-depth walk; ``"name": "LongShortNMargin"``
    appearing in a plugin description or any other JSON context does
    not match because brace depth tracking places it outside the
    owner-interior scope.
    """
    allowed: Set[int] = set()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return allowed
    if not isinstance(data, dict):
        return allowed
    owner = data.get("owner")
    if not isinstance(owner, dict):
        return allowed
    name = owner.get("name")
    if not isinstance(name, str) or not PUBLIC_ORG_SLUG_RE.fullmatch(name):
        return allowed

    name_re = re.compile(
        r'^\s*"name"\s*:\s*"' + re.escape(name) + r'"\s*,?\s*$'
    )
    owner_open_re = re.compile(r'"owner"\s*:\s*\{')

    in_owner = False
    owner_interior_depth = -1
    cur_depth = 0
    for idx, line in enumerate(text.splitlines(), start=1):
        opens = line.count("{")
        closes = line.count("}")
        # Detect the line that opens the owner object. The owner
        # object's interior is one deeper than the line-start depth.
        if not in_owner and owner_open_re.search(line):
            in_owner = True
            owner_interior_depth = cur_depth + 1
        cur_depth += opens - closes
        # The owner-name line carries no braces of its own and sits at
        # owner_interior_depth. Check after applying this line's
        # braces so the opening-line itself (which lands at the
        # interior depth) does not match — that line contains
        # `"owner": {`, not the name regex anyway.
        if in_owner and cur_depth == owner_interior_depth:
            if name_re.match(line):
                allowed.add(idx)
        if in_owner and cur_depth < owner_interior_depth:
            in_owner = False
            owner_interior_depth = -1
    return allowed


def _public_org_allowed_lines(rel_path: str, text: str) -> Set[int]:
    """Build the set of line numbers in ``text`` where the public-org
    slug is permitted, given the file's path. Returns an empty set for
    files outside the allow-list — every match in those files trips
    the scanner.
    """
    if rel_path == ".claude-plugin/marketplace.json":
        return _marketplace_json_allowed_lines(text)
    if rel_path == "README.md":
        return _readme_allowed_lines(text)
    if rel_path == "MARKETPLACE.md":
        return _marketplace_md_allowed_lines(text)
    return set()


def scan_file(filepath: Path, rel_path: str = "") -> List[Violation]:
    violations: List[Violation] = []
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError) as exc:
        print(
            f"WARNING: cannot read {filepath} ({exc}) — file skipped by "
            f"confidentiality scanner. Verify manually.",
            file=sys.stderr,
        )
        return violations

    # Compute the per-line allow set for the public-org slug once. For
    # files outside the predicate allow-list this is the empty set and
    # the in-loop check below short-circuits cheaply.
    if rel_path in PUBLIC_ORG_PREDICATE_PATHS:
        org_allowed_lines = _public_org_allowed_lines(rel_path, text)
    else:
        org_allowed_lines = set()

    for line_no, line in enumerate(text.splitlines(), start=1):
        for bp in BANNED_PATTERNS:
            match = bp.pattern.search(line)
            if not match:
                continue
            # Public-org slug allowance: a `longshortnmargin` match on
            # a line that satisfies the file's context predicate is
            # permitted. Every other pattern — and the slug pattern in
            # any other file — still trips the scanner.
            if (
                bp.category == "user_id"
                and PUBLIC_ORG_SLUG_RE.fullmatch(match.group())
                and line_no in org_allowed_lines
            ):
                continue
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


def iter_files(root: Path) -> Iterable[Tuple[Path, str]]:
    """Yield (absolute_path, relative_posix_path) for every scannable file."""
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)

        # Prune walk: drop disallowed dot-dirs in-place so os.walk does
        # not descend into them. Anything not on the allow-list (notably
        # .claude/, .claude-plugin/, .github/) is kept.
        dirnames[:] = [d for d in dirnames if d not in ALLOWED_DOT_DIR_SKIPS]

        # Defensive: even if we already walked into a disallowed parent
        # via a relative path, skip its files.
        if any(part in ALLOWED_DOT_DIR_SKIPS for part in rel_dir.parts):
            continue

        for fname in filenames:
            filepath = Path(dirpath) / fname
            rel_path = (rel_dir / fname).as_posix()
            if rel_path in EXCLUDED_PATHS:
                continue
            if not is_scannable(filepath):
                continue
            yield filepath, rel_path


def scan_directory(root: str) -> List[Violation]:
    all_violations: List[Violation] = []
    root_path = Path(root).resolve()
    for filepath, rel_path in iter_files(root_path):
        all_violations.extend(scan_file(filepath, rel_path=rel_path))
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
