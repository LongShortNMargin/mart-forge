# mart-forge

A methodology-first, agent-executable specification for scaffolding and reviewing Kimball data warehouses.

## What is mart-forge?

mart-forge provides the Kimball methodology as structured templates and agent skills — covering dimensional design, layered transforms, and a control-catalog-based quality framework. It turns vague stakeholder input into a working, tested data warehouse with full lineage and governance.

**Core value:** Structured methodology at the transform and governance layer. Agents can write SQL, but they lack architectural intent — no bus matrix, no grain discipline, no conformed dimensions. mart-forge bridges that gap.

## Quick Start

```bash
# Install
pip install mart-forge

# Or use as a Claude Code plugin
claude plugin install /path/to/mart-forge
```

### Lifecycle Phases

```
stakeholder input → [Phase A] BRD → [Phase B] TDD → sign-off → [Phase C] scaffold → [Phase D] DQC → [Phase E] presentation
(vague)             (domain model)   (physical design   (gate)     (dbt project)       (tests +         (dashboard)
                                      + calculations)                                    scorecard)
```

1. **Phase A — Business Requirements (BRD):** Accept stakeholder input, produce a structured BRD with metrics catalog, domain glossary, data sources, and acceptance criteria.
2. **Phase B — Technical Design (TDD):** From the BRD, produce a complete Kimball design: bus matrix, grain declaration, ODS/DIM/DWD/DWS/ADS table specs with column-level calculations.
3. **Phase C — Scaffold:** Generate a complete dbt project from the signed-off TDD.
4. **Phase D — DQC Verification:** Run the 8-class control catalog and produce a machine-readable scorecard.
5. **Phase E — Presentation:** Optional dashboard with metric traceability and verification links.

**Hard gates enforced:** No TDD without a signed-off BRD. No scaffold without a signed-off TDD.

## Architecture

### Data Layers (Kimball Four-Tier + ADS)

| Layer | Purpose | Naming Pattern | Materialization |
|-------|---------|---------------|-----------------|
| **ODS** | Raw ingestion, no transforms | `{prefix}_ods_{source}_{entity}` | incremental |
| **DIM** | Conformed dimensions, seed-backed | `{prefix}_dim_{entity}` | table |
| **DWD** | Cleaned facts with business keys | `{prefix}_dwd_{grain}_{entity}_di` | incremental |
| **DWS** | Aggregations, rollups, windows | `{prefix}_dws_{dims}_{metric}_{window}` | table |
| **ADS** | Application-facing One Big Tables | `{prefix}_ads_{consumer}_{purpose}` | table |

### DQC Control Catalog (8 Classes)

Every mart must implement all applicable control classes:

| Control Class | Checks | Severity |
|---------------|--------|----------|
| PK Integrity | PK not null + unique | `error` |
| FK Integrity | FK resolves to DIM row | `error` |
| Freshness | Data within SLA window | `error` |
| Completeness / Volume | Row count within expected range | `warn` |
| Accepted Ranges | Numeric metrics within bounds | `warn` |
| Duplicate Detection | No duplicate business keys | `error` |
| Null-Rate Threshold | Non-PK columns under null % | `warn` |
| Business Reconciliation | Metrics match external source | `error`/`warn` |

### Metric Classification

Every metric declares:
- **Source type:** `native` (pass-through) | `derived` (computed, explicit SQL required) | `hybrid` (mixed, reconciliation rules required)
- **Link status:** `exact` (verified external match) | `proxy` (advisory comparator only) | `unsupported` (no external source after resource exhaustion)

## Agent Skills

mart-forge ships as a Claude Code plugin with skills that enforce the lifecycle:

| Skill | Phase | Purpose |
|-------|-------|---------|
| `using-mart-forge` | Bootstrap | Phase detection + skill routing on session start |
| `mart-brd` | A | Generate BRD from stakeholder input |
| `mart-tdd` | B | Generate TDD from signed-off BRD |
| `mart-bootstrap` | C | Scaffold dbt project from signed-off TDD |
| `mart-dqc` | D | Generate DQC tests + scorecard |
| `dqc-audit` | D | Audit DQC coverage against control catalog |
| `schema-evolve` | Maintenance | Handle source schema changes |
| `mart-review` | Review | Production readiness assessment |
| `source-discovery` | A/B | Verify data source availability and fitness |

## GME Options Mart — Live Example

`examples/gme-options-mart/` contains a real conformance trial against the mart-forge lifecycle:

- **BRD + TDD:** Scoped to public GME options-chain analytics (spot, max pain, GEX, IV, P/C ratio).
- **Streamlit Dashboard:** Connects to a live MotherDuck warehouse (`gme_db`) via `MOTHERDUCK_TOKEN`. Renders real charts when data is available; shows explicit BLOCKED/SCHEMA UNVERIFIED status when it is not.
- **Coverage Panel:** Shows which metrics are verified vs pending, with numerator/denominator coverage.

Phase F (framework quality iteration) continues in parallel — incomplete metric coverage is recorded, not hidden.

## Repository Structure

```
mart-forge/
├── README.md
├── CLAUDE.md                     # Project rules for agent sessions
├── SPEC.md                       # Governance and conformance contract
├── METHODOLOGY.md                # Full Kimball methodology reference
├── pyproject.toml
├── .claude-plugin/plugin.json    # Claude Code plugin manifest
├── hooks/hooks.json              # SessionStart hooks
├── templates/                    # BRD, TDD, mart.yml, model, test, pipeline templates
├── skills/                       # Agent skills with hard gates
├── scripts/                      # DQC update, validation scripts
├── docs/                         # Methodology documentation
├── examples/                     # Conformance trial examples
│   └── gme-options-mart/         # Live GME public analytics example
└── tests/                        # Framework validation tests
```

## Requirements

- Python 3.11+
- dbt-core + dbt-duckdb (reference implementation)
- DuckDB (local development and CI)

## License

Apache 2.0 — see [LICENSE](LICENSE).
