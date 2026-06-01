# Business Requirements Document: sample-mart (fixture, signed)

> Fixture used by `scripts/lint_signed_brd.py` regression tests and by
> the CI step that proves the signing-gate linter fires on real
> documents via the production code path. Generic example content.

## B-1: Version History

| Version | Date       | Author        | Changes        |
|---------|------------|---------------|----------------|
| 1.0     | 2026-06-01 | example-owner | Initial draft  |

## B-2: Business Context

Generic business context: an example orders mart used as a fixture for
the signing-gate linter.

## B-3: Metrics

| Metric       | Definition                  | Source       | Status   |
|--------------|-----------------------------|--------------|----------|
| order_count  | distinct order identifiers  | orders.csv   | verified |

## B-4: Unsupported Metrics

None — every metric in this fixture is backed by a verified source.

## B-5: Acceptance Criteria

The mart can be considered ready when the fixture build passes.

## Signature

| Role     | Name           | Date       | Signature |
|----------|----------------|------------|-----------|
| Sponsor  | example-owner  | 2026-06-01 | signed    |
