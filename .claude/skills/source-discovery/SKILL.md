---
name: source-discovery
description: "Phase A0 — discover, verify, and catalog data sources from stakeholder requirements before writing the BRD"
user-invocable: true
---

# source-discovery — Phase A0: Source Discovery

## When to use

Invoke this skill when a stakeholder has provided business requirements
(a brief, a document, or a conversation) and you need to identify which
data sources can fulfill the requested metrics **before** writing the
BRD. This is the mandatory first phase of every new mart.

## Prerequisites

- Stakeholder input describing the metrics or KPIs the mart must serve.
  Acceptable formats: markdown doc, PDF brief, plain-text list, or
  inline prompt.
- Access to the data platform catalog or schema metadata
  (a `sources.yml`, information-schema dump, or API documentation).
- `mart.yml` exists with at least `mart_name` defined.

## Workflow

### Step 1 — Extract metric inventory

Parse the stakeholder input. For each metric capture: `metric_name`,
`metric_definition` (one sentence), `expected_grain`,
`stakeholder_priority` (high / medium / low).

### Step 2 — Provider enumeration

For each metric, enumerate candidate data providers. A provider is any
system, API, database, or file that could supply the raw or
pre-aggregated data. List every plausible provider — do not filter yet.

### Step 3 — Five-point verification per provider

For every (metric, provider) pair, execute the following checks. Each
check produces `pass`, `fail`, or `unknown`.

| # | Check | Pass criteria |
|---|-------|---------------|
| 1 | Availability | Endpoint/table/API is reachable and returns data |
| 2 | Asset identity | Specific table, endpoint, or dataset is unambiguously identified |
| 3 | License / Terms | Usage is permitted under the provider's license; mark `unknown` if not determinable |
| 4 | Freshness / SLA | Update cadence meets or exceeds the mart's freshness requirement |
| 5 | Semantic match | Provider's field(s) map to the metric's definition without lossy transformation |

### Step 4 — Resource exhaustion protocol

Before marking any metric as `unsupported`:

1. Confirm every enumerated provider has been checked (not just the
   first or most obvious one).
2. Attempt at least one alternative search strategy (derived calculation
   from related fields, proxy metric from a sibling table, federated
   join across two providers).
3. Document every alternative attempted and why each failed.

Only after exhausting all resources may a metric be classified as
`unsupported`.

### Step 5 — Produce source catalog

Write `docs/source_catalog.json` (path overridable via `mart.yml`).
Schema:

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

### Step 6 — Update mart.yml

Set `source_catalog_path` to the written file path. Set `phase` to
`A0_complete`.

### Step 7 — Append skill-invocation log

Append one line to `.skill-invocations.jsonl` at the project root:

```json
{"timestamp": "<ISO-8601>", "skill_name": "source-discovery", "input_artifact": "<stakeholder input path>", "output_artifact": "docs/source_catalog.json", "checkpoint": "A0_complete", "reconstructed": false}
```

## Output format

Primary artifact: `docs/source_catalog.json`.
Secondary: updated `mart.yml`, appended `.skill-invocations.jsonl`.

## NOT for

- Writing the BRD itself (use `/mart-brd` after this skill completes).
- Reviewing an existing mart's sources (use `/mart-review`).
- Running dbt or building models.
- Situations where the source catalog already exists and is up to date.
