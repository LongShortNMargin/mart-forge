---
name: pull
description: "Sync a remote branch into a new isolated worktree without overwriting existing work"
user-invocable: true
---

# pull — Worktree-isolated branch sync

## When to use

Invoke this skill when you need to fetch and check out a remote branch
into a fresh worktree, leaving any existing working directory intact.
The skill never resets or deletes an existing worktree.

## Prerequisites

- A git repository with a remote.
- `.claude/worktree_init.sh` is present and executable.

## Hard gate

```
GATE: Existing worktrees are never modified by this skill.
```

If a worktree for the requested branch already exists, report and
choose a new path — do NOT delete.

## Workflow

### Step 1 — Fetch

```
git fetch origin
```

### Step 2 — Determine worktree path

Default: `../mart-forge-<branch-slug>`. If the path is taken, append
`-2`, `-3`, etc.

### Step 3 — Create the worktree

```
.claude/worktree_init.sh <branch> <worktree-path>
```

`worktree_init.sh` is a short shell script (≤16 lines) that:
- Verifies the branch exists on the remote.
- Creates a worktree at the given path.
- Runs `pip install -e ".[dev]"` if `pyproject.toml` is present.

### Step 4 — Verify

```
cd <worktree-path>
git status
git log --oneline -1
```

### Step 5 — Append skill-invocation log

```json
{"timestamp": "<ISO-8601>", "skill_name": "pull", "input_artifact": "<branch>", "output_artifact": "<worktree path>", "checkpoint": "pull", "reconstructed": false}
```

### Step 6 — Print the worktree path

The path is the deliverable.

## Output format

A new git worktree at the printed path, with the requested branch
checked out.

## NOT for

- Modifying or deleting an existing worktree.
- Updating the current worktree's branch (use plain `git pull` for that).
- Cloning a repository for the first time.
