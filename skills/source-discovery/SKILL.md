# source-discovery — Data Source Verification

**Trigger:** "discover sources for {domain}" or called by mart-brd during Phase A.

## Behavior

For each candidate data source, verify:

| # | Check | Question | Gate |
|---|-------|----------|------|
| 1 | Provider availability | Does the API/endpoint respond? Is data accessible without paid keys? | Fail → try next provider |
| 2 | Correct identity | Does the response contain the expected entity/asset? | Fail → reject source |
| 3 | License usability | Is data usable under Apache 2.0? Redistribution restrictions? | Fail → document restriction |
| 4 | Freshness fitness | Is data delayed within acceptable SLA for the declared grain? | Fail → document SLA gap |
| 5 | Semantic match | Does the field semantically match the BRD metric definition? | Fail → cannot be exact_match |

## Link Verification Protocol

For each candidate comparison link, record:

| Field | Description |
|-------|------------|
| url | Exact URL tested |
| capture_timestamp | ISO-8601 timestamp |
| rendered_identity | Entity/asset shown on the page |
| rendered_metric | Metric shown on the page |
| candidate_result | exact_match / advisory_proxy / rejected |

### Classification Rules

- Different entity than expected → `rejected` (e.g., wrong ticker)
- Same entity, different metric → `advisory_proxy` if useful, else `rejected`
- `exact_match` requires: correct entity, correct metric, same methodology, evidence

### Resolving Metric-Level link_status

After all candidates for a metric are tested:
- Any `exact_match` → metric link_status = `exact`
- No exact but advisory_proxy exists → metric link_status = `proxy`
- All rejected AND resource exhaustion complete → metric link_status = `unsupported`
- Candidates untested → metric remains `unverified` (must resolve before TDD sign-off)

## Output

Source discovery evidence document with:
- Per-provider verification results (5 checks)
- Per-link verification records
- Resolved metric-level link_status
- Recommendation: which providers to bind in TDD
