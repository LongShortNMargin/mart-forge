---
name: mart-review
description: "Adversarial read-only review of a mart -- grades BRD, TDD, scaffold, and DQC artifacts against the mart-forge spec and returns structured findings"
user-invocable: true
---

# mart-review -- Adversarial Review

## When to use

Invoke this skill to perform a comprehensive, read-only quality review of any
mart-forge project. Use it before signing a BRD or TDD, after scaffold generation,
after a DQC run, or at any point where an independent quality assessment is needed.
This skill never modifies files -- it only reads and reports.

## Prerequisites

- At least one mart-forge artifact exists (BRD, TDD, scaffold, or DQC scorecard).
- `mart.yml` exists at the project root.
- The review is read-only; no write access to the project is required.

## Workflow

### Step 1 -- Determine review scope

Read `mart.yml` and detect which artifacts are present:

| Artifact | Path field in mart.yml | Review module |
|----------|----------------------|---------------|
| Source catalog | `source_catalog_path` | Source bindings |
| BRD | `brd_path` | BRD review |
| TDD | `tdd_path` | TDD review |
| Scaffold | `models/` directory | Scaffold review |
| DQC scorecard | `dqc_scorecard_path` | DQC review |

Review all artifacts that exist. Report which artifacts are missing (informational,
not a failure).

### Step 2 -- BRD review checks

If the BRD exists, evaluate:

| # | Check | Criteria |
|---|-------|----------|
| 1 | **Section completeness** | All four sections (B-1 through B-4) are present and non-empty. |
| 2 | **Metric traceability** | Every metric in B-3 traces back to a source catalog entry. |
| 3 | **Source binding compliance** | Every non-DWS metric has a source binding with `source_type` and `link_status`. |
| 4 | **Unsupported metrics** | All `unsupported` metrics appear in B-4 with exhaustion log. |
| 5 | **Signature block** | Signature table exists with correct format. Both rows present. |
| 6 | **Confidentiality scan** | No internal system names, credentials, API keys, employee names, or proprietary references appear in the document. |
| 7 | **Version history** | B-1 has at least one entry with version, date, author, and summary. |

### Step 3 -- TDD review checks

If the TDD exists, evaluate:

| # | Check | Criteria |
|---|-------|----------|
| 1 | **Section completeness** | All sections T-1 through T-21 are present and non-empty. |
| 2 | **ODS contract validity** | Every ODS contract has all 8 fields (source, grain, partition, incremental_strategy, unique_key, backfill, restatement, provenance). |
| 3 | **Column catalog format** | T-9 uses the 6-column format (column_name, data_type, definition, example_value, calculation, data_source). |
| 4 | **Calculation compliance** | Derived columns have executable SQL in the `calculation` field. Native columns use `"pass-through from <provider>.<field>"` format exactly. No pseudocode or prose. |
| 5 | **BRD-TDD alignment** | Every metric in the signed BRD appears in the TDD. No orphan TDD metrics without BRD backing. |
| 6 | **Gate enforcement** | TDD signature block references a signed BRD (date ordering is valid). |
| 7 | **Confidentiality scan** | Same as BRD check. |

### Step 4 -- Scaffold review checks

If the scaffold exists, evaluate:

| # | Check | Criteria |
|---|-------|----------|
| 1 | **Layer coverage** | Models exist for every layer declared in TDD (ODS, DIM, DWD, DWS, ADS). |
| 2 | **TDD-scaffold alignment** | Every model in the TDD has a corresponding SQL and YAML file. |
| 3 | **Test coverage** | Every model has at least one test in its schema YAML. |
| 4 | **Incremental config** | Models declared as incremental in TDD have `materialized='incremental'` and correct `unique_key`. |
| 5 | **Source definitions** | `sources.yml` exists and defines all ODS sources. |
| 6 | **Dogfood log** | `dogfood-log.jsonl` exists and has a `scaffold_complete` checkpoint. |

### Step 5 -- DQC review checks

If the DQC scorecard exists, evaluate:

| # | Check | Criteria |
|---|-------|----------|
| 1 | **8-class coverage** | All 8 control classes are represented in the scorecard. |
| 2 | **Non-applicable rationale** | Every non-applicable (model, control_class) pair has a documented rationale. |
| 3 | **Gap identification** | All gaps (applicable but untested) are listed. |
| 4 | **Pass rate thresholds** | Flag any control class below 95% pass rate. |
| 5 | **Coverage thresholds** | Flag any control class below 80% coverage. |

### Step 6 -- Grade assignment

Assign an overall grade using this scale:

| Grade | Criteria |
|-------|----------|
| **A -- Exemplary** | All checks pass. No gaps, no confidentiality issues, full traceability. |
| **B -- Satisfactory** | Minor issues only: missing example values, incomplete B-4 entries, cosmetic formatting. No structural or compliance failures. |
| **C -- Needs Work** | Structural issues: missing sections, broken traceability for 1-3 metrics, incomplete ODS contracts. No gate violations. |
| **D -- Deficient** | Gate violations, missing source bindings for non-DWS metrics, pseudocode in calculation columns, or confidentiality leaks. |
| **F -- Fail** | Multiple gate violations, majority of checks failing, or sensitive data exposure. |

### Step 7 -- Produce findings report

Write findings as structured JSON to stdout (do not write to file unless the user
requests it):

```json
{
  "mart_name": "<string>",
  "reviewed_at": "<ISO-8601>",
  "artifacts_reviewed": ["BRD", "TDD", "scaffold", "DQC"],
  "artifacts_missing": ["<list>"],
  "overall_grade": "A|B|C|D|F",
  "findings": [
    {
      "artifact": "BRD|TDD|scaffold|DQC",
      "check": "<check name>",
      "severity": "critical|major|minor|info",
      "status": "pass|fail",
      "detail": "<description of the finding>",
      "location": "<file path or section reference>",
      "recommendation": "<suggested fix>"
    }
  ],
  "summary": {
    "total_checks": "<int>",
    "passed": "<int>",
    "failed": "<int>",
    "critical_failures": "<int>",
    "major_failures": "<int>"
  }
}
```

### Step 8 -- Print human-readable summary

After the JSON output, print a concise summary:

```
Review: <mart_name> | Grade: <grade>
Checks: <passed>/<total> passed | Critical: <N> | Major: <N>
Top issues:
  1. <most severe finding>
  2. <second most severe>
  3. <third most severe>
```

## Output format

Primary: structured findings JSON (to stdout or file on request).
No files modified -- this skill is strictly read-only.

## NOT for

- Fixing issues found during review (make corrections manually, then re-review).
- Writing or modifying BRD, TDD, or scaffold files.
- Running dbt tests (use `/mart-dqc`).
- Routing to the correct phase (use `/using-mart-forge`).
- Approving or signing documents -- the review informs the decision but does not
  sign on behalf of stakeholders.
