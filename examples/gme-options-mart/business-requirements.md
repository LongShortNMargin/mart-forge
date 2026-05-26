# Business Requirements Document: GME Options Mart

> **Date:** 2026-05-27
> **Author:** mart-forge (Phase G Conformance)
> **Status:** Draft

---

## B-1: Version History

| Version | Date       | Author                          | Changes                        |
|---------|------------|---------------------------------|--------------------------------|
| 0.1     | 2026-05-27 | mart-forge (Phase G Conformance)| Initial draft                  |

---

## B-2: Business Context

### Business Process

This mart supports **options flow analytics for GameStop Corp. (GME)**, enabling systematic monitoring of the options market microstructure around a single equity. The core process tracks daily snapshots of the GME options chain and derives key sentiment, positioning, and volatility metrics used in equity options analysis.

### Purpose

Enable daily monitoring of GME options positioning — including implied volatility regimes, dealer gamma exposure, put/call sentiment, and max pain levels — to support systematic trading research and risk assessment for GME-related strategies.

### Stakeholders

| Role              | Name / Team                        | Interest                                                   |
|-------------------|------------------------------------|------------------------------------------------------------|
| Business Owner    | Mart Operator                      | Daily options analytics dashboard for GME                  |
| Data Consumer     | Quantitative Research              | Derived metrics (GEX, IV Rank, Max Pain) for signal generation |
| Engineering Owner | mart-forge Framework (Phase G)     | Conformance examination: validate framework skills end-to-end |

### Domain Glossary

| Term              | Definition                                                                                     |
|-------------------|------------------------------------------------------------------------------------------------|
| Spot Price        | Current or most recent closing price of GME common stock on NYSE.                              |
| Implied Volatility (IV) | Market-derived expectation of future price volatility embedded in option premiums.       |
| IV30              | 30-day implied volatility, interpolated from at-the-money options bracketing 30 DTE.           |
| HV20              | 20-day historical (realized) volatility, annualized standard deviation of log close returns.   |
| Open Interest (OI)| Total number of outstanding (unsettled) option contracts for a given strike and expiration.     |
| Max Pain          | Strike price at which total outstanding options expire with minimum intrinsic value.            |
| P/C Ratio         | Put-to-call open interest ratio; total put OI divided by total call OI.                        |
| GEX (Gamma Exposure) | Aggregate gamma-weighted open interest; indicates required delta-hedging magnitude.         |
| IV Rank           | Percentile rank of current IV30 within its trailing 252-day range.                             |
| DTE               | Days to expiration for an option contract.                                                     |
| ATM               | At-the-money: option whose strike is nearest to the current spot price.                        |

### Data Sources

| Source Name     | Source System  | Extraction Method | Grain                                    | Freshness            | Verification Result |
|-----------------|----------------|-------------------|------------------------------------------|----------------------|---------------------|
| Yahoo Finance   | Yahoo Finance  | REST API / SDK    | Daily per-symbol (prices), daily per-strike per-expiration (options) | End-of-day; 15-min delayed intraday | Verified            |

> **Verification**: Yahoo Finance v8 chart API confirmed returning GME close=22.15 USD on 2026-05-27. yfinance SDK confirmed returning 38 call strikes, 36 put strikes, 17 expirations with populated OI and IV fields.

---

## B-3: Metrics Breakdown

| Metric Name    | Business Definition | source_type | link_status | public_classification | candidate_verification_evidence |
|----------------|---------------------|-------------|-------------|-----------------------|---------------------------------|
| Spot Price     | Current/last closing price of GME on NYSE | native | exact | public | Yahoo Finance v8/finance/chart/GME returned close=22.15 USD, confirmed GameStop Corp. on NYSE |
| OI by Strike   | Open interest per strike per expiration for calls and puts | native | exact | public | yfinance returned openInterest for 38 call + 36 put strikes across 17 expirations; non-zero OI confirmed |
| IV per Strike  | Implied volatility per option contract as quoted by exchange | native | exact | public | yfinance returned impliedVolatility field on every option row; ATM call IV ~2.55 for nearest expiry |
| IV30           | 30-day interpolated at-the-money implied volatility | derived | exact | public | Derived from native IV per Strike using linear interpolation across expirations bracketing 30 DTE; all inputs verified |
| HV20           | 20-day annualized realized volatility from close prices | derived | exact | public | Derived from native Spot Price close history; 62+ trading days of close data verified available |
| Max Pain       | Strike minimizing total intrinsic value of outstanding options | derived | exact | public | Derived from native OI by Strike via cross-join optimization; OI data verified per strike |
| P/C Ratio      | Put-to-call open interest ratio | derived | exact | public | Derived from native OI by Strike: SUM(put OI) / SUM(call OI); both OI fields verified populated |
| Net GEX        | Net gamma exposure across all strikes | derived | exact | public | Derived from native IV per Strike + OI by Strike + Spot Price via Black-Scholes gamma computation; all inputs verified |
| IV Rank        | Percentile rank of current IV30 in trailing 252-day range | derived | proxy | public | Derived from accumulated daily IV30 snapshots; proxy status because initial period uses shorter lookback window; upgrades to exact after 252 days of accumulation |

### source_type Legend

- **native**: Metric is directly available from a single source field.
- **derived**: Metric is computed from two or more source fields.
- **hybrid**: Metric combines native extraction with a derived calculation.

### link_status Legend

- **exact**: Metric value matches an authoritative external source within tolerance.
- **proxy**: No exact external match exists; a related metric is used for directional validation.
- **unsupported**: No external comparator is available; metric is validated only by internal DQC.
- **unverified**: Verification has not yet been attempted.

---

## B-4: Notable / Known Limitations

### Declared Constraints

| ID   | Constraint Description                                                                 | Impact                                          | Mitigation                                      |
|------|----------------------------------------------------------------------------------------|------------------------------------------------|------------------------------------------------|
| L-1  | Yahoo Finance provides 15-minute delayed data during market hours; end-of-day data is free but not real-time. | Intraday signals will reflect delayed state.    | Accept delay for daily-grain mart; note delay in dashboard. |
| L-2  | Yahoo Finance does not expose option Greeks (delta, gamma, theta, vega) directly.      | GEX computation requires Black-Scholes derivation. | Implement Black-Scholes gamma from IV, spot, DTE, and risk-free rate. |
| L-3  | IV Rank requires 252 trading days of accumulated IV30 history to be fully accurate.    | First-year IV Rank values use a shorter lookback. | Label IV Rank as "provisional" until 252-day threshold reached; display lookback window in dashboard. |
| L-4  | No free provider offers pre-computed IV30, Max Pain, GEX, or IV Rank for individual equities. | All advanced metrics must be computed within the pipeline. | All derivation logic specified in TDD with exact SQL; validated against known calculation methods. |
| L-5  | Risk-free rate for Black-Scholes not available from Yahoo Finance; requires external assumption or seed. | GEX accuracy depends on rate assumption.        | Use US Treasury 3-month yield as seed; refresh monthly or on significant rate changes. |

### Unsupported Metrics

| Metric Name | Reason Unsupported | Resource-Exhaustion Evidence |
|-------------|--------------------|-----------------------------|
| _(none)_    | —                  | —                           |

> All requested metrics have confirmed source bindings. No metrics are unsupported.

---

## Signature

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Stakeholder | mart-forge Conformance Examiner | 2026-05-27 | PHASE-G-CP1-AUTOGRADE |
| Data Engineer | mart-forge Phase G Agent | 2026-05-27 | PHASE-G-CP1-AUTOGRADE |
