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
        assert "column_name" in content
        assert "data_type" in content
        assert "definition" in content
        assert "example_value" in content
        assert "calculation" in content
        assert "data_source" in content

    def test_has_ods_contract_fields(self):
        content = (ROOT / "templates" / "tech-design-doc.template.md").read_text()
        for field in ["Grain", "Logical Partition", "Incremental Strategy", "Unique Key", "Backfill", "Restatement", "Provenance"]:
            assert field in content, f"TDD template missing ODS contract field: {field}"

    def test_has_idempotence_reference(self):
        content = (ROOT / "templates" / "tech-design-doc.template.md").read_text()
        assert "idempoten" in content.lower()


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
