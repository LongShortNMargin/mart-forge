# Skill Spec: /creating-duckdb-mart

> **Category:** duckdb
> **Priority:** high

## Skill Summary

Stand up a DuckDB-backed Kimball mart with parquet seeds, an
incremental staging contract, and an optional MotherDuck deploy
target.

## Static Assertions

- [ ] Frontmatter complete (`name`, `description`, `user-invocable`).
- [ ] Body has `## When to use`, `## Prerequisites`, `## Workflow`,
  `## Output format`, `## NOT for` sections.
- [ ] Workflow defines both `dev` (local file) and `prod` (MotherDuck)
  profile targets.
- [ ] Workflow declares per-layer materialization defaults (ODS
  incremental, DIM table, DWD incremental, DWS table, ADS view).
- [ ] Workflow names the three provenance columns required on ODS
  (`_ingest_ts_utc`, `_source_id`, `_load_batch`).

## Test Cases

### Case 1: Happy path

**Fixture:** A signed TDD that declares `platform: duckdb` in mart.yml.

**Expected behavior:** Skill writes `dbt_project.yml`, the profile
file, and the parquet-seed macro; the smoke `dbt build --target dev`
succeeds.

**Assertions:**
- [ ] `dbt_project.yml` exists with the per-layer config.
- [ ] `profiles/<mart_name>.yml` has dev + prod targets.
- [ ] `dbt build --target dev` exits 0.

**Case Verdict:** PASS

### Case 2: Missing signed TDD — gate blocks

**Fixture:** TDD has placeholder signature only.

**Expected behavior:** Skill refuses to scaffold; surfaces the signing
linter's remediation message.

**Assertions:**
- [ ] No files written.
- [ ] `signing-enforcement` skill was called.

**Case Verdict:** PASS

### Case 3: Adversarial — TDD declares non-DuckDB platform

**Fixture:** mart.yml says `platform: snowflake`.

**Expected behavior:** Skill refuses to run; points at the appropriate
warehouse track.

**Assertions:**
- [ ] No files written.
- [ ] Stderr names `platform: duckdb` as the precondition.

**Case Verdict:** PASS

## Protocol Compliance

- [ ] Skill emits a dogfood log entry on successful invocation.
- [ ] Skill emits a dogfood log entry on aborted invocation
  (`checkpoint: aborted_gate`).
- [ ] No banned strings in output.

## Coverage Notes

The dev-target smoke build is the cheapest end-to-end signal. The
prod (MotherDuck) path is exercised by `motherduck-deploy`'s tests.
