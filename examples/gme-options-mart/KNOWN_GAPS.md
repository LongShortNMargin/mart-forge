# GME Options Mart — Known Gaps

Last updated: 2026-05-24
Status: MVP Checkpoint (Phase F iteration continues)

---

## Coverage Summary

**Verified rendered metrics: 0 / 10** (0%)

All 10 public metrics load from MotherDuck when data is available and are tagged `[REAL_API]`. None have completed external DQC reconciliation. Values are data observations from the warehouse pipeline, not fact-checked figures.

---

## Gap Categories

### 1. Data Correctness / DQC

| Gap | Impact | Resolution Path | Priority |
|-----|--------|----------------|----------|
| No external reconciliation tests | Metrics may diverge from reference sources | Implement G-LINK gate with browser-automated verification | High |
| GEX formula not externally validated | Net GEX magnitude may differ from SpotGamma/similar | Compare formula output against known reference day | High |
| Max pain algorithm unverified | Strike selection may differ from swaggystocks | Side-by-side comparison on same date | Medium |
| IV percentile window undocumented | Trailing window length affects rank | Document window; compare with marketchameleon | Medium |
| P/C ratio methodology | Volume vs OI-based ratio may differ by provider | Clarify methodology in BRD | Low |

### 2. Source Verification

| Gap | Impact | Resolution Path | Priority |
|-----|--------|----------------|----------|
| BRD comparison links not browser-verified | G-LINK gate not satisfied | Playwright verification pass | High |
| OpenBB CBOE endpoint stability | Free-tier may change without notice | Document fallback to yfinance; test both | Medium |
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
| No IV term structure chart | Missing visualization for skew analysis | Add once IV surface data available | Low |
| No OI delta (day-over-day) | Cannot show OI flow changes | Requires 2+ days of ODS history | Medium |
| No fixture/demo mode toggle | Demo without live token shows blocked state only | Add fixture mode with sample data and banner | Low |

### 5. Excluded from Public Scope (Permanent)

These items belong to the private DaPES system and will never appear in this public mart:

- Warrant monitor table (`gme_dws_warrant_monitor_1d`)
- Operator position data (holdings, cost basis, account details)
- Tactical strategy / FLQP state
- Private DragonRook paths or identifiers
- Cycle phase decisions tied to operator positions

---

## Handoff Items

Items requiring operator or Codex verification before promotion:

1. **Live MotherDuck smoke test** — requires `MOTHERDUCK_TOKEN` in a secure environment
2. **External DQC reconciliation** — operator compares dashboard values against reference sites on a live trading day
3. **Ingestion pipeline documentation** — operator confirms which OpenBB endpoints currently feed the warehouse
4. **Column schema reconciliation** — verify TDD column specs match actual MotherDuck table schemas
