# mart-forge

**Methodology-first, agent-executable specification for scaffolding and reviewing Kimball data warehouses.**

mart-forge turns stakeholder requirements into a complete, verified data warehouse — with tests, quality scorecards, and a live dashboard — through a structured lifecycle enforced by AI agent skills.

## What It Does

```
stakeholder doc → /source-discovery → BRD → sign-off → TDD → sign-off → /scaffold → DQC → dashboard
```

Each phase gates the next. No scaffold without a signed Technical Design Document. No TDD without an approved Business Requirements Document. Every metric traces from stakeholder need through table column to dashboard tile.

## Quick Start

```bash
pip install mart-forge
mart-forge init my-mart
cd my-mart
# Follow the guided lifecycle: source-discovery → BRD → TDD → scaffold
```

## For Data Engineers

mart-forge provides opinionated Kimball methodology as structured templates and agent skills:
- **4-tier data layer** (ODS → DIM → DWD → DWS → ADS) with naming conventions and grain rules
- **8-control DQC catalog** with machine-readable scorecards linked to dbt test results
- **Source-native preference** — ingest directly when providers expose metrics; derive only when necessary
- **Incremental checkpoint delivery** — each layer merges independently; defects fix locally

## Canonical Example

See `examples/gme-options-mart/` — a live GME options analytics dashboard built entirely through mart-forge's own skills, proving the framework end-to-end.

## License

MIT
