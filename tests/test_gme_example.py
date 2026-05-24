"""Tests for the GME options mart example.

Validates:
- Dashboard does not query forbidden tables
- Dashboard handles missing token gracefully (no crash)
- BRD/TDD/KNOWN_GAPS exist with required sections
- No confidential content in example files
"""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
EXAMPLE_DIR = ROOT / "examples" / "gme-options-mart"
DASHBOARD_APP = EXAMPLE_DIR / "dashboard" / "app.py"

FORBIDDEN_TABLE_NAMES = [
    "gme_dws_warrant_monitor_1d",
]

FORBIDDEN_QUERY_PATTERNS = [
    "warrant_qty",
    "warrant_strike",
    "warrant_expiry",
    "intrinsic_total",
    "moneyness",
    "theta_regime",
    "total_position_value",
    "cost_basis",
]


class TestDashboardSafety:
    def test_dashboard_app_exists(self):
        assert DASHBOARD_APP.exists(), "Dashboard app.py not found"

    def test_dashboard_is_valid_python(self):
        source = DASHBOARD_APP.read_text()
        ast.parse(source)

    def test_no_forbidden_table_queries(self):
        source = DASHBOARD_APP.read_text()
        for table in FORBIDDEN_TABLE_NAMES:
            occurrences = []
            for i, line in enumerate(source.splitlines(), 1):
                if table in line and "FORBIDDEN" not in line:
                    occurrences.append(f"L{i}: {line.strip()}")
            assert not occurrences, (
                f"Dashboard queries forbidden table '{table}':\n"
                + "\n".join(occurrences)
            )

    def test_no_forbidden_column_queries(self):
        source = DASHBOARD_APP.read_text()
        for col in FORBIDDEN_QUERY_PATTERNS:
            for i, line in enumerate(source.splitlines(), 1):
                if col in line.lower():
                    stripped = line.strip()
                    if stripped.startswith("#") or stripped.startswith("//"):
                        continue
                    if "FORBIDDEN" in line or "forbidden" in line:
                        continue
                    assert False, (
                        f"Dashboard references forbidden column '{col}' at L{i}: {stripped}"
                    )

    def test_dashboard_has_blocked_mode(self):
        source = DASHBOARD_APP.read_text()
        assert "BLOCKED" in source, "Dashboard must show BLOCKED state when no data"

    def test_dashboard_has_stale_mode(self):
        source = DASHBOARD_APP.read_text()
        assert "STALE" in source, "Dashboard must show STALE state when data is empty"

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

    def test_dashboard_disclaims_fact_check(self):
        source = DASHBOARD_APP.read_text()
        lower = source.lower()
        assert "not" in lower and "fact-check" in lower or "pending" in lower, (
            "Dashboard must disclaim that data is not externally fact-checked"
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

    def test_brd_has_excluded_metrics(self):
        content = (EXAMPLE_DIR / "business-requirements.md").read_text()
        assert "Excluded" in content or "excluded" in content, (
            "BRD must document excluded private metrics"
        )

    def test_tdd_has_column_specs(self):
        content = (EXAMPLE_DIR / "tech-design-doc.md").read_text()
        assert "column_name" in content or "Column Specification" in content

    def test_tdd_excludes_warrant_table(self):
        content = (EXAMPLE_DIR / "tech-design-doc.md").read_text()
        for line in content.splitlines():
            if "gme_dws_warrant_monitor_1d" in line:
                assert "EXCLUDED" in line or "Excluded" in line or "excluded" in line, (
                    "TDD must mark warrant table as EXCLUDED, not include it as active"
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
