# GME Options Mart — Business Requirements Document (BRD)

Status: **MVP Checkpoint** (pending full verification — Phase F iteration)
Grade: **B-** (coverage gaps documented, not hidden)

---

## B-1: Version History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 0.1 | 2026-05-24 | DROOK-OPUS | MVP checkpoint: scoped to public metrics rendered by dashboard |

---

## B-2: Business Context

### Business Process

Public GME (GameStop Corp) options-chain analytics: daily capture and aggregation of publicly available options market data for analytical observation.

### Purpose

Provide a repeatable, verifiable analytical surface for public GME options metrics. This mart demonstrates the mart-forge lifecycle (source discovery, BRD, TDD, scaffold, DQC, dashboard) against a real domain with live data.

### Domain

US equity options analytics — single-ticker (GME), daily grain, options-chain-derived metrics.

### Stakeholders

- Data engineers evaluating the mart-forge framework
- Operators reviewing public market analytics (no private position data)

### Cadence

Daily at market close (16:45 ET, weekdays). Weekend/holiday data is stale-carried from last trading day.

### Data Sources

| Source | Provider | Type | Auth | Freshness | Status |
|--------|----------|------|------|-----------|--------|
| Options chain (CBOE) | OpenBB SDK v4 / yfinance | API | Free (rate-limited) | EOD | `verified` |
| Price data | OpenBB SDK v4 / yfinance | API | Free | EOD | `verified` |
| Reddit sentiment | Reddit API | API | OAuth required | Varies | `unsupported` — Phase 2 |
| IBKR positions | IBKR API | API | Account required | Real-time | `blocked` — private/operator-only, excluded from public mart |

---

## B-3: Metrics Breakdown

### Public Metric Catalog

| # | Metric | Source Type | Link Status | Verification Status |
|---|--------|------------|-------------|---------------------|
| M-01 | Spot Price (last close) | `native` | `exact` | `verified` — Yahoo Finance, MarketWatch |
| M-02 | Max Pain Strike | `derived` | `proxy` | `pending_verification` — swaggystocks.com (advisory) |
| M-03 | Max Pain Convergence % | `derived` | `unsupported` | `pending_verification` |
| M-04 | Put/Call Ratio (volume) | `native` | `proxy` | `pending_verification` — barchart.com (advisory) |
| M-05 | Net GEX (Gamma Exposure) | `derived` | `proxy` | `pending_verification` — spotgamma.com methodology differs |
| M-06 | Call GEX by Strike | `derived` | `unsupported` | `pending_verification` |
| M-07 | Put GEX by Strike | `derived` | `unsupported` | `pending_verification` |
| M-08 | IV (Implied Volatility avg) | `native` | `proxy` | `pending_verification` — marketchameleon.com (advisory) |
| M-09 | IV Percentile (rolling) | `derived` | `proxy` | `pending_verification` |
| M-10 | OI by Strike (top N) | `native` | `proxy` | `pending_verification` — barchart.com (advisory) |

### Excluded Metrics (Private / Operator-Only)

The following metrics exist in the private DaPES system but are explicitly excluded from this public mart:

- Warrant quantity, strike, expiry, cost basis, intrinsic value, moneyness, DTE, theta regime
- Account positions, tactical strategy, FLQP state
- Operator-specific cycle phase decisions
- Any data from `gme_dws_warrant_monitor_1d` (excluded — private operator table)

### Domain Glossary

| Term | Definition |
|------|-----------|
| GEX | Gamma Exposure: `gamma * OI * 100 * spot^2 * 0.01 * sign` where sign is +1 for calls, -1 for puts |
| Max Pain | Strike price at which total dollar value of outstanding put and call options causes greatest financial loss to option holders |
| IV Percentile | Current IV rank relative to trailing history, expressed as 0-100% |
| P/C Ratio | Put volume / Call volume for a given period; >1.0 = bearish sentiment bias |
| OI | Open Interest: total outstanding option contracts at a given strike |

---

## B-4: Known Limitations

### Coverage

**Verified rendered metrics: 0 / 10** (0% coverage at MVP checkpoint)

All 10 metrics load from MotherDuck warehouse tables (`gme_dws_daily_snapshot_1d`, `gme_dws_strike_gex_1d`) and are tagged `[REAL_API]` when data is present. However, DQC verification (external source reconciliation) has not been completed for any metric. Values are data observations, not fact-checked figures.

### Unsupported Metrics

| Metric | Attempts | Reason |
|--------|----------|--------|
| Reddit Sentiment Score | Reddit API requires OAuth app registration | Phase 2 — not in scope for MVP |
| IBKR Position Data | Requires authenticated broker account | Private/operator-only — permanently excluded from public mart |

### Constraints

- Free-tier API rate limits may cause intermittent ingestion failures
- GEX calculation methodology varies across providers; our formula may differ from commercial services
- IV percentile calculation uses internal history window; external providers may use different windows
- Weekend/holiday data shows last trading day values (stale-carry, not interpolation)

### Phase F Iteration Items

Items deferred to subsequent Phase F quality iterations:

1. Complete DQC reconciliation for all 10 metrics against external sources
2. Browser-automated link verification (G-LINK gate)
3. Fixture manifest with source date and schema hash
4. OI delta (day-over-day change) metric
5. IV term structure (skew) visualization
6. 7-day and 30-day trailing aggregation tables
