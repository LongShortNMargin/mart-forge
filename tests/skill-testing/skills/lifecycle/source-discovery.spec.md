# Skill Spec: /source-discovery

## Summary

The `/source-discovery` skill identifies available data providers for metrics
defined in a stakeholder requirements document. It produces a source catalog that
maps each business metric to one or more providers, validates that providers
deliver data for the correct asset, and flags metrics that cannot be sourced.

## Domain

### Files Read
- `docs/stakeholder-requirements.md` — input document containing business questions and required metrics
- `mart.yml` — existing provider registry (if any)

### Files Written
- `docs/source-catalog.md` — output: provider-to-metric mapping with availability status
- `docs/source-catalog.json` — machine-readable version of the catalog

### Directories Owned
- `docs/` (writes source catalog artifacts)

## Static Assertions

### Frontmatter Requirements

The output `source-catalog.md` must contain frontmatter with these fields:

| Field            | Type     | Required | Description                          |
|------------------|----------|----------|--------------------------------------|
| `status`         | string   | yes      | `complete`, `partial`, or `blocked`  |
| `mart_prefix`    | string   | yes      | The mart's short prefix              |
| `metric_count`   | integer  | yes      | Total metrics evaluated              |
| `bound_count`    | integer  | yes      | Metrics successfully bound to provider |
| `unbound_count`  | integer  | yes      | Metrics with no viable provider      |
| `discovery_date` | string   | yes      | ISO 8601 date of discovery run       |

### Required Output Schema

The `source-catalog.json` must conform to this structure:

```json
{
  "metrics": [
    {
      "name": "string",
      "description": "string",
      "providers": [
        {
          "name": "string",
          "type": "api | file | database",
          "status": "bound | unsupported | rejected",
          "rejection_reason": "string | null"
        }
      ],
      "source_type": "native | derived",
      "bound": true
    }
  ],
  "summary": {
    "total_metrics": 0,
    "bound": 0,
    "unsupported": 0,
    "rejected": 0
  }
}
```

## Test Cases

### TC-1: Happy Path — Full Provider Coverage

**Fixture:**
A stakeholder document defining 5 metrics across 3 providers:

- Metric `daily_close_price` — available from `provider_alpha` (API)
- Metric `daily_volume` — available from `provider_alpha` (API)
- Metric `quarterly_dividend` — available from `provider_beta` (API)
- Metric `instrument_sector` — available from `provider_gamma` (file)
- Metric `historical_splits` — available from `provider_gamma` (file)

**Expected Behavior:**
1. Skill reads the stakeholder document and extracts all 5 metrics.
2. Skill queries each provider's capability manifest.
3. Skill produces a source catalog with all 5 metrics bound.

**Assertions:**
- `source-catalog.md` frontmatter: `status: complete`, `metric_count: 5`, `bound_count: 5`, `unbound_count: 0`.
- `source-catalog.json` has 5 entries in `metrics[]`, all with `bound: true`.
- Each metric's `providers[]` array contains at least one entry with `status: bound`.
- `summary.total_metrics == 5`, `summary.bound == 5`.

**Rubric Categories:** gate enforcement, template compliance, output format, traceability.

---

### TC-2: No Providers Found — Unsupported Metric

**Fixture:**
A stakeholder document defining 3 metrics, one of which has no available provider:

- Metric `daily_close_price` — available from `provider_alpha`
- Metric `daily_volume` — available from `provider_alpha`
- Metric `insider_sentiment_score` — NO provider in the registry can deliver this

**Expected Behavior:**
1. Skill extracts all 3 metrics.
2. Skill binds 2 metrics successfully.
3. For `insider_sentiment_score`, skill exhausts all registered providers and marks it `unsupported`.
4. Output includes exhaustion evidence: which providers were checked and why each failed.

**Assertions:**
- `source-catalog.md` frontmatter: `status: partial`, `metric_count: 3`, `bound_count: 2`, `unbound_count: 1`.
- The unsupported metric entry has `bound: false`.
- The unsupported metric's `providers[]` array is non-empty (shows checked providers), each with `status: unsupported` and a non-null `rejection_reason`.
- The rejection reasons are specific (e.g., "provider_alpha does not expose sentiment data") not generic ("not available").

**Rubric Categories:** gate enforcement, template compliance, finding specificity.

---

### TC-3: Wrong-Asset Rejection — Provider Returns Mismatched Data

**Fixture:**
A stakeholder document requesting metrics for asset class "equity options":

- Metric `option_open_interest` — `provider_alpha` claims to support it, but returns data for futures contracts, not equity options

**Expected Behavior:**
1. Skill extracts the metric and identifies `provider_alpha` as a candidate.
2. Skill validates that the provider's data matches the requested asset class.
3. Skill detects the asset mismatch (futures vs. equity options).
4. Skill rejects `provider_alpha` for this metric with a specific reason.
5. If no other provider is available, metric is marked `unsupported`.

**Assertions:**
- The metric entry in `source-catalog.json` has `bound: false`.
- `provider_alpha` appears in the metric's `providers[]` with `status: rejected`.
- `rejection_reason` mentions the asset class mismatch explicitly (e.g., "provider returns futures data, requested equity options").
- The provider is NOT marked as `bound` despite claiming support — proxy data is never accepted.
- If a fallback provider exists and matches the correct asset class, the metric may still be bound to the fallback.

**Rubric Categories:** finding specificity, traceability, correct routing.
