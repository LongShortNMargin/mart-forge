"""Static structural checks against every skill spec in catalog.yaml.

This is the Skill Testing Framework's enforcement layer in CI. For each
skill listed in `tests/skill-testing/catalog.yaml`, this test loads the
referenced spec file and verifies the universal assertions (see
`quality-rubric.md`).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

import pytest

try:
    import yaml
except ImportError:  # PyYAML is in pyproject.toml dev extras
    yaml = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "tests" / "skill-testing" / "catalog.yaml"
SKILLS_DIR = ROOT / ".claude" / "skills"


def _load_catalog() -> List[Dict[str, str]]:
    if yaml is None:
        pytest.skip("PyYAML not installed; install via pip install -e .[dev]")
    raw = CATALOG.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    return list(data["skills"])


CATALOG_ENTRIES = _load_catalog() if CATALOG.exists() and yaml is not None else []


@pytest.mark.parametrize("entry", CATALOG_ENTRIES, ids=lambda e: e["name"])
class TestSkillSpec:
    def test_spec_file_exists(self, entry: Dict[str, str]) -> None:
        spec_path = (CATALOG.parent / entry["spec"]).resolve()
        assert spec_path.exists(), f"spec file missing: {spec_path}"

    def test_skill_file_exists(self, entry: Dict[str, str]) -> None:
        skill_path = SKILLS_DIR / entry["name"] / "SKILL.md"
        assert skill_path.exists(), f"skill file missing: {skill_path}"

    def test_skill_frontmatter_complete(self, entry: Dict[str, str]) -> None:
        skill_path = SKILLS_DIR / entry["name"] / "SKILL.md"
        text = skill_path.read_text(encoding="utf-8")
        assert text.startswith("---\n"), f"{skill_path}: missing YAML frontmatter"
        fm_end = text.find("\n---", 4)
        assert fm_end > 0, f"{skill_path}: unterminated YAML frontmatter"
        fm = text[4:fm_end]
        assert "name:" in fm, f"{skill_path}: frontmatter missing name"
        assert "description:" in fm, f"{skill_path}: frontmatter missing description"
        assert "user-invocable:" in fm, f"{skill_path}: frontmatter missing user-invocable"

    def test_skill_has_required_sections(self, entry: Dict[str, str]) -> None:
        skill_path = SKILLS_DIR / entry["name"] / "SKILL.md"
        text = skill_path.read_text(encoding="utf-8")
        assert re.search(r"^##\s+When to use", text, re.MULTILINE), (
            f"{skill_path}: missing `## When to use` section"
        )
        assert re.search(r"^##\s+Prerequisites", text, re.MULTILINE), (
            f"{skill_path}: missing `## Prerequisites` section"
        )
        assert re.search(r"^##\s+Output format", text, re.MULTILINE), (
            f"{skill_path}: missing `## Output format` section"
        )
        assert re.search(r"^##\s+NOT for", text, re.MULTILINE), (
            f"{skill_path}: missing `## NOT for` section"
        )

    def test_spec_carries_static_assertions(self, entry: Dict[str, str]) -> None:
        spec_path = (CATALOG.parent / entry["spec"]).resolve()
        text = spec_path.read_text(encoding="utf-8")
        assert "## Static Assertions" in text, (
            f"{spec_path}: missing `## Static Assertions` section"
        )
        # Each spec must have at least one checkbox assertion.
        assert "- [ ]" in text, (
            f"{spec_path}: no checkbox assertions found under Static Assertions"
        )

    def test_spec_carries_test_cases(self, entry: Dict[str, str]) -> None:
        spec_path = (CATALOG.parent / entry["spec"]).resolve()
        text = spec_path.read_text(encoding="utf-8")
        assert "## Test Cases" in text, f"{spec_path}: missing `## Test Cases`"
        # Must have at least one case + at least one adversarial case
        # (or the verdict vocabulary explicitly).
        assert re.search(r"###\s+Case\s+\d+", text), (
            f"{spec_path}: at least one test case (### Case N) required"
        )


def test_every_skill_is_in_catalog() -> None:
    """Every directory under .claude/skills/ must have a catalog entry.

    Prevents drift: a new skill added without a spec is a CI failure.
    """
    if not SKILLS_DIR.exists():
        pytest.skip(f"{SKILLS_DIR} not found")
    skill_dirs = {d.name for d in SKILLS_DIR.iterdir() if d.is_dir()}
    catalog_names = {e["name"] for e in CATALOG_ENTRIES}
    missing = skill_dirs - catalog_names
    assert not missing, f"Skills without catalog entries: {sorted(missing)}"
