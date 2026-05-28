# Skill Spec: /source-discovery

> **Category:** lifecycle
> **Priority:** critical

## Skill Summary

Phase A0. Discovers, verifies, and catalogs data sources from stakeholder
requirements. Writes `docs/source_catalog.json`. Hard prerequisite for
`/mart-brd`.

## Static Assertions

- [ ] Frontmatter has `name: source-discovery`.
- [ ] Frontmatter has `description` field.
- [ ] Frontmatter has `user-invocable: true`.
- [ ] Body has `## When to use` section.
- [ ] Body has `## Prerequisites` section.
- [ ] Body has `## Workflow` section with numbered steps.
- [ ] Workflow includes a "Resource exhaustion protocol" step.
- [ ] Workflow ends with an "Append skill-invocation log" step.
- [ ] Body has `## Output format` section.
- [ ] Body has `## NOT for` section.

## Test Cases

### Case 1: Happy path

**Fixture:** A stakeholder document declaring three metrics with known
public providers.

**Expected behavior:**
1. The skill extracts the three metrics.
2. For each metric, it enumerates ≥1 provider.
3. The five-point verification runs for every (metric, provider) pair.
4. A complete `source_catalog.json` is written with the required schema.

**Assertions:**
- [ ] `docs/source_catalog.json` exists.
- [ ] Each metric has at least one `source_bindings[]` entry.
- [ ] Each binding has a `verification` block with all 5 checks.
- [ ] `mart.yml` `phase` is set to `A0_complete`.
- [ ] `.skill-invocations.jsonl` carries one new line with
  `skill_name: source-discovery` and `reconstructed: false`.

**Case Verdict:** PASS

### Case 2: Metric with no provider

**Fixture:** Stakeholder input requesting a metric for which no
provider exists.

**Expected behavior:**
1. The skill enumerates candidate providers.
2. All providers fail the verification.
3. The resource-exhaustion protocol records each attempt.
4. The metric is marked `unsupported` with `exhaustion_log` populated.

**Assertions:**
- [ ] Metric appears in `source_catalog.json` with `link_status: unsupported`.
- [ ] `exhaustion_log` is non-empty.

**Case Verdict:** PASS

### Case 3: Mart.yml missing

**Fixture:** Empty working directory.

**Expected behavior:** The skill informs the user that `mart.yml` is
absent and offers to initialize.

**Assertions:**
- [ ] No `source_catalog.json` is written.
- [ ] Output explains the missing prerequisite.

**Case Verdict:** PASS

## Protocol Compliance

- [ ] Skill does not write outside `docs/` and `mart.yml`.
- [ ] Skill does not modify any model files.
- [ ] Skill emits a dogfood log entry on completion.
- [ ] Skill rejects invocation if prerequisites are not met.

## Coverage Notes

End-to-end behavioral runs require a real agent runtime and are deferred
(see `docs/tech-debt-tracker.md` TD-001). Static structural checks cover
this spec.
