---
name: push
description: "Push the current worktree to its remote tracking branch, with branch protection awareness"
user-invocable: true
---

# push — Remote sync

## When to use

Invoke this skill when you have committed work in a worktree and need
to push it to the remote. The skill is branch-protection aware: it
refuses to push directly to `main`, and it refuses to force-push
without explicit operator authorization.

## Prerequisites

- A worktree with at least one local commit ahead of the remote.
- `git remote -v` shows a configured remote (usually `origin`).
- The remote tracking branch is set or can be set with `-u`.

## Hard gate

```
GATE: This skill never pushes to main. It never force-pushes without explicit operator authorization.
```

If `git branch --show-current` returns `main`, refuse:

```
BLOCKED: Refusing to push directly to main.
Use a feature branch and open a PR via /land.
```

## Workflow

### Step 1 — Inspect state

```
git status
git log --oneline @{u}..HEAD       # commits ahead
```

If there are no commits ahead, stop with "Nothing to push".

### Step 2 — Confirm not on main

```
git branch --show-current
```

If `main` (or whatever the protected branch is), reject.

### Step 3 — Push

For a fresh branch:
```
git push -u origin <branch>
```

For an existing tracking branch:
```
git push
```

If the push is rejected because the remote is ahead:
- Default: stop and ask the operator. The remote has changes you have
  not seen.
- Operator may instruct `git pull --rebase` followed by `git push`.

### Step 4 — Force-push (rare)

If a force-push is explicitly authorized by the human operator:

```
git push --force-with-lease
```

NEVER `git push --force` (no lease). The `--force-with-lease` flag
fails if the remote has commits the local does not have, preventing
accidental clobbering of someone else's work.

### Step 5 — Append skill-invocation log

```json
{"timestamp": "<ISO-8601>", "skill_name": "push", "input_artifact": "<branch>", "output_artifact": "<remote ref>", "checkpoint": "push", "reconstructed": false}
```

### Step 6 — Print the result

The remote ref the branch now points to. If the branch is new, include
the URL to create a PR (the URL `gh` prints, or the GitHub web URL).

## Output format

A successful push to the remote.

## NOT for

- Pushing to a protected branch.
- Force-pushing without operator authorization.
- Pushing in a dirty state. (Commit first via `/commit`.)
- Opening a PR. (Use `/land` after pushing.)
