"""Test fixtures for the gme-options-mart Python test suite (TC-13 / TC-14 / TC-15).

These tests run against a built warehouse: either a local DuckDB target at
`data/fixtures/gme.duckdb` (the default, created by `dbt seed && dbt run`
on the `local` profile) or a MotherDuck instance when `MOTHERDUCK_TOKEN`
is set. If neither is available, tests are skipped — pytest is collected
but reports `SKIPPED` so an unbuilt environment never produces a false
green.
"""
from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pytest

EXAMPLE_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = EXAMPLE_ROOT / "data" / "fixtures" / "gme.duckdb"


@pytest.fixture(scope="session")
def warehouse() -> duckdb.DuckDBPyConnection:
    """Read-only handle to the materialised warehouse."""
    token = os.environ.get("MOTHERDUCK_TOKEN", "").strip()
    if token:
        return duckdb.connect(f"md:gme_db?motherduck_token={token}", read_only=True)
    if not FIXTURE_PATH.exists():
        pytest.skip(
            f"no MOTHERDUCK_TOKEN and no local fixture at {FIXTURE_PATH}; "
            "run `dbt seed && dbt run --target local` from "
            "examples/gme-options-mart/ first."
        )
    return duckdb.connect(str(FIXTURE_PATH), read_only=True)
