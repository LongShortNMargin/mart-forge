"""
Template Validation Script — G-HARNESS Gate

Validates that all required framework templates and skills exist and
contain the mandatory sections/structures.
"""

import sys
from pathlib import Path

REQUIRED_TEMPLATES = [
    "templates/mart.yml.template",
    "templates/business-requirements.template.md",
    "templates/tech-design-doc.template.md",
    "templates/models/ods/template.sql",
    "templates/models/dim/template.sql",
    "templates/models/dwd/template.sql",
    "templates/models/dws/template.sql",
    "templates/models/ads/template.sql",
    "templates/seeds/dim_date.csv",
    "templates/tests/template_singular.sql",
    "templates/dashboard/app.py",
    "templates/dashboard/requirements.txt",
    "templates/pipeline/daily.yml.template",
]

REQUIRED_SKILLS = [
    "skills/using-mart-forge/SKILL.md",
    "skills/mart-brd/SKILL.md",
    "skills/mart-tdd/SKILL.md",
    "skills/mart-bootstrap/SKILL.md",
    "skills/mart-dqc/SKILL.md",
    "skills/dqc-audit/SKILL.md",
    "skills/schema-evolve/SKILL.md",
    "skills/mart-review/SKILL.md",
    "skills/source-discovery/SKILL.md",
]

REQUIRED_DOCS = [
    "README.md",
    "CLAUDE.md",
    "SPEC.md",
    "METHODOLOGY.md",
    "LICENSE",
    "pyproject.toml",
    ".claude-plugin/plugin.json",
    "hooks/hooks.json",
    "docs/bus-matrix.md",
    "docs/dqc-framework.md",
    "docs/naming-conventions.md",
    "docs/agent-orchestration.md",
    "docs/provider-abstraction.md",
]

BRD_MANDATORY_SECTIONS = ["B-1", "B-2", "B-3", "B-4"]
TDD_MANDATORY_SECTIONS = [f"T-{i}" for i in range(1, 18)]


def check_files_exist(file_list: list[str], category: str) -> list[str]:
    missing = []
    for f in file_list:
        if not Path(f).exists():
            missing.append(f)
            print(f"  MISSING: {f}")
        else:
            print(f"  OK: {f}")
    return missing


def check_brd_template_sections() -> list[str]:
    path = Path("templates/business-requirements.template.md")
    if not path.exists():
        return ["BRD template missing"]

    content = path.read_text()
    missing = []
    for section in BRD_MANDATORY_SECTIONS:
        if section not in content:
            missing.append(f"BRD template missing section {section}")
    return missing


def check_tdd_template_sections() -> list[str]:
    path = Path("templates/tech-design-doc.template.md")
    if not path.exists():
        return ["TDD template missing"]

    content = path.read_text()
    missing = []
    for section in TDD_MANDATORY_SECTIONS:
        if section not in content:
            missing.append(f"TDD template missing section {section}")
    return missing


def check_hard_gates() -> list[str]:
    issues = []
    bootstrap_skill = Path("skills/mart-bootstrap/SKILL.md")
    if bootstrap_skill.exists():
        content = bootstrap_skill.read_text()
        if "signed-off TDD" not in content and "signed-off" not in content:
            issues.append("mart-bootstrap skill missing TDD gate reference")

    tdd_skill = Path("skills/mart-tdd/SKILL.md")
    if tdd_skill.exists():
        content = tdd_skill.read_text()
        if "signed-off BRD" not in content and "signed-off" not in content:
            issues.append("mart-tdd skill missing BRD gate reference")

    return issues


def main():
    all_issues = []

    print("=== Template Validation ===\n")

    print("--- Required Templates ---")
    all_issues.extend(check_files_exist(REQUIRED_TEMPLATES, "templates"))

    print("\n--- Required Skills ---")
    all_issues.extend(check_files_exist(REQUIRED_SKILLS, "skills"))

    print("\n--- Required Documentation ---")
    all_issues.extend(check_files_exist(REQUIRED_DOCS, "docs"))

    print("\n--- BRD Template Sections ---")
    brd_issues = check_brd_template_sections()
    all_issues.extend(brd_issues)
    for issue in brd_issues:
        print(f"  MISSING: {issue}")
    if not brd_issues:
        print("  OK: All BRD mandatory sections present")

    print("\n--- TDD Template Sections ---")
    tdd_issues = check_tdd_template_sections()
    all_issues.extend(tdd_issues)
    for issue in tdd_issues:
        print(f"  MISSING: {issue}")
    if not tdd_issues:
        print("  OK: All TDD mandatory sections present")

    print("\n--- Hard Gate Enforcement ---")
    gate_issues = check_hard_gates()
    all_issues.extend(gate_issues)
    for issue in gate_issues:
        print(f"  ISSUE: {issue}")
    if not gate_issues:
        print("  OK: Hard gates enforced in skills")

    print(f"\n=== Results ===")
    print(f"Total issues: {len(all_issues)}")

    if all_issues:
        print("\nFAILED: Framework validation failed.")
        for issue in all_issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("\nPASSED: All framework validation checks pass.")


if __name__ == "__main__":
    main()
