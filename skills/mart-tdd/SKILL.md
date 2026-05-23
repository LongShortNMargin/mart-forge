# mart-tdd — Technical Design Document Generation

**Trigger:** "create tech design for {mart}" or Phase B detection by using-mart-forge.

**Prerequisite:** Signed-off BRD (Grade A or waived) must exist.

## Behavior

1. Read signed-off BRD and data source schemas.
2. Generate TDD using `templates/tech-design-doc.template.md` with all mandatory sections:
   - T-1: Version History
   - T-2: Design Reasoning (4-step Kimball: process → grain → dimensions → facts)
   - T-3: Table Summary (all layers with grain and materialization)
   - T-4: Data Architecture Diagram
   - T-5: Column Specification (6-column format per table)
   - T-6: ODS Table Design (full ODS contract: source, grain, partition, strategy, unique_key, backfill, restatement, provenance)
   - T-7: Dimension Table Design (SCD strategy, unknown member)
   - T-8: Fact Table Design (source_type per metric, native pass-through, derived SQL)
   - T-9: Count Aggregation Design (explicit SQL)
   - T-10: Performance Aggregation Design (explicit SQL)
   - T-11: Presentation Table Design (metric-to-column traceability)
   - T-12: Physical Design (column-level spec for all table types)
   - T-13: Implementation Specification (dbt config)
   - T-14: DQC Plan (8-class control catalog with applicability)
   - T-15: Test Inventory
   - T-16: Operations (schedule, SLA, alerting)
   - T-17: Known Limitations
3. Ensure every metric traces from BRD → table design → physical design → dashboard spec.
4. Present for reviewer sign-off and grading.

## Hard Gate

**No scaffold until this TDD is explicitly signed off.**

The TDD must receive Grade A. A Grade B waiver requires explicit authorization.

## Validation Rules

- All 4 Kimball design steps present in T-2
- Bus matrix has ≥1 fact and ≥1 dimension
- Every ODS table has all 8 contract fields (source, grain, partition, strategy, unique_key, backfill, restatement, provenance)
- Every column has all 6 physical design fields
- `calculation` contains actual SQL/formula for derived columns (no placeholders)
- Every table in T-3 has entries in T-5 and T-12
- No `unverified` link_status metrics at sign-off
- Table types not required have `not_applicable` rationale

## Output

- TDD markdown file in the mart's directory
- Grade request to reviewer
