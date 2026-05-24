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


class TestExampleConfidentiality:
    """Example content must not leak operator-private data."""

    FORBIDDEN_STRINGS = [
        "gme_dws_warrant_monitor_1d",
        "warrant_qty",
        "warrant_strike",
        "warrant_expiry",
        "intrinsic_total",
        "total_position_value",
        "cost_basis",
        "FLQP",
        "flqp",
        "VaultPass",
        "Notion",
    ]

    FORBIDDEN_PATTERNS = [
        re.compile(r"warrant.{0,20}(?:quantity|position|holding)", re.IGNORECASE),
        re.compile(r"(?:account|portfolio).{0,20}(?:balance|equity|value)", re.IGNORECASE),
    ]

    EXCLUSION_CONTEXT = re.compile(
        r"(?:EXCLUDED|FORBIDDEN|excluded|forbidden|not part of|never|"
        r"Excluded|private|Private|operator-only|permanently excluded|"
        r"does not contain|must not|MUST NOT)",
        re.IGNORECASE,
    )

    def _is_exclusion_context(self, line: str) -> bool:
        return bool(self.EXCLUSION_CONTEXT.search(line))

    def test_no_forbidden_strings_in_examples(self):
        examples_dir = ROOT / "examples"
        if not examples_dir.exists():
            return
        violations = []
        for filepath in examples_dir.rglob("*"):
            if not filepath.is_file() or filepath.suffix in BINARY_EXTENSIONS:
                continue
            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()
                for line_num, line in enumerate(lines, 1):
                    for forbidden in self.FORBIDDEN_STRINGS:
                        if forbidden in line:
                            context_window = lines[max(0, line_num - 4):line_num + 1]
                            if any(self._is_exclusion_context(ctx) for ctx in context_window):
                                continue
                            rel = filepath.relative_to(ROOT)
                            violations.append(
                                f"{rel}:L{line_num} contains '{forbidden}': {line.strip()[:120]}"
                            )
            except (OSError, UnicodeDecodeError):
                pass
        assert not violations, (
            "Forbidden private strings found in examples/:\n" + "\n".join(violations)
        )

    def test_no_forbidden_patterns_in_examples(self):
        examples_dir = ROOT / "examples"
        if not examples_dir.exists():
            return
        violations = []
        for filepath in examples_dir.rglob("*"):
            if not filepath.is_file() or filepath.suffix in BINARY_EXTENSIONS:
                continue
            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()
                for line_num, line in enumerate(lines, 1):
                    for pattern in self.FORBIDDEN_PATTERNS:
                        if pattern.search(line):
                            context_window = lines[max(0, line_num - 4):line_num + 1]
                            if any(self._is_exclusion_context(ctx) for ctx in context_window):
                                continue
                            rel = filepath.relative_to(ROOT)
                            violations.append(
                                f"{rel}:L{line_num} matches forbidden pattern: {line.strip()[:120]}"
                            )
            except (OSError, UnicodeDecodeError):
                pass
        assert not violations, (
            "Forbidden patterns found in examples/:\n" + "\n".join(violations)
        )
