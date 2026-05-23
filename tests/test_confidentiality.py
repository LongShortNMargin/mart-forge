"""Confidentiality boundary tests.

Ensures no private paths, proprietary identifiers, operator data,
or internal project names appear in any public artifact.
"""

from pathlib import Path

ROOT = Path(__file__).parent.parent

FORBIDDEN_PATTERNS = [
    "DragonRook",
    "DaPES",
    "Emberlock",
    "Argent",
    "Shopee",
    "Chatbot Mart",
    "Chatbot-Mart",
    "item-mart",
    "Confluence",
    "FLQP",
    "emberlockpc",
    "vuduclong0309",
    "Stormborn",
    "/Users/",
    "Google Drive",
    "GoogleDrive",
]

SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules"}
SKIP_FILES = {"confidentiality_scan.py", "test_confidentiality.py"}
BINARY_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pyc"}


def get_all_text_files():
    files = []
    for f in ROOT.rglob("*"):
        if any(part in SKIP_DIRS for part in f.parts):
            continue
        if not f.is_file():
            continue
        if f.suffix in BINARY_EXTENSIONS:
            continue
        if f.name in SKIP_FILES:
            continue
        files.append(f)
    return files


class TestNoConfidentialContent:
    def test_no_forbidden_strings(self):
        violations = []
        for filepath in get_all_text_files():
            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
                for pattern in FORBIDDEN_PATTERNS:
                    if pattern.lower() in content.lower():
                        rel = filepath.relative_to(ROOT)
                        violations.append(f"{rel}: contains '{pattern}'")
            except (OSError, UnicodeDecodeError):
                pass

        assert not violations, (
            f"Confidentiality violations found:\n" + "\n".join(violations)
        )


class TestNoGMEContent:
    """Phase F: zero GME-specific content on main."""

    GME_PATTERNS = [
        "GameStop",
        " GME ",
        "gme_",
        "gme-options",
        "options-mart",
        "CBOE",
        "cboe",
        "max_pain",
        "gamma exposure",
        "GEX",
        "put-call ratio",
    ]

    def test_no_gme_specific_content(self):
        violations = []
        for filepath in get_all_text_files():
            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
                for pattern in self.GME_PATTERNS:
                    if pattern in content:
                        rel = filepath.relative_to(ROOT)
                        violations.append(f"{rel}: contains GME-specific '{pattern}'")
            except (OSError, UnicodeDecodeError):
                pass

        assert not violations, (
            f"GME-specific content found (Phase F must be zero-GME):\n"
            + "\n".join(violations)
        )
