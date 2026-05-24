# dqc-audit — DQC Coverage Audit

**Trigger:** "audit DQC coverage for {mart}"

## Behavior

1. For each of the 8 control classes, verify at least one test exists per applicable model:
   - PK Integrity: `not_null` + `unique` on every PK
   - FK Integrity: `relationships` test for every FK
   - Freshness: SLA check on ODS/DWD tables
   - Completeness: Volume check on refreshed tables
   - Accepted Ranges: Bound checks on numeric metrics
   - Duplicate Detection: Business key uniqueness on fact tables
   - Null-Rate: Null percentage checks on non-PK columns
   - Business Reconciliation: External comparison for exact-link metrics
2. Validate `dqc_scorecard.json` exists and has no `fail` or unresolved `exhausted` entries.
3. Check freshness SLA is defined and testable.
4. Identify untested columns and missing integrity tests.
5. Verify scorecard is mechanically linked to `dbt test` results (not hand-edited).
6. Check that non-applicable controls have documented rationale.

## Output

Control-catalog coverage matrix:

```
| Control Class          | Model              | Status    | Test Name              |
|------------------------|--------------------|-----------|------------------------|
| PK Integrity           | ods_source_entity  | covered   | test_pk_not_null       |
| FK Integrity           | dwd_fact           | covered   | test_fk_dim_date       |
| Business Reconciliation| dws_metric         | exhausted | (attempts documented)  |
```

Gap list with severity ranking:
- Critical: Missing PK/FK/freshness tests
- High: Missing duplicate detection on fact tables
- Medium: Missing null-rate or accepted-range checks
- Low: Missing reconciliation for proxy-link metrics

Overall readiness grade: A/B/C/D/F
