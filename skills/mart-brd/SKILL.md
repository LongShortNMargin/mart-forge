# mart-brd — Business Requirements Document Generation

**Trigger:** "create business requirements for {domain}" or Phase A detection by using-mart-forge.

## Behavior

1. Accept stakeholder input in any form: case study, data file, verbal description, existing documentation.
2. Run source discovery (delegate to source-discovery skill if needed).
3. Generate structured BRD using `templates/business-requirements.template.md` with all mandatory sections:
   - B-1: Version History
   - B-2: Business Context (business process, purpose, domain, stakeholders, cadence, data sources)
   - B-3: Metrics Breakdown (metrics catalog with source_type + link_status per metric, domain glossary, public/private boundary)
   - B-4: Known Limitations (constraints, unsupported metrics with resource exhaustion evidence, gaps)
4. For each metric, classify:
   - `source_type`: native | derived | hybrid
   - `link_status`: exact | proxy | unsupported | unverified
5. For each candidate comparison link, verify and record:
   - URL, capture timestamp, rendered identity, rendered metric, candidate_result
6. Present BRD for operator review and grading.

## Hard Gate

**No TDD generation until this BRD is explicitly signed off by the operator.**

The BRD must receive Grade A from the reviewer before a TDD can be drafted. A Grade B waiver requires explicit authorization with documented rationale.

## Validation Rules

- Every metric has source_type + link_status
- No source asserted without verification evidence
- Business process section is non-empty
- Domain glossary is non-empty
- Stakeholder needs are documented
- All metrics with `unverified` link_status are flagged for resolution
- Public/private boundary is explicit per metric

## Output

- BRD markdown file in the mart's directory
- Link verification evidence table
- Grade request to reviewer
