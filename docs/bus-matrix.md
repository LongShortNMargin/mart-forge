# Bus Matrix — Conformed Dimension Guide

## What Is a Bus Matrix?

The bus matrix is a foundational Kimball concept that maps the relationship between
fact tables (business processes) and the dimensions that describe them. It serves as
the blueprint for dimensional model integration across an entire data warehouse.

In a bus matrix:
- **Rows** represent business processes, each backed by one or more fact tables.
- **Columns** represent conformed dimensions shared across those processes.
- **X marks** indicate that a fact table uses that dimension.

The bus matrix ensures that dimensions are designed once and reused everywhere,
preventing the "stovepipe" problem where each fact table invents its own incompatible
version of the same descriptive data.

## Why Conformed Dimensions Matter

A conformed dimension is a dimension table that is shared — with identical structure,
keys, and attribute values — across multiple fact tables. When two fact tables both
join to the same `dim_instrument` table, analysts can drill across both processes
using a single consistent set of filters.

**Without conformed dimensions:** Each mart builds its own instrument lookup, leading
to conflicting names, missing attributes, and impossible cross-process analysis.

**With conformed dimensions:** A single `dim_instrument` is the authority. Every fact
table references it by surrogate key, and every dashboard filter works everywhere.

## Rules for Conformed Dimensions

1. **Single source of truth.** Each conformed dimension is defined exactly once, in
   the `dim/` layer. No fact table may redefine or extend it inline.

2. **Shared grain.** The dimension grain must be consistent for all consumers. If
   `dim_instrument` is at the individual-instrument grain, every fact table that
   joins it must do so at that grain (or aggregate after the join).

3. **Consistent naming.** Column names in the dimension table are authoritative. Fact
   tables must not rename dimension attributes when denormalizing into ADS.

4. **Surrogate key contract.** Every conformed dimension exposes a surrogate key
   (`{entity}_sk`) that fact tables use as the foreign key. Business keys
   (`{entity}_bk`) are retained for traceability but not used for joins at the
   DWD layer and beyond.

5. **Versioning via SCD.** When a dimension attribute changes over time, use SCD Type 2
   with `valid_from`, `valid_to`, and `is_current` columns. Fact tables join on
   the surrogate key, which naturally resolves to the correct version.

6. **Seed-backed when appropriate.** Static or slowly changing reference data (e.g.,
   exchange codes, country mappings) may be maintained as dbt seeds that feed
   into the dimension build.

## Template Bus Matrix

The following template shows how to document fact-to-dimension relationships for
a mart. Replace the example names with your actual entities.

### Example: Financial Instruments Mart

| Business Process (Fact)      | dim_instrument | dim_exchange | dim_calendar | dim_strategy | dim_account |
|------------------------------|:--------------:|:------------:|:------------:|:------------:|:-----------:|
| dwd_trades_daily             |       X        |      X       |      X       |      X       |      X      |
| dwd_options_daily            |       X        |      X       |      X       |              |             |
| dwd_dividends_quarterly      |       X        |      X       |      X       |              |      X      |
| dws_volume_daily             |       X        |      X       |      X       |              |             |
| dws_performance_monthly      |       X        |              |      X       |      X       |      X      |

**Reading the matrix:** `dwd_trades_daily` uses all five dimensions. An analyst can
filter trades by instrument, exchange, date, strategy, or account. `dwd_options_daily`
uses only instrument, exchange, and calendar — it has no strategy or account context.

### Blank Template

Copy this template when starting a new mart:

| Business Process (Fact)      | dim_??? | dim_??? | dim_??? | dim_??? |
|------------------------------|:-------:|:-------:|:-------:|:-------:|
| dwd_{entity}_{grain}         |         |         |         |         |
| dwd_{entity}_{grain}         |         |         |         |         |
| dws_{entity}_{grain}         |         |         |         |         |

## Building the Bus Matrix

### Step 1: List Business Processes

Start with the BRD (Business Requirements Document). Each stakeholder question
implies a business process. "How much volume traded daily?" implies a daily-trade
fact table.

### Step 2: Identify Candidate Dimensions

For each fact, ask: "What descriptive attributes do stakeholders want to filter,
group, or label by?" Each answer is a candidate dimension.

### Step 3: Conform and Deduplicate

Multiple facts may reference "instrument" — unify these into a single
`dim_instrument` definition. Resolve grain conflicts (does "instrument" mean
ticker, or ticker + expiry for options?).

### Step 4: Fill the Matrix

Mark X where each fact uses each dimension. Gaps are informative — they show
which processes are isolated and which are well-integrated.

### Step 5: Validate with Stakeholders

The bus matrix is a communication tool. Review it with business stakeholders to
confirm that the cross-process analysis paths make sense.

## Bus Matrix in mart-forge

In mart-forge, the bus matrix is documented in the mart's BRD and referenced
during TDD design. The `/mart-review` skill checks that every FK relationship
declared in `mart.yml` has a corresponding conformed dimension in the `dim/` layer.

The matrix also drives DQC control #2 (FK Integrity): every X in the matrix
implies a foreign key relationship that must be tested.

## Common Anti-Patterns

| Anti-Pattern                     | Problem                                    | Fix                              |
|----------------------------------|--------------------------------------------|----------------------------------|
| Fact-local dimension columns     | Attributes duplicated, drift over time      | Extract to conformed DIM         |
| Dimension without surrogate key  | Fragile joins on natural keys               | Add `{entity}_sk`                |
| Unshared "private" dimensions    | Cross-process analysis impossible           | Conform or document why isolated |
| Grain mismatch in join           | Fan-out or lost rows                        | Align grain before joining       |
