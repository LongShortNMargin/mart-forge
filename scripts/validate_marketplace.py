#!/usr/bin/env python3
"""Validate `.claude-plugin/marketplace.json`.

Acceptance criteria (per dispatch EMB-322 AC#1):
- File parses as JSON.
- Declares exactly the expected number of plugins.
- Every plugin lists >= 1 skill.
- Every skill path is a relative path that exists on disk and contains
  a SKILL.md with valid YAML frontmatter (`name:` and `description:`).

Exit code 1 on any failure, 0 if clean.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List

EXPECTED_PLUGIN_COUNT = 4
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
REQUIRED_FRONTMATTER_KEYS = {"name", "description"}


def _frontmatter(text: str) -> dict | None:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    block = m.group(1)
    fields: dict = {}
    current_key: str | None = None
    for line in block.splitlines():
        if not line.strip():
            current_key = None
            continue
        if line.startswith(" ") and current_key is not None:
            # continuation of multi-line value
            fields[current_key] = (fields[current_key] + " " + line.strip()).strip()
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            fields[key] = value
            current_key = key
    return fields


def validate(manifest_path: Path, repo_root: Path) -> List[str]:
    errors: List[str] = []
    if not manifest_path.exists():
        return [f"{manifest_path}: file not found"]

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{manifest_path}: invalid JSON — {exc}"]

    for required in ("name", "owner", "metadata", "plugins"):
        if required not in data:
            errors.append(f"{manifest_path}: missing top-level key '{required}'")
    if errors:
        return errors

    plugins = data["plugins"]
    if not isinstance(plugins, list):
        return [f"{manifest_path}: 'plugins' must be a list"]
    if len(plugins) != EXPECTED_PLUGIN_COUNT:
        errors.append(
            f"{manifest_path}: expected {EXPECTED_PLUGIN_COUNT} plugins, found {len(plugins)}"
        )

    seen_names: set[str] = set()
    for idx, plugin in enumerate(plugins):
        for required in ("name", "description", "source", "skills"):
            if required not in plugin:
                errors.append(
                    f"{manifest_path}: plugin #{idx} missing key '{required}'"
                )
        pname = plugin.get("name", f"<plugin-{idx}>")
        if pname in seen_names:
            errors.append(f"{manifest_path}: duplicate plugin name {pname!r}")
        seen_names.add(pname)

        skills = plugin.get("skills", [])
        if not isinstance(skills, list) or len(skills) == 0:
            errors.append(f"{manifest_path}: plugin {pname!r} must list >= 1 skill")
            continue

        for skill_ref in skills:
            if not isinstance(skill_ref, str) or not skill_ref.startswith("./"):
                errors.append(
                    f"{manifest_path}: plugin {pname!r} skill ref {skill_ref!r} "
                    f"must be a relative path beginning with './'"
                )
                continue
            skill_path = (repo_root / skill_ref.lstrip("./")).resolve()
            if not skill_path.exists() or not skill_path.is_dir():
                errors.append(
                    f"{manifest_path}: plugin {pname!r} skill path {skill_ref!r} "
                    f"does not exist on disk ({skill_path})"
                )
                continue
            skill_md = skill_path / "SKILL.md"
            if not skill_md.exists():
                errors.append(
                    f"{manifest_path}: plugin {pname!r} skill {skill_ref!r} "
                    f"missing SKILL.md"
                )
                continue
            fm = _frontmatter(skill_md.read_text(encoding="utf-8"))
            if fm is None:
                errors.append(
                    f"{skill_md}: missing YAML frontmatter (--- ... ---)"
                )
                continue
            missing_keys = REQUIRED_FRONTMATTER_KEYS - set(fm.keys())
            if missing_keys:
                errors.append(
                    f"{skill_md}: frontmatter missing required keys: "
                    f"{sorted(missing_keys)}"
                )

    return errors


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate .claude-plugin/marketplace.json"
    )
    parser.add_argument(
        "manifest",
        nargs="?",
        default=".claude-plugin/marketplace.json",
        help="Path to marketplace.json",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repo root for resolving relative skill paths",
    )
    args = parser.parse_args(argv)

    errors = validate(Path(args.manifest), Path(args.repo_root).resolve())
    if errors:
        print(f"MARKETPLACE VALIDATION FAILED — {len(errors)} error(s):\n")
        for err in errors:
            print(f"  {err}")
        return 1
    print(f"Marketplace validation passed: {args.manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
