"""
mart-forge scaffold — Generate a dbt project from a signed BRD/TDD.

Two scaffold paths:
  fixture=True  → CI smoke-fixture using built-in order/revenue templates.
                   Labelled FIXTURE/DEMO. Cannot be the general implementation command.
  fixture=False → General signed-design path requiring an implementation contract
                   (impl_contract.yml) alongside signed BRD/TDD. Contract binds model
                   names, user-supplied SQL assets, ADS metric columns, and visualization
                   definitions. Requires Grade A and [ARGENT-PROXY <ISO>] approval stamp.

Enforces structural contract validation:
- BRD must have all mandatory sections (B-1..B-4) with populated metric catalog
- TDD must have all mandatory sections (T-1..T-17) with per-layer column specs
- Grade A required; Grade B and below rejected
- No unverified link_status at sign-off
- Each metric must declare valid source_type and resolved link_status
- Bare heading vocabulary and bare N/A tokens rejected
- Required layers (ODS/DWD/ADS) must have populated column specs — N/A rejected
- T-3/T-12/T-14/T-16 must have substantive content (not token text)
- BRD metric-to-ADS mapping validated for completeness and link_status consistency
- General path: ARGENT-PROXY stamp, implementation contract, visualization definitions
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

FIXTURE_MODEL_NAMES = {
    "ods": "{prefix}_ods_csv_sample",
    "dim": "{prefix}_dim_date",
    "dwd": "{prefix}_dwd_daily_sample_di",
    "dws": "{prefix}_dws_daily_revenue_1d",
    "ads": "{prefix}_ads_exec_dashboard",
}

MODEL_NAMES = FIXTURE_MODEL_NAMES

TABLE_SECTIONS = {
    "T-6": {"label": "ODS", "extra": ["Grain", "Incremental Strategy", "Unique Key", "Provenance"]},
    "T-7": {"label": "DIM", "extra": []},
    "T-8": {"label": "DWD", "extra": ["source_type", "provenance"]},
    "T-9": {"label": "DWS-Count", "extra": []},
    "T-10": {"label": "DWS-Perf", "extra": []},
    "T-11": {"label": "ADS", "extra": ["BRD"]},
}

REQUIRED_LAYER_SECTIONS = {"T-6", "T-8", "T-11"}

FIXTURE_ADS_METRIC_COLUMNS = {"daily_revenue", "order_count"}

CONTENT_SECTIONS = {
    "T-3": "Table Summary",
    "T-12": "Physical Design",
    "T-14": "DQC Plan",
    "T-16": "Operations",
}

ARGENT_PROXY_RE = re.compile(
    r"\[ARGENT-PROXY\s+\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
)

CONTRACT_FILE_NAMES = ("impl_contract.yml", "impl_contract.yaml")

REQUIRED_VIZ_FIELDS = ("metric_id", "chart_type", "x_column", "y_column", "model")


def _sanitize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", name.lower().replace("-", "_"))


def _is_signed(doc_path: Path) -> bool:
    if not doc_path.exists():
        return False
    content = doc_path.read_text()
    if re.search(r"Grade:\s*[BCDF]", content):
        return False
    return bool(re.search(r"Grade:\s*A\b", content))


def _has_proxy_stamp(doc_path: Path) -> bool:
    if not doc_path.exists():
        return False
    return bool(ARGENT_PROXY_RE.search(doc_path.read_text()))


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


def _section_has_substantive_content(section_text: str) -> bool:
    for line in section_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("---"):
            continue
        clean = re.sub(r"[*_#|{}\-`]", "", stripped).strip()
        if len(clean) >= 15:
            return True
    return False


def _count_table_data_rows(section_text: str) -> int:
    table_lines = [
        l for l in section_text.splitlines()
        if "|" in l and l.strip().startswith("|")
    ]
    count = 0
    for line in table_lines:
        if re.match(r"^\s*\|[\s\-|]+\|\s*$", line):
            continue
        if "column_name" in line.lower() and "data_type" in line.lower():
            continue
        count += 1
    return count


def _parse_brd_metrics(brd_path: Path) -> list[dict]:
    content = brd_path.read_text()
    b3_text = _extract_section(content, "B-3", "B-4")
    metrics = []
    for line in b3_text.splitlines():
        if "|" not in line or not line.strip().startswith("|"):
            continue
        if re.match(r"^\s*\|[\s\-|]+\|\s*$", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        if "metric" in cells[0].lower() and ("source_type" in cells[1].lower() or "link_status" in cells[2].lower()):
            continue
        m = re.match(r"(M-\d+)\s*(.*)", cells[0].strip())
        if m:
            metrics.append({
                "id": m.group(1),
                "name": m.group(2).strip(),
                "source_type": cells[1].strip().lower(),
                "link_status": cells[2].strip().lower(),
                "definition": cells[3].strip() if len(cells) > 3 else "",
            })
    return metrics


def _parse_ads_metric_map(tdd_path: Path) -> dict:
    content = tdd_path.read_text()
    ads_text = _extract_section(content, "T-11", "T-12")
    if not ads_text:
        return {}

    result = {}
    table_lines = [
        l for l in ads_text.splitlines()
        if "|" in l and l.strip().startswith("|")
    ]
    if len(table_lines) < 2:
        return {}

    headers = [h.strip().lower() for h in table_lines[0].strip().strip("|").split("|")]
    col_idx = {h: i for i, h in enumerate(headers)}

    brd_col = col_idx.get("brd_ref", col_idx.get("brd", None))
    link_col = col_idx.get("link_status", None)
    name_col = col_idx.get("column_name", 0)

    for line in table_lines[1:]:
        if re.match(r"^\s*\|[\s\-|]+\|\s*$", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]

        col_name = cells[name_col] if name_col < len(cells) else ""
        brd_ref = cells[brd_col] if brd_col is not None and brd_col < len(cells) else ""
        link_status = cells[link_col] if link_col is not None and link_col < len(cells) else ""

        if brd_ref and brd_ref != "-" and re.match(r"M-\d+", brd_ref):
            result[brd_ref] = {"column": col_name, "link_status": link_status.lower()}

    return result


def _validate_brd(brd_path: Path) -> list[str]:
    errors = []
    if not brd_path.exists():
        return ["BRD not found. Create a BRD before scaffolding (Phase A gate)."]

    content = brd_path.read_text()

    if not _is_signed(brd_path):
        errors.append("BRD exists but is not signed off. Require Grade: A.")

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
        if not data_rows:
            errors.append("BRD B-3 metric catalog has no populated metric rows.")

    if "source_type" not in content and "source type" not in content.lower():
        if not any(s in content for s in ["native", "derived", "hybrid"]):
            errors.append("BRD missing metric source_type classification (native/derived/hybrid).")

    if "link_status" not in content and "link status" not in content.lower():
        if not any(s in content for s in ["exact", "proxy", "unsupported"]):
            errors.append("BRD missing link_status classification (exact/proxy/unsupported).")

    if "unverified" in content.lower():
        errors.append("BRD contains 'unverified' link_status — all links must be resolved before sign-off.")

    metrics = _parse_brd_metrics(brd_path)
    for m in metrics:
        if m["source_type"] not in VALID_SOURCE_TYPES:
            errors.append(
                f"BRD metric {m['id']} has invalid source_type '{m['source_type']}' "
                f"— must be one of {sorted(VALID_SOURCE_TYPES)}."
            )
        if m["link_status"] not in VALID_LINK_STATUSES:
            errors.append(
                f"BRD metric {m['id']} has invalid link_status '{m['link_status']}' "
                f"— must be one of {sorted(VALID_LINK_STATUSES)}."
            )

    return errors


def _validate_tdd(tdd_path: Path) -> list[str]:
    errors = []
    if not tdd_path.exists():
        return ["TDD not found. Create a TDD before scaffolding (Phase B gate)."]

    content = tdd_path.read_text()

    if not _is_signed(tdd_path):
        errors.append("TDD exists but is not signed off. Require Grade: A.")

    for section in TDD_REQUIRED_SECTIONS:
        if section not in content:
            errors.append(f"TDD missing mandatory section {section}.")

    for section_id, label in CONTENT_SECTIONS.items():
        next_num = int(section_id.split("-")[1]) + 1
        next_section = f"T-{next_num}"
        section_text = _extract_section(content, section_id, next_section)
        if not section_text or not _section_has_substantive_content(section_text):
            errors.append(f"TDD {section_id} ({label}) requires substantive content, not just a heading or token text.")

    has_any_table = False
    for section_label, spec in TABLE_SECTIONS.items():
        next_num = int(section_label.split("-")[1]) + 1
        next_label = f"T-{next_num}"
        section_text = _extract_section(content, section_label, next_label)

        if not section_text:
            errors.append(f"TDD {section_label} ({spec['label']}) section not found.")
            continue

        has_column_spec = "column_name" in section_text
        has_na = "not_applicable" in section_text.lower()

        if section_label in REQUIRED_LAYER_SECTIONS and not has_column_spec:
            if has_na:
                errors.append(
                    f"TDD {section_label} ({spec['label']}) cannot be N/A — "
                    f"this layer is required and must have populated column specs."
                )
            else:
                errors.append(
                    f"TDD {section_label} ({spec['label']}) missing column specification table — "
                    f"this layer is required."
                )
            continue

        if not has_column_spec and has_na:
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
                        f"TDD {section_label} ({spec['label']}) has bare not_applicable without rationale."
                    )
                    continue
            continue

        if not has_column_spec and not has_na:
            errors.append(f"TDD {section_label} ({spec['label']}) missing column specification table.")
            continue

        if has_column_spec and _count_table_data_rows(section_text) < 1:
            errors.append(
                f"TDD {section_label} ({spec['label']}) has column spec header but no populated data rows."
            )
            continue

        has_any_table = True
        for field in COLUMN_SPEC_FIELDS:
            if field not in section_text:
                errors.append(f"TDD {section_label} ({spec['label']}) missing column spec field: {field}")

        for extra in spec["extra"]:
            if extra.lower() not in section_text.lower():
                errors.append(f"TDD {section_label} ({spec['label']}) missing required element: {extra}")

    if not has_any_table:
        errors.append("TDD has no table sections with column specifications — at least one layer required.")

    if "unverified" in content.lower():
        errors.append("TDD contains 'unverified' — all verifications must be resolved before sign-off.")

    return errors


def _validate_metric_mapping(brd_path: Path, tdd_path: Path) -> list[str]:
    errors = []
    brd_metrics = _parse_brd_metrics(brd_path)
    if not brd_metrics:
        return errors

    ads_map = _parse_ads_metric_map(tdd_path)

    for metric in brd_metrics:
        mid = metric["id"]
        if mid not in ads_map:
            errors.append(f"BRD metric {mid} ({metric['name']}) has no mapping in TDD T-11 (ADS).")
        else:
            ads_entry = ads_map[mid]
            col = ads_entry.get("column", "")
            if not col or col == "-":
                errors.append(
                    f"BRD metric {mid} ({metric['name']}) has empty ADS column binding in TDD T-11."
                )
            tdd_ls = ads_entry["link_status"]
            if tdd_ls and tdd_ls not in VALID_LINK_STATUSES:
                errors.append(
                    f"TDD T-11 metric {mid} has invalid link_status '{tdd_ls}' "
                    f"— must be one of {sorted(VALID_LINK_STATUSES)}."
                )
            brd_ls = metric["link_status"]
            if tdd_ls and brd_ls and tdd_ls != brd_ls:
                errors.append(
                    f"Metric {mid} link_status mismatch: BRD says '{brd_ls}', TDD T-11 says '{tdd_ls}'."
                )

    return errors


def _check_gates(mart_dir: Path) -> list[str]:
    errors = []
    brd_path = mart_dir / "brd.md"
    tdd_path = mart_dir / "tdd.md"
    errors.extend(_validate_brd(brd_path))
    errors.extend(_validate_tdd(tdd_path))
    if brd_path.exists() and tdd_path.exists():
        errors.extend(_validate_metric_mapping(brd_path, tdd_path))
    return errors


# ---------------------------------------------------------------------------
# Implementation contract loading & validation (general path only)
# ---------------------------------------------------------------------------

def _load_impl_contract(mart_dir: Path) -> dict | None:
    for name in CONTRACT_FILE_NAMES:
        path = mart_dir / name
        if path.exists():
            return yaml.safe_load(path.read_text())
    return None


def _validate_impl_contract(
    contract: dict | None,
    brd_metrics: list[dict],
    ads_map: dict,
    mart_dir: Path,
) -> list[str]:
    errors: list[str] = []
    if not contract:
        errors.append(
            "Implementation contract (impl_contract.yml) is required for "
            "general scaffold. Use --fixture for CI smoke-fixture generation."
        )
        return errors

    if "models" not in contract:
        errors.append("Contract missing 'models' section.")
    if "metrics" not in contract:
        errors.append("Contract missing 'metrics' section.")
    if "visualizations" not in contract:
        errors.append("Contract missing 'visualizations' section.")

    if errors:
        return errors

    contract_metrics = contract.get("metrics", [])
    contract_metric_ids = {m["id"] for m in contract_metrics}
    brd_metric_ids = {m["id"] for m in brd_metrics}

    for mid in brd_metric_ids:
        if mid not in contract_metric_ids:
            errors.append(f"BRD metric {mid} not declared in implementation contract.")

    for cm in contract_metrics:
        mid = cm.get("id", "")
        ads_col = cm.get("ads_column", "")
        if not ads_col:
            errors.append(f"Contract metric {mid} missing ads_column.")
        if mid in ads_map:
            tdd_col = ads_map[mid].get("column", "")
            if ads_col and tdd_col and ads_col != tdd_col:
                errors.append(
                    f"Contract metric {mid} ads_column '{ads_col}' does not match "
                    f"TDD T-11 column '{tdd_col}'."
                )

    models = contract.get("models", {})
    for layer in ("ods", "dwd", "dws", "ads"):
        layer_def = models.get(layer)
        if not layer_def:
            errors.append(f"Contract models missing required layer '{layer}'.")
            continue
        if not layer_def.get("name"):
            errors.append(f"Contract models.{layer} missing 'name'.")
        sql_path = layer_def.get("sql_path")
        sql_inline = layer_def.get("sql")
        if not sql_path and not sql_inline:
            errors.append(
                f"Contract models.{layer} must provide 'sql_path' or 'sql' content."
            )
        if sql_path and not (mart_dir / sql_path).exists():
            errors.append(
                f"Contract models.{layer}.sql_path '{sql_path}' not found in mart directory."
            )

    viz_defs = contract.get("visualizations", [])
    if not viz_defs:
        errors.append(
            "Contract must include at least one visualization definition. "
            "A metric list alone is insufficient."
        )
    for viz in viz_defs:
        for field in REQUIRED_VIZ_FIELDS:
            if field not in viz or not viz[field]:
                errors.append(
                    f"Visualization definition missing required field '{field}'."
                )
        vid = viz.get("metric_id", "")
        if vid and vid not in contract_metric_ids:
            errors.append(
                f"Visualization references metric '{vid}' not in contract metrics."
            )

    return errors


# ---------------------------------------------------------------------------
# Scaffold entry point
# ---------------------------------------------------------------------------

def scaffold(mart_dir: Path, mart_name: str, prefix: str, *, fixture: bool = False) -> dict:
    """Generate a runnable dbt project skeleton in mart_dir.

    fixture=True:  CI smoke-fixture path (built-in order/revenue templates).
    fixture=False: General contract-driven path (requires impl_contract.yml).
    """
    if fixture:
        return _scaffold_fixture(mart_dir, mart_name, prefix)
    return _scaffold_general(mart_dir, mart_name, prefix)


# ---------------------------------------------------------------------------
# Fixture scaffold (CI smoke only)
# ---------------------------------------------------------------------------

def _scaffold_fixture(mart_dir: Path, mart_name: str, prefix: str) -> dict:
    """CI smoke-fixture generation using built-in order/revenue templates."""
    gate_errors = _check_gates(mart_dir)
    if gate_errors:
        return {"success": False, "errors": gate_errors, "files_created": []}

    resource_root = get_resource_root()
    templates_dir = resource_root / "templates"
    scripts_dir = resource_root / "scripts"
    files_created = []

    safe_name = _sanitize_name(mart_name)

    brd_metrics = _parse_brd_metrics(mart_dir / "brd.md")
    ads_map = _parse_ads_metric_map(mart_dir / "tdd.md")
    contract_metrics = []
    for m in brd_metrics:
        mid = m["id"]
        ads_info = ads_map.get(mid, {})
        contract_metrics.append({
            "id": mid,
            "name": m["name"],
            "source_type": m["source_type"],
            "link_status": m["link_status"],
            "ads_column": ads_info.get("column", ""),
        })

    for m in contract_metrics:
        ads_col = m.get("ads_column", "")
        if ads_col and ads_col not in FIXTURE_ADS_METRIC_COLUMNS:
            return {
                "success": False,
                "errors": [
                    f"Fixture scaffold metric {m['id']} binds to ADS column '{ads_col}' "
                    f"which is not produced by the fixture template. The fixture "
                    f"generates columns {sorted(FIXTURE_ADS_METRIC_COLUMNS)}. "
                    f"Use the general scaffold (without --fixture) with an "
                    f"implementation contract for arbitrary domains."
                ],
                "files_created": [],
            }

    contract = {
        "mart": {"name": mart_name, "prefix": prefix, "version": "1.0"},
        "metrics": contract_metrics,
        "fixture": {
            "enabled": True,
            "seed_domain": "order-revenue",
            "note": "CI smoke data only — replace with domain seeds for production",
        },
    }
    contract_path = mart_dir / "mart_contract.json"
    contract_path.write_text(json.dumps(contract, indent=2))
    files_created.append("mart_contract.json")

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

    # Model SQL files — render templates with {prefix} substitution
    for layer, model_pattern in FIXTURE_MODEL_NAMES.items():
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

    # Seeds — both raw_sample_data and dim_date
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
    ods_model = FIXTURE_MODEL_NAMES["ods"].replace("{prefix}", prefix)
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

    # schema.yml with all models and generic tests
    schema = mart_dir / "models" / "schema.yml"
    dwd_model = FIXTURE_MODEL_NAMES["dwd"].replace("{prefix}", prefix)
    dim_model = FIXTURE_MODEL_NAMES["dim"].replace("{prefix}", prefix)
    dws_model = FIXTURE_MODEL_NAMES["dws"].replace("{prefix}", prefix)
    ads_model = FIXTURE_MODEL_NAMES["ads"].replace("{prefix}", prefix)
    schema.write_text(
        f"version: 2\n\n"
        f"models:\n"
        f"  - name: {ods_model}\n"
        f"    description: 'ODS layer — raw ingestion from sample CSV'\n"
        f"    columns:\n"
        f"      - name: record_id\n"
        f"        data_tests:\n"
        f"          - not_null\n"
        f"      - name: pull_date\n"
        f"        data_tests:\n"
        f"          - not_null\n\n"
        f"  - name: {dim_model}\n"
        f"    description: 'Date dimension (seed-backed)'\n"
        f"    columns:\n"
        f"      - name: date_sk\n"
        f"        data_tests:\n"
        f"          - not_null\n\n"
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
        f"seeds:\n"
        f"  - name: raw_sample_data\n"
        f"    description: 'Sample order data for fixture/demo'\n"
        f"  - name: dim_date\n"
        f"    description: 'Calendar seed with business day flags'\n"
    )
    files_created.append("models/schema.yml")

    # Dashboard — render template with contract metrics injection
    dash_dir = mart_dir / "dashboard"
    dash_dir.mkdir(exist_ok=True)
    dash_template = templates_dir / "dashboard" / "app.py"
    if dash_template.exists():
        dash_content = dash_template.read_text()
        dash_content = dash_content.replace("{mart_name}", mart_name)
        dash_content = dash_content.replace("{prefix}", prefix)
        dash_content = dash_content.replace("{db_name}", safe_name)
        contract_metrics_str = json.dumps(contract_metrics, indent=4)
        dash_content = dash_content.replace("{contract_metrics}", contract_metrics_str)
        (dash_dir / "app.py").write_text(dash_content)
    files_created.append("dashboard/app.py")

    (dash_dir / "requirements.txt").write_text("streamlit>=1.30\nduckdb>=0.10\n")
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


# ---------------------------------------------------------------------------
# General contract-driven scaffold
# ---------------------------------------------------------------------------

def _generate_general_dashboard(
    mart_name: str,
    safe_name: str,
    ads_model_name: str,
    contract_metrics: list[dict],
    viz_defs: list[dict],
) -> str:
    metrics_json = json.dumps(contract_metrics, indent=4)
    viz_json = json.dumps(viz_defs, indent=4)

    metric_columns = [m["ads_column"] for m in contract_metrics if m.get("ads_column")]
    select_cols = ["calendar_date"] + metric_columns + ["calculated_at"]
    select_clause = ", ".join(select_cols)

    return (
        '"""\n'
        f'{mart_name} Dashboard — Streamlit Presentation Layer\n'
        '\n'
        'Generated by mart-forge scaffold (general contract-driven path).\n'
        'Metrics, table bindings, and visualizations are bound to the signed\n'
        'implementation contract. No fixture/demo data is included.\n'
        '"""\n'
        '\n'
        'import json\n'
        'import os\n'
        'from pathlib import Path\n'
        '\n'
        'import duckdb\n'
        'import streamlit as st\n'
        '\n'
        f'MART_NAME = {json.dumps(mart_name)}\n'
        f'DB_PATH = os.getenv("MART_DB_PATH", {json.dumps(safe_name + ".duckdb")})\n'
        'DQC_SCORECARD_PATH = os.getenv("DQC_SCORECARD_PATH", "dqc_scorecard.json")\n'
        'IS_FIXTURE_MODE = os.getenv("MART_FIXTURE_MODE", "false").lower() == "true"\n'
        '\n'
        f'ADS_TABLE = {json.dumps(ads_model_name)}\n'
        '\n'
        f'CONTRACTED_METRICS = {metrics_json}\n'
        '\n'
        f'VISUALIZATION_DEFS = {viz_json}\n'
        '\n'
        'LINK_STATUS_LABELS = {\n'
        '    "exact": ("green", "Exact verification source"),\n'
        '    "proxy": ("orange", "Advisory comparator (proxy) \\u2014 not ingestion provenance"),\n'
        '}\n'
        '\n'
        '\n'
        '@st.cache_resource\n'
        'def get_connection():\n'
        '    return duckdb.connect(DB_PATH, read_only=True)\n'
        '\n'
        '\n'
        'def load_scorecard(path: str) -> dict | None:\n'
        '    p = Path(path)\n'
        '    if p.exists():\n'
        '        return json.loads(p.read_text())\n'
        '    return None\n'
        '\n'
        '\n'
        'def load_ads_data():\n'
        '    try:\n'
        '        conn = get_connection()\n'
        '        df = conn.execute(\n'
        f'            f"SELECT {select_clause} FROM {{ADS_TABLE}} ORDER BY calendar_date"\n'
        '        ).fetchdf()\n'
        '        return df\n'
        '    except Exception:\n'
        '        return None\n'
        '\n'
        '\n'
        'def render_link_badge(link_status: str) -> None:\n'
        '    color, label = LINK_STATUS_LABELS.get(\n'
        '        link_status, ("gray", f"Status: {link_status}")\n'
        '    )\n'
        '    st.caption(f":{color}_circle: {label}")\n'
        '\n'
        '\n'
        'def render_error_badge() -> None:\n'
        '    st.caption(":gray_circle: Data unavailable \\u2014 check database connection")\n'
        '\n'
        '\n'
        'def section_mode_banner():\n'
        '    if IS_FIXTURE_MODE:\n'
        '        st.warning("FIXTURE/DEMO MODE \\u2014 Static seed data, not live ingestion.")\n'
        '    st.title(f"{MART_NAME} Dashboard")\n'
        '    st.caption(f"Database: {DB_PATH}")\n'
        '\n'
        '\n'
        'def section_dqc_scorecard():\n'
        '    st.header("Data Quality Scorecard")\n'
        '    scorecard = load_scorecard(DQC_SCORECARD_PATH)\n'
        '    if not scorecard:\n'
        '        st.warning("Scorecard not found. Run `dbt test` then `dqc-update`.")\n'
        '        return\n'
        '    controls = scorecard.get("controls", [])\n'
        '    if not controls:\n'
        '        st.info("No DQC controls recorded. Run the DQC pipeline.")\n'
        '        return\n'
        '    cols = st.columns(min(len(controls), 4))\n'
        '    for i, ctrl in enumerate(controls):\n'
        '        status = ctrl.get("status", "unknown")\n'
        '        color = {"pass": "green", "fail": "red", "exhausted": "orange"}.get(status, "gray")\n'
        '        with cols[i % len(cols)]:\n'
        "            st.markdown(f\":{color}_circle: **{ctrl.get('class', '?')}**\")\n"
        "            st.caption(f\"{ctrl.get('metric', '?')}: {status}\")\n"
        '            if status == "exhausted" and "attempts" in ctrl:\n'
        '                with st.expander("Resource exhaustion evidence"):\n'
        '                    for a in ctrl["attempts"]:\n'
        "                        st.text(f\"  {a.get('source','?')}: {a.get('result','?')} \\u2014 {a.get('reason','?')}\")\n"
        '\n'
        '\n'
        'def section_metric_cards(ads_df):\n'
        '    st.header("Metrics Overview")\n'
        '    if not CONTRACTED_METRICS:\n'
        '        st.info("No contracted metrics defined.")\n'
        '        return\n'
        '    data_available = ads_df is not None and not ads_df.empty\n'
        '    cols = st.columns(len(CONTRACTED_METRICS))\n'
        '    for i, metric in enumerate(CONTRACTED_METRICS):\n'
        '        with cols[i]:\n'
        "            label = f\"{metric['name']} ({metric['id']})\"\n"
        '            ads_col = metric.get("ads_column", "")\n'
        '            link_status = metric.get("link_status", "")\n'
        '            if data_available and ads_col and ads_col in ads_df.columns:\n'
        '                value = ads_df[ads_col].sum()\n'
        '                st.metric(label=label, value=f"{value:,.2f}")\n'
        '                render_link_badge(link_status)\n'
        '            else:\n'
        '                st.metric(label=label, value="\\u2014")\n'
        '                render_error_badge()\n'
        '    if not data_available:\n'
        '        st.info("Run `dbt seed && dbt run` to populate metrics from the ADS table.")\n'
        '\n'
        '\n'
        'def section_visualizations(ads_df):\n'
        '    st.header("Metric Trends")\n'
        '    if ads_df is None or ads_df.empty:\n'
        '        st.info("No trend data available. Run `dbt seed && dbt run` first.")\n'
        '        return\n'
        '    plotted = False\n'
        '    for viz in VISUALIZATION_DEFS:\n'
        '        y_col = viz.get("y_column", "")\n'
        '        x_col = viz.get("x_column", "calendar_date")\n'
        '        chart_type = viz.get("chart_type", "line")\n'
        '        title = viz.get("title", y_col)\n'
        '        if y_col not in ads_df.columns or x_col not in ads_df.columns:\n'
        '            continue\n'
        '        st.subheader(title)\n'
        '        mid = viz.get("metric_id", "")\n'
        '        matched = [m for m in CONTRACTED_METRICS if m["id"] == mid]\n'
        '        if matched:\n'
        '            render_link_badge(matched[0].get("link_status", ""))\n'
        '        chart_data = ads_df.set_index(x_col)[[y_col]]\n'
        '        if chart_type == "bar":\n'
        '            st.bar_chart(chart_data)\n'
        '        elif chart_type == "area":\n'
        '            st.area_chart(chart_data)\n'
        '        else:\n'
        '            st.line_chart(chart_data)\n'
        '        plotted = True\n'
        '    if not plotted:\n'
        '        st.info("No contracted metrics available for trend display.")\n'
        '\n'
        '\n'
        'def section_provenance():\n'
        '    st.header("Data Provenance")\n'
        '    st.markdown(\n'
        '        "| Field | Description |\\n"\n'
        '        "|-------|------------|\\n"\n'
        '        "| `provider` | Data source identifier |\\n"\n'
        '        "| `pull_ts_utc` | When ingestion ran |\\n"\n'
        '        "| `quote_ts_utc` | Source data timestamp |\\n"\n'
        '        "| `run_id` | Pipeline run trace |"\n'
        '    )\n'
        '\n'
        '\n'
        'def main():\n'
        '    st.set_page_config(page_title=f"{MART_NAME} Dashboard", layout="wide")\n'
        '    section_mode_banner()\n'
        '    section_dqc_scorecard()\n'
        '    ads_df = load_ads_data()\n'
        '    section_metric_cards(ads_df)\n'
        '    section_visualizations(ads_df)\n'
        '    section_provenance()\n'
        '\n'
        '\n'
        'if __name__ == "__main__":\n'
        '    main()\n'
    )


def _scaffold_general(mart_dir: Path, mart_name: str, prefix: str) -> dict:
    """General contract-driven scaffold requiring impl_contract.yml."""
    gate_errors = _check_gates(mart_dir)
    if gate_errors:
        return {"success": False, "errors": gate_errors, "files_created": []}

    brd_path = mart_dir / "brd.md"
    tdd_path = mart_dir / "tdd.md"

    proxy_errors = []
    if not _has_proxy_stamp(brd_path):
        proxy_errors.append(
            "BRD missing [ARGENT-PROXY <ISO timestamp>] approval stamp. "
            "General scaffold requires proxy approval in both BRD and TDD."
        )
    if not _has_proxy_stamp(tdd_path):
        proxy_errors.append(
            "TDD missing [ARGENT-PROXY <ISO timestamp>] approval stamp. "
            "General scaffold requires proxy approval in both BRD and TDD."
        )
    if proxy_errors:
        return {"success": False, "errors": proxy_errors, "files_created": []}

    brd_metrics = _parse_brd_metrics(brd_path)
    ads_map = _parse_ads_metric_map(tdd_path)

    impl_contract = _load_impl_contract(mart_dir)
    contract_errors = _validate_impl_contract(
        impl_contract, brd_metrics, ads_map, mart_dir
    )
    if contract_errors:
        return {"success": False, "errors": contract_errors, "files_created": []}

    resource_root = get_resource_root()
    templates_dir = resource_root / "templates"
    scripts_dir = resource_root / "scripts"
    files_created: list[str] = []

    safe_name = _sanitize_name(mart_name)
    models_def = impl_contract["models"]
    contract_metrics_raw = impl_contract["metrics"]
    viz_defs = impl_contract["visualizations"]

    contract_metrics = []
    for cm in contract_metrics_raw:
        mid = cm["id"]
        brd_match = next((m for m in brd_metrics if m["id"] == mid), None)
        contract_metrics.append({
            "id": mid,
            "name": cm.get("name", brd_match["name"] if brd_match else mid),
            "source_type": brd_match["source_type"] if brd_match else cm.get("source_type", ""),
            "link_status": brd_match["link_status"] if brd_match else cm.get("link_status", ""),
            "ads_column": cm["ads_column"],
        })

    contract_json = {
        "mart": {"name": mart_name, "prefix": prefix, "version": "1.0"},
        "metrics": contract_metrics,
        "fixture": {"enabled": False},
        "visualizations": viz_defs,
    }
    contract_path = mart_dir / "mart_contract.json"
    contract_path.write_text(json.dumps(contract_json, indent=2))
    files_created.append("mart_contract.json")

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

    # Model SQL files — copy user-supplied SQL from contract
    for layer in ("ods", "dwd", "dws", "ads"):
        layer_def = models_def[layer]
        model_name = layer_def["name"]
        layer_dir = mart_dir / "models" / layer
        layer_dir.mkdir(parents=True, exist_ok=True)

        sql_path = layer_def.get("sql_path")
        sql_inline = layer_def.get("sql")
        if sql_path:
            sql_content = (mart_dir / sql_path).read_text()
        else:
            sql_content = sql_inline

        target_file = layer_dir / f"{model_name}.sql"
        target_file.write_text(sql_content)
        files_created.append(f"models/{layer}/{model_name}.sql")

    # DIM model — framework-provided, always included
    dim_def = models_def.get("dim", {})
    dim_name = dim_def.get("name", f"{prefix}_dim_date")
    dim_dir = mart_dir / "models" / "dim"
    dim_dir.mkdir(parents=True, exist_ok=True)
    dim_template = templates_dir / "models" / "dim" / "template.sql"
    if dim_template.exists():
        dim_content = dim_template.read_text()
        (dim_dir / f"{dim_name}.sql").write_text(dim_content)
        files_created.append(f"models/dim/{dim_name}.sql")

    # Seeds — dim_date always included; user seeds from contract
    seeds_dir = mart_dir / "seeds"
    seeds_dir.mkdir(exist_ok=True)
    dim_date_seed = templates_dir / "seeds" / "dim_date.csv"
    if dim_date_seed.exists():
        shutil.copy2(dim_date_seed, seeds_dir / "dim_date.csv")
        files_created.append("seeds/dim_date.csv")

    for seed_def in impl_contract.get("seeds", []):
        seed_path = seed_def.get("path", "")
        if seed_path and (mart_dir / seed_path).exists():
            src = mart_dir / seed_path
            dst = seeds_dir / src.name
            if src.resolve() != dst.resolve():
                shutil.copy2(src, dst)
            files_created.append(f"seeds/{src.name}")

    # Tests
    tests_dir = mart_dir / "tests"
    tests_dir.mkdir(exist_ok=True)
    ods_model = models_def["ods"]["name"]
    test_content = (
        f"-- Validates: no duplicate primary keys in ODS\n"
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

    # schema.yml — contract-driven
    ads_model_name = models_def["ads"]["name"]
    dws_model_name = models_def["dws"]["name"]
    dwd_model_name = models_def["dwd"]["name"]
    ods_model_name = models_def["ods"]["name"]
    schema_lines = [
        "version: 2\n",
        "models:",
        f"  - name: {ods_model_name}",
        f"    description: 'ODS layer — raw ingestion'",
        f"    columns:",
        f"      - name: record_id",
        f"        data_tests:",
        f"          - not_null",
        f"      - name: pull_date",
        f"        data_tests:",
        f"          - not_null\n",
        f"  - name: {dim_name}",
        f"    description: 'Date dimension (seed-backed)'",
        f"    columns:",
        f"      - name: date_sk",
        f"        data_tests:",
        f"          - not_null\n",
        f"  - name: {dwd_model_name}",
        f"    description: 'DWD fact layer'",
        f"    columns:",
        f"      - name: date_key",
        f"        data_tests:",
        f"          - not_null",
        f"          - relationships:",
        f"              arguments:",
        f"                to: ref('{dim_name}')",
        f"                field: date_sk\n",
        f"  - name: {dws_model_name}",
        f"    description: 'DWS aggregation layer'",
        f"    columns:",
        f"      - name: date_key",
        f"        data_tests:",
        f"          - not_null",
    ]
    for cm in contract_metrics:
        col = cm.get("ads_column", "")
        if col:
            schema_lines.append(f"      - name: {col}")
            schema_lines.append(f"        data_tests:")
            schema_lines.append(f"          - not_null")
    schema_lines.append("")
    schema_lines.append(f"  - name: {ads_model_name}")
    schema_lines.append(f"    description: 'ADS — presentation layer'")
    schema_lines.append(f"    columns:")
    schema_lines.append(f"      - name: calendar_date")
    schema_lines.append(f"        data_tests:")
    schema_lines.append(f"          - not_null")
    for cm in contract_metrics:
        col = cm.get("ads_column", "")
        if col:
            schema_lines.append(f"      - name: {col}")
            schema_lines.append(f"        data_tests:")
            schema_lines.append(f"          - not_null")
    schema_lines.append("")
    schema_lines.append("seeds:")
    schema_lines.append("  - name: dim_date")
    schema_lines.append("    description: 'Calendar seed with business day flags'")
    for seed_def in impl_contract.get("seeds", []):
        sname = seed_def.get("name", "")
        if sname:
            schema_lines.append(f"  - name: {sname}")
            schema_lines.append(f"    description: 'User-supplied seed data'")
    schema_lines.append("")

    schema = mart_dir / "models" / "schema.yml"
    schema.write_text("\n".join(schema_lines))
    files_created.append("models/schema.yml")

    # Dashboard — generated from contract visualization definitions
    dash_dir = mart_dir / "dashboard"
    dash_dir.mkdir(exist_ok=True)
    dash_content = _generate_general_dashboard(
        mart_name, safe_name, ads_model_name, contract_metrics, viz_defs,
    )
    (dash_dir / "app.py").write_text(dash_content)
    files_created.append("dashboard/app.py")

    (dash_dir / "requirements.txt").write_text("streamlit>=1.30\nduckdb>=0.10\n")
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
