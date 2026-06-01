#!/usr/bin/env python3
"""Regenerate `.claude/skills/<name>` symlinks into `./skills/{group}/{name}`.

The marketplace manifest is the source of truth: it declares which
groups exist and which skills belong to each. This script walks the
manifest, removes any stale entries under `.claude/skills/`, and
writes a symlink for every skill the manifest declares.

Use this on a fresh clone if symlinks did not survive transit (rare on
macOS/Linux, common on Windows or when extracting from a zip).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Dict


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_skill_paths(manifest: dict) -> Dict[str, str]:
    """{skill_name -> source-relative path}, e.g. {"mart-brd": "skills/lifecycle/mart-brd"}."""
    skills: Dict[str, str] = {}
    for plugin in manifest.get("plugins", []):
        for skill_ref in plugin.get("skills", []):
            rel = skill_ref.lstrip("./").rstrip("/")
            name = Path(rel).name
            if name in skills and skills[name] != rel:
                raise SystemExit(
                    f"manifest collision: skill {name!r} declared at two paths: "
                    f"{skills[name]} and {rel}"
                )
            skills[name] = rel
    return skills


def sync(repo_root: Path, manifest_path: Path) -> int:
    manifest = load_manifest(manifest_path)
    skills = collect_skill_paths(manifest)

    target_dir = repo_root / ".claude" / "skills"
    target_dir.mkdir(parents=True, exist_ok=True)

    # Wipe stale entries.
    for entry in target_dir.iterdir():
        if entry.is_symlink() or entry.is_dir():
            if entry.name not in skills:
                if entry.is_symlink():
                    entry.unlink()
                else:
                    shutil.rmtree(entry)

    # Create / refresh symlinks.
    for name, rel in skills.items():
        link = target_dir / name
        source_abs = repo_root / rel
        if not source_abs.exists():
            print(f"WARN: manifest references missing skill source: {rel}")
            continue
        link_target = os.path.relpath(source_abs, link.parent)
        if link.is_symlink() or link.exists():
            try:
                if link.is_symlink() and os.readlink(link) == link_target:
                    continue
            except OSError:
                pass
            try:
                link.unlink()
            except IsADirectoryError:
                shutil.rmtree(link)
        os.symlink(link_target, link)

    print(f"Synced {len(skills)} skill symlinks under {target_dir}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate .claude/skills symlinks from the marketplace manifest."
    )
    parser.add_argument(
        "--manifest",
        default=".claude-plugin/marketplace.json",
        help="Path to marketplace.json (default: .claude-plugin/marketplace.json).",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repo root (default: current directory).",
    )
    args = parser.parse_args(argv)
    return sync(Path(args.repo_root).resolve(), Path(args.manifest))


if __name__ == "__main__":
    sys.exit(main())
