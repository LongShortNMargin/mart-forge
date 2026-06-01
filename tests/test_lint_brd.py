"""Tests for scripts.lint_brd.

Covers happy path, missing-section detection, invalid link_status, and
bypass attempts (table without headers, headers without rows).
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from scripts.lint_brd import lint


GOOD_BRD = textwrap.dedent(
    """
    # BRD: example-mart

    ## B-1: Version History

    | Version | Date | Author | Changes |
    |---------|------|--------|---------|
    | 0.1 | 2026-05-28 | Author | Initial draft |

    ## B-2: Business Context

    Some context.

    ## B-3: Metrics Breakdown

    | metric_name | metric_definition | source_type | link_status | candidate_verification_evidence |
    |-------------|-------------------|-------------|-------------|---------------------------------|
    | rev | total revenue | native | exact | Tied to invoice.total_amount, row-count parity verified 2026-05-20. |
    | gex | gamma exposure | derived | proxy | Computed from option_oi and gamma; spot-checked against vendor X within 2% tolerance. |

    ## B-4: Notable / Known Limitations

    None at this time.
    """
).strip()


def _write(tmp_path: Path, content: str, *, name: str = "brd.md") -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


class TestHappyPath:
    def test_well_formed_brd_passes(self, tmp_path: Path) -> None:
        p = _write(tmp_path, GOOD_BRD)
        assert lint(p) == []


class TestMissingSections:
    @pytest.mark.parametrize("section", ["B-1", "B-2", "B-3", "B-4"])
    def test_missing_section_rejected(self, tmp_path: Path, section: str) -> None:
        body = GOOD_BRD.replace(f"## {section}:", f"## NOT-{section}:")
        p = _write(tmp_path, body)
        errors = lint(p)
        assert errors
        assert any(f"§{section}" in err for err in errors)
        assert any("remediation" in err for err in errors)


class TestB3Columns:
    def test_missing_link_status_column_rejected(self, tmp_path: Path) -> None:
        body = GOOD_BRD.replace(
            "| metric_name | metric_definition | source_type | link_status |",
            "| metric_name | metric_definition | source_type | something_else |",
        ).replace(
            "|-------------|-------------------|-------------|-------------|",
            "|-------------|-------------------|-------------|----------------|",
        )
        p = _write(tmp_path, body)
        errors = lint(p)
        assert errors
        assert any("link_status" in err for err in errors)

    def test_invalid_link_status_value_rejected(self, tmp_path: Path) -> None:
        body = GOOD_BRD.replace(
            "| rev | total revenue | native | exact |",
            "| rev | total revenue | native | bogus |",
        )
        p = _write(tmp_path, body)
        errors = lint(p)
        assert any("invalid link_status" in err.lower() or "link_status" in err for err in errors)

    def test_invalid_source_type_value_rejected(self, tmp_path: Path) -> None:
        body = GOOD_BRD.replace(
            "| rev | total revenue | native | exact |",
            "| rev | total revenue | nuclear | exact |",
        )
        p = _write(tmp_path, body)
        errors = lint(p)
        assert any("source_type" in err for err in errors)


class TestAdversarial:
    def test_file_not_found_clear_error(self, tmp_path: Path) -> None:
        errors = lint(tmp_path / "missing.md")
        assert errors
        assert any("file not found" in err for err in errors)

    def test_empty_b3_table_rejected(self, tmp_path: Path) -> None:
        body = textwrap.dedent(
            """
            # BRD

            ## B-1: Version History

            v1

            ## B-2: Business Context

            ctx

            ## B-3: Metrics Breakdown

            (no table here)

            ## B-4: Notable / Known Limitations

            None.
            """
        ).strip()
        p = _write(tmp_path, body)
        errors = lint(p)
        assert any("§B-3" in err for err in errors)


class TestRowSourceBinding:
    """Reviewer finding #4: every B-3 metric needs a source binding OR
    must be listed in B-4 unsupported with exhaustion evidence."""

    def test_metric_without_binding_or_b4_listing_rejected(
        self, tmp_path: Path
    ) -> None:
        body = textwrap.dedent(
            """
            # BRD

            ## B-1: Version History

            v1

            ## B-2: Business Context

            ctx

            ## B-3: Metrics Breakdown

            | metric_name | metric_definition | source_type | link_status | candidate_verification_evidence |
            |-------------|-------------------|-------------|-------------|---------------------------------|
            | rev | revenue | native | exact | _TODO_ |

            ## B-4: Notable / Known Limitations

            None at this time.
            """
        ).strip()
        p = _write(tmp_path, body)
        errors = lint(p)
        assert errors
        assert any("no source binding" in err for err in errors)

    def test_metric_listed_in_b4_with_evidence_passes(self, tmp_path: Path) -> None:
        body = textwrap.dedent(
            """
            # BRD

            ## B-1: Version History

            v1

            ## B-2: Business Context

            ctx

            ## B-3: Metrics Breakdown

            | metric_name | metric_definition | source_type | link_status | candidate_verification_evidence |
            |-------------|-------------------|-------------|-------------|---------------------------------|
            | flow_proxy | non-sourceable proxy | derived | unsupported |  |

            ## B-4: Notable / Known Limitations

            | metric_name | Reason Unsupported | Resource-Exhaustion Evidence |
            |-------------|--------------------|-------------------------------|
            | flow_proxy | vendor API discontinued | Investigated 4 vendors 2026-05-20, all behind paywall; logged in tech-debt-tracker. |
            """
        ).strip()
        p = _write(tmp_path, body)
        errors = lint(p)
        assert errors == [], f"unexpected: {errors}"

    def test_b4_unsupported_without_evidence_rejected(self, tmp_path: Path) -> None:
        body = textwrap.dedent(
            """
            # BRD

            ## B-1: Version History

            v1

            ## B-2: Business Context

            ctx

            ## B-3: Metrics Breakdown

            | metric_name | metric_definition | source_type | link_status | candidate_verification_evidence |
            |-------------|-------------------|-------------|-------------|---------------------------------|
            | rev | total revenue | native | exact | Tied to invoice.total_amount. |

            ## B-4: Notable / Known Limitations

            | metric_name | Reason Unsupported | Resource-Exhaustion Evidence |
            |-------------|--------------------|-------------------------------|
            | flow_proxy | vendor API discontinued | _TODO_ |
            """
        ).strip()
        p = _write(tmp_path, body)
        errors = lint(p)
        assert errors
        assert any("exhaustion evidence" in err for err in errors)


class TestSlashEscapeScope:
    """Reviewer finding #5: the slash-as-legend escape used to fire on
    every BRD. It now only applies to template files."""

    def test_slash_legend_passes_on_template_path(self, tmp_path: Path) -> None:
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        body = textwrap.dedent(
            """
            # BRD Template

            ## B-1: Version History

            v1

            ## B-2: Business Context

            ctx

            ## B-3: Metrics Breakdown

            | metric_name | metric_definition | source_type | link_status |
            |-------------|-------------------|-------------|-------------|
            |             |                   | native / derived / hybrid | exact / proxy / unsupported / unverified |

            ## B-4: Notable / Known Limitations

            None.
            """
        ).strip()
        p = templates_dir / "business-requirements.template.md"
        p.write_text(body, encoding="utf-8")
        errors = lint(p)
        # Template legend rows should pass without binding-check noise.
        assert errors == [], f"unexpected errors on template: {errors}"

    def test_slash_legend_rejected_on_real_brd(self, tmp_path: Path) -> None:
        # A real BRD living outside templates/ must commit to one value.
        body = textwrap.dedent(
            """
            # BRD

            ## B-1: Version History

            v1

            ## B-2: Business Context

            ctx

            ## B-3: Metrics Breakdown

            | metric_name | metric_definition | source_type | link_status | candidate_verification_evidence |
            |-------------|-------------------|-------------|-------------|---------------------------------|
            | rev | revenue | native / derived | exact / proxy | Tied to invoice.total. |

            ## B-4: Notable / Known Limitations

            None.
            """
        ).strip()
        # Land it under a docs/marts/ path, NOT templates/.
        marts_dir = tmp_path / "docs" / "marts" / "example"
        marts_dir.mkdir(parents=True)
        p = marts_dir / "brd.md"
        p.write_text(body, encoding="utf-8")
        errors = lint(p)
        assert errors, "finding #5 regression: legend slipped through on real BRD"
        assert any("legend" in err.lower() for err in errors)

    def test_link_status_slash_value_like_na_caught_on_real_brd(
        self, tmp_path: Path
    ) -> None:
        # Reviewer's example: `link_status: n/a` slid past the old check.
        body = textwrap.dedent(
            """
            # BRD

            ## B-1: Version History

            v1

            ## B-2: Business Context

            ctx

            ## B-3: Metrics Breakdown

            | metric_name | metric_definition | source_type | link_status | candidate_verification_evidence |
            |-------------|-------------------|-------------|-------------|---------------------------------|
            | rev | revenue | native | n/a | Tied to invoice.total. |

            ## B-4: Notable / Known Limitations

            None.
            """
        ).strip()
        marts_dir = tmp_path / "docs" / "marts" / "example"
        marts_dir.mkdir(parents=True)
        p = marts_dir / "brd.md"
        p.write_text(body, encoding="utf-8")
        errors = lint(p)
        assert errors
