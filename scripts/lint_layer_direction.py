#!/usr/bin/env python3
"""Layer-direction linter.

Enforces the one-way layer rule for dbt models:
    ODS -> DIM, DWD
    DIM -> DWD
    DWD -> DWS
    DWS -> ADS

A `ref()` that goes upward (e.g., a DWD model ref()-ing an ADS model)
is a structural defect and fails CI.

Detection: parse each .sql file under the given directory tree, extract
the layer prefix from the filename (e.g., `gme_dws_strike_gex_1d.sql`
-> `dws`), then find every `{{ ref('model_name') }}` and read its layer
from the referenced filename. Compare against the allowed direction map.

Note: this linter inspects the template directory by default, where
SQL files use placeholders. Placeholder refs (containing '<' or '>' or
'_TODO_' or being literally '<' delimited) are skipped.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List

# Layer order: lower index = upstream. A ref() may only go to a layer
# with index <= the source's index.
LAYER_ORDER = {
    "ods": 0,
    "dim": 1,
    "dwd": 2,
    "dws": 3,
    "ads": 4,
}

REF_PATTERN = re.compile(r"\{\{\s*ref\(\s*['\"]([^'\"]+)['\"]\s*\)\s*\}\}")
LAYER_REGEX = re.compile(r"_?(ods|dim|dwd|dws|ads)_", re.IGNORECASE)


def extract_layer(name: str) -> str | None:
    """Extract the layer prefix from a model name or filename."""
    # Strip path and extension.
    stem = Path(name).stem.lower()
    # Look for the layer marker.
    if stem.startswith("dim_") or "_dim_" in stem:
        return "dim"
    m = LAYER_REGEX.search(stem)
    if m:
        return m.group(1).lower()
    if stem.startswith("dim"):
        return "dim"
    return None


def lint(root: Path) -> List[str]:
    errors: List[str] = []
    if not root.exists():
        return [f"{root}: directory not found"]

    sql_files = list(root.rglob("*.sql"))
    if not sql_files:
        return errors

    # Build a model-name -> layer map from all discovered SQL files.
    model_layer: Dict[str, str] = {}
    for sql_file in sql_files:
        layer = extract_layer(sql_file.name)
        if layer:
            model_layer[sql_file.stem] = layer

    for sql_file in sql_files:
        own_layer = extract_layer(sql_file.name)
        if not own_layer:
            # Templates without a recognizable layer prefix are skipped.
            continue
        text = sql_file.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for m in REF_PATTERN.finditer(line):
                ref_name = m.group(1)
                # Skip placeholder refs.
                if "<" in ref_name or ">" in ref_name or "_TODO_" in ref_name.upper():
                    continue
                # Find the layer for the referenced model.
                referenced_layer = model_layer.get(ref_name) or extract_layer(ref_name)
                if not referenced_layer:
                    continue
                if LAYER_ORDER[referenced_layer] > LAYER_ORDER[own_layer]:
                    errors.append(
                        f"{sql_file}:{line_no}: model in layer {own_layer.upper()} "
                        f"references upward to layer {referenced_layer.upper()} "
                        f"(model: {ref_name})\n"
                        f"    -> remediation: refactor so the upstream layer ({referenced_layer.upper()}) "
                        f"does not depend on the downstream layer ({own_layer.upper()}). "
                        f"Allowed direction: ODS -> DIM, DWD -> DWS -> ADS."
                    )
    return errors


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Enforce ODS->DIM->DWD->DWS->ADS layer direction across .sql files."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default="templates/models",
        help="Directory to walk (default: templates/models).",
    )
    args = parser.parse_args(argv)

    errors = lint(Path(args.directory))
    if errors:
        print(f"LAYER DIRECTION LINT FAILED — {len(errors)} violation(s):\n")
        for err in errors:
            print(f"  {err}")
        return 1
    print(f"Layer direction lint passed: {args.directory}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
