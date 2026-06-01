# Skill Spec: /naming-conventions-lint

> **Category:** quality
> **Priority:** high

## Skill Summary

Check that every dbt model and column in a mart matches the documented
ODS / DIM / DWD / DWS / ADS prefix + grain + suffix rules.

## Static Assertions

- [ ] Frontmatter complete.
- [ ] Body declares the model-name regex
  `<prefix>_<layer>_<noun>[_<grain>]`.
- [ ] Body lists the column-pattern rules (`_sk`, `_ts_utc`, `_date`,
  `_amt_<ccy>`, `_pct`, `is_<adj>`, etc.).
- [ ] Body declares DIM files MUST NOT carry the mart prefix.
- [ ] `## NOT for` section present.

## Test Cases

### Case 1: Happy path — clean mart passes

**Fixture:** A scaffolded mart with every model named per convention.

**Expected behavior:** Skill reports zero errors; warnings (if any)
are documented in schema.yml.

**Assertions:**
- [ ] Exit code 0.
- [ ] Report has no `error` rows.

**Case Verdict:** PASS

### Case 2: Adversarial — provider name leaked into noun

**Fixture:** Model named `gme_dwd_cboe_option_contract_di`.

**Expected behavior:** Warn — provider identity should live in the
ODS contract, not the DWD name.

**Assertions:**
- [ ] Report includes a warn row naming `cboe` as the offending token.

**Case Verdict:** PASS

### Case 3: Adversarial — DIM file with mart prefix

**Fixture:** `models/dim/gme_dim_instrument.sql` (should be
`dim_instrument.sql`).

**Expected behavior:** Error — conformed dims must not carry the
mart prefix.

**Assertions:**
- [ ] Exit code 1.
- [ ] Report names the file with the layered prefix-on-dim error.

**Case Verdict:** PASS

## Protocol Compliance

- [ ] Dogfood log entry on every invocation.
- [ ] No banned strings in output.

## Coverage Notes

This skill works alongside `scripts/lint_layer_direction.py`; together
they catch most "hand-edited models bypassed the lifecycle" drift.
