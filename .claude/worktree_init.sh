#!/usr/bin/env bash
# Initialize an isolated worktree for the given branch.
# Usage: worktree_init.sh <branch> <worktree-path>
set -euo pipefail

branch="${1:?branch required}"
path="${2:?worktree-path required}"

if [ -e "$path" ]; then
  echo "ERROR: $path already exists. Choose a different worktree path." >&2
  exit 1
fi

git fetch origin "$branch" 2>/dev/null || true
git worktree add "$path" "$branch"

if [ -f "$path/pyproject.toml" ]; then
  ( cd "$path" && pip install -e ".[dev]" >/dev/null )
fi

echo "$path"
