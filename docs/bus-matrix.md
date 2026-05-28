# Bus Matrix

A bus matrix is the single page that proves your warehouse has a coherent
conformed-dimension model. It is required in every TDD at §T-5.

## The shape

Rows are business processes (or fact tables — one per row). Columns are
conformed dimensions. An `X` at the intersection means that fact table
participates in that dimension.

```
                    dim_date  dim_entity  dim_product  dim_geography
fact_orders         X         X           X            X
fact_inventory      X                     X            X
fact_returns        X         X           X
fact_pricing        X                     X            X
```

## Rules

1. **One row per fact, one column per dimension.** If a process produces
   more than one fact (rollups at different grains, for example), each
   gets its own row.
2. **Date is always a dimension.** Every fact joins to `dim_date` for
   time-series slicing.
3. **`dim_*` for conformed dimensions only.** Local, non-conformed
   lookup tables that exist only inside one DWD layer do not appear in
   the bus matrix.
4. **An empty column is a bad smell.** If a dimension has no `X` in any
   row, it is unused — either delete it or document why it must exist
   (e.g., near-term roadmap).

## Filling it out from a TDD

The agent fills the bus matrix at TDD authoring time, after the 4-step
Kimball method (T-4) has identified the business processes and
dimensions:

1. From T-4 step 1, list every business process — one per row.
2. From T-4 step 3, list every dimension — one per column.
3. For each (process, dimension) pair, ask whether the fact table for
   that process carries a foreign key to that dimension.
4. Mark `X` where the answer is yes.

## Common mistakes

- **Renaming a dimension between facts.** `dim_date` in one row,
  `dim_calendar` in another row is a non-conformed mistake. Pick one.
- **Putting dimensions in rows.** This is a roles-and-responsibilities
  matrix, not a join matrix. Roles go elsewhere.
- **Cells that aren't `X` or empty.** Anything other than `X` or an
  empty cell is structural noise. `?` is not allowed at sign-off.

## Referenced from

- `SPEC.md` §4.5 T-5.
- `templates/tech-design-doc.template.md` §T-5.
- `scripts/lint_tdd.py` (validates that T-5 has at least one fact row
  and at least one dimension column).
