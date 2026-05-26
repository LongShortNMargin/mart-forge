# Quality Rubric — Skill & Agent Test Evaluation

## Overview

This rubric defines the pass/fail criteria for each skill category in mart-forge.
Test specs reference these criteria by category. A skill passes its test suite only
when ALL applicable criteria are met for every test case.

## Lifecycle Skills

Lifecycle skills manage the progression of a mart from discovery through bootstrap.
They enforce gates, produce structured documents, and must maintain traceability.

### Gate Enforcement

| Criterion                      | Pass                                              | Fail                                              |
|--------------------------------|---------------------------------------------------|---------------------------------------------------|
| Prerequisite gate check        | Skill rejects execution when prerequisite document is unsigned or missing | Skill proceeds without checking prerequisites     |
| Gate status in output          | Output explicitly states gate status (APPROVED / REJECTED) | Gate status is ambiguous or omitted               |
| Rejection reason               | REJECT output includes specific reason and missing prerequisite | REJECT output is generic ("prerequisites not met") |

### Template Compliance

| Criterion                      | Pass                                              | Fail                                              |
|--------------------------------|---------------------------------------------------|---------------------------------------------------|
| Required sections present      | All sections defined in the template are present in output | One or more required sections missing             |
| Section ordering               | Sections appear in the order defined by the template | Sections are reordered or interleaved             |
| Frontmatter fields             | All required frontmatter keys (grade, status, mart_prefix, grain) present and non-empty | Frontmatter missing keys or contains empty values |

### Output Format

| Criterion                      | Pass                                              | Fail                                              |
|--------------------------------|---------------------------------------------------|---------------------------------------------------|
| Valid markdown                  | Output parses as valid markdown with no broken links or unclosed fences | Markdown parse errors                             |
| Valid JSON (where applicable)  | JSON outputs parse without error, match expected schema | JSON parse error or schema mismatch               |
| File placement                 | Output files written to correct directory per convention | Files written to wrong directory                  |

### Traceability

| Criterion                      | Pass                                              | Fail                                              |
|--------------------------------|---------------------------------------------------|---------------------------------------------------|
| Metric end-to-end trace        | Every metric in the output traces from stakeholder question through BRD, TDD, to model | Metric appears in output without upstream trace   |
| Source tagging                  | Every numeric value or metric is tagged with source_type (native/derived) | Metrics lack source_type tags                     |
| Provider binding               | Each metric binds to a declared provider           | Metric has no provider or references undeclared provider |

## Quality Skills

Quality skills validate pipeline correctness and data integrity. They must be
thorough, specific, and produce actionable findings.

### Control Coverage

| Criterion                      | Pass                                              | Fail                                              |
|--------------------------------|---------------------------------------------------|---------------------------------------------------|
| All 8 DQC controls evaluated   | Output explicitly addresses all 8 controls in the catalog | One or more controls skipped without justification |
| N/A controls documented        | Controls not applicable to the target are marked N/A with reason | Non-applicable controls silently omitted          |
| Control ID referenced          | Findings reference control by ID and name (e.g., "Control 3: Freshness") | Findings use ad-hoc descriptions without control ID |

### Severity Accuracy

| Criterion                      | Pass                                              | Fail                                              |
|--------------------------------|---------------------------------------------------|---------------------------------------------------|
| Severity matches catalog       | Finding severity matches the catalog definition (error vs warn) | Severity is invented or mismatched                |
| Escalation rules applied       | Repeated warnings flagged for escalation per the 3-run rule | Chronic warnings ignored                          |

### Finding Specificity

| Criterion                      | Pass                                              | Fail                                              |
|--------------------------------|---------------------------------------------------|---------------------------------------------------|
| Line-level references          | Findings reference specific model files and line numbers | Findings are vague ("some model has an issue")    |
| Actionable recommendation      | Each finding includes a concrete fix suggestion    | Findings state problems without solutions         |
| Evidence included              | Findings include sample data, row counts, or query results | Findings are assertions without evidence          |

## Utility Skills

Utility skills handle routing, state detection, and general-purpose operations.
They must accurately assess the current state and route to the correct next action.

### Correct Routing

| Criterion                      | Pass                                              | Fail                                              |
|--------------------------------|---------------------------------------------------|---------------------------------------------------|
| Next skill identified          | Skill correctly identifies the next lifecycle skill to invoke | Wrong skill suggested or no suggestion            |
| Routing reason documented      | Output explains why this routing was chosen        | Routing without rationale                         |
| Blocked state detected         | When no forward progress is possible, skill reports blocked status | Skill suggests a next step that cannot succeed    |

### State Detection Accuracy

| Criterion                      | Pass                                              | Fail                                              |
|--------------------------------|---------------------------------------------------|---------------------------------------------------|
| Current phase identified       | Skill correctly identifies the current lifecycle phase | Phase misidentified                               |
| Artifact inventory accurate    | Skill lists existing artifacts and their statuses correctly | Artifacts missed or phantom artifacts reported    |
| Gap analysis correct           | Missing prerequisites are correctly identified     | False positives or false negatives in gap analysis |

## Scoring

Each test case is evaluated against all applicable criteria for its category.

| Result        | Definition                                              |
|---------------|---------------------------------------------------------|
| **PASS**      | All criteria met. No failures, no partial compliance.   |
| **PARTIAL**   | Most criteria met but one or more minor gaps exist.     |
| **FAIL**      | One or more critical criteria not met.                  |

A skill's overall status is determined by its worst test case result:
- All PASS = skill passes
- Any PARTIAL = skill is conditionally approved (issues logged)
- Any FAIL = skill fails (must fix and retest)

## Test Execution Protocol

1. Set up the test fixture (input documents, file structure).
2. Invoke the skill with the fixture as input.
3. Capture the skill's output (files, stdout, stderr).
4. Evaluate each criterion in the applicable rubric section.
5. Record results in `tests/skill-testing/results/` as a timestamped JSON file.

Results schema:

```json
{
  "skill": "source-discovery",
  "test_case": "happy-path",
  "timestamp": "2025-01-15T10:30:00Z",
  "result": "PASS",
  "criteria": [
    {"name": "gate_enforcement", "result": "PASS", "notes": ""},
    {"name": "template_compliance", "result": "PASS", "notes": ""}
  ]
}
```
