# Skill Spec: /mart-dqc

> **Category:** quality
> **Priority:** critical

## Skill Summary

Phase D. Runs dbt tests and generates `dqc_scorecard.json` with
applicability across the 8 control classes.

## Static Assertions

- [ ] Frontmatter complete.
- [ ] Body references all 8 DQC control classes (PK, FK, Freshness,
  Volume, Range, Duplicate, Null-Rate, Reconciliation).
- [ ] Body defines the test-name -> control mapping.
- [ ] Body asserts non-pass statuses never render green.
- [ ] Workflow updates `coverage_manifest.json`.
- [ ] `## NOT for` section present.

## Test Cases

### Case 1: Happy path

**Fixture:** A scaffolded mart with passing dbt tests.

**Expected behavior:** Scorecard reports each control as `pass` with
linked dbt tests. Coverage manifest updated.

**Assertions:**
- [ ] Every control has `linked_dbt_tests[]`.
- [ ] `summary.pass_count` equals total controls minus `not_applicable`.
- [ ] `dqc_scorecard.json` includes `last_dbt_run` timestamp.

**Case Verdict:** PASS

### Case 2: Adversarial — silent green when test fails

**Fixture:** A control whose linked dbt test returns `fail`.

**Expected behavior:** The scorecard reflects `error` status; the
dashboard renders red, NOT green.

**Assertions:**
- [ ] `status: error` recorded.
- [ ] `attempts[]` populated.
- [ ] Dashboard does NOT render the control as pass.

**Case Verdict:** PASS

### Case 3: Control with no linked tests

**Fixture:** T-18 declares a control but no test was added.

**Expected behavior:** Scorecard records `pending` status until either
the test is added or the control is explicitly `not_applicable`.

**Assertions:**
- [ ] `status: pending` recorded.
- [ ] Skill output flags the gap.

**Case Verdict:** PASS

## Protocol Compliance

- [ ] Scorecard is mechanically generated from `target/run_results.json`.
- [ ] No hand-editing of the scorecard.
- [ ] Skill emits dogfood log entry.

## Coverage Notes

The behavioral spec assumes a working dbt project; testing without one
is out of scope for the static checks.
