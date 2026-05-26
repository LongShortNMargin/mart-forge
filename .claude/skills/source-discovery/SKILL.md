---
name: source-discovery
description: "Phase A0 -- discover, verify, and catalog data sources from stakeholder requirements before writing the BRD"
user-invocable: true
---

# source-discovery -- Phase A0: Source Discovery

## When to use

Invoke this skill when a stakeholder has provided business requirements (a brief,
a document, or a conversation) and you need to identify which data sources can
fulfill the requested metrics **before** writing the BRD. This is the mandatory
first phase of every new mart.

## Prerequisites

- Stakeholder input describing the metrics or KPIs the mart must serve.
  Acceptable formats: markdown doc, PDF brief, plain-text list, or inline prompt.
- Access to the data platform catalog or schema metadata (e.g., a `sources.yml`,
  information-schema dump, or API documentation for external providers).
- `mart.yml` must exist with at least `mart_name` defined.

## Workflow

### Step 1 -- Extract metric inventory

Parse the stakeholder input and produce a deduplicated list of metrics. For each
metric capture:

- `metric_name` -- human-readable label.
- `metric_definition` -- one-sentence business definition.
- `expected_grain` -- the lowest granularity the stakeholder expects (e.g., daily
  per-user, hourly per-device).
- `stakeholder_priority` -- high / medium / low, inferred from context.

### Step 2 -- Provider enumeration

For each metric, enumerate candidate data providers. A provider is any system,
API, database, or file that could supply the raw or pre-aggregated data. List
every plausible provider -- do not filter yet.

### Step 3 -- Five-point verification per provider

For every (metric, provider) pair, execute the following checks. Each check
produces a status of `pass`, `fail`, or `unknown`.

| # | Check | Pass criteria |
|---|-------|---------------|
| 1 | **Availability** | The provider endpoint/table/API is reachable and returns data. |
| 2 | **Asset identity** | The specific table, endpoint, or dataset is unambiguously identified (schema + table name, API path, file glob). |
| 3 | **License / Terms** | Usage is permitted under the provider's license or data-sharing agreement. Mark `unknown` if you cannot determine terms programmatically. |
| 4 | **Freshness / SLA** | The provider updates at a cadence that meets or exceeds the mart's required freshness. Document the cadence. |
| 5 | **Semantic match** | The provider's field(s) map to the metric's definition without lossy transformation. Document the mapping. |

### Step 4 -- Resource exhaustion protocol

Before marking any metric as `unsupported`:

1. Confirm that **every** enumerated provider has been checked (not just the
   first or most obvious one).
2. Attempt at least one alternative search strategy (e.g., derived calculation
   from related fields, proxy metric from a sibling table, federated join across
   two providers).
3. Document the alternatives attempted and why each failed.

Only after exhausting all resources may a metric be classified as `unsupported`.

### Step 5 -- Produce source catalog

Write `source_catalog.json` to the path specified in `mart.yml` (default:
`docs/source_catalog.json`). Schema:

```json
{
  "mart_name": "<string>",
  "generated_at": "<ISO-8601>",
  "metrics": [
    {
      "metric_name": "<string>",
      "metric_definition": "<string>",
      "expected_grain": "<string>",
      "stakeholder_priority": "high|medium|low",
      "source_bindings": [
        {
          "provider": "<string>",
          "asset": "<schema.table or API path>",
          "fields": ["<field1>", "<field2>"],
          "source_type": "native|derived|hybrid",
          "link_status": "exact|proxy|unsupported|unverified",
          "verification": {
            "availability": "pass|fail|unknown",
            "asset_identity": "pass|fail|unknown",
            "license": "pass|fail|unknown",
            "freshness": "pass|fail|unknown",
            "semantic_match": "pass|fail|unknown"
          },
          "freshness_cadence": "<string>",
          "notes": "<string>"
        }
      ],
      "exhaustion_log": ["<attempted alternative 1>", "..."]
    }
  ]
}
```

### Step 6 -- Update mart.yml

Set `source_catalog_path` to the written file path. Set `phase` to `A0_complete`.

## Output format

Primary artifact: `docs/source_catalog.json`.
Secondary: updated `mart.yml`.

## NOT for

- Writing the BRD itself (use `/mart-brd` after this skill completes).
- Reviewing an existing mart's sources (use `/mart-review`).
- Running dbt or building models.
- Situations where the source catalog already exists and is up to date.
