# Bus Matrix Guide

The bus matrix is the backbone of a Kimball dimensional model. It maps fact tables to conformed dimensions, ensuring consistent analysis across the data warehouse.

## Structure

```
                        dim_date  dim_entity_1  dim_entity_2  dim_category
fact_event_di              X          X                            X
fact_transaction_di        X          X              X
fact_snapshot_di           X          X              X             X
```

## Rules

1. **Every fact table must connect to dim_date.** Date is the universal dimension.
2. **Conformed dimensions are shared definitions.** A dimension used across multiple fact tables must have one canonical definition.
3. **Role-playing dimensions** are the same dimension used in different roles (e.g., dim_date as `order_date`, `ship_date`, `delivery_date`). Implement as views or aliases pointing to the same base dimension.
4. **Drill-across queries** work because conformed dimensions share the same keys and attributes across fact tables.

## Creating a Bus Matrix

### Step 1: List all fact tables

Identify every measurable business process that becomes a fact table.

### Step 2: List all dimensions

Identify every descriptive context needed across all fact tables.

### Step 3: Map intersections

For each fact-dimension pair, mark `X` if that dimension provides context for that fact table.

### Step 4: Identify conformed dimensions

Any dimension that appears in more than one fact table must be conformed (single definition, shared keys).

## Example

For an e-commerce domain:

```
                        dim_date  dim_customer  dim_product  dim_store
fact_order_line_di         X          X             X           X
fact_return_di             X          X             X           X
fact_inventory_di          X                        X           X
```

`dim_date`, `dim_product`, and `dim_store` are conformed dimensions shared across all fact tables.

## Validation

The mart-review skill checks:
- Every fact table appears in the bus matrix
- Every dimension referenced by a fact table FK exists in the matrix
- Conformed dimensions have consistent definitions
