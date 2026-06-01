---
name: mart-bootstrap
description: "Phase C — scaffold a complete dbt project from the signed TDD, generating models, seeds, tests, and pipeline configuration"
user-invocable: true
---

# mart-bootstrap — Phase C: Scaffold Generation

## When to use

Invoke this skill after the TDD has been signed and you are ready to
generate the full dbt project scaffold. This skill translates the
technical design into a working, testable dbt project structure.

## Prerequisites

- `docs/tech-design-doc.md` exists with a completed signature block.
- `mart.yml` has `tdd_signed: true`.
- `docs/source_catalog.json` and `docs/business-requirements.md` are
  available.
- `templates/` directory contains the mart-forge scaffold templates.

## Hard gate

```
GATE: No scaffold generation may begin until the TDD carries a valid signature block.
```

If the TDD is unsigned, reject immediately:

```
BLOCKED: TDD signature required before scaffold generation.
Run /mart-tdd to complete Phase B.
```

## Workflow

### Step 1 — Validate TDD signature

Read `docs/tech-design-doc.md`. Parse the T-21 signature table. Confirm
both Stakeholder and Data Engineer rows have non-empty Name and Date.

### Step 2 — Parse TDD into scaffold spec

Extract:
- ODS contracts (T-9): source definitions, grain, partition keys,
  incremental strategies, unique keys.
- Layer models (T-6 + T-10 through T-14): names, columns, relationships.
- Column catalog (T-8): types, calculations, sources.
- Seed data (T-10 conformed dimensions).
- Test plan (T-19): test types per model.
- Pipeline config (T-20): scheduling and SLAs.

### Step 3 — Generate ODS layer

For each ODS contract, create:
- `models/ods/<prefix>_ods_<source>.sql` — staging model from
  `templates/models/ods/template.sql`. Materialization: `incremental`.
  `unique_key` from the contract.
- `models/ods/schema.yml` entries — column tests, source freshness
  checks.

### Step 4 — Generate DIM layer

For each dimension table:
- `models/dim/dim_<entity>.sql` — surrogate key generation, SCD type
  as specified, grain enforcement.
- `models/dim/schema.yml` — uniqueness + not-null on the surrogate key.

### Step 5 — Generate DWD layer

For each detail-grain fact:
- `models/dwd/<prefix>_dwd_<fact>.sql` — fact model joining ODS to DIMs,
  applying T-8 `calculation` SQL where derived columns are declared.
- `models/dwd/schema.yml` — relationships to dim tables, range tests.

### Step 6 — Generate DWS layer

For each summary table (count or performance):
- `models/dws/<prefix>_dws_<summary>.sql` — aggregation model with GROUP
  BY, window functions, and derived calcs.
- `models/dws/schema.yml` — accepted-value, range, and consistency tests.

### Step 7 — Generate ADS layer

For each application view:
- `models/ads/<prefix>_ads_<view>.sql` — one-big-table with link-status
  columns inline.
- `models/ads/schema.yml` — documentation and exposure definitions.

### Step 8 — Generate seeds

For each seed in T-10:
- `seeds/<seed_name>.csv` — copy or generate from templates/seeds/.

### Step 9 — Generate tests

Map T-19 test plan to dbt definitions:
- Generic tests in schema.yml (unique, not_null, accepted_values,
  relationships).
- Singular tests in `tests/` for business-reconciliation checks.

### Step 10 — Generate pipeline configuration

- `dbt_project.yml` — project-level config.
- `profiles.yml.example` — template connection profile (no credentials).
- `.github/workflows/daily.yml` — from `templates/pipeline/daily.yml.template`.

### Step 11 — Generate dashboard

- `dashboard/app.py` — from `templates/dashboard/app.py`.
- `dashboard/requirements.txt` — from template.

### Step 12 — Append skill-invocation log

One entry per layer generated, plus a summary entry:

```json
{"timestamp": "<ISO-8601>", "skill_name": "mart-bootstrap", "input_artifact": "docs/tech-design-doc.md", "output_artifact": "models/", "checkpoint": "C_complete", "reconstructed": false}
```

### Step 13 — Update mart.yml

Set `phase` to `C_complete`. Add `scaffold_generated_at` timestamp.

### Step 14 — Post-generation summary

Print:

| Layer | Models | Columns | Tests |
|-------|--------|---------|-------|
| ODS | N | N | N |
| DIM | N | N | N |
| DWD | N | N | N |
| DWS | N | N | N |
| ADS | N | N | N |
| Seeds | N | -- | -- |
| Total | N | N | N |

## Output format

Primary artifacts: complete dbt project under `models/`, `seeds/`,
`tests/`, `dashboard/`, plus `dbt_project.yml`.
Secondary: appended `.skill-invocations.jsonl`, updated `mart.yml`.

## NOT for

- Writing the TDD (use `/mart-tdd`).
- Running tests after scaffold is built (use `/mart-dqc`).
- Reviewing scaffold quality (use `/mart-review`).
- Modifying an existing scaffold — manual edits should be made directly
  to the generated files; use `/schema-evolve` for column additions.
