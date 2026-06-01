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
from typing import Dict, List, Tuple


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


def _planned_link_target(repo_root: Path, target_dir: Path, rel: str) -> str:
    source_abs = repo_root / rel
    return os.path.relpath(source_abs, target_dir)


def detect_drift(
    repo_root: Path, manifest_path: Path
) -> Tuple[List[str], Dict[str, str]]:
    """Return (drift_messages, planned_skills).

    A non-empty drift list means `.claude/skills/` does not match what
    the marketplace manifest declares. Drift sources:

    - A skill in the manifest has no corresponding entry under
      `.claude/skills/<name>`.
    - A skill in the manifest points at a missing source directory.
    - An entry under `.claude/skills/` is not declared in the manifest.
    - An entry exists but is a real directory (not a symlink) — local
      dev would silently diverge from marketplace consumers.
    - A symlink exists but points at the wrong target.
    """
    manifest = load_manifest(manifest_path)
    skills = collect_skill_paths(manifest)
    target_dir = repo_root / ".claude" / "skills"

    drift: List[str] = []

    for name, rel in skills.items():
        source_abs = repo_root / rel
        if not source_abs.exists():
            drift.append(
                f"manifest references missing skill source: {rel}"
            )
            continue
        link = target_dir / name
        if not link.exists() and not link.is_symlink():
            drift.append(
                f".claude/skills/{name} is missing (manifest expects symlink → {rel})"
            )
            continue
        if not link.is_symlink():
            drift.append(
                f".claude/skills/{name} is a real directory, not a symlink "
                f"(local-dev mirror would diverge from marketplace consumers)"
            )
            continue
        expected = _planned_link_target(repo_root, target_dir, rel)
        try:
            actual = os.readlink(link)
        except OSError as exc:
            drift.append(f".claude/skills/{name}: cannot read symlink ({exc})")
            continue
        if actual != expected:
            drift.append(
                f".claude/skills/{name} points at {actual!r}, expected {expected!r}"
            )

    if target_dir.exists():
        for entry in target_dir.iterdir():
            if entry.name not in skills:
                drift.append(
                    f".claude/skills/{entry.name} exists but is not in the manifest"
                )

    return drift, skills


def sync(
    repo_root: Path,
    manifest_path: Path,
    *,
    force: bool = False,
) -> int:
    manifest = load_manifest(manifest_path)
    skills = collect_skill_paths(manifest)

    target_dir = repo_root / ".claude" / "skills"
    target_dir.mkdir(parents=True, exist_ok=True)

    # Wipe stale entries. A real directory under `.claude/skills/` is
    # data the user might have authored manually (Windows users who
    # cannot create symlinks, or a clone extracted from a zip). Refuse
    # to remove it without --force; print a loud warning either way.
    for entry in target_dir.iterdir():
        if entry.name in skills and (entry.is_symlink() or entry.is_dir()):
            # Will be refreshed below; do not delete here.
            continue
        if entry.is_symlink():
            entry.unlink()
        elif entry.is_dir():
            if not force:
                print(
                    f"REFUSING to remove non-symlink directory "
                    f"{entry} — pass --force to overwrite. Skipping.",
                    file=sys.stderr,
                )
                continue
            print(
                f"WARNING: --force enabled; removing real directory {entry}.",
                file=sys.stderr,
            )
            shutil.rmtree(entry)

    # Create / refresh symlinks.
    for name, rel in skills.items():
        link = target_dir / name
        source_abs = repo_root / rel
        if not source_abs.exists():
            print(f"WARN: manifest references missing skill source: {rel}")
            continue
        link_target = _planned_link_target(repo_root, target_dir, rel)
        if link.is_symlink() or link.exists():
            try:
                if link.is_symlink() and os.readlink(link) == link_target:
                    continue
            except OSError:
                pass
            if link.is_symlink():
                link.unlink()
            elif link.is_dir():
                if not force:
                    print(
                        f"REFUSING to remove non-symlink directory "
                        f"{link} — pass --force to overwrite. Skipping symlink for {name}.",
                        file=sys.stderr,
                    )
                    continue
                print(
                    f"WARNING: --force enabled; removing real directory {link}.",
                    file=sys.stderr,
                )
                shutil.rmtree(link)
            else:
                link.unlink()
        try:
            os.symlink(link_target, link)
        except FileExistsError:
            # Defensive: if a non-symlink slot survives the cleanup
            # above (e.g. a Windows clone where symlink-removal failed
            # silently, or a race with a parallel writer), surface the
            # same hint as the explicit REFUSING branch rather than
            # leaking a bare OSError trace.
            print(
                f"REFUSING to overwrite non-symlink slot at {link} — "
                f"pass --force to remove and replace, or move the "
                f"existing entry aside. Skipping symlink for {name}.",
                file=sys.stderr,
            )

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
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Dry-run: exit 1 if .claude/skills/ does not match the "
            "marketplace manifest, exit 0 if in sync. Does not modify "
            "the filesystem. Wired into CI to prevent drift."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Allow removing non-symlink directories under .claude/skills/. "
            "Default behaviour is to refuse and warn — protects users on "
            "Windows or zip-extracted clones who put real content there."
        ),
    )
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    manifest_path = Path(args.manifest)

    if args.check:
        drift, _ = detect_drift(repo_root, manifest_path)
        if drift:
            print(
                f"SKILLS-MIRROR DRIFT — {len(drift)} issue(s) found:\n"
            )
            for msg in drift:
                print(f"  - {msg}")
            print(
                "\n  -> remediation: run `python scripts/sync_local_skills.py` "
                "and commit the refreshed symlinks."
            )
            return 1
        print("Skills mirror is in sync with the marketplace manifest.")
        return 0

    return sync(repo_root, manifest_path, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
