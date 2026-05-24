# mart-dqc — DQC Generation and Scorecard Update

**Trigger:** "generate DQC for {mart}" or Phase D detection by using-mart-forge.

**Prerequisite:** Scaffolded dbt project (Phase C complete).

## Behavior

1. Read the signed TDD DQC plan (T-14) and test inventory (T-15).
2. Generate tests for all 8 control classes per the applicability matrix:

   | Control Class | Implementation | Severity |
   |---------------|---------------|----------|
   | PK Integrity | Generic: `not_null` + `unique` on every PK | `error` |
   | FK Integrity | Generic: `relationships` to each DIM | `error` |
   | Freshness | Singular: `max(pull_ts_utc) > current_timestamp - interval '{sla}'` | `error` |
   | Completeness | Singular: today vs yesterday count, fail if delta > threshold | `warn` |
   | Accepted Ranges | Generic: `accepted_values`; singular: numeric range checks | `warn` |
   | Duplicate Detection | Singular: `GROUP BY business_key HAVING COUNT(*) > 1` | `error` |
   | Null-Rate | Singular: `COUNT(*) FILTER (WHERE col IS NULL) / COUNT(*) > threshold` | `warn` |
   | Business Reconciliation | Singular: compare mart output to external reference | `error`/`warn` |

3. For controls not applicable to a table/metric, create `not_applicable` entries with rationale.
4. Run `dbt test` and capture `target/run_results.json`.
5. Run `scripts/dqc_update.py` to generate `dqc_scorecard.json` from test results.

## Scorecard Requirements

- Mechanically generated from `dbt test` results (never hand-edited)
- Each entry: control class, metric, status, linked_dbt_tests[], last_dbt_run
- Non-pass entries: attempts[] array per resource exhaustion protocol
- Statuses: `pass`, `fail`, `exhausted`

## Resource Exhaustion Protocol

Before marking any control `exhausted`:
1. Enumerate all resources from BRD + candidate sources
2. Attempt each with documented evidence
3. Only after ALL attempted can `exhausted` be assigned
4. Document in attempts[]: source, result, reason, date, evidence

## Output

- Generated test files in `tests/`
- Updated `schema.yml` with generic tests
- `dqc_scorecard.json` linked to dbt test results
