# Skill Spec: /duckdb-incremental-models

> **Category:** duckdb
> **Priority:** high

## Skill Summary

Author DuckDB incremental dbt models with `unique_key`, partition
strategy, and a deterministic backfill protocol.

## Static Assertions

- [ ] Frontmatter complete.
- [ ] Body names the three valid `incremental_strategy` values
  (`append`, `delete+insert`, `merge`).
- [ ] Body declares when to pick each strategy.
- [ ] Body wires `unique_key` against the DQC C-3 uniqueness control.
- [ ] Body documents the backfill protocol via `var('backfill_window')`.

## Test Cases

### Case 1: Happy path — daily DWD with delete+insert

**Fixture:** Source with `event_ts` and `event_id`.

**Expected behavior:** Model uses `delete+insert` with a 7-day
buffer; DQC C-3 unique test fires against `event_id`; DQC C-6
freshness test fires against `event_ts`.

**Assertions:**
- [ ] Model config includes `unique_key`, `incremental_strategy:
  delete+insert`, `incremental_predicates`.
- [ ] schema.yml binds `unique` + `not_null` against `event_id`.

**Case Verdict:** PASS

### Case 2: Backfill protocol invoked

**Fixture:** Operator runs `dbt run --vars '{backfill_window:
"2026-04-01,2026-06-01"}' --full-refresh`.

**Expected behavior:** Model honours the window and re-materializes
only inside it; DQC C-6 alarms suspended for the backfill run.

**Assertions:**
- [ ] Backfilled rows match the window inclusively.
- [ ] No data outside the window is rewritten.

**Case Verdict:** PASS

### Case 3: Adversarial — `append` strategy without source dedupe

**Fixture:** Source emits duplicates within the same load batch.

**Expected behavior:** Model fails DQC C-3; skill output names
`merge` as the correct fix; the bug is not hidden by warnings.

**Assertions:**
- [ ] DQC C-3 status is `error`.
- [ ] Remediation message points at `incremental_strategy: merge`.

**Case Verdict:** PASS

## Protocol Compliance

- [ ] No bypass flag on the backfill predicate.
- [ ] Dogfood log entry on every invocation.
- [ ] No banned strings in output.

## Coverage Notes

The 7-day buffer is the v3 default; adjust per source distribution
in TDD §T-13.
