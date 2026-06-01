# Technical Design Document: sample-mart (fixture, UNSIGNED)

> Fixture used as the adversarial input for the signing-gate CI step:
> running `scripts/lint_signed_tdd.py` against this file MUST exit 1.
> Generic example content.

## T-1: Source Bindings

| Source       | Pull cadence | Grain       | Owner         |
|--------------|--------------|-------------|---------------|
| orders.csv   | daily        | order_line  | example-owner |

## T-2: Layer Design

ODS → DIM → DWD → DWS → ADS.

## Signature

| Role          | Name | Date | Signature |
|---------------|------|------|-----------|
| Lead engineer | ____ | ____ | ____      |
