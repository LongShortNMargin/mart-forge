"""Generic confidentiality scan — packaged version."""

import re
import sys
from pathlib import Path

from mart_forge._resources import get_resource_root

GENERIC_PATTERNS: list[tuple[str, re.Pattern]] = [
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
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
    ".pytest_cache", ".ruff_cache", ".mypy_cache", "htmlcov", "target", ".eggs",
}
BINARY_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pyc", ".duckdb"}


def run_scan(root: Path | None = None) -> bool:
    root = root or get_resource_root()
    violations = []

    for filepath in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS or part.endswith(".egg-info") for part in filepath.parts):
            continue
        if not filepath.is_file() or filepath.suffix in BINARY_EXTENSIONS:
            continue
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
            for line_num, line in enumerate(content.splitlines(), 1):
                for category, pattern in GENERIC_PATTERNS:
                    if pattern.search(line):
                        violations.append(f"{filepath.relative_to(root)}:L{line_num} [{category}]")
        except (OSError, UnicodeDecodeError):
            pass

    if violations:
        print("Confidentiality scan FAILED:")
        for v in violations:
            print(f"  {v}")
        return False

    print("Confidentiality scan PASSED.")
    return True


if __name__ == "__main__":
    sys.exit(0 if run_scan() else 1)
