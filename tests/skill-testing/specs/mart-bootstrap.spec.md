# Skill Spec: /mart-bootstrap

> **Category:** lifecycle
> **Priority:** critical

## Skill Summary

Phase C. Generates the full dbt project scaffold from the signed TDD.

## Static Assertions

- [ ] Frontmatter complete.
- [ ] `## Hard gate` declares signed TDD requirement.
- [ ] Workflow generates ODS, DIM, DWD, DWS, ADS layers.
- [ ] Workflow generates seeds, tests, dashboard, pipeline.
- [ ] Workflow appends dogfood log.
- [ ] `## NOT for` section present.

## Test Cases

### Case 1: Happy path

**Fixture:** A signed TDD with 1 ODS contract, 2 DIM tables, 1 DWD,
1 DWS-count, 1 DWS-perf, 1 ADS view.

**Expected behavior:** Scaffold generated with:
- `models/ods/<prefix>_ods_<source>.sql` (1 file).
- `models/dim/dim_<entity>.sql` (2 files).
- `models/dwd/<prefix>_dwd_<fact>.sql` (1 file).
- `models/dws/<prefix>_dws_count_<entity>.sql` and
  `<prefix>_dws_perf_<entity>.sql` (2 files).
- `models/ads/<prefix>_ads_<view>.sql` (1 file).
- `models/<layer>/schema.yml` per layer.
- `dbt_project.yml`, `seeds/dim_date.csv`, `dashboard/app.py`.

**Assertions:**
- [ ] Every model in T-6 has a corresponding `.sql` file.
- [ ] Layer direction lints clean.
- [ ] `mart.yml` shows `phase: C_complete`.

**Case Verdict:** PASS

### Case 2: Unsigned TDD -> rejection

**Fixture:** TDD exists but T-21 signature block empty.

**Expected behavior:** Skill rejects with BLOCKED naming `/mart-tdd`.

**Assertions:**
- [ ] No scaffold files written.

**Case Verdict:** PASS

### Case 3: Adversarial — contract / output mismatch

**Fixture:** TDD declares metric X in T-3. Agent attempts to scaffold
ADS without column X.

**Expected behavior:** `mart-review` catches the gap. The bootstrap
skill itself MUST surface every T-3 metric in the scaffold; the review
gate catches any drift.

**Assertions:**
- [ ] All T-3 metrics map to an output column.
- [ ] `mart-review` flags any missing metric.

**Case Verdict:** PASS

## Protocol Compliance

- [ ] Scaffold output strictly follows the SPEC §8.1 directory layout.
- [ ] Layer direction is one-way (verified by `lint_layer_direction.py`).
- [ ] Skill emits dogfood log entries (one per layer + summary).

## Coverage Notes

End-to-end runs deferred (TD-001). Layer-direction enforcement covered
by `scripts/lint_layer_direction.py` and its tests.
