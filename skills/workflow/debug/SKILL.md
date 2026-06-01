---
name: debug
description: "Investigate a failure with an explicit hypothesis log — no fixing until the root cause is named"
user-invocable: true
---

# debug — Hypothesis-log investigation

## When to use

Invoke this skill when a test, build, or pipeline has failed and you
need to investigate before changing anything. The skill enforces
discipline: form a hypothesis, gather evidence, name the root cause —
only then attempt a fix.

## Prerequisites

- A reproducible failure (a failing test, a non-zero exit code, a
  broken artifact).
- Read access to logs, run results, or the failing artifact.

## Hard gate

```
GATE: No code changes until the root cause is named in writing.
```

The skill MUST refuse to write any fix until the hypothesis log
contains a named root cause. This prevents the "tweak and re-run" loop.

## Workflow

### Step 1 — Capture the symptom

What failed, when, with what message? Copy the exact error text.

### Step 2 — Form a hypothesis

State a falsifiable belief about why the failure occurred. Example:

```
H1: dbt test failed on unique_gme_dwd_orders_order_sk because the
    upstream ODS dedup logic does not include pull_date in the
    unique_key, so re-runs append rather than replace.
```

### Step 3 — Predict evidence

If H1 is true, what should you see in the data?

```
P1: row count of gme_dwd_orders grows by ~20 every run instead of
    holding steady.
P2: target/run_results.json shows the failing test had > 1 violation
    rows in `relation_name`.
```

### Step 4 — Gather evidence

Run the smallest possible queries / log inspections to test the
predictions. Capture results inline.

### Step 5 — Reach a verdict

| Outcome | Action |
|---------|--------|
| All predictions confirmed | Name the root cause and proceed to Step 6 |
| Predictions disconfirmed | Form H2; return to Step 3 |
| Inconclusive | Refine the prediction; do not move to fix |

### Step 6 — Name the root cause

In one sentence, state the root cause. Distinguish from contributing
factors. Example:

```
Root cause: gme_ods_orders has unique_key=['order_id'] but should be
['order_id','pull_date'] because the source publishes a snapshot per
day; orders without pull_date in the key dedupe across days.
```

### Step 7 — Propose the fix

In one sentence, state the fix. The fix MUST address the root cause,
not the symptom.

### Step 8 — Append skill-invocation log

```json
{"timestamp": "<ISO-8601>", "skill_name": "debug", "input_artifact": "<failure context>", "output_artifact": "<hypothesis log + root cause>", "checkpoint": "debug", "reconstructed": false}
```

## Output format

A markdown hypothesis log printed to the session:

```markdown
# Debug session: <one-line summary>

## Symptom
...

## Hypotheses
- H1 (rejected | confirmed): ...
- H2 (rejected | confirmed): ...

## Root cause
...

## Proposed fix
...
```

## NOT for

- Fixing the bug. (This skill produces a verdict; the fix is a
  separate step.)
- Performance tuning that does not stem from a specific failure.
- Code review. (Use `/mart-review` for mart artifacts.)
