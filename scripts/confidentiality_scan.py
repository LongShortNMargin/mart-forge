"""
Confidentiality Scan — G-CONFIDENTIAL Gate

Scans tracked files for generic leak categories that would violate
public-release readiness: absolute home paths, credential/token patterns,
unrendered private configuration.

This scanner uses structural patterns only. A project-specific or
operator-specific denylist belongs in an external/private release gate,
not in this public repository.
"""

import re
import sys
from pathlib import Path

GENERIC_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("absolute-home-path", re.compile(r"/(?:Users|home)/\w+/")),
    ("windows-user-path", re.compile(r"[A-Z]:\\Users\\\w+")),
    ("api-key-assignment", re.compile(r"""(?:api[_-]?key|secret[_-]?key|token)\s*[=:]\s*['"][^'"]{8,}['"]""", re.IGNORECASE)),
    ("bearer-token", re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{20,}")),
    ("private-key-header", re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----")),
    ("env-credential-leak", re.compile(r"""(?:PASSWORD|PASSWD|DB_PASS)\s*[=:]\s*['"][^'"]+['"]""", re.IGNORECASE)),
    ("cloud-storage-path", re.compile(r"(?:CloudStorage|Google\s*Drive)/", re.IGNORECASE)),
]

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
    ".pytest_cache", ".ruff_cache", ".mypy_cache", "htmlcov", "target",
    ".eggs", "*.egg-info",
}

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2",
    ".ttf", ".eot", ".pyc", ".pyo", ".so", ".duckdb",
}


def scan_file(filepath: Path) -> list[tuple[int, str, str]]:
    if filepath.suffix in BINARY_EXTENSIONS:
        return []

    violations = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
        for line_num, line in enumerate(content.splitlines(), 1):
            for category, pattern in GENERIC_PATTERNS:
                if pattern.search(line):
                    violations.append((line_num, category, line.strip()[:120]))
    except (OSError, UnicodeDecodeError):
        pass
    return violations


def should_skip(filepath: Path) -> bool:
    for part in filepath.parts:
        if part in SKIP_DIRS:
            return True
        if part.endswith(".egg-info"):
            return True
    return False


def main():
    root = Path(".")
    total_violations = 0
    files_with_violations = 0
    files_scanned = 0

    for filepath in sorted(root.rglob("*")):
        if should_skip(filepath):
            continue
        if not filepath.is_file():
            continue
        files_scanned += 1

        violations = scan_file(filepath)
        if violations:
            files_with_violations += 1
            print(f"\n{filepath}:")
            for line_num, category, context in violations:
                print(f"  L{line_num}: [{category}] {context}")
                total_violations += 1

    print(f"\n--- Confidentiality Scan Results ---")
    print(f"Files scanned: {files_scanned}")
    print(f"Files with violations: {files_with_violations}")
    print(f"Total violations: {total_violations}")

    if total_violations > 0:
        print("\nFAILED: Confidentiality violations found. Fix before merge.")
        sys.exit(1)
    else:
        print("\nPASSED: No confidentiality violations found.")


if __name__ == "__main__":
    main()
