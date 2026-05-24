"""Framework structure validation tests.

Verifies that all required files, templates, skills, and documentation
exist and contain the mandatory content for Phase F acceptance.
"""

from pathlib import Path

ROOT = Path(__file__).parent.parent


class TestRequiredFiles:
    def test_readme_exists(self):
        assert (ROOT / "README.md").exists()

    def test_claude_md_exists(self):
        assert (ROOT / "CLAUDE.md").exists()

    def test_spec_exists(self):
        assert (ROOT / "SPEC.md").exists()

    def test_methodology_exists(self):
        assert (ROOT / "METHODOLOGY.md").exists()

    def test_license_exists(self):
        assert (ROOT / "LICENSE").exists()

    def test_pyproject_exists(self):
        assert (ROOT / "pyproject.toml").exists()

    def test_plugin_manifest_exists(self):
        assert (ROOT / ".claude-plugin" / "plugin.json").exists()

    def test_hooks_json_exists(self):
        assert (ROOT / "hooks" / "hooks.json").exists()

    def test_gitignore_exists(self):
        assert (ROOT / ".gitignore").exists()


class TestTemplates:
    def test_mart_yml_template(self):
        assert (ROOT / "templates" / "mart.yml.template").exists()

    def test_brd_template(self):
        assert (ROOT / "templates" / "business-requirements.template.md").exists()

    def test_tdd_template(self):
        assert (ROOT / "templates" / "tech-design-doc.template.md").exists()

    def test_ods_model_template(self):
        assert (ROOT / "templates" / "models" / "ods" / "template.sql").exists()

    def test_dim_model_template(self):
        assert (ROOT / "templates" / "models" / "dim" / "template.sql").exists()

    def test_dwd_model_template(self):
        assert (ROOT / "templates" / "models" / "dwd" / "template.sql").exists()

    def test_dws_model_template(self):
        assert (ROOT / "templates" / "models" / "dws" / "template.sql").exists()

    def test_ads_model_template(self):
        assert (ROOT / "templates" / "models" / "ads" / "template.sql").exists()

    def test_dim_date_seed(self):
        assert (ROOT / "templates" / "seeds" / "dim_date.csv").exists()

    def test_raw_sample_data_seed(self):
        assert (ROOT / "templates" / "seeds" / "raw_sample_data.csv").exists()

    def test_singular_test_template(self):
        assert (ROOT / "templates" / "tests" / "template_singular.sql").exists()

    def test_dashboard_template(self):
        assert (ROOT / "templates" / "dashboard" / "app.py").exists()

    def test_pipeline_template(self):
        assert (ROOT / "templates" / "pipeline" / "daily.yml.template").exists()


class TestSkills:
    REQUIRED_SKILLS = [
        "using-mart-forge",
        "mart-brd",
        "mart-tdd",
        "mart-bootstrap",
        "mart-dqc",
        "dqc-audit",
        "schema-evolve",
        "mart-review",
        "source-discovery",
    ]

    def test_all_skills_exist(self):
        for skill in self.REQUIRED_SKILLS:
            skill_path = ROOT / "skills" / skill / "SKILL.md"
            assert skill_path.exists(), f"Missing skill: {skill}"


class TestDocumentation:
    REQUIRED_DOCS = [
        "bus-matrix.md",
        "dqc-framework.md",
        "naming-conventions.md",
        "agent-orchestration.md",
        "provider-abstraction.md",
    ]

    def test_all_docs_exist(self):
        for doc in self.REQUIRED_DOCS:
            doc_path = ROOT / "docs" / doc
            assert doc_path.exists(), f"Missing doc: {doc}"


class TestBRDTemplateSections:
    def test_has_all_mandatory_sections(self):
        content = (ROOT / "templates" / "business-requirements.template.md").read_text()
        for section in ["B-1", "B-2", "B-3", "B-4"]:
            assert section in content, f"BRD template missing section {section}"

    def test_has_source_type_guidance(self):
        content = (ROOT / "templates" / "business-requirements.template.md").read_text()
        assert "native" in content
        assert "derived" in content
        assert "hybrid" in content

    def test_has_link_status_guidance(self):
        content = (ROOT / "templates" / "business-requirements.template.md").read_text()
        assert "exact" in content
        assert "proxy" in content
        assert "unsupported" in content
        assert "unverified" in content

    def test_has_link_verification_table(self):
        content = (ROOT / "templates" / "business-requirements.template.md").read_text()
        assert "candidate_result" in content.lower() or "Candidate Result" in content


class TestTDDTemplateSections:
    def test_has_all_mandatory_sections(self):
        content = (ROOT / "templates" / "tech-design-doc.template.md").read_text()
        for i in range(1, 18):
            section = f"T-{i}"
            assert section in content, f"TDD template missing section {section}"

    def test_has_six_column_physical_design(self):
        content = (ROOT / "templates" / "tech-design-doc.template.md").read_text()
        for col in ["column_name", "data_type", "definition", "example_value", "calculation", "data_source"]:
            assert col in content, f"TDD template missing column spec field: {col}"

    def test_has_ods_contract_fields(self):
        content = (ROOT / "templates" / "tech-design-doc.template.md").read_text()
        for field in ["Grain", "Logical Partition", "Incremental Strategy", "Unique Key",
                       "Backfill", "Restatement", "Provenance"]:
            assert field in content, f"TDD template missing ODS contract field: {field}"

    def test_has_idempotence_reference(self):
        content = (ROOT / "templates" / "tech-design-doc.template.md").read_text()
        assert "idempoten" in content.lower()

    def test_t7_has_full_column_spec(self):
        content = (ROOT / "templates" / "tech-design-doc.template.md").read_text()
        t7_start = content.find("## T-7")
        t8_start = content.find("## T-8")
        assert t7_start > 0 and t8_start > t7_start
        t7_section = content[t7_start:t8_start]
        assert "column_name" in t7_section, "T-7 missing full column spec table"
        assert "calculation" in t7_section, "T-7 missing calculation column"
        assert "not_applicable" in t7_section, "T-7 missing N/A rationale provision"

    def test_t8_has_full_column_spec_with_source_type(self):
        content = (ROOT / "templates" / "tech-design-doc.template.md").read_text()
        t8_start = content.find("## T-8")
        t9_start = content.find("## T-9")
        assert t8_start > 0 and t9_start > t8_start
        t8_section = content[t8_start:t9_start]
        assert "column_name" in t8_section, "T-8 missing full column spec table"
        assert "source_type" in t8_section, "T-8 missing source_type classification"
        assert "native" in t8_section, "T-8 missing native source_type"
        assert "derived" in t8_section, "T-8 missing derived source_type"
        assert "provenance" in t8_section.lower(), "T-8 missing provenance columns"

    def test_t9_has_full_column_spec(self):
        content = (ROOT / "templates" / "tech-design-doc.template.md").read_text()
        t9_start = content.find("## T-9")
        t10_start = content.find("## T-10")
        assert t9_start > 0 and t10_start > t9_start
        t9_section = content[t9_start:t10_start]
        assert "column_name" in t9_section, "T-9 missing full column spec table"
        assert "calculation" in t9_section, "T-9 missing calculation column"

    def test_t10_has_full_column_spec(self):
        content = (ROOT / "templates" / "tech-design-doc.template.md").read_text()
        t10_start = content.find("## T-10")
        t11_start = content.find("## T-11")
        assert t10_start > 0 and t11_start > t10_start
        t10_section = content[t10_start:t11_start]
        assert "column_name" in t10_section, "T-10 missing full column spec table"
        assert "calculation" in t10_section, "T-10 missing calculation column"

    def test_t11_has_full_column_spec_with_traceability(self):
        content = (ROOT / "templates" / "tech-design-doc.template.md").read_text()
        t11_start = content.find("## T-11")
        t12_start = content.find("## T-12")
        assert t11_start > 0 and t12_start > t11_start
        t11_section = content[t11_start:t12_start]
        assert "column_name" in t11_section, "T-11 missing full column spec table"
        assert "BRD" in t11_section, "T-11 missing BRD traceability"
        assert "link_status" in t11_section.lower() or "Link Status" in t11_section, \
            "T-11 missing link_status in traceability"

    def test_t6_has_column_spec_and_ods_contract(self):
        content = (ROOT / "templates" / "tech-design-doc.template.md").read_text()
        t6_start = content.find("## T-6")
        t7_start = content.find("## T-7")
        assert t6_start > 0 and t7_start > t6_start
        t6_section = content[t6_start:t7_start]
        assert "column_name" in t6_section, "T-6 missing column spec table"
        assert "calculation" in t6_section, "T-6 missing calculation column"
        assert "Grain" in t6_section, "T-6 missing ODS contract Grain"
        assert "Incremental Strategy" in t6_section, "T-6 missing ODS contract Incremental Strategy"
        assert "Unique Key" in t6_section, "T-6 missing ODS contract Unique Key"
        assert "Provenance" in t6_section, "T-6 missing ODS contract Provenance"
        assert "not_applicable" in t6_section, "T-6 missing N/A rationale provision"

    def test_all_table_sections_have_not_applicable_provision(self):
        content = (ROOT / "templates" / "tech-design-doc.template.md").read_text()
        for section_label in ["T-6", "T-7", "T-8", "T-9", "T-10", "T-11"]:
            start = content.find(f"## {section_label}")
            next_num = int(section_label.split("-")[1]) + 1
            end = content.find(f"## T-{next_num}")
            if end < 0:
                end = len(content)
            section = content[start:end]
            assert "not_applicable" in section, \
                f"{section_label} missing not_applicable rationale provision"


class TestHardGates:
    def test_bootstrap_requires_tdd(self):
        content = (ROOT / "skills" / "mart-bootstrap" / "SKILL.md").read_text()
        assert "signed-off TDD" in content or "Signed-off TDD" in content

    def test_tdd_requires_brd(self):
        content = (ROOT / "skills" / "mart-tdd" / "SKILL.md").read_text()
        assert "signed-off BRD" in content or "Signed-off BRD" in content

    def test_session_bootstrap_detects_phases(self):
        content = (ROOT / "skills" / "using-mart-forge" / "SKILL.md").read_text()
        assert "Phase" in content
        assert "BRD" in content
        assert "TDD" in content


class TestModelTemplates:
    @staticmethod
    def _code_lines(content: str) -> list[str]:
        lines = []
        in_jinja_comment = False
        for raw in content.splitlines():
            stripped = raw.strip()
            if "{#" in stripped:
                in_jinja_comment = True
            if in_jinja_comment:
                if "#}" in stripped:
                    in_jinja_comment = False
                continue
            if not stripped or stripped.startswith("--") or stripped.startswith("{"):
                continue
            lines.append(stripped)
        return lines

    def test_no_select_star_in_ods(self):
        content = (ROOT / "templates" / "models" / "ods" / "template.sql").read_text()
        for line in self._code_lines(content):
            assert "select *" not in line.lower(), f"ODS template uses SELECT *: {line}"

    def test_no_select_star_in_dim(self):
        content = (ROOT / "templates" / "models" / "dim" / "template.sql").read_text()
        for line in self._code_lines(content):
            assert "select *" not in line.lower(), f"DIM template uses SELECT *: {line}"

    def test_no_select_star_in_dwd(self):
        content = (ROOT / "templates" / "models" / "dwd" / "template.sql").read_text()
        for line in self._code_lines(content):
            assert "select *" not in line.lower(), f"DWD template uses SELECT *: {line}"

    def test_no_select_star_in_dws(self):
        content = (ROOT / "templates" / "models" / "dws" / "template.sql").read_text()
        for line in self._code_lines(content):
            assert "select *" not in line.lower(), f"DWS template uses SELECT *: {line}"

    def test_no_select_star_in_ads(self):
        content = (ROOT / "templates" / "models" / "ads" / "template.sql").read_text()
        for line in self._code_lines(content):
            assert "select *" not in line.lower(), f"ADS template uses SELECT *: {line}"

    def test_dwd_no_dbt_utils_dependency(self):
        content = (ROOT / "templates" / "models" / "dwd" / "template.sql").read_text()
        assert "dbt_utils" not in content, "DWD template depends on dbt_utils"


class TestScripts:
    def test_dqc_update_exists(self):
        assert (ROOT / "scripts" / "dqc_update.py").exists()

    def test_confidentiality_scan_exists(self):
        assert (ROOT / "scripts" / "confidentiality_scan.py").exists()

    def test_validate_templates_exists(self):
        assert (ROOT / "scripts" / "validate_templates.py").exists()


class TestCI:
    def test_framework_ci_exists(self):
        assert (ROOT / ".github" / "workflows" / "framework-ci.yml").exists()
