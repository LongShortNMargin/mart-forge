# Skill Spec: /debug

> **Category:** utility
> **Priority:** medium

## Skill Summary

Investigate a failure with an explicit hypothesis log. No code changes
until the root cause is named.

## Static Assertions

- [ ] Hard gate: no fix before named root cause.
- [ ] Workflow includes hypothesis -> prediction -> evidence -> verdict cycle.
- [ ] Output is a markdown hypothesis log.
- [ ] `## NOT for` section present.

## Test Cases

### Case 1: Happy path

**Fixture:** A failing dbt test with an obvious cause (missing
unique_key on incremental).

**Assertions:**
- [ ] Hypothesis log contains at least one H1 with evidence.
- [ ] Root cause is named in one sentence.

**Case Verdict:** PASS

### Case 2: Inconclusive evidence

**Fixture:** A failure whose first hypothesis is disconfirmed.

**Assertions:**
- [ ] H1 marked rejected.
- [ ] H2 formed and tested.

**Case Verdict:** PASS

### Case 3: Adversarial — skill refuses to write a fix

**Fixture:** Agent invokes /debug then immediately tries to write code.

**Assertions:**
- [ ] /debug emits no fix.
- [ ] Output reminds the agent the fix is a separate step.

**Case Verdict:** PASS

## Protocol Compliance

- [ ] No edits to source files.
- [ ] Output is the hypothesis log only.
- [ ] Skill emits dogfood log entry.

## Coverage Notes

Hypothesis discipline is what this skill enforces; verification is
behavioral. Static checks cover the structure.
