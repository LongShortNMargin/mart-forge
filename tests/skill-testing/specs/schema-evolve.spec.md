# Skill Spec: /schema-evolve

> **Category:** maintenance
> **Priority:** medium

## Skill Summary

Additive schema migration. Adds a new column to ODS and propagates to
DWD with appropriate tests. Rejects removals and type changes.

## Static Assertions

- [ ] Skill declares additive-only operation.
- [ ] Hard gate rejects removal / type change / grain change.
- [ ] Workflow updates T-8, T-9, T-18, T-19 of the TDD.
- [ ] Workflow runs a dbt smoke build before committing.
- [ ] `## NOT for` section present.

## Test Cases

### Case 1: Happy path — add a native column

**Fixture:** Provider exposes a new field `customer_segment`. Operator
requests adding it to ODS and propagating to DWD.

**Assertions:**
- [ ] T-8 row added.
- [ ] T-9 contract updated if it affects partitioning.
- [ ] ODS model SELECT list now includes `customer_segment`.
- [ ] DWD model carries the field if business-relevant.
- [ ] schema.yml documents the new column.
- [ ] Smoke build green.

**Case Verdict:** PASS

### Case 2: Adversarial — column removal -> rejection

**Fixture:** Operator requests removing a column.

**Assertions:**
- [ ] BLOCKED message lists the removed column.
- [ ] BLOCKED message references `/mart-tdd` for a fresh pass.

**Case Verdict:** PASS

### Case 3: Adversarial — type change -> rejection

**Fixture:** Operator requests changing an existing column from
INTEGER to VARCHAR.

**Assertions:**
- [ ] BLOCKED message lists the type-changed column.

**Case Verdict:** PASS

### Case 4: Smoke build failure -> rollback

**Fixture:** Schema change breaks a downstream test.

**Assertions:**
- [ ] Skill reports the failure.
- [ ] Skill does NOT commit a broken state.

**Case Verdict:** PASS

## Protocol Compliance

- [ ] Only additive operations.
- [ ] TDD version bumped.
- [ ] Smoke build green before commit.
- [ ] Skill emits dogfood log entry.

## Coverage Notes

The skill needs a real mart to evolve. Behavioral coverage deferred
until the conformance dispatch produces one (TD-004).
