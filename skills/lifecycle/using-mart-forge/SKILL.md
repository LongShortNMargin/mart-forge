---
name: using-mart-forge
description: "Router skill that detects the current mart phase from project state and routes to the correct phase skill"
user-invocable: true
---

# using-mart-forge — Phase router

## When to use

Invoke this skill at session start or whenever you need to determine
which mart-forge phase applies next. It inspects the project working
tree and `mart.yml` to decide the correct phase skill automatically.

This is the **default entry point** for any mart-forge project. If you
are unsure which skill to run, start here.

## Prerequisites

- A git repository following the mart-forge layout.
- `mart.yml` exists at the repository root (or at the path declared in
  the project).

## Hard gate

This skill is a router — no enforcement gate of its own. It delegates
to a phase skill whose gate applies.

## Workflow

### Step 1 — Read project manifest

Read `mart.yml`. Extract:
- `mart_name`.
- `phase` (may be absent on a fresh repo).
- `brd_signed`.
- `tdd_signed`.
- `source_catalog_path`.

If `mart.yml` does not exist, inform the user the repository has not
been initialized as a mart-forge project. Offer to initialize via
`templates/mart.yml.template`.

### Step 2 — Detect current state

Evaluate the following conditions **in order**; the first matching
condition determines the route.

| # | Condition | Route |
|---|-----------|-------|
| 1 | `source_catalog_path` absent or file missing | `/source-discovery` |
| 2 | Source catalog exists but no `docs/business-requirements.md` | `/mart-brd` |
| 3 | BRD exists but `brd_signed: false` or signature block empty | `/mart-brd` (resume) |
| 4 | BRD signed but no `docs/tech-design-doc.md` | `/mart-tdd` |
| 5 | TDD exists but `tdd_signed: false` or signature block empty | `/mart-tdd` (resume) |
| 6 | TDD signed but no `models/` directory | `/mart-bootstrap` |
| 7 | Scaffold exists but no `dqc_scorecard.json` | `/mart-dqc` |
| 8 | Everything present | `/mart-review` |

### Step 3 — Announce and delegate

Print:

```
[mart-forge] Mart "<mart_name>" is at phase <detected_phase>. Routing to /<skill>.
```

Then invoke the target skill. Do NOT skip the target skill's own
prerequisite checks — they serve as an independent gate.

### Step 4 — Post-delegation update (optional)

After the delegated skill completes, update `mart.yml`:
- Set `phase` to the phase that just completed.
- Set `last_run` to the current ISO-8601 timestamp.

### Step 5 — Append skill-invocation log

```json
{"timestamp": "<ISO-8601>", "skill_name": "using-mart-forge", "input_artifact": "mart.yml", "output_artifact": "<route taken>", "checkpoint": "router", "reconstructed": false}
```

## Output format

A one-line status print plus delegation. No file artifacts produced
directly by this skill.

## NOT for

- Running dbt commands (use `/mart-dqc`).
- Reviewing an already-built mart (use `/mart-review`).
- Initializing a brand-new mart-forge repository (copy
  `templates/mart.yml.template` to `mart.yml` first).
- Any non-mart-forge project.
