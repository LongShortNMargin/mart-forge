# Skill Spec: /motherduck-deploy

> **Category:** duckdb
> **Priority:** high

## Skill Summary

Deploy a DuckDB mart to MotherDuck cloud — connection profile from
env, fixture vs live mode, preflight schema-drift check.

## Static Assertions

- [ ] Frontmatter complete.
- [ ] Body resolves credentials from `MOTHERDUCK_TOKEN` env, never
  literal value in the profile.
- [ ] Body names two deploy modes (`fixture` and `live`).
- [ ] Body describes a preflight schema-drift check that aborts on
  unreconciled drift.
- [ ] Body has the `## NOT for` section.

## Test Cases

### Case 1: Fixture-mode deploy

**Fixture:** Mart with parquet seeds; no cloud calls expected.

**Expected behavior:** Skill runs `dbt build --target prod
--vars '{deploy_mode: fixture}'`; preflight reports zero drift; no
cloud writes occur (no network calls).

**Assertions:**
- [ ] Preflight emitted with zero drift.
- [ ] No outbound network calls.

**Case Verdict:** PASS

### Case 2: Live-mode deploy with clean schema

**Fixture:** Local build green; MotherDuck warehouse schema matches.

**Expected behavior:** Preflight passes; deploy executes; post-deploy
DQC kicks off.

**Assertions:**
- [ ] Preflight passes.
- [ ] `dbt build --target prod` exits 0.
- [ ] Post-deploy DQC scorecard updated.

**Case Verdict:** PASS

### Case 3: Adversarial — drift detected, deploy blocked

**Fixture:** A dim_* table on MotherDuck has been hand-modified.

**Expected behavior:** Preflight exits 1; deploy refuses to start;
operator gets a reconciliation report.

**Assertions:**
- [ ] Preflight exits 1.
- [ ] No write to MotherDuck.
- [ ] Reconciliation report names the drifted table.

**Case Verdict:** PASS

## Protocol Compliance

- [ ] Token never echoed in logs.
- [ ] Dogfood log entry on success and on aborted deploy.
- [ ] No banned strings in output.

## Coverage Notes

Live-mode tests require either a sandbox MotherDuck account or a
mocked endpoint. Fixture-mode tests run offline and are the CI
default.
