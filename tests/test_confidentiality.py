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
