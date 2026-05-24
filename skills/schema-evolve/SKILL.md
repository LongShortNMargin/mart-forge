# schema-evolve — Source Schema Change Handler

**Trigger:** "evolve schema for {mart} — source added column {name}"

## Behavior

1. Identify the affected ODS model (explicit column list — no SELECT *).
2. Add the new column to the ODS model's column list.
3. If the column is a business attribute, propagate to DWD:
   - Native: add pass-through field mapping
   - Derived: add calculation SQL
4. Add appropriate tests:
   - `not_null` if the column should never be null
   - `accepted_values` if the column has a known domain
   - Null-rate threshold check
5. Update `schema.yml` documentation with the new column.
6. Update `dqc_scorecard.json` if new controls are needed.

## Schema Drift Detection

ODS models use explicit column lists (no `SELECT *`). This means:
- Unknown column → dbt compile error (schema drift detected)
- Missing column → model fails (explicit reference to removed column)
- Pipeline fails loudly; fix requires ODS model update

## Output

- Updated ODS model SQL
- Updated DWD model SQL (if propagated)
- New/updated tests
- Updated schema.yml
- Diff summary + migration notes
