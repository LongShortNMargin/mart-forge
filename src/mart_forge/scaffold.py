"""
mart-forge scaffold — Generate a dbt project from a signed TDD.

Enforces hard gates:
- Refuses if BRD is missing or unsigned
- Refuses if TDD is missing or unsigned
- Produces a complete generic dbt project skeleton
"""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).parent.parent.parent
TEMPLATES_DIR = FRAMEWORK_ROOT / "templates"

SIGN_OFF_MARKERS = ["Grade: A", "Grade: B", "Sign-off:", "APPROVED", "Signed"]


def _is_signed(doc_path: Path) -> bool:
    if not doc_path.exists():
        return False
    content = doc_path.read_text()
    return any(marker in content for marker in SIGN_OFF_MARKERS)


def _check_gates(mart_dir: Path) -> list[str]:
    errors = []
    brd_path = mart_dir / "brd.md"
    tdd_path = mart_dir / "tdd.md"

    if not brd_path.exists():
        errors.append("BRD not found. Create a BRD before scaffolding (Phase A gate).")
    elif not _is_signed(brd_path):
        errors.append("BRD exists but is not signed off. Get BRD approval before proceeding.")

    if not tdd_path.exists():
        errors.append("TDD not found. Create a TDD before scaffolding (Phase B gate).")
    elif not _is_signed(tdd_path):
        errors.append("TDD exists but is not signed off. Get TDD approval before proceeding.")

    return errors


def scaffold(mart_dir: Path, mart_name: str, prefix: str) -> dict:
    """Generate a dbt project skeleton in mart_dir.

    Returns a dict with 'success', 'errors', and 'files_created'.
    """
    gate_errors = _check_gates(mart_dir)
    if gate_errors:
        return {"success": False, "errors": gate_errors, "files_created": []}

    files_created = []

    # dbt_project.yml
    dbt_project = mart_dir / "dbt_project.yml"
    dbt_project.write_text(
        f"name: '{mart_name}'\n"
        f"version: '1.0.0'\n"
        f"config-version: 2\n"
        f"profile: '{mart_name}'\n"
        f"\n"
        f"model-paths: ['models']\n"
        f"seed-paths: ['seeds']\n"
        f"test-paths: ['tests']\n"
        f"analysis-paths: ['analyses']\n"
        f"macro-paths: ['macros']\n"
        f"\n"
        f"clean-targets: ['target', 'dbt_packages']\n"
    )
    files_created.append(str(dbt_project.relative_to(mart_dir)))

    # profiles.yml
    profiles = mart_dir / "profiles.yml"
    profiles.write_text(
        f"{mart_name}:\n"
        f"  target: dev\n"
        f"  outputs:\n"
        f"    dev:\n"
        f"      type: duckdb\n"
        f"      path: '{mart_name}.duckdb'\n"
        f"    ci:\n"
        f"      type: duckdb\n"
        f"      path: ':memory:'\n"
    )
    files_created.append(str(profiles.relative_to(mart_dir)))

    # Model directories
    for layer in ["ods", "dim", "dwd", "dws", "ads"]:
        layer_dir = mart_dir / "models" / layer
        layer_dir.mkdir(parents=True, exist_ok=True)
        gitkeep = layer_dir / ".gitkeep"
        gitkeep.touch()
        files_created.append(str(gitkeep.relative_to(mart_dir)))

    # Seeds directory
    seeds_dir = mart_dir / "seeds"
    seeds_dir.mkdir(exist_ok=True)
    dim_date_src = TEMPLATES_DIR / "seeds" / "dim_date.csv"
    if dim_date_src.exists():
        shutil.copy2(dim_date_src, seeds_dir / "dim_date.csv")
        files_created.append("seeds/dim_date.csv")

    # Tests directory
    tests_dir = mart_dir / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / ".gitkeep").touch()
    files_created.append("tests/.gitkeep")

    # schema.yml skeleton
    schema = mart_dir / "models" / "schema.yml"
    schema.write_text(
        f"version: 2\n"
        f"\n"
        f"models:\n"
        f"  - name: {prefix}_dim_date\n"
        f"    description: 'Date dimension (seed-backed)'\n"
        f"    columns:\n"
        f"      - name: date_sk\n"
        f"        tests:\n"
        f"          - not_null\n"
        f"          - unique\n"
        f"\n"
        f"seeds:\n"
        f"  - name: dim_date\n"
        f"    description: 'Calendar seed with business day flags'\n"
    )
    files_created.append("models/schema.yml")

    # Dashboard skeleton
    dash_dir = mart_dir / "dashboard"
    dash_dir.mkdir(exist_ok=True)

    dash_app = dash_dir / "app.py"
    dash_app.write_text(_generate_dashboard(mart_name))
    files_created.append("dashboard/app.py")

    dash_reqs = dash_dir / "requirements.txt"
    dash_reqs.write_text("streamlit>=1.30\nduckdb>=0.10\n")
    files_created.append("dashboard/requirements.txt")

    # DQC scorecard template
    scorecard = mart_dir / "dqc_scorecard.json"
    scorecard.write_text(json.dumps({
        "mart": mart_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "controls": [],
    }, indent=2))
    files_created.append("dqc_scorecard.json")

    # CI pipeline
    ci_dir = mart_dir / ".github" / "workflows"
    ci_dir.mkdir(parents=True, exist_ok=True)
    pipeline_src = TEMPLATES_DIR / "pipeline" / "daily.yml.template"
    if pipeline_src.exists():
        content = pipeline_src.read_text()
        content = content.replace("{Mart Name}", mart_name)
        content = content.replace("{cron_expression}", "0 6 * * *")
        (ci_dir / "daily.yml").write_text(content)
        files_created.append(".github/workflows/daily.yml")

    return {"success": True, "errors": [], "files_created": files_created}


def _generate_dashboard(mart_name: str) -> str:
    return f'''"""
{mart_name} Dashboard — Generated by mart-forge scaffold.

Visualization structure driven by the signed TDD dashboard specification.
Displays DQC scorecard status, data provenance, and metric cards
with link_status-aware comparison display.
"""

import json
import os
from pathlib import Path

import streamlit as st

MART_NAME = "{mart_name}"
IS_FIXTURE = os.getenv("MART_FIXTURE_MODE", "false").lower() == "true"
SCORECARD_PATH = Path("dqc_scorecard.json")


def load_scorecard() -> dict | None:
    if SCORECARD_PATH.exists():
        return json.loads(SCORECARD_PATH.read_text())
    return None


def render_link_badge(link_status: str, url: str | None = None) -> str:
    if link_status == "exact" and url:
        return f"[Exact verification source]({{url}})"
    elif link_status == "proxy" and url:
        return f"Advisory comparator (proxy) — not ingestion provenance. [Link]({{url}})"
    elif link_status == "unsupported":
        return "No external comparator — see DQC scorecard"
    return f"Status: {{link_status}}"


def main():
    st.set_page_config(page_title=f"{{MART_NAME}} Dashboard", layout="wide")

    if IS_FIXTURE:
        st.warning("FIXTURE/DEMO MODE — Static data, not live.")

    st.title(f"{{MART_NAME}} Dashboard")

    # --- DQC Scorecard Section ---
    st.header("Data Quality")
    scorecard = load_scorecard()
    if scorecard:
        controls = scorecard.get("controls", [])
        if controls:
            cols = st.columns(min(len(controls), 4))
            for i, ctrl in enumerate(controls):
                status = ctrl.get("status", "unknown")
                color = {{"pass": "green", "fail": "red", "exhausted": "orange"}}.get(status, "gray")
                with cols[i % len(cols)]:
                    st.markdown(f":{{color}}_circle: **{{ctrl.get(\'class\', \'?\')}}**")
                    st.caption(f"{{ctrl.get(\'metric\', \'?\')}}: {{status}}")
        else:
            st.info("No DQC controls recorded yet. Run `dbt test` then `dqc-update`.")
    else:
        st.warning("Scorecard not found. Run the DQC pipeline.")

    # --- Metrics Section (driven by TDD dashboard spec) ---
    st.header("Metrics")
    st.info(
        "Metric cards are generated from the signed TDD dashboard specification. "
        "Each card traces to a BRD metric and displays its link_status badge."
    )

    # --- Provenance Section ---
    st.header("Data Provenance")
    st.markdown(
        "| Field | Description |\\n"
        "|-------|------------|\\n"
        "| `provider` | Data source identifier |\\n"
        "| `pull_ts_utc` | When ingestion ran |\\n"
        "| `quote_ts_utc` | Source data timestamp |\\n"
        "| `run_id` | Pipeline run trace |"
    )


if __name__ == "__main__":
    main()
'''
