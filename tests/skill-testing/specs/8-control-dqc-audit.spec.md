# Skill Spec: /8-control-dqc-audit

> **Category:** quality
> **Priority:** critical

## Skill Summary

Audit a mart against the eight DQC control classes and produce a
scorecard that names the gaps + remediation owner.

## Static Assertions

- [ ] Frontmatter complete.
- [ ] Body references all 8 control classes (PK, FK, Freshness,
  Volume, Range, Duplicate, Null-Rate, Reconciliation).
- [ ] Body declares the dbt-status → scorecard-status mapping.
- [ ] Body distinguishes `not_applicable` from `pending`.
- [ ] Body names every non-pass row requires `attempts[]` history.

## Test Cases

### Case 1: Happy path — all controls pass

**Fixture:** A mart whose dbt test suite is fully green.

**Expected behavior:** Scorecard reports every control `pass`; orphan
test list is empty; report file lands under `docs/dqc-audit-<date>.md`.

**Assertions:**
- [ ] Every control row has `status: pass`.
- [ ] `summary.pass_count` equals total non-`not_applicable` rows.

**Case Verdict:** PASS

### Case 2: Regression — one warn appears

**Fixture:** Volume control flagged warn (row count 12% above baseline).

**Expected behavior:** Scorecard reflects `warn`; audit report lists
the regression in the "Regressions" section; remediation owner named.

**Assertions:**
- [ ] `status: warn` recorded.
- [ ] `attempts[]` populated.

**Case Verdict:** PASS

### Case 3: Adversarial — error-severity test with empty attempts

**Fixture:** A control row with `status: error` and `attempts: []`
committed to the scorecard.

**Expected behavior:** Lint script rejects the scorecard; CI blocks
merge.

**Assertions:**
- [ ] Lint exits 1.
- [ ] Remediation message names `attempts[]` requirement.

**Case Verdict:** PASS

## Protocol Compliance

- [ ] Dogfood log entry on every invocation.
- [ ] No banned strings in audit report.

## Coverage Notes

The control-test linkage convention (`<control>_<table>_<column>`) is
declared in SPEC §T-15; the spec drift test asserts the skill body
references it.
