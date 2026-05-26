# Skill Spec: /mart-bootstrap

## Summary

The `/mart-bootstrap` skill generates a complete dbt project scaffold from a signed
Technical Design Document (TDD). It creates model SQL files, mart.yml configurations,
seed files, and test stubs for every layer defined in the TDD. The skill enforces
a strict gate: only TDDs graded "A" and marked "APPROVED" are accepted.

## Domain

### Files Read
- `docs/technical-design.md` — signed TDD containing layer definitions, model specs, grain declarations, and column inventories
- `docs/source-catalog.md` — provider bindings (referenced for ODS model generation)
- `mart.yml` — top-level mart configuration (prefix, providers)

### Files Written
- `models/ods/*.sql` — ODS model files
- `models/dim/*.sql` — Dimension model files
- `models/dwd/*.sql` — Detail/Fact model files
- `models/dws/*.sql` — Summary model files
- `models/ads/*.sql` — Application Data Store model files
- `models/*/mart.yml` — Per-layer schema definitions
- `seeds/*.csv` — Seed files for seed-backed dimensions
- `tests/*.sql` — Custom test stubs
- `dogfood-log.jsonl` — Artifact generation log (G-DOGFOOD protocol)

### Directories Owned
- `models/` (creates layer subdirectories and all model files)
- `seeds/` (creates seed CSV files)
- `tests/` (creates test stub files)

## Static Assertions

### Frontmatter Requirements

The TDD input must contain frontmatter with these fields for the skill to proceed:

| Field         | Type   | Required | Gate Condition                     |
|---------------|--------|----------|------------------------------------|
| `grade`       | string | yes      | Must be exactly `A`               |
| `status`      | string | yes      | Must contain `APPROVED`           |
| `mart_prefix` | string | yes      | Non-empty, matches `[a-z]{2,4}`   |
| `version`     | string | yes      | Semantic version (e.g., `1.0.0`)  |

### Required Gates

Before generating any files, the skill must verify:

1. **TDD Grade Gate:** `grade` field equals `A`. Any other grade triggers REJECT.
2. **TDD Approval Gate:** `status` field contains the string `APPROVED`. Unsigned or draft TDDs trigger REJECT.
3. **Source Catalog Exists:** `docs/source-catalog.md` must exist with `status: complete` or `status: partial`. Missing source catalog triggers REJECT.

## Test Cases

### TC-1: Happy Path — Full Scaffold Generation

**Fixture:**
A signed TDD (Grade A, APPROVED) defining:
- 3 ODS models: `gme_ods_prices_daily`, `gme_ods_options_daily`, `gme_ods_dividends_quarterly`
- 2 DIM models: `gme_dim_instrument`, `gme_dim_exchange`
- 2 DWD models: `gme_dwd_prices_daily`, `gme_dwd_options_daily`
- 1 DWS model: `gme_dws_volume_daily`
- 1 ADS model: `gme_ads_dashboard_daily`

TDD frontmatter:
```yaml
grade: A
status: APPROVED
mart_prefix: gme
version: 1.0.0
```

Source catalog exists with `status: complete`.

**Expected Behavior:**
1. Skill reads the TDD and validates all gates (grade, approval, source catalog).
2. All gates pass.
3. Skill generates the complete scaffold:
   - 3 SQL files in `models/ods/`
   - 2 SQL files in `models/dim/`
   - 2 SQL files in `models/dwd/`
   - 1 SQL file in `models/dws/`
   - 1 SQL file in `models/ads/`
   - 5 `mart.yml` files (one per layer directory)
   - Seed CSV stubs for seed-backed dimensions
   - Test stubs for PK integrity on every model
4. Skill writes `dogfood-log.jsonl` with an entry for every generated artifact.

**Assertions:**
- File count: exactly 9 SQL model files, 5 mart.yml files.
- Each SQL file contains a `{{ config(...) }}` block with correct materialization.
- Each SQL file references the correct upstream model (ODS references source, DWD references ODS + DIM, etc.).
- Each `mart.yml` contains column definitions matching the TDD spec.
- Naming conventions are followed: all files match `{prefix}_{layer}_{entity}_{grain}.sql`.
- Grain is declared in every `mart.yml` model entry.
- `dogfood-log.jsonl` exists and contains one JSON line per generated file (minimum 14 entries).

**Rubric Categories:** gate enforcement, template compliance, output format, traceability.

---

### TC-2: Unsigned TDD Rejection

**Fixture:**
A TDD with the following frontmatter (not approved):
```yaml
grade: B
status: DRAFT
mart_prefix: gme
version: 0.9.0
```

Source catalog exists with `status: complete`.

**Expected Behavior:**
1. Skill reads the TDD and checks the grade gate.
2. Grade is `B`, not `A` — gate fails.
3. Skill outputs a REJECT response with:
   - Explicit statement that the TDD grade gate failed.
   - The actual grade found (`B`) vs. the required grade (`A`).
   - The actual status found (`DRAFT`) vs. required (`APPROVED`).
   - No scaffold files are generated.
4. No files are created in `models/`, `seeds/`, or `tests/`.

**Assertions:**
- Skill output contains the word `REJECT` (case-insensitive).
- Skill output references both the grade failure and the approval failure.
- `models/` directory is empty or unchanged from before the run.
- `seeds/` directory is empty or unchanged.
- `tests/` directory is empty or unchanged.
- `dogfood-log.jsonl` is NOT created (no artifacts generated).
- Skill does NOT produce a partial scaffold (no "best effort" generation).

**Rubric Categories:** gate enforcement, correct routing.

---

### TC-3: G-DOGFOOD Log Assertion

**Fixture:**
Same as TC-1 (successful scaffold generation). This test case focuses specifically
on the dogfood log integrity after a successful run.

**Expected Behavior:**
1. After successful scaffold generation, `dogfood-log.jsonl` exists in the mart root.
2. The log contains one JSON entry per generated artifact.
3. Each entry records the artifact path, type, and generation timestamp.

**Assertions:**
- `dogfood-log.jsonl` exists and is valid JSONL (one JSON object per line).
- Each line parses as valid JSON with these required fields:

```json
{
  "artifact_path": "models/ods/gme_ods_prices_daily.sql",
  "artifact_type": "model | schema | seed | test",
  "layer": "ods | dim | dwd | dws | ads",
  "generated_ts_utc": "2025-01-15T10:30:00Z",
  "source_tdd_version": "1.0.0"
}
```

- Total line count matches the total number of generated files (SQL + mart.yml + seeds + tests).
- Every file that exists in `models/`, `seeds/`, and `tests/` after the run has a corresponding log entry.
- No log entry references a file that does not exist (no phantom entries).
- `artifact_type` values are consistent: `.sql` model files are `model`, `mart.yml` files are `schema`, `.csv` files are `seed`, test files are `test`.
- `source_tdd_version` matches the TDD frontmatter version on every entry.
- Log entries are ordered chronologically (non-decreasing `generated_ts_utc`).

**Rubric Categories:** output format, traceability, template compliance.
