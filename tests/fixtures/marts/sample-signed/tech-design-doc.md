# Technical Design Document: sample-mart (fixture, signed)

> Fixture used by `scripts/lint_signed_tdd.py` regression tests and by
> the CI step that proves the signing-gate linter fires on real
> documents via the production code path. Generic example content.

## T-1: Source Bindings

| Source       | Pull cadence | Grain       | Owner         |
|--------------|--------------|-------------|---------------|
| orders.csv   | daily        | order_line  | example-owner |

## T-2: Layer Design

ODS → DIM → DWD → DWS → ADS, following the mart-forge generic
methodology. No layer is skipped.

## T-3: Grain Declaration

`fct_orders` is grained at one row per order_line.

## T-4: DQC Plan

Eight control classes are exercised; see the corresponding
`8-control-dqc-audit` skill catalog for the full list.

## Signature

| Role         | Name           | Date       | Signature |
|--------------|----------------|------------|-----------|
| Lead engineer| example-owner  | 2026-06-01 | signed    |
