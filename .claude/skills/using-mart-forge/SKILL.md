---
name: using-mart-forge
description: "Router skill that detects the current mart phase from project state and routes to the correct phase skill"
user-invocable: true
---

# using-mart-forge -- Phase Router

## When to use

Invoke this skill at session start or whenever you need to determine which mart-forge
phase applies next. It inspects the project working tree and `mart.yml` to decide
the correct phase skill automatically.

This is the **default entry point** for any mart-forge project. If you are unsure
which skill to run, start here.

## Prerequisites

- A git repository that follows the mart-forge layout.
- `mart.yml` exists at the repository root (or the path declared in the project).

## Workflow

### Step 1 -- Read project manifest

Read `mart.yml` from the project root. Extract:

- `mart_name` -- the logical name of the data mart.
- `phase` -- last recorded phase (may be absent on a fresh repo).
- `brd_signed` -- boolean, whether the BRD carries a stakeholder signature block.
- `tdd_signed` -- boolean, whether the TDD carries a stakeholder signature block.
- `source_catalog_path` -- path to the source catalog JSON, if it exists.

If `mart.yml` does not exist, inform the user that the repository has not been
initialized as a mart-forge project and stop.

### Step 2 -- Detect current state

Evaluate the following conditions **in order**; the first matching condition
determines the route.

| # | Condition | Route |
|---|-----------|-------|
| 1 | `source_catalog_path` is absent or the file does not exist | `/source-discovery` |
| 2 | Source catalog exists but no `docs/business-requirements.md` | `/mart-brd` |
| 3 | BRD exists but `brd_signed` is false or signature block is missing | `/mart-brd` (resume) |
| 4 | BRD signed but no `docs/tech-design-doc.md` | `/mart-tdd` |
| 5 | TDD exists but `tdd_signed` is false or signature block is missing | `/mart-tdd` (resume) |
| 6 | TDD signed but scaffold has not been generated (no `models/` directory) | `/mart-bootstrap` |
| 7 | Scaffold exists | `/mart-dqc` or `/mart-review` (ask user) |

### Step 3 -- Announce and delegate

Print a one-line status summary:

```
[mart-forge] Mart "<mart_name>" is at phase <detected_phase>. Routing to /<skill>.
```

Then invoke the target skill. Do **not** skip the target skill's own prerequisite
checks -- they serve as an independent gate.

### Step 4 -- Post-delegation (optional)

After the delegated skill completes, update `mart.yml`:

- Set `phase` to the phase that just completed.
- Set `last_run` to the current ISO-8601 timestamp.

## Output format

No direct artifact. The router produces a status line and delegates to the
appropriate phase skill.

## NOT for

- Running dbt commands directly (use `/mart-dqc`).
- Reviewing an already-built mart (use `/mart-review`).
- Creating a mart from scratch without `mart.yml` -- initialize the repo first
  using the mart-forge `init` template.
- Any non-mart-forge project.
