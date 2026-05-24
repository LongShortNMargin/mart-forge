"""Framework template validation — packaged version.

Validates framework templates, skills, and documentation exist and
contain mandatory structural content. Performs per-section validation
of TDD table layers (T-6..T-11) for complete column specification.
"""

import sys
from pathlib import Path

from mart_forge._resources import get_resource_root

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
    "templates/seeds/raw_sample_data.csv",
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
    "CLAUDE.md",
    "SPEC.md",
    "METHODOLOGY.md",
]

BRD_SECTIONS = ["B-1", "B-2", "B-3", "B-4"]
TDD_SECTIONS = [f"T-{i}" for i in range(1, 18)]

COLUMN_SPEC_FIELDS = [
    "column_name", "data_type", "definition",
    "example_value", "calculation", "data_source",
]

TABLE_SECTIONS = {
    "T-6": {"label": "ODS", "extra": ["Grain", "Incremental Strategy", "Unique Key", "Provenance"]},
    "T-7": {"label": "DIM", "extra": []},
    "T-8": {"label": "DWD", "extra": ["source_type", "provenance"]},
    "T-9": {"label": "DWS-Count", "extra": []},
    "T-10": {"label": "DWS-Perf", "extra": []},
    "T-11": {"label": "ADS", "extra": ["BRD"]},
}


def _extract_section(content: str, label: str, next_label: str | None) -> str:
    start = content.find(f"## {label}")
    if start < 0:
        return ""
    if next_label:
        end = content.find(f"## {next_label}")
        if end < 0:
            end = len(content)
    else:
        end = len(content)
    return content[start:end]


def _check_tdd_table_sections(content: str) -> list[str]:
    issues = []
    for section_label, spec in TABLE_SECTIONS.items():
        next_num = int(section_label.split("-")[1]) + 1
        next_label = f"T-{next_num}"
        section_text = _extract_section(content, section_label, next_label)

        if not section_text:
            issues.append(f"{section_label} ({spec['label']}) section not found")
            continue

        for field in COLUMN_SPEC_FIELDS:
            if field not in section_text:
                issues.append(f"{section_label} ({spec['label']}) missing column spec field: {field}")

        if "not_applicable" not in section_text:
            issues.append(f"{section_label} ({spec['label']}) missing not_applicable rationale provision")

        for extra in spec["extra"]:
            if extra.lower() not in section_text.lower():
                issues.append(f"{section_label} ({spec['label']}) missing required element: {extra}")

    return issues


def validate_framework(root: Path | None = None) -> bool:
    root = root or get_resource_root()
    issues = []

    for f in REQUIRED_FILES:
        if not (root / f).exists():
            issues.append(f"Missing: {f}")

    brd = root / "templates" / "business-requirements.template.md"
    if brd.exists():
        content = brd.read_text()
        for s in BRD_SECTIONS:
            if s not in content:
                issues.append(f"BRD template missing section {s}")
        for term, alt in [("source_type", "source type"), ("link_status", "link status")]:
            if term not in content and alt not in content.lower():
                issues.append(f"BRD template missing {term} guidance")
        for classification in ["native", "derived", "hybrid"]:
            if classification not in content:
                issues.append(f"BRD template missing source_type classification: {classification}")
        for status in ["exact", "proxy", "unsupported"]:
            if status not in content:
                issues.append(f"BRD template missing link_status: {status}")

    tdd = root / "templates" / "tech-design-doc.template.md"
    if tdd.exists():
        content = tdd.read_text()
        for s in TDD_SECTIONS:
            if s not in content:
                issues.append(f"TDD template missing section {s}")

        issues.extend(_check_tdd_table_sections(content))

        if "idempoten" not in content.lower():
            issues.append("TDD template missing idempotence reference")

    if issues:
        print("Framework validation FAILED:")
        for i in issues:
            print(f"  - {i}")
        return False

    print("Framework validation PASSED.")
    return True


if __name__ == "__main__":
    sys.exit(0 if validate_framework() else 1)
