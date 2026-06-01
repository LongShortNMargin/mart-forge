# Skill Spec: /mart-review

> **Category:** review
> **Priority:** high

## Skill Summary

Adversarial, read-only review of a mart's artifacts. Produces a
verdict report with findings categorized as Blocking, Concerning, or
Notes.

## Static Assertions

- [ ] Skill declares read-only operation.
- [ ] Workflow runs `lint_brd.py`, `lint_tdd.py`, `lint_layer_direction.py`.
- [ ] Workflow performs bidirectional traceability (BRD <-> TDD <-> model <-> dashboard).
- [ ] Verdict vocabulary is one of READY / NEEDS_WORK / BLOCKED.
- [ ] Findings split into Blocking / Concerning / Notes.
- [ ] `## NOT for` section present.

## Test Cases

### Case 1: Happy path — fully built mart returns READY

**Fixture:** All artifacts present, all gates green.

**Assertions:**
- [ ] Verdict: READY
- [ ] No blocking findings.

**Case Verdict:** PASS

### Case 2: BRD with missing section -> BLOCKED

**Fixture:** BRD missing B-4.

**Assertions:**
- [ ] Verdict: BLOCKED
- [ ] Blocking finding cites §B-4.

**Case Verdict:** PASS

### Case 3: Layer direction violation -> BLOCKED

**Fixture:** A DWD model `ref()`s an ADS model.

**Assertions:**
- [ ] Verdict: BLOCKED
- [ ] Blocking finding identifies the offending file and line.

**Case Verdict:** PASS

### Case 4: Adversarial — dashboard panel without TDD entry

**Fixture:** Dashboard renders a metric not in T-17 of the TDD.

**Assertions:**
- [ ] Verdict: NEEDS_WORK or BLOCKED.
- [ ] Concerning or blocking finding cites the missing TDD entry.

**Case Verdict:** PASS

## Protocol Compliance

- [ ] Skill does not modify any files.
- [ ] Skill emits dogfood log entry.
- [ ] Verdict report follows the documented format.

## Coverage Notes

The bidirectional traceability matrix is part of the verdict output;
spot-checking it requires a real mart and is deferred.
