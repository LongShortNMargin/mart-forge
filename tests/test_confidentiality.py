"""Confidentiality boundary tests.

Verifies that tracked files contain no generic leak patterns:
absolute home paths, credential/token literals, cloud storage paths.

Project-specific denylists belong in an external/private release gate.
"""

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent

GENERIC_LEAK_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("absolute-home-path", re.compile(r"/(?:Users|home)/\w+/")),
    ("windows-user-path", re.compile(r"[A-Z]:\\Users\\\w+")),
    ("api-key-assignment", re.compile(
        r"""(?:api[_-]?key|secret[_-]?key|token)\s*[=:]\s*['"][^'"]{8,}['"]""",
        re.IGNORECASE,
    )),
    ("bearer-token", re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{20,}")),
    ("private-key-header", re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----")),
    ("cloud-storage-path", re.compile(r"(?:CloudStorage|Google\s*Drive)/", re.IGNORECASE)),
]

SKIP_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "node_modules",
    ".pytest_cache", ".ruff_cache", ".mypy_cache", "htmlcov",
    "target", "dist", "build", ".eggs",
}
BINARY_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pyc", ".duckdb"}


def _should_skip(path: Path) -> bool:
    for part in path.parts:
        if part in SKIP_DIRS or part.endswith(".egg-info"):
            return True
    return False


def _get_tracked_text_files() -> list[Path]:
    files = []
    for f in ROOT.rglob("*"):
        if _should_skip(f):
            continue
        if not f.is_file():
            continue
        if f.suffix in BINARY_EXTENSIONS:
            continue
        files.append(f)
    return files


GENERIC_CATEGORY_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("position-reference", re.compile(r"\bposition\b", re.IGNORECASE)),
    ("account-reference", re.compile(r"\baccount\s+balance\b", re.IGNORECASE)),
    ("strategy-reference", re.compile(r"\bstrategy\b", re.IGNORECASE)),
    ("internal-path-wording", re.compile(r"\binternal\s+path\b", re.IGNORECASE)),
]

CATEGORY_ALLOWLIST = {
    "position-reference": {"gex_rank"},
    "strategy-reference": {"incremental strategy", "incremental_strategy", "scd strategy"},
}

EXAMPLE_DIR = ROOT / "examples"

PUBLIC_TABLE_ALLOWLIST = {"gme_dws_daily_snapshot_1d", "gme_dws_strike_gex_1d",
                          "gme_ods_options_chain", "gme_dim_date", "gme_db",
                          "gme_ods_options", "gme_dws_daily", "gme_dws_strike"}


class TestGenericLeakPatterns:
    def test_no_absolute_home_paths_or_credentials(self):
        violations = []
        for filepath in _get_tracked_text_files():
            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
                for line_num, line in enumerate(content.splitlines(), 1):
                    for category, pattern in GENERIC_LEAK_PATTERNS:
                        if pattern.search(line):
                            rel = filepath.relative_to(ROOT)
                            violations.append(
                                f"{rel}:L{line_num} [{category}] {line.strip()[:100]}"
                            )
            except (OSError, UnicodeDecodeError):
                pass

        assert not violations, (
            "Generic confidentiality violations found:\n" + "\n".join(violations)
        )


class TestExampleIdentifierAllowlist:
    def test_gme_identifiers_in_public_allowlist(self):
        gme_id_pattern = re.compile(r"\bgme_\w+\b")
        violations = []
        if not EXAMPLE_DIR.exists():
            return
        for filepath in EXAMPLE_DIR.rglob("*"):
            if not filepath.is_file() or filepath.suffix in BINARY_EXTENSIONS:
                continue
            if _should_skip(filepath):
                continue
            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
                for line_num, line in enumerate(content.splitlines(), 1):
                    for match in gme_id_pattern.finditer(line):
                        ident = match.group()
                        if ident not in PUBLIC_TABLE_ALLOWLIST:
                            rel = filepath.relative_to(ROOT)
                            violations.append(
                                f"{rel}:L{line_num} identifier '{ident}' "
                                f"not in public allowlist"
                            )
            except (OSError, UnicodeDecodeError):
                pass

        assert not violations, (
            "Example files reference identifiers outside public allowlist:\n"
            + "\n".join(violations)
        )

    def test_no_sensitive_category_terms_in_examples(self):
        violations = []
        if not EXAMPLE_DIR.exists():
            return
        for filepath in EXAMPLE_DIR.rglob("*"):
            if not filepath.is_file() or filepath.suffix in BINARY_EXTENSIONS:
                continue
            if _should_skip(filepath):
                continue
            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
                for line_num, line in enumerate(content.splitlines(), 1):
                    lower_line = line.lower()
                    for category, pattern in GENERIC_CATEGORY_PATTERNS:
                        if pattern.search(line):
                            allowed = CATEGORY_ALLOWLIST.get(category, set())
                            if any(a in lower_line for a in allowed):
                                continue
                            rel = filepath.relative_to(ROOT)
                            violations.append(
                                f"{rel}:L{line_num} [{category}] {line.strip()[:100]}"
                            )
            except (OSError, UnicodeDecodeError):
                pass

        assert not violations, (
            "Sensitive category terms found in example files:\n"
            + "\n".join(violations)
        )
