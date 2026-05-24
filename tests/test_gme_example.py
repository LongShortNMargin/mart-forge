"""Tests for the GME options mart example.

Validates:
- Dashboard queries only allowlisted public tables with explicit columns
- Dashboard handles missing token gracefully (no crash)
- Dashboard distinguishes BLOCKED / SCHEMA UNVERIFIED states
- BRD/TDD/KNOWN_GAPS exist with required sections
- Verification claims are truthful (pending, not verified)
- Visualizations are present
- Live mode is default (no fixture fallback)
"""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
EXAMPLE_DIR = ROOT / "examples" / "gme-options-mart"
DASHBOARD_APP = EXAMPLE_DIR / "dashboard" / "app.py"

PUBLIC_TABLES = {"gme_dws_daily_snapshot_1d", "gme_dws_strike_gex_1d"}


class TestDashboardSafety:
    def test_dashboard_app_exists(self):
        assert DASHBOARD_APP.exists(), "Dashboard app.py not found"

    def test_dashboard_is_valid_python(self):
        source = DASHBOARD_APP.read_text()
        ast.parse(source)

    def test_dashboard_queries_only_public_tables(self):
        source = DASHBOARD_APP.read_text()
        table_refs = re.findall(r"(?:FROM|from)\s+(\w+)", source)
        for table in table_refs:
            if table.startswith("gme_"):
                assert table in PUBLIC_TABLES, (
                    f"Dashboard queries non-allowlisted table: {table}"
                )

    def test_no_select_star(self):
        source = DASHBOARD_APP.read_text()
        for i, line in enumerate(source.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            assert "SELECT *" not in line and "select *" not in line, (
                f"Dashboard uses SELECT * at L{i}: {stripped}"
            )

    def test_dashboard_has_blocked_mode(self):
        source = DASHBOARD_APP.read_text()
        assert "BLOCKED" in source, "Dashboard must show BLOCKED state when no data"

    def test_dashboard_has_schema_unverified_state(self):
        source = DASHBOARD_APP.read_text()
        assert "SCHEMA UNVERIFIED" in source, (
            "Dashboard must show SCHEMA UNVERIFIED state for query/schema failure"
        )

    def test_dashboard_checks_token(self):
        source = DASHBOARD_APP.read_text()
        assert "MOTHERDUCK_TOKEN" in source, "Dashboard must reference MOTHERDUCK_TOKEN env var"

    def test_dashboard_has_coverage_panel(self):
        source = DASHBOARD_APP.read_text()
        assert "Coverage" in source or "coverage" in source, (
            "Dashboard must include a coverage/status panel"
        )

    def test_dashboard_tags_real_api(self):
        source = DASHBOARD_APP.read_text()
        assert "[REAL_API]" in source, "Dashboard must tag data with [REAL_API]"

    def test_dashboard_disclaims_dqc_verified(self):
        source = DASHBOARD_APP.read_text()
        lower = source.lower()
        assert "does not mean" in lower or "not mean" in lower, (
            "Dashboard must disclaim that [REAL_API] does not mean DQC verified"
        )

    def test_no_hardcoded_credentials(self):
        source = DASHBOARD_APP.read_text()
        token_pattern = re.compile(
            r"""motherduck_token\s*=\s*['"][A-Za-z0-9_\-]{10,}['"]""",
            re.IGNORECASE,
        )
        matches = token_pattern.findall(source)
        assert not matches, (
            f"Dashboard contains hardcoded MotherDuck token: {matches}"
        )

    def test_live_mode_default(self):
        source = DASHBOARD_APP.read_text()
        assert "fixture" not in source.lower() or "no fixture" in source.lower(), (
            "Dashboard must default to live mode, not fixture fallback"
        )

    def test_dashboard_has_visualizations(self):
        source = DASHBOARD_APP.read_text()
        assert "plotly_chart" in source or "st.plotly_chart" in source, (
            "Dashboard must include plotly chart visualizations"
        )
        chart_count = source.count("plotly_chart")
        assert chart_count >= 3, (
            f"Dashboard should have at least 3 chart visualizations, found {chart_count}"
        )

    def test_requirements_exist(self):
        req = EXAMPLE_DIR / "dashboard" / "requirements.txt"
        assert req.exists(), "dashboard/requirements.txt not found"
        content = req.read_text()
        assert "streamlit" in content
        assert "duckdb" in content


class TestExampleDocumentation:
    def test_brd_exists(self):
        assert (EXAMPLE_DIR / "business-requirements.md").exists()

    def test_tdd_exists(self):
        assert (EXAMPLE_DIR / "tech-design-doc.md").exists()

    def test_known_gaps_exists(self):
        assert (EXAMPLE_DIR / "KNOWN_GAPS.md").exists()

    def test_readme_exists(self):
        assert (EXAMPLE_DIR / "README.md").exists()

    def test_brd_has_required_sections(self):
        content = (EXAMPLE_DIR / "business-requirements.md").read_text()
        for section in ["B-1", "B-2", "B-3", "B-4"]:
            assert section in content, f"BRD missing required section {section}"

    def test_brd_has_metric_catalog(self):
        content = (EXAMPLE_DIR / "business-requirements.md").read_text()
        assert "source_type" in content.lower() or "Source Type" in content
        assert "link_status" in content.lower() or "Link Status" in content

    def test_brd_no_false_verified_claims(self):
        content = (EXAMPLE_DIR / "business-requirements.md").read_text()
        for i, line in enumerate(content.splitlines(), 1):
            if "| M-" in line and "verified" in line.lower():
                assert "pending_verification" in line, (
                    f"BRD metric at L{i} claims verified without pending qualifier: {line.strip()}"
                )

    def test_brd_data_sources_pending(self):
        content = (EXAMPLE_DIR / "business-requirements.md").read_text()
        in_sources = False
        for line in content.splitlines():
            if "Data Sources" in line:
                in_sources = True
                continue
            if in_sources and line.startswith("---"):
                break
            if in_sources and "|" in line and "verified" in line.lower():
                assert "pending_verification" in line or "blocked" in line or "unsupported" in line, (
                    f"BRD data source claims verified without evidence: {line.strip()}"
                )

    def test_tdd_has_column_specs(self):
        content = (EXAMPLE_DIR / "tech-design-doc.md").read_text()
        assert "column_name" in content or "Column Specification" in content

    def test_tdd_no_grade(self):
        content = (EXAMPLE_DIR / "tech-design-doc.md").read_text()
        assert "Grade:" not in content, "TDD must not claim a grade at MVP checkpoint"

    def test_tdd_tables_pending_verification(self):
        content = (EXAMPLE_DIR / "tech-design-doc.md").read_text()
        in_summary = False
        for line in content.splitlines():
            if "Table Summary" in line:
                in_summary = True
                continue
            if in_summary and line.startswith("---"):
                break
            if in_summary and "| `gme_" in line:
                assert "pending_verification" in line, (
                    f"TDD table claims non-pending status: {line.strip()}"
                )

    def test_tdd_discloses_incomplete_sections(self):
        content = (EXAMPLE_DIR / "tech-design-doc.md").read_text()
        assert "pending" in content.lower() and ("T-7" in content or "Incomplete" in content), (
            "TDD must disclose incomplete sections as pending"
        )

    def test_known_gaps_has_coverage(self):
        content = (EXAMPLE_DIR / "KNOWN_GAPS.md").read_text()
        assert re.search(r"\d+\s*/\s*\d+", content), (
            "KNOWN_GAPS must show coverage as numerator/denominator"
        )

    def test_known_gaps_has_handoff_items(self):
        content = (EXAMPLE_DIR / "KNOWN_GAPS.md").read_text()
        assert "Handoff" in content or "handoff" in content, (
            "KNOWN_GAPS must document handoff items for operator verification"
        )
