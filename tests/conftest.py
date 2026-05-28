"""Shared pytest fixtures.

Imports the project's `scripts/` package so the test modules can call
linter functions directly without subprocesses (faster, easier to
assert on).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Make `scripts.*` importable.
sys.path.insert(0, str(ROOT))
