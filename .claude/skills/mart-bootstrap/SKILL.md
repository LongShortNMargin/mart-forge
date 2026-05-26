---
name: mart-bootstrap
description: "Phase C -- scaffold a complete dbt project from the signed TDD, generating models, seeds, tests, and pipeline configuration"
user-invocable: true
---

# mart-bootstrap -- Phase C: Scaffold Generation

## When to use

Invoke this skill after the TDD has been signed and you are ready to generate the
full dbt project scaffold. This skill translates the technical design into a
working, testable dbt project structure.

## Prerequisites

- `docs/tech-design-doc.md` exists with a **completed signature block** (both
  rows filled).
- `mart.yml` has `tdd_signed: true`.
- `docs/source_catalog.json` and `docs/business-requirements.md` are available.
- `templates/` directory contains the mart-forge scaffold templates.

## Hard gate

```
GATE: No scaffold generation may begin until the TDD carries a valid signature block.
```

If the TDD is unsigned, reject the invocation immediately:

```
BLOCKED: TDD signature required before scaffold generation.
Run /mart-tdd to complete Phase B.
```

## Workflow

### Step 1 -- Validate TDD signature

Read `docs/tech-design-doc.md`. Parse the T-21 signature table. Confirm both
Stakeholder and Data Engineer rows have non-empty Name and Date fields. If
validation fails, stop and report which signatures are missing.

### Step 2 -- Parse TDD into scaffold spec

Extract the following from the TDD:

- **ODS contracts** (T-4): source definitions, grain, partition keys, incremental
  strategies, unique keys.
- **Layer models** (T-5 through T-8): model names, columns, relationships.
- **Column catalog** (T-9): all columns with types, calculations, sources.
- **Seed data** (T-10): static reference tables.
- **Test plan** (T-12): test types per model.
- **Pipeline config** (T-13): DAG structure and scheduling.

### Step 3 -- Generate ODS layer models

For each ODS contract, create:

- `models/staging/ods_<source_name>.sql` -- the staging model with:
  - Source reference via `{{ source(...) }}`.
  - Column list matching the contract.
  - Incremental strategy as declared (append/merge/delete+insert/snapshot).
  - `unique_key` configuration.
- `models/staging/ods_<source_name>.yml` -- schema file with column descriptions,
  tests, and source freshness checks.

### Step 4 -- Generate DIM layer models

For each dimension table in T-5:

- `models/dims/dim_<entity>.sql` -- dimension model with surrogate key generation,
  SCD type as specified, and grain enforcement.
- `models/dims/dim_<entity>.yml` -- schema with uniqueness and not-null tests on
  the surrogate key.

### Step 5 -- Generate DWD layer models

For each detail-grain fact in T-6:

- `models/facts/dwd_<fact>.sql` -- fact model joining ODS to DIMs, applying
  business logic from the calculation column in T-9.
- `models/facts/dwd_<fact>.yml` -- schema with referential integrity tests
  against dimension tables.

### Step 6 -- Generate DWS layer models

For each summary table in T-7:

- `models/aggregates/dws_<summary>.sql` -- aggregate model with GROUP BY, window
  functions, and derived metric calculations (SQL from T-9 calculation column).
- `models/aggregates/dws_<summary>.yml` -- schema with accepted-value and range
  tests.

### Step 7 -- Generate ADS layer models

For each application view in T-8:

- `models/app/ads_<view>.sql` -- final presentation layer model.
- `models/app/ads_<view>.yml` -- schema with documentation and exposure
  definitions.

### Step 8 -- Generate seeds

For each seed in T-10:

- `seeds/<seed_name>.csv` -- static data file.
- Document in `seeds/seeds.yml`.

### Step 9 -- Generate test configurations

Map the T-12 test plan to dbt test definitions:

- Generic tests in schema YAML files (unique, not_null, accepted_values,
  relationships).
- Singular tests in `tests/` for complex business-reconciliation checks.
- Custom test macros in `macros/tests/` if needed.

### Step 10 -- Generate pipeline configuration

- `dbt_project.yml` -- project-level config with model paths, materializations.
- `profiles.yml.example` -- template connection profile (no credentials).
- `packages.yml` -- required dbt packages (e.g., dbt-utils, dbt-expectations).

### Step 11 -- Generate dashboard stubs

- `dashboards/` directory with placeholder dashboard definitions referencing ADS
  models.

### Step 12 -- Write dogfood log

Write `dogfood-log.jsonl` (append if exists). Each line is a JSON object:

```json
{
  "timestamp": "<ISO-8601>",
  "skill_name": "mart-bootstrap",
  "input_artifact": "docs/tech-design-doc.md",
  "output_artifact": "<path of generated file>",
  "checkpoint": "scaffold_complete"
}
```

One entry per generated file, plus a final summary entry with
`checkpoint: scaffold_complete`.

### Step 13 -- Update mart.yml

Set `phase` to `C_complete`. Add `scaffold_generated_at` timestamp. List all
generated model paths under `models`.

### Step 14 -- Post-generation summary

Print a summary table:

| Layer | Models | Columns | Tests |
|-------|--------|---------|-------|
| ODS | N | N | N |
| DIM | N | N | N |
| DWD | N | N | N |
| DWS | N | N | N |
| ADS | N | N | N |
| Seeds | N | -- | -- |
| **Total** | **N** | **N** | **N** |

## Output format

Primary artifacts: complete dbt project under `models/`, `seeds/`, `tests/`,
`macros/`, `dashboards/`.
Secondary: `dogfood-log.jsonl`, updated `mart.yml`.

## NOT for

- Writing the TDD (use `/mart-tdd`).
- Running tests after scaffold is built (use `/mart-dqc`).
- Reviewing scaffold quality (use `/mart-review`).
- Modifying an existing scaffold -- this skill generates from scratch. Manual
  edits should be made directly to the generated files.
