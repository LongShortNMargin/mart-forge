"""Framework template validation — packaged version."""

from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).parent.parent.parent

REQUIRED_FILES = [
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
    "templates/pipeline/daily.yml.template",
    "skills/using-mart-forge/SKILL.md",
    "skills/mart-brd/SKILL.md",
    "skills/mart-tdd/SKILL.md",
    "skills/mart-bootstrap/SKILL.md",
    "skills/mart-dqc/SKILL.md",
    "skills/dqc-audit/SKILL.md",
    "skills/schema-evolve/SKILL.md",
    "skills/mart-review/SKILL.md",
    "skills/source-discovery/SKILL.md",
    "README.md",
    "CLAUDE.md",
    "SPEC.md",
    "METHODOLOGY.md",
]

BRD_SECTIONS = ["B-1", "B-2", "B-3", "B-4"]
TDD_SECTIONS = [f"T-{i}" for i in range(1, 18)]


def validate_framework() -> bool:
    issues = []

    for f in REQUIRED_FILES:
        if not (FRAMEWORK_ROOT / f).exists():
            issues.append(f"Missing: {f}")

    brd = FRAMEWORK_ROOT / "templates" / "business-requirements.template.md"
    if brd.exists():
        content = brd.read_text()
        for s in BRD_SECTIONS:
            if s not in content:
                issues.append(f"BRD template missing section {s}")

    tdd = FRAMEWORK_ROOT / "templates" / "tech-design-doc.template.md"
    if tdd.exists():
        content = tdd.read_text()
        for s in TDD_SECTIONS:
            if s not in content:
                issues.append(f"TDD template missing section {s}")

        for layer in ["T-7", "T-8", "T-9", "T-10", "T-11"]:
            if "column_name" not in content or "calculation" not in content:
                issues.append(f"TDD {layer} missing full column specification")
                break

        if "not_applicable" not in content:
            issues.append("TDD template missing not_applicable rationale provision")

    if issues:
        print("Framework validation FAILED:")
        for i in issues:
            print(f"  - {i}")
        return False

    print("Framework validation PASSED.")
    return True


if __name__ == "__main__":
    import sys
    sys.exit(0 if validate_framework() else 1)
