---
name: land
description: "Open a pull request with a full description, reviewer assignment, and acceptance-criteria checklist"
user-invocable: true
---

# land — Pull request construction

## When to use

Invoke this skill when a branch is ready for review and you need to
open a PR. The skill produces a PR with a description that the PR
description linter will accept and assigns the appropriate reviewer.

## Prerequisites

- A pushed branch with at least one commit ahead of `main`.
- `git remote -v` shows a GitHub remote.
- `gh` CLI is installed and authenticated.

## Hard gate

```
GATE: Local lint + test MUST be green before /land opens the PR.
```

If local checks fail, refuse to open the PR.

## Workflow

### Step 1 — Confirm branch state

```
git status
git log --oneline main..HEAD
git diff main..HEAD --stat
```

If the working tree is dirty, ask the user to commit (via `/commit`)
first.

### Step 2 — Run local checks

Same suite as `/commit` step 2. Any failure blocks landing.

### Step 3 — Compose the PR body

Format:

```markdown
## Summary

<2-3 sentences on what changed and why>

## Acceptance criteria

- [ ] <criterion 1, copied from the source issue>
- [ ] <criterion 2>
- [ ] ...

## Test plan

- [ ] <how to verify locally>

## References

- Issue: <issue-key>
- Related PRs: <none | list>
```

The `pr-description-lint.yml` workflow rejects PRs without an
"Acceptance criteria" section containing checkboxes.

### Step 4 — Decide reviewer

For mart-forge framework PRs, the default reviewer is the maintainer
group. For conformance-mart PRs, the reviewer is whichever adversarial
reviewer is named in the dispatch ticket.

### Step 5 — Open the PR

```
gh pr create \
  --title "<type>: <short summary>" \
  --body "<body from step 3>" \
  --reviewer <reviewer> \
  --base main
```

### Step 6 — Append skill-invocation log

```json
{"timestamp": "<ISO-8601>", "skill_name": "land", "input_artifact": "<branch>", "output_artifact": "<pr url>", "checkpoint": "land", "reconstructed": false}
```

### Step 7 — Print the URL

The PR URL is the deliverable. Print it to the session so the user can
share it.

## Output format

A pull request on the configured GitHub remote.

## NOT for

- Merging the PR. (Merge is human-operator action.)
- Force-pushing to a PR branch. (Use `/push --force-with-lease` only
  if the human operator explicitly authorizes it.)
- Closing a PR. (That is a separate action with separate consequences.)
