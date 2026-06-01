---
name: linear
description: "Operate on the issue tracker — read, comment, change status — for an active ticket"
user-invocable: true
---

# linear — Issue tracker bindings

## When to use

Invoke this skill when you need to interact with the issue tracker
that holds the active ticket: read the issue body, post a comment,
update status, or list comments. The skill is provider-agnostic; the
binding to a specific tracker (GitHub Issues, Linear, multica, etc.)
lives in `mart.yml` under `issue_tracker`.

## Prerequisites

- `mart.yml` has an `issue_tracker` block:
  ```yaml
  issue_tracker:
    provider: github | linear | multica
    project: <repo or workspace>
  ```
- The corresponding CLI is installed (`gh`, `linear-cli`, `multica`).

## Hard gate

This skill has no enforcement gate of its own. It is a transport.

## Workflow

The skill accepts subcommands:

### `read <issue-key>`

Print the issue body and metadata. For GitHub: `gh issue view <num>`.
For multica: `multica issue get <id> --output json`.

### `comment <issue-key> <message>`

Post a comment to the issue. Use multi-line input where possible:

- GitHub: `gh issue comment <num> --body "<text>"`
- multica: `multica issue comment add <id> --content "<text>"` or
  `--content-stdin` for multi-line.

### `status <issue-key> <new-status>`

Change the issue status. Valid statuses depend on the provider.

- multica: `multica issue status <id> <status>` (todo, in_progress,
  in_review, done, blocked, backfill, cancelled).
- GitHub: requires the GitHub Projects API; not all repos use it.

### `comments <issue-key>`

List all comments on the issue.

- multica: `multica issue comment list <id> --output json`.
- GitHub: `gh issue view <num> --comments`.

### Step — Append skill-invocation log

```json
{"timestamp": "<ISO-8601>", "skill_name": "linear", "input_artifact": "<issue-key>", "output_artifact": "<action taken>", "checkpoint": "tracker", "reconstructed": false}
```

## Output format

Tracker-specific (issue body, comment confirmation, status update
confirmation, comment list).

## NOT for

- Creating new issues. (That is a separate decision usually made by a
  human or by a higher-level orchestrator.)
- Closing issues. (Closure is a status change that requires the
  reviewer's sign-off; do not auto-close.)
- Bulk operations across many issues.
- Modifying issues you are not the assignee on.
