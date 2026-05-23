"""
mart-forge scaffold — Generate a dbt project from a signed BRD/TDD.

Enforces structural contract validation:
- BRD must have all mandatory sections (B-1..B-4) with populated metric catalog
- TDD must have all mandatory sections (T-1..T-17) with per-layer column specs
- Grade A or explicit APPROVED required; Grade B and below rejected
- No unverified link_status at sign-off
- Each metric must declare valid source_type and resolved link_status
- Bare heading vocabulary and bare N/A tokens rejected
- ODS (T-6) and ADS (T-11) cannot be not_applicable
- Cross-validates BRD metric-to-ADS traceability
- Generates machine-readable implementation contract (mart.yml) from signed BRD/TDD
- Produces a complete, runnable dbt project with SQL models, DQC assets, and dashboard
"""

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml

from mart_forge._resources import get_resource_root

BRD_REQUIRED_SECTIONS = ["B-1", "B-2", "B-3", "B-4"]
TDD_REQUIRED_SECTIONS = [f"T-{i}" for i in range(1, 18)]

COLUMN_SPEC_FIELDS = [
    "column_name", "data_type", "definition",
    "example_value", "calculation", "data_source",
]

VALID_SOURCE_TYPES = {"native", "derived", "hybrid"}
VALID_LINK_STATUSES = {"exact", "proxy", "unsupported"}

MODEL_NAMES = {
    "ods": "{prefix}_ods_csv_sample",
    "dim": "{prefix}_dim_date",
    "dwd": "{prefix}_dwd_daily_sample_di",
    "dws": "{prefix}_dws_daily_revenue_1d",
    "ads": "{prefix}_ads_exec_dashboard",
}

TABLE_SECTIONS = {
    "T-6": {"label": "ODS", "extra": ["Grain", "Incremental Strategy", "Unique Key", "Provenance"]},
    "T-7": {"label": "DIM", "extra": []},
    "T-8": {"label": "DWD", "extra": ["source_type", "provenance"]},
    "T-9": {"label": "DWS-Count", "extra": []},
    "T-10": {"label": "DWS-Perf", "extra": []},
    "T-11": {"label": "ADS", "extra": ["BRD"]},
}

MANDATORY_LAYERS = {"T-6": "ODS", "T-11": "ADS"}

LAYER_TO_SECTION = {"ods": "T-6", "dim": "T-7", "dwd": "T-8", "dws": "T-9", "ads": "T-11"}


def _sanitize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", name.lower().replace("-", "_"))


def _is_signed(doc_path: Path) -> bool:
    if not doc_path.exists():
        return False
    content = doc_path.read_text()
    if re.search(r"Grade:\s*[BCDF]", content):
        return False
    return "Grade: A" in content or "APPROVED" in content


def _extract_section(content: str, label: str, next_label: str | None) -> str:
    start = content.find(f"## {label}")
    if start < 0:
        start = content.find(label)
    if start < 0:
        return ""
    if next_label:
        end = content.find(f"## {next_label}")
        if end < 0:
            end = content.find(next_label)
        if end < 0 or end <= start:
            end = len(content)
    else:
        end = len(content)
    return content[start:end]


def _section_has_content(section_text: str, heading: str) -> bool:
    lines = section_text.splitlines()
    content_lines = [
        l.strip() for l in lines
        if l.strip()
        and not l.strip().startswith("#")
        and l.strip() != heading
        and not l.strip().startswith("---")
    ]
    return len(content_lines) >= 1


def _has_populated_column_spec(section_text: str) -> bool:
    """Check if section has a column spec table with at least one data row."""
    lines = section_text.splitlines()
    found_header = False
    found_separator = False
    data_rows = 0
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            if found_separator:
                break
            continue
        if not found_header:
            if "column_name" in stripped.lower():
                found_header = True
            continue
        if not found_separator:
            if re.match(r"^\s*\|[\s\-|]+\|\s*$", stripped):
                found_separator = True
            continue
        cells = [c.strip() for c in stripped.split("|")[1:-1]]
        if cells and cells[0]:
            data_rows += 1
    return data_rows > 0


def _extract_metrics(brd_content: str) -> list[dict]:
    """Extract metrics from BRD B-3 metric catalog."""
    b3_text = _extract_section(brd_content, "B-3", "B-4")
    metrics = []
    for line in b3_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or re.match(r"^\s*\|[\s\-|]+\|\s*$", stripped):
            continue
        cells = [c.strip() for c in stripped.split("|")[1:-1]]
        if len(cells) < 4:
            continue
        metric_cell = cells[0]
        if "metric" in metric_cell.lower() and len(cells) > 1 and "source" in cells[1].lower():
            continue
        match = re.match(r"(M-\d+)\s+(.*)", metric_cell)
        if match:
            metrics.append({
                "id": match.group(1),
                "name": match.group(2).strip(),
                "source_type": cells[1].strip(),
                "link_status": cells[2].strip(),
                "definition": cells[3].strip() if len(cells) > 3 else "",
            })
    return metrics


def _extract_ads_columns(tdd_content: str) -> list[dict]:
    """Extract ADS column-to-metric mapping from TDD T-11."""
    t11_text = _extract_section(tdd_content, "T-11", "T-12")
    columns = []
    for line in t11_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or re.match(r"^\s*\|[\s\-|]+\|\s*$", stripped):
            continue
        cells = [c.strip() for c in stripped.split("|")[1:-1]]
        if len(cells) < 6:
            continue
        if "column_name" in cells[0].lower():
            continue
        brd_ref = cells[6].strip() if len(cells) > 6 else "-"
        link_status = cells[7].strip() if len(cells) > 7 else ""
        columns.append({
            "column_name": cells[0],
            "data_type": cells[1] if len(cells) > 1 else "",
            "brd_ref": brd_ref,
            "link_status": link_status,
        })
    return columns


def _get_active_layers(tdd_content: str) -> dict[str, bool]:
    """Determine which TDD table sections have populated column specs."""
    result = {}
    for section_label in TABLE_SECTIONS:
        next_num = int(section_label.split("-")[1]) + 1
        next_label = f"T-{next_num}"
        section_text = _extract_section(tdd_content, section_label, next_label)
        if section_text and "column_name" in section_text and _has_populated_column_spec(section_text):
            result[section_label] = True
        else:
            result[section_label] = False
    return result


def _validate_brd(brd_path: Path) -> list[str]:
    errors = []
    if not brd_path.exists():
        return ["BRD not found. Create a BRD before scaffolding (Phase A gate)."]

    content = brd_path.read_text()

    if not _is_signed(brd_path):
        errors.append("BRD exists but is not signed off. Require Grade: A or APPROVED.")

    for i, section in enumerate(BRD_REQUIRED_SECTIONS):
        if section not in content:
            errors.append(f"BRD missing mandatory section {section}.")
            continue
        next_section = BRD_REQUIRED_SECTIONS[i + 1] if i + 1 < len(BRD_REQUIRED_SECTIONS) else None
        section_text = _extract_section(content, section, next_section)
        if not _section_has_content(section_text, section):
            errors.append(f"BRD section {section} has no substantive content (bare heading).")

    b3_text = _extract_section(content, "B-3", "B-4")
    if b3_text:
        has_source_type = any(st in b3_text.lower() for st in VALID_SOURCE_TYPES)
        if not has_source_type:
            errors.append("BRD B-3 metric catalog missing source_type classification (native/derived/hybrid).")
        has_link_status = any(ls in b3_text.lower() for ls in VALID_LINK_STATUSES)
        if not has_link_status:
            errors.append("BRD B-3 metric catalog missing link_status (exact/proxy/unsupported).")
        table_rows = [
            l for l in b3_text.splitlines()
            if "|" in l
            and l.strip().startswith("|")
            and not re.match(r"^\s*\|[\s\-|]+\|\s*$", l)
        ]
        data_rows = [
            r for r in table_rows
            if not all(kw in r.lower() for kw in {"metric"})
            or any(st in r.lower() for st in VALID_SOURCE_TYPES)
        ]
        if len(data_rows) < 2:
            errors.append("BRD B-3 metric catalog has no populated metric rows.")

    if "source_type" not in content and "source type" not in content.lower():
        if not any(s in content for s in ["native", "derived", "hybrid"]):
            errors.append("BRD missing metric source_type classification (native/derived/hybrid).")

    if "link_status" not in content and "link status" not in content.lower():
        if not any(s in content for s in ["exact", "proxy", "unsupported"]):
            errors.append("BRD missing link_status classification (exact/proxy/unsupported).")

    if "unverified" in content.lower():
        errors.append("BRD contains 'unverified' link_status — all links must be resolved before sign-off.")

    return errors


def _validate_tdd(tdd_path: Path) -> list[str]:
    errors = []
    if not tdd_path.exists():
        return ["TDD not found. Create a TDD before scaffolding (Phase B gate)."]

    content = tdd_path.read_text()

    if not _is_signed(tdd_path):
        errors.append("TDD exists but is not signed off. Require Grade: A or APPROVED.")

    for section in TDD_REQUIRED_SECTIONS:
        if section not in content:
            errors.append(f"TDD missing mandatory section {section}.")

    active_layers = {}

    for section_label, spec in TABLE_SECTIONS.items():
        next_num = int(section_label.split("-")[1]) + 1
        next_label = f"T-{next_num}"
        section_text = _extract_section(content, section_label, next_label)

        if not section_text:
            errors.append(f"TDD {section_label} ({spec['label']}) section not found.")
            active_layers[section_label] = False
            continue

        has_column_spec = "column_name" in section_text
        has_na = "not_applicable" in section_text.lower()

        if not has_column_spec and has_na:
            if section_label in MANDATORY_LAYERS:
                errors.append(
                    f"TDD {section_label} ({MANDATORY_LAYERS[section_label]}) cannot be "
                    f"not_applicable — every mart requires this layer."
                )
            else:
                na_line_idx = None
                lines = section_text.splitlines()
                for idx, line in enumerate(lines):
                    if "not_applicable" in line.lower():
                        na_line_idx = idx
                        break
                if na_line_idx is not None:
                    remaining = " ".join(lines[na_line_idx:]).strip()
                    remaining = remaining.replace("not_applicable", "").strip()
                    remaining = re.sub(r"[*_#|{}\-\s]", "", remaining)
                    if len(remaining) < 10:
                        errors.append(
                            f"TDD {section_label} ({spec['label']}) has bare "
                            f"not_applicable without rationale."
                        )
            active_layers[section_label] = False
            continue

        if not has_column_spec and not has_na:
            errors.append(
                f"TDD {section_label} ({spec['label']}) missing column specification table."
            )
            active_layers[section_label] = False
            continue

        if not _has_populated_column_spec(section_text):
            errors.append(
                f"TDD {section_label} ({spec['label']}) has column spec header but no data rows."
            )
            active_layers[section_label] = False
            continue

        active_layers[section_label] = True

        for field in COLUMN_SPEC_FIELDS:
            if field not in section_text:
                errors.append(
                    f"TDD {section_label} ({spec['label']}) missing column spec field: {field}"
                )

        for extra in spec["extra"]:
            if extra.lower() not in section_text.lower():
                errors.append(
                    f"TDD {section_label} ({spec['label']}) missing required element: {extra}"
                )

    if not any(active_layers.get(l, False) for l in ("T-8", "T-9")):
        errors.append(
            "TDD requires at least one fact/aggregation layer (T-8 DWD or T-9 DWS)."
        )

    t3_text = _extract_section(content, "T-3", "T-4")
    if t3_text:
        t3_has_data = False
        for line in t3_text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("|"):
                continue
            if re.match(r"^\s*\|[\s\-|]+\|\s*$", stripped):
                continue
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if not cells:
                continue
            if "table name" in cells[0].lower() or cells[0].lower() == "table":
                continue
            t3_has_data = True
            break
        if not t3_has_data:
            errors.append("TDD T-3 table summary has no table entries.")

    if "unverified" in content.lower():
        errors.append(
            "TDD contains 'unverified' — all verifications must be resolved before sign-off."
        )

    return errors


def _validate_contract_linkage(brd_path: Path, tdd_path: Path) -> list[str]:
    """Cross-validate BRD metrics against TDD T-11 ADS traceability."""
    errors = []
    if not brd_path.exists() or not tdd_path.exists():
        return errors
    brd_content = brd_path.read_text()
    tdd_content = tdd_path.read_text()
    metrics = _extract_metrics(brd_content)
    ads_columns = _extract_ads_columns(tdd_content)
    if not metrics or not ads_columns:
        return errors
    metric_ids = {m["id"] for m in metrics}
    metric_link = {m["id"]: m["link_status"] for m in metrics}
    for col in ads_columns:
        ref = col["brd_ref"]
        if ref in ("-", ""):
            continue
        if ref not in metric_ids:
            errors.append(
                f"TDD T-11 column '{col['column_name']}' references {ref} "
                f"which is not in BRD B-3 metric catalog."
            )
        elif col["link_status"] and col["link_status"] != metric_link.get(ref, ""):
            errors.append(
                f"TDD T-11 column '{col['column_name']}' has link_status "
                f"'{col['link_status']}' but BRD metric {ref} declares "
                f"link_status '{metric_link[ref]}'."
            )
    referenced = {col["brd_ref"] for col in ads_columns if col["brd_ref"] not in ("-", "")}
    for m in metrics:
        if m["id"] not in referenced:
            errors.append(
                f"BRD metric {m['id']} ({m['name']}) is not traced in TDD T-11."
            )
    return errors


def _generate_contract(
    mart_name: str, prefix: str, brd_content: str, tdd_content: str,
) -> dict:
    """Generate implementation contract from validated BRD/TDD."""
    safe_name = _sanitize_name(mart_name)
    metrics = _extract_metrics(brd_content)
    active = _get_active_layers(tdd_content)
    ads_columns = _extract_ads_columns(tdd_content)

    for metric in metrics:
        for col in ads_columns:
            if col.get("brd_ref") == metric["id"]:
                metric["ads_column"] = col["column_name"]
                break

    layer_map = {
        "T-6": ("ods", MODEL_NAMES.get("ods")),
        "T-7": ("dim", MODEL_NAMES.get("dim")),
        "T-8": ("dwd", MODEL_NAMES.get("dwd")),
        "T-9": ("dws_count", MODEL_NAMES.get("dws")),
        "T-10": ("dws_perf", None),
        "T-11": ("ads", MODEL_NAMES.get("ads")),
    }
    layers = {}
    for section, (key, model_pat) in layer_map.items():
        is_active = active.get(section, False)
        entry = {"active": is_active}
        if is_active and model_pat:
            entry["model"] = model_pat.replace("{prefix}", prefix)
        layers[key] = entry

    return {
        "mart": {
            "name": mart_name,
            "db_name": safe_name,
            "prefix": prefix,
            "version": "1.0",
        },
        "metrics": [{k: v for k, v in m.items()} for m in metrics],
        "layers": layers,
        "dashboard": {
            "ads_table": MODEL_NAMES["ads"].replace("{prefix}", prefix),
            "dws_table": MODEL_NAMES["dws"].replace("{prefix}", prefix),
        },
    }


def _check_gates(mart_dir: Path) -> list[str]:
    errors = []
    errors.extend(_validate_brd(mart_dir / "brd.md"))
    errors.extend(_validate_tdd(mart_dir / "tdd.md"))
    errors.extend(_validate_contract_linkage(mart_dir / "brd.md", mart_dir / "tdd.md"))
    return errors


def scaffold(mart_dir: Path, mart_name: str, prefix: str) -> dict:
    """Generate a runnable dbt project skeleton in mart_dir."""
    gate_errors = _check_gates(mart_dir)
    if gate_errors:
        return {"success": False, "errors": gate_errors, "files_created": []}

    resource_root = get_resource_root()
    templates_dir = resource_root / "templates"
    scripts_dir = resource_root / "scripts"
    files_created = []

    safe_name = _sanitize_name(mart_name)

    brd_content = (mart_dir / "brd.md").read_text()
    tdd_content = (mart_dir / "tdd.md").read_text()
    contract = _generate_contract(mart_name, prefix, brd_content, tdd_content)
    contract_path = mart_dir / "mart.yml"
    contract_path.write_text(yaml.dump(contract, default_flow_style=False, sort_keys=False))
    files_created.append("mart.yml")

    active = _get_active_layers(tdd_content)

    # dbt_project.yml
    dbt_project = mart_dir / "dbt_project.yml"
    dbt_project.write_text(
        f"name: '{safe_name}'\n"
        f"version: '1.0.0'\n"
        f"config-version: 2\n"
        f"profile: '{safe_name}'\n"
        f"\n"
        f"model-paths: ['models']\n"
        f"seed-paths: ['seeds']\n"
        f"test-paths: ['tests']\n"
        f"analysis-paths: ['analyses']\n"
        f"macro-paths: ['macros']\n"
        f"\n"
        f"clean-targets: ['target', 'dbt_packages']\n"
    )
    files_created.append("dbt_project.yml")

    # profiles.yml
    profiles = mart_dir / "profiles.yml"
    profiles.write_text(
        f"{safe_name}:\n"
        f"  target: dev\n"
        f"  outputs:\n"
        f"    dev:\n"
        f"      type: duckdb\n"
        f"      path: '{safe_name}.duckdb'\n"
        f"    ci:\n"
        f"      type: duckdb\n"
        f"      path: 'ci.duckdb'\n"
    )
    files_created.append("profiles.yml")

    # Model SQL files — only for active layers
    for layer, model_pattern in MODEL_NAMES.items():
        section = LAYER_TO_SECTION.get(layer)
        if section and not active.get(section, False):
            continue
        layer_dir = mart_dir / "models" / layer
        layer_dir.mkdir(parents=True, exist_ok=True)
        template_sql = templates_dir / "models" / layer / "template.sql"
        if template_sql.exists():
            content = template_sql.read_text()
            content = content.replace("{prefix}", prefix)
            model_name = model_pattern.replace("{prefix}", prefix)
            target_file = layer_dir / f"{model_name}.sql"
            target_file.write_text(content)
            files_created.append(f"models/{layer}/{model_name}.sql")

    # Seeds
    seeds_dir = mart_dir / "seeds"
    seeds_dir.mkdir(exist_ok=True)
    for seed_name in ["raw_sample_data.csv", "dim_date.csv"]:
        seed_src = templates_dir / "seeds" / seed_name
        if seed_src.exists():
            shutil.copy2(seed_src, seeds_dir / seed_name)
            files_created.append(f"seeds/{seed_name}")

    # Tests directory with runnable singular test
    tests_dir = mart_dir / "tests"
    tests_dir.mkdir(exist_ok=True)
    ods_model = MODEL_NAMES["ods"].replace("{prefix}", prefix)
    test_content = (
        f"-- Validates: no duplicate primary keys in ODS (record_id + pull_date)\n"
        f"-- Control class: Duplicate Detection\n"
        f"-- Severity: error\n\n"
        f"select\n"
        f"    record_id,\n"
        f"    pull_date,\n"
        f"    count(*) as row_count\n"
        f"from {{{{ ref('{ods_model}') }}}}\n"
        f"group by record_id, pull_date\n"
        f"having count(*) > 1\n"
    )
    test_file = tests_dir / f"test_{prefix}_ods_no_duplicate_keys.sql"
    test_file.write_text(test_content)
    files_created.append(f"tests/test_{prefix}_ods_no_duplicate_keys.sql")

    # schema.yml — conditional on active layers, uses data_tests
    dwd_model = MODEL_NAMES["dwd"].replace("{prefix}", prefix)
    dim_model = MODEL_NAMES["dim"].replace("{prefix}", prefix)
    dws_model = MODEL_NAMES["dws"].replace("{prefix}", prefix)
    ads_model = MODEL_NAMES["ads"].replace("{prefix}", prefix)

    schema_content = "version: 2\n\nmodels:\n"

    if active.get("T-6", False):
        schema_content += (
            f"  - name: {ods_model}\n"
            f"    description: 'ODS layer — raw ingestion from sample CSV'\n"
            f"    columns:\n"
            f"      - name: record_id\n"
            f"        data_tests:\n"
            f"          - not_null\n"
            f"      - name: pull_date\n"
            f"        data_tests:\n"
            f"          - not_null\n\n"
        )

    if active.get("T-7", False):
        schema_content += (
            f"  - name: {dim_model}\n"
            f"    description: 'Date dimension (seed-backed)'\n"
            f"    columns:\n"
            f"      - name: date_sk\n"
            f"        data_tests:\n"
            f"          - not_null\n\n"
        )

    if active.get("T-8", False):
        schema_content += (
            f"  - name: {dwd_model}\n"
            f"    description: 'DWD fact — daily order line detail'\n"
            f"    columns:\n"
            f"      - name: order_line_sk\n"
            f"        data_tests:\n"
            f"          - not_null\n"
            f"          - unique\n"
            f"      - name: date_key\n"
            f"        data_tests:\n"
            f"          - not_null\n"
            f"          - relationships:\n"
            f"              arguments:\n"
            f"                to: ref('{dim_model}')\n"
            f"                field: date_sk\n\n"
        )

    if active.get("T-9", False):
        schema_content += (
            f"  - name: {dws_model}\n"
            f"    description: 'DWS — daily revenue aggregation'\n"
            f"    columns:\n"
            f"      - name: date_key\n"
            f"        data_tests:\n"
            f"          - not_null\n"
            f"      - name: order_count\n"
            f"        data_tests:\n"
            f"          - not_null\n"
            f"      - name: daily_revenue\n"
            f"        data_tests:\n"
            f"          - not_null\n\n"
        )

    if active.get("T-11", False):
        schema_content += (
            f"  - name: {ads_model}\n"
            f"    description: 'ADS — executive dashboard OBT'\n"
            f"    columns:\n"
            f"      - name: calendar_date\n"
            f"        data_tests:\n"
            f"          - not_null\n"
            f"      - name: order_count\n"
            f"        data_tests:\n"
            f"          - not_null\n"
            f"      - name: daily_revenue\n"
            f"        data_tests:\n"
            f"          - not_null\n\n"
        )

    schema_content += (
        "seeds:\n"
        "  - name: raw_sample_data\n"
        "    description: 'Sample order data for fixture/demo'\n"
        "  - name: dim_date\n"
        "    description: 'Calendar seed with business day flags'\n"
    )

    schema = mart_dir / "models" / "schema.yml"
    (mart_dir / "models").mkdir(parents=True, exist_ok=True)
    schema.write_text(schema_content)
    files_created.append("models/schema.yml")

    # Dashboard — copy template (reads from mart.yml at runtime)
    dash_dir = mart_dir / "dashboard"
    dash_dir.mkdir(exist_ok=True)
    dash_template = templates_dir / "dashboard" / "app.py"
    if dash_template.exists():
        shutil.copy2(dash_template, dash_dir / "app.py")
    files_created.append("dashboard/app.py")
    (dash_dir / "requirements.txt").write_text(
        "streamlit>=1.30\nduckdb>=0.10\npyyaml>=6.0\n"
    )
    files_created.append("dashboard/requirements.txt")

    # DQC scorecard template
    scorecard = mart_dir / "dqc_scorecard.json"
    scorecard.write_text(json.dumps({
        "mart": mart_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "controls": [],
    }, indent=2))
    files_created.append("dqc_scorecard.json")

    # DQC update script
    mart_scripts_dir = mart_dir / "scripts"
    mart_scripts_dir.mkdir(exist_ok=True)
    dqc_script_src = scripts_dir / "dqc_update.py"
    if dqc_script_src.exists():
        shutil.copy2(dqc_script_src, mart_scripts_dir / "dqc_update.py")
    else:
        (mart_scripts_dir / "dqc_update.py").write_text(
            '"""DQC scorecard update — generated by mart-forge scaffold."""\n'
            'print("Run mart-forge dqc-update or install mart-forge for full functionality.")\n'
        )
    files_created.append("scripts/dqc_update.py")

    # CI pipeline
    ci_dir = mart_dir / ".github" / "workflows"
    ci_dir.mkdir(parents=True, exist_ok=True)
    pipeline_src = templates_dir / "pipeline" / "daily.yml.template"
    if pipeline_src.exists():
        content = pipeline_src.read_text()
        content = content.replace("{Mart Name}", mart_name)
        content = content.replace("{cron_expression}", "0 6 * * *")
        (ci_dir / "daily.yml").write_text(content)
        files_created.append(".github/workflows/daily.yml")

    # Macros directory (dbt expects it)
    (mart_dir / "macros").mkdir(exist_ok=True)
    (mart_dir / "analyses").mkdir(exist_ok=True)

    return {"success": True, "errors": [], "files_created": files_created}
