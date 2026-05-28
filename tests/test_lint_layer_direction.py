"""Tests for scripts.lint_layer_direction.

The check: a model in layer X may only reference models in layers <= X.
A DWD model that ref()s an ADS model is the canonical upward violation
and must be caught.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.lint_layer_direction import lint


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestHappyPath:
    def test_downstream_refs_allowed(self, tmp_path: Path) -> None:
        # An ADS model referencing a DWS model is fine.
        _write(tmp_path / "ods" / "ord_ods_orders.sql", "select 1 as a\n")
        _write(tmp_path / "dwd" / "ord_dwd_orders.sql", "select * from {{ ref('ord_ods_orders') }}\n")
        _write(tmp_path / "dws" / "ord_dws_orders.sql", "select * from {{ ref('ord_dwd_orders') }}\n")
        _write(tmp_path / "ads" / "ord_ads_orders.sql", "select * from {{ ref('ord_dws_orders') }}\n")
        assert lint(tmp_path) == []

    def test_same_layer_refs_allowed(self, tmp_path: Path) -> None:
        _write(tmp_path / "dws" / "a.sql", "select * from {{ ref('b') }}\n")
        _write(tmp_path / "dws" / "b.sql", "select 1\n")
        # No layer can be inferred from 'b.sql' without a prefix, so
        # this should be silently skipped.
        assert lint(tmp_path) == []


class TestAdversarial:
    def test_dwd_refs_ads_rejected(self, tmp_path: Path) -> None:
        _write(tmp_path / "ads" / "ord_ads_view.sql", "select 1 as a\n")
        _write(tmp_path / "dwd" / "ord_dwd_bad.sql", "select * from {{ ref('ord_ads_view') }}\n")
        errors = lint(tmp_path)
        assert errors
        assert any("DWD" in err and "ADS" in err for err in errors)
        assert any("remediation" in err for err in errors)

    def test_ods_refs_dws_rejected(self, tmp_path: Path) -> None:
        _write(tmp_path / "dws" / "ord_dws_x.sql", "select 1\n")
        _write(tmp_path / "ods" / "ord_ods_bad.sql", "select * from {{ ref('ord_dws_x') }}\n")
        errors = lint(tmp_path)
        assert errors
        assert any("ODS" in err and "DWS" in err for err in errors)

    def test_placeholder_refs_skipped(self, tmp_path: Path) -> None:
        # Template files reference '<prefix>_dws_<entity>' style
        # placeholders. These should not trigger.
        _write(tmp_path / "dws" / "ord_dws_x.sql", "select * from {{ ref('<prefix>_ads_view') }}\n")
        assert lint(tmp_path) == []
