# Skill Spec: /grain-rules-check

> **Category:** quality
> **Priority:** high

## Skill Summary

Every fact-grade table declares its grain in `mart.yml` AND in a
per-model SQL comment; every join across grains either re-aggregates
or is waived in TDD §T-7.

## Static Assertions

- [ ] Frontmatter complete.
- [ ] Body requires `grain:` + `grain_keys:` in both `mart.yml` AND
  the model SQL leading comment block.
- [ ] Body declares the fan-out join detection rule (right-hand grain
  finer + no GROUP BY rolling back = error).
- [ ] Body allows an explicit `-- grain_waiver: T-7.<n>` escape that
  references a TDD §T-7 row.
- [ ] `## NOT for` section present.

## Test Cases

### Case 1: Happy path — declared grain matches model

**Fixture:** `dwd_orders.sql` declares "one row per order_line per
second"; `mart.yml` declares the same.

**Expected behavior:** Skill exits 0.

**Assertions:**
- [ ] Exit code 0.

**Case Verdict:** PASS

### Case 2: Mismatched grain declarations

**Fixture:** `mart.yml` says "one row per order per day"; SQL comment
says "one row per order_line per day".

**Expected behavior:** Error — two declarations drift.

**Assertions:**
- [ ] Exit code 1.
- [ ] Report names both declarations and the drift.

**Case Verdict:** PASS

### Case 3: Adversarial — fan-out join without waiver

**Fixture:** A DWS model joins a finer-grain ODS table without a
matching GROUP BY and without a `grain_waiver` comment.

**Expected behavior:** Error — silent fan-out is the failure this
skill exists to catch.

**Assertions:**
- [ ] Exit code 1.
- [ ] Report names the suspect JOIN clause.

**Case Verdict:** PASS

## Protocol Compliance

- [ ] Dogfood log entry on every invocation.
- [ ] No banned strings in output.

## Coverage Notes

The fan-out detector is intentionally conservative (catches more than
strictly necessary). Operators add `-- grain_waiver: T-7.<n>` to
silence intentional fan-outs.
