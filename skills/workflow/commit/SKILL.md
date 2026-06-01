---
name: commit
description: "Produce a single atomic commit with a verifiable message and a green local check suite"
user-invocable: true
---

# commit — Atomic commit construction

## When to use

Invoke this skill when you have completed a reviewable unit of work and
need to create a single atomic commit. This skill enforces commit
discipline: one logical change, a message that explains *why*, and a
local green check before the commit lands.

## Prerequisites

- A worktree with staged or unstaged changes.
- The work belongs to one logical unit (one feature, one fix, one
  refactor — not a mix).

## Hard gate

```
GATE: Local lint + test suite MUST pass before the commit is written.
```

If the local check suite fails, refuse to commit:

```
BLOCKED: Local checks failed. Fix and re-run /commit.
  - <one line per failing check>
```

## Workflow

### Step 1 — Inspect the change

```
git status
git diff
git diff --cached
```

Identify what is being committed. If the change spans multiple logical
units, stop and ask the user how to split it.

### Step 2 — Run local checks

```
python scripts/confidentiality_scan.py .
python scripts/lint_brd.py templates/business-requirements.template.md
python scripts/lint_tdd.py templates/tech-design-doc.template.md
python scripts/lint_layer_direction.py templates/models/
python scripts/validate_dogfood.py .skill-invocations.jsonl
python scripts/lint_docs_freshness.py .
pytest tests/
```

Any non-zero exit code blocks the commit.

### Step 3 — Stage explicitly

```
git add <specific files>
```

NEVER use `git add -A` or `git add .`. Staging specific files prevents
accidentally committing `.env`, `.DS_Store`, or other untracked noise.

### Step 4 — Compose the message

Format:

```
<type>: <short summary, imperative, ≤72 chars>

<body explaining WHY, wrapped at 72 chars>

<blank line>
<optional: refs to issue, e.g., "Refs: <issue-key>">
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`.

The body explains *why* the change is needed. Avoid restating *what*
the diff shows.

### Step 5 — Write the commit

```
git commit -m "<message>"
```

If a pre-commit hook fails, fix the issue and create a new commit. Do
NOT `--amend` to paper over hook failures — the failure was real.

### Step 6 — Append skill-invocation log

```json
{"timestamp": "<ISO-8601>", "skill_name": "commit", "input_artifact": "<staged files>", "output_artifact": "<commit sha>", "checkpoint": "commit", "reconstructed": false}
```

## Output format

A single commit on the current branch. Commit SHA printed.

## NOT for

- Amending a previous commit. (Create a new commit; that is the
  default workflow.)
- Committing multiple logical units at once.
- Bypassing the local check suite. If a check is wrong, fix the check
  first.
- Committing secrets, `.env`, or generated artifacts.
