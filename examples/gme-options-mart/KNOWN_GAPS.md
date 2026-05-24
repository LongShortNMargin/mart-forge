# GME Options Mart — Known Gaps

Last updated: 2026-05-24
Status: MVP Checkpoint (Phase F iteration continues)

---

## Coverage Summary

**Verified rendered metrics: 0 / 10** (0%)

All 10 public metrics are intended to load from MotherDuck when data is available. Column schemas and live data availability are pending runtime verification. None have completed external DQC reconciliation. Values are data observations from the warehouse pipeline, not fact-checked figures.

---

## Gap Categories

### 1. Data Correctness / DQC

| Gap | Impact | Resolution Path | Priority |
|-----|--------|----------------|----------|
| No external reconciliation tests | Metrics may diverge from reference sources | Implement G-LINK gate with browser-automated verification | High |
| GEX formula not externally validated | Net GEX magnitude may differ from commercial providers | Compare formula output against known reference day | High |
| Max pain algorithm unverified | Strike selection may differ from reference sources | Side-by-side comparison on same date | Medium |
| IV percentile window undocumented | Trailing window length affects rank | Document window; compare with external providers | Medium |
| P/C ratio methodology | Volume vs OI-based ratio may differ by provider | Clarify methodology in BRD | Low |

### 2. Source Verification

| Gap | Impact | Resolution Path | Priority |
|-----|--------|----------------|----------|
| External comparison links not browser-verified | G-LINK gate not satisfied | Playwright verification pass | High |
| Data source provider endpoints not runtime-tested | Provider availability unproven | Runtime test of data source endpoints (pending source confirmation) | High |
| No fixture manifest | G-FIXTURE gate not satisfied | Generate manifest with source date + schema hash | Medium |

### 3. Pipeline / Reproduction

| Gap | Impact | Resolution Path | Priority |
|-----|--------|----------------|----------|
| ODS ingestion script not in public repo | Cannot reproduce pipeline from scratch | Add ingestion script or document manual steps | High |
| No CI pipeline for example mart | Harness tests run but mart-specific CI absent | Add GitHub Actions workflow per template | Medium |
| Rerun idempotence untested | G-ODS gate partial | Add rerun test that asserts row count stability | Medium |

### 4. Dashboard / Presentation

| Gap | Impact | Resolution Path | Priority |
|-----|--------|----------------|----------|
| Snapshot column reconciliation partial | Live DWS surface lacks `provider`/`pull_ts_utc` (ODS provenance); dashboard projection corrected to exclude them. Remaining columns pending full reconciliation. | Runtime schema verification against MotherDuck | High |
| No IV term structure chart | Missing visualization for skew analysis | Add once IV surface data available | Low |
| No OI delta (day-over-day) | Cannot show OI flow changes | Requires 2+ days of ODS history | Medium |
| No fixture/demo mode toggle | Demo without live token shows blocked state only | Add fixture mode with sample data and banner | Low |

### 5. TDD Completeness

| Gap | Impact | Resolution Path | Priority |
|-----|--------|----------------|----------|
| TDD sections T-7 through T-13 incomplete | Dimension, fact, and implementation specs missing | Populate during Phase F iteration | Medium |
| TDD sections T-15, T-16 incomplete | Test inventory and operations specs missing | Populate during Phase F iteration | Medium |

---

## Handoff Items

Items requiring operator or Codex verification before promotion:

1. **Live MotherDuck smoke test** — requires `MOTHERDUCK_TOKEN` in a secure environment
2. **External DQC reconciliation** — operator compares dashboard values against reference sites on a live trading day
3. **Source binding confirmation** — operator confirms which endpoints and providers currently feed the warehouse
4. **Column schema reconciliation** — verify TDD column specs match actual MotherDuck table schemas
5. **Provider endpoint runtime test** — confirm data source APIs respond with expected data (provider pending confirmation)
