"""
mart-forge scaffold — Generate a dbt project from a signed BRD/TDD and
implementation contract (mart.yml).

Enforces structural contract validation:
- BRD must have all mandatory sections (B-1..B-4) with populated metric catalog
- TDD must have all mandatory sections (T-1..T-17) with per-layer column specs
- Grade A and proxy stamp required; Grade B and below rejected
- No unverified link_status at sign-off
- Each metric must declare valid source_type and resolved link_status
- Bare heading vocabulary and bare N/A tokens rejected
- Required layers (ODS/DWD/ADS) must have populated column specs — N/A rejected
- T-3/T-12/T-14/T-16 must have substantive content (not token text)
- BRD metric-to-ADS mapping validated for completeness and link_status consistency
- mart.yml implementation contract required: SQL bindings, metric columns, visualizations
- Dashboard visualizations bound to signed contract specification
- Smoke fixture explicitly separated from general domain-neutral scaffold path
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
VALID_CHART_TYPES = {"line_chart", "bar_chart"}

TABLE_SECTIONS = {
    "T-6": {"label": "ODS", "extra": ["Grain", "Incremental Strategy", "Unique Key", "Provenance"]},
    "T-7": {"label": "DIM", "extra": []},
    "T-8": {"label": "DWD", "extra": ["source_type", "provenance"]},
    "T-9": {"label": "DWS-Count", "extra": []},
    "T-10": {"label": "DWS-Perf", "extra": []},
    "T-11": {"label": "ADS", "extra": ["BRD"]},
}

REQUIRED_LAYER_SECTIONS = {"T-6", "T-8", "T-11"}

CONTENT_SECTIONS = {
    "T-3": "Table Summary",
    "T-12": "Physical Design",
    "T-14": "DQC Plan",
    "T-16": "Operations",
}

SMOKE_FIXTURE_LAYERS = {
    "ods": {"model": "{prefix}_ods_csv_sample", "sql": "sql/ods.sql"},
    "dim": {"model": "{prefix}_dim_date", "sql": "sql/dim.sql"},
    "dwd": {"model": "{prefix}_dwd_daily_sample_di", "sql": "sql/dwd.sql"},
    "dws": {"model": "{prefix}_dws_daily_revenue_1d", "sql": "sql/dws.sql"},
    "ads": {"model": "{prefix}_ads_exec_dashboard", "sql": "sql/ads.sql"},
}


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
    content = doc_path.read_text()
    return bool(re.search(r"Proxy:\s*\S+", content))


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

    if not _has_proxy_stamp(brd_path):
        errors.append("BRD missing proxy approval stamp. Require Proxy: <stamp>.")

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
        header_keywords = {"metric", "source_type", "link_status", "definition"}
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

    if not _has_proxy_stamp(tdd_path):
        errors.append("TDD missing proxy approval stamp. Require Proxy: <stamp>.")

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


def _load_mart_yml(mart_dir: Path) -> tuple[dict | None, list[str]]:
    mart_yml_path = mart_dir / "mart.yml"
    errors = []
    if not mart_yml_path.exists():
        return None, [
            "mart.yml not found. Create an implementation contract binding "
            "signed BRD/TDD to SQL templates and dashboard visualizations."
        ]

    try:
        data = yaml.safe_load(mart_yml_path.read_text())
    except yaml.YAMLError as e:
        return None, [f"mart.yml is not valid YAML: {e}"]

    if not isinstance(data, dict):
        return None, ["mart.yml must be a YAML mapping."]

    for key in ("version", "layers", "metrics", "dashboard"):
        if key not in data:
            errors.append(f"mart.yml missing required key '{key}'.")

    if errors:
        return None, errors

    layers = data.get("layers", {})
    if not isinstance(layers, dict):
        errors.append("mart.yml 'layers' must be a mapping.")
    else:
        for layer_key in ("ods", "dim", "dwd", "dws", "ads"):
            if layer_key not in layers:
                errors.append(f"mart.yml missing required layer '{layer_key}'.")
                continue
            layer = layers[layer_key]
            if not isinstance(layer, dict):
                errors.append(f"mart.yml layer '{layer_key}' must be a mapping.")
                continue
            if "model" not in layer:
                errors.append(f"mart.yml layer '{layer_key}' missing 'model' name.")
            if "sql" not in layer:
                errors.append(f"mart.yml layer '{layer_key}' missing 'sql' template path.")
            elif not (mart_dir / layer["sql"]).exists():
                errors.append(
                    f"mart.yml layer '{layer_key}' SQL template not found: {layer['sql']}"
                )

    metrics = data.get("metrics", [])
    if not isinstance(metrics, list) or len(metrics) == 0:
        errors.append("mart.yml 'metrics' must be a non-empty list.")
    else:
        for m in metrics:
            if not isinstance(m, dict):
                errors.append("mart.yml metric entry must be a mapping.")
                continue
            if "id" not in m:
                errors.append("mart.yml metric missing 'id' field.")
            if "ads_column" not in m:
                errors.append(f"mart.yml metric {m.get('id', '?')} missing 'ads_column' field.")

    dashboard = data.get("dashboard", {})
    if not isinstance(dashboard, dict):
        errors.append("mart.yml 'dashboard' must be a mapping.")
    else:
        visualizations = dashboard.get("visualizations", [])
        if not isinstance(visualizations, list) or len(visualizations) == 0:
            errors.append("mart.yml dashboard must have at least one visualization.")
        else:
            metric_ids = {m.get("id") for m in metrics if isinstance(m, dict)}
            for viz in visualizations:
                if not isinstance(viz, dict):
                    errors.append("mart.yml visualization entry must be a mapping.")
                    continue
                if "metric_id" not in viz:
                    errors.append("mart.yml visualization missing 'metric_id'.")
                elif viz["metric_id"] not in metric_ids:
                    errors.append(
                        f"mart.yml visualization references unknown metric '{viz['metric_id']}'."
                    )
                if "chart_type" not in viz:
                    errors.append("mart.yml visualization missing 'chart_type'.")
                elif viz["chart_type"] not in VALID_CHART_TYPES:
                    errors.append(
                        f"mart.yml visualization has invalid chart_type '{viz['chart_type']}' "
                        f"— must be one of {sorted(VALID_CHART_TYPES)}."
                    )
                if "title" not in viz:
                    errors.append("mart.yml visualization missing 'title'.")

    return data, errors


def _validate_mart_yml_bindings(
    mart_yml: dict, brd_metrics: list[dict], ads_map: dict,
) -> list[str]:
    errors = []
    yml_metrics = mart_yml.get("metrics", [])
    brd_ids = {m["id"] for m in brd_metrics}
    ads_columns = {v.get("column", "") for v in ads_map.values()}

    for m in yml_metrics:
        mid = m.get("id", "")
        if mid and mid not in brd_ids:
            errors.append(f"mart.yml metric '{mid}' not found in BRD B-3 metric catalog.")
        ads_col = m.get("ads_column", "")
        if ads_col and ads_col not in ads_columns:
            errors.append(
                f"mart.yml metric '{mid}' ads_column '{ads_col}' "
                f"not found in TDD T-11 ADS column spec."
            )

    yml_ids = {m.get("id") for m in yml_metrics}
    for m in brd_metrics:
        if m["id"] not in yml_ids:
            errors.append(
                f"BRD metric {m['id']} ({m['name']}) has no binding in mart.yml."
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

    mart_yml, yml_errors = _load_mart_yml(mart_dir)
    errors.extend(yml_errors)

    if mart_yml and brd_path.exists() and tdd_path.exists():
        brd_metrics = _parse_brd_metrics(brd_path)
        ads_map = _parse_ads_metric_map(tdd_path)
        errors.extend(_validate_mart_yml_bindings(mart_yml, brd_metrics, ads_map))

    return errors


def scaffold(mart_dir: Path, mart_name: str, prefix: str) -> dict:
    """Generate a runnable dbt project from signed BRD/TDD and mart.yml contract."""
    gate_errors = _check_gates(mart_dir)
    if gate_errors:
        return {"success": False, "errors": gate_errors, "files_created": []}

    mart_yml, _ = _load_mart_yml(mart_dir)
    scripts_dir = get_resource_root() / "scripts"
    files_created = []
    safe_name = _sanitize_name(mart_name)

    brd_metrics = _parse_brd_metrics(mart_dir / "brd.md")
    ads_map = _parse_ads_metric_map(mart_dir / "tdd.md")
    layers = mart_yml["layers"]
    yml_metrics = mart_yml["metrics"]
    visualizations = mart_yml["dashboard"]["visualizations"]

    contract_metrics = []
    for m in brd_metrics:
        mid = m["id"]
        ads_info = ads_map.get(mid, {})
        yml_entry = next((ym for ym in yml_metrics if ym["id"] == mid), {})
        contract_metrics.append({
            "id": mid,
            "name": m["name"],
            "source_type": m["source_type"],
            "link_status": m["link_status"],
            "ads_column": yml_entry.get("ads_column", ads_info.get("column", "")),
        })

    is_fixture = mart_yml.get("fixture", {}).get("enabled", False)
    contract = {
        "mart": {"name": mart_name, "prefix": prefix, "version": "1.0"},
        "metrics": contract_metrics,
        "visualizations": visualizations,
    }
    if is_fixture:
        contract["fixture"] = mart_yml["fixture"]

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

    # Model SQL files — read from mart.yml-specified templates
    for layer_key, layer_spec in layers.items():
        layer_dir = mart_dir / "models" / layer_key
        layer_dir.mkdir(parents=True, exist_ok=True)
        sql_path = mart_dir / layer_spec["sql"]
        if sql_path.exists():
            content = sql_path.read_text()
            content = content.replace("{prefix}", prefix)
            model_name = layer_spec["model"].replace("{prefix}", prefix)
            target_file = layer_dir / f"{model_name}.sql"
            target_file.write_text(content)
            files_created.append(f"models/{layer_key}/{model_name}.sql")

    # Seeds — copy from mart.yml seeds or create empty dir
    seeds_dir = mart_dir / "seeds"
    seeds_dir.mkdir(exist_ok=True)
    yml_seeds = mart_yml.get("seeds", [])
    for seed_spec in yml_seeds:
        seed_file = mart_dir / seed_spec["file"]
        if seed_file.exists() and seed_file.parent != seeds_dir:
            shutil.copy2(seed_file, seeds_dir / seed_file.name)
        files_created.append(f"seeds/{seed_file.name}")

    # Tests directory with runnable singular test
    tests_dir = mart_dir / "tests"
    tests_dir.mkdir(exist_ok=True)
    ods_model = layers["ods"]["model"].replace("{prefix}", prefix)
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

    # schema.yml — generated from mart.yml model names and metric columns
    schema = mart_dir / "models" / "schema.yml"
    schema_lines = ["version: 2\n", "models:"]
    for layer_key in ("ods", "dim", "dwd", "dws", "ads"):
        model_name = layers[layer_key]["model"].replace("{prefix}", prefix)
        schema_lines.append(f"  - name: {model_name}")
        if layer_key == "ads":
            schema_lines.append(f"    description: 'ADS — executive dashboard OBT'")
            schema_lines.append(f"    columns:")
            for cm in contract_metrics:
                schema_lines.append(f"      - name: {cm['ads_column']}")
                schema_lines.append(f"        data_tests:")
                schema_lines.append(f"          - not_null")
        else:
            schema_lines.append(f"    description: '{layer_key.upper()} layer'")
    schema_lines.append("")
    if yml_seeds:
        schema_lines.append("seeds:")
        for seed_spec in yml_seeds:
            schema_lines.append(f"  - name: {seed_spec['name']}")
            schema_lines.append(f"    description: 'Seed data'")
    schema.write_text("\n".join(schema_lines) + "\n")
    files_created.append("models/schema.yml")

    # Dashboard — render template with contract metrics + visualizations
    dash_dir = mart_dir / "dashboard"
    dash_dir.mkdir(exist_ok=True)
    dash_template = get_resource_root() / "templates" / "dashboard" / "app.py"
    if dash_template.exists():
        dash_content = dash_template.read_text()
        dash_content = dash_content.replace("{mart_name}", mart_name)
        dash_content = dash_content.replace("{prefix}", prefix)
        dash_content = dash_content.replace("{db_name}", safe_name)
        dash_content = dash_content.replace(
            "{contract_metrics}", json.dumps(contract_metrics, indent=4),
        )
        dash_content = dash_content.replace(
            "{contract_visualizations}", json.dumps(visualizations, indent=4),
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
    pipeline_src = get_resource_root() / "templates" / "pipeline" / "daily.yml.template"
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


def scaffold_smoke_fixture(mart_dir: Path, mart_name: str, prefix: str) -> dict:
    """Generate the order/revenue smoke fixture for CI testing.

    Copies the framework's built-in SQL templates and seeds, generates a
    mart.yml implementation contract for the fixture domain, then delegates
    to scaffold() for the actual project generation.
    """
    resource_root = get_resource_root()
    templates_dir = resource_root / "templates"

    sql_dir = mart_dir / "sql"
    sql_dir.mkdir(parents=True, exist_ok=True)
    for layer in ("ods", "dim", "dwd", "dws", "ads"):
        src = templates_dir / "models" / layer / "template.sql"
        if src.exists():
            shutil.copy2(src, sql_dir / f"{layer}.sql")

    seeds_dir = mart_dir / "seeds"
    seeds_dir.mkdir(exist_ok=True)
    for seed_name in ("raw_sample_data.csv", "dim_date.csv"):
        src = templates_dir / "seeds" / seed_name
        if src.exists():
            shutil.copy2(src, seeds_dir / seed_name)

    mart_yml = {
        "version": "1.0",
        "layers": dict(SMOKE_FIXTURE_LAYERS),
        "metrics": [
            {"id": "M-1", "ads_column": "daily_revenue"},
            {"id": "M-2", "ads_column": "order_count"},
        ],
        "seeds": [
            {"name": "raw_sample_data", "file": "seeds/raw_sample_data.csv"},
            {"name": "dim_date", "file": "seeds/dim_date.csv"},
        ],
        "dashboard": {
            "visualizations": [
                {"metric_id": "M-1", "chart_type": "line_chart", "title": "Revenue Trend"},
                {"metric_id": "M-2", "chart_type": "line_chart", "title": "Order Volume"},
            ],
        },
        "fixture": {
            "enabled": True,
            "seed_domain": "order-revenue",
            "note": "CI smoke data only — replace with domain seeds for production",
        },
    }
    (mart_dir / "mart.yml").write_text(yaml.dump(mart_yml, default_flow_style=False))

    return scaffold(mart_dir, mart_name, prefix)
