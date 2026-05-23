"""
Confidentiality Scan — G-CONFIDENTIAL Gate

Scans all files in the repository for forbidden strings that would violate
the confidentiality boundary. No private paths, proprietary identifiers,
operator data, or internal project names in public artifacts.
"""

import sys
from pathlib import Path

FORBIDDEN_PATTERNS = [
    "/Users/",
    "Google Drive",
    "GoogleDrive",
    "DragonRook",
    "DaPES",
    "Emberlock",
    "Argent",
    "Shopee",
    "Chatbot Mart",
    "Chatbot-Mart",
    "chatbot_mart",
    "item-mart",
    "item_mart",
    "Confluence Save",
    "Notion",
    "FLQP",
    "warrant",
    "cost basis",
    "emberlockpc",
    "vuduclong0309",
    "dragonrook",
    "dapes",
    "Stormborn",
]

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
SKIP_FILES = {"confidentiality_scan.py", "test_confidentiality.py", "LICENSE"}

BINARY_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".pyc", ".pyo"}


def scan_file(filepath: Path) -> list[tuple[int, str, str]]:
    if filepath.suffix in BINARY_EXTENSIONS:
        return []
    if filepath.name in SKIP_FILES:
        return []

    violations = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
        for line_num, line in enumerate(content.splitlines(), 1):
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.lower() in line.lower():
                    violations.append((line_num, pattern, line.strip()[:120]))
    except (OSError, UnicodeDecodeError):
        pass
    return violations


def main():
    root = Path(".")
    total_violations = 0
    files_with_violations = 0

    for filepath in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in filepath.parts):
            continue
        if not filepath.is_file():
            continue

        violations = scan_file(filepath)
        if violations:
            files_with_violations += 1
            print(f"\n{filepath}:")
            for line_num, pattern, context in violations:
                print(f"  L{line_num}: [{pattern}] {context}")
                total_violations += 1

    print(f"\n--- Confidentiality Scan Results ---")
    print(f"Files scanned: {sum(1 for _ in root.rglob('*') if _.is_file())}")
    print(f"Files with violations: {files_with_violations}")
    print(f"Total violations: {total_violations}")

    if total_violations > 0:
        print("\nFAILED: Confidentiality violations found. Fix before merge.")
        sys.exit(1)
    else:
        print("\nPASSED: No confidentiality violations found.")


if __name__ == "__main__":
    main()
