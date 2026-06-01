# TEST PLAN — gme-options-mart

> **Scope.** This file is the binding acceptance contract for the canonical
> mart-forge example `examples/gme-options-mart/`. It is committed as the
> **first commit on the feature branch**, before any source-catalog,
> BRD, TDD, scaffold, dashboard, or test code lands. Every tier below
> must have a corresponding executable test in
> `examples/gme-options-mart/tests/` or top-level `tests/`. CI runs all
> of them on every push and on the merge gate.
>
> **Revision note (round 2).** Sections updated below address reviewer
> findings 1-12 in comment `8bd7a35c`: single locked sign convention
> for net_gex (finding 1); `dealer_net_gamma` scope-distinct from
> `net_gex` and T3.4 reframed (finding 2); `gex_zero_cross_strike`
> rename + T1.7 algorithm clarified (finding 3); T1.6 + T1.6b
> parametric sensitivity (finding 4); iv30 interp pinned to total
> variance (finding 5); iv_rank link_status phase-gated (finding 6);
> T2.1/T2.3 unified on `pull_age <= 26h` (finding 7); T1.7 front-month
> scope explicit (finding 8); T1.1 same-day OHLC chart endpoint, not
> "Previous Close" header (finding 9); concrete API endpoints in
> source_catalog (finding 10); T1.3 comparator selector locked
> (finding 11); neutral phrasing (finding 12).

## Provenance

- Source dispatch: EMB-323.
- Predecessor: `bae4af2` shipped a GME mart at grade C due to a
  cross-join cardinality bug in max-pain, null IV-rank with no
  provisional label, dealer_net_gamma identical to net_gex, and
  non-clickable link-status badges. This plan exists so the rebuild
  cannot ship those defects again.
- Grading rubric is fixed: A = all 8 tiers PASS, zero waivers;
  B = all tiers PASS with at most two documented Tier 1 waivers;
  C = six of eight tiers PASS (do not merge); F = fewer than six.

## Tier 1 — Per-metric correctness vs external comparators (BLOCKING)

| ID    | Metric                    | Comparator                                                                                                  | Tolerance                  | Method                                                                                                                                                                                                                                                                                          |
|-------|---------------------------|-------------------------------------------------------------------------------------------------------------|----------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| T1.1  | Spot                      | Yahoo v8 chart endpoint OHLC bar for the **same trading_date** the mart used                                | exact (penny)              | `GET https://query2.finance.yahoo.com/v8/finance/chart/GME?interval=1d&range=5d` → read `chart.result[0].indicators.quote[0].close[i]` for the i whose timestamp matches the mart's trading_date. Do NOT use the quote header's "Previous Close" field — that drifts by one trading day during market hours (closes finding 9). |
| T1.2  | Max Pain                  | max-pain.com + ChartExchange (both)                                                                          | ≤ $1 from either           | Claude-in-Chrome navigate + scrape; also internal recompute cross-check.                                                                                                                                                                                                                         |
| T1.3  | P/C Ratio (OI)            | Barchart **"OI Ratio" column on the "All" (chain-wide) row**, NOT 5-day/20-day volume rows                  | ±5%                        | Claude-in-Chrome `barchart.com/stocks/quotes/GME/put-call-ratios`. Lock to the "All" row's "OI Ratio" cell (column header "OI Ratio", row label "All"). Closes finding 11.                                                                                                                       |
| T1.4  | IV30                      | Market Chameleon GME IV30                                                                                    | ±5%                        | Claude-in-Chrome `marketchameleon.com/Overview/GME/`. Producer and validator both implement **linear interpolation in total variance σ²·t** (see BRD §B-3 iv30 row) — interpolation method is pinned, not vendor-chosen (closes finding 5).                                                       |
| T1.5  | HV20                      | Barchart 20-day HV                                                                                           | ±10%                       | Claude-in-Chrome `barchart.com/stocks/quotes/GME/price-history/historical`.                                                                                                                                                                                                                       |
| T1.6  | Net GEX (same-r parity)   | Internal Python recompute at the **same** `risk_free_rate=0.045` as the producer                              | ±1%                        | `tests/test_net_gex_recompute.py`. Validates absence of unit/scale drift in the producer's own pipeline at the published r. Does NOT validate correctness across rate choices — that's T1.6b.                                                                                                    |
| T1.6b | Net GEX (rate sensitivity)| Internal Python recompute at `r ∈ {0.03, 0.045, 0.06}`                                                       | `(max - min) / abs(producer) ≤ 1%` | `tests/test_net_gex_rate_sensitivity.py`. Asserts BRD §B-4 L-4's claim that the net_gex value is rate-insensitive within ±1% across the plausible rate band. Closes reviewer finding 4 (T1.6 alone is otherwise tautological under L-4).                                                          |
| T1.7  | gex_zero_cross_strike     | Internal Python recompute — sort per-strike GEX (at current spot s₀), find cumulative sign change, linearly interpolate. **Front-month expiry only.** | ±$0.50 on the interpolated strike | `tests/test_gex_zero_cross_strike_recompute.py`. The "front-month expiry only" scope qualifier is explicit (closes finding 8). The metric and the test are both strike-axis diagnostics; the misleading "spot-price flip" framing of the prior iteration is removed throughout (closes finding 3). |
| T1.8  | IV Rank                   | Coverage logic — link_status is phase-gated                                                                  | null when lookback < 252; ±5% vs Market Chameleon IV Rank thereafter | Coverage check while `iv_rank_lookback_days < 252`: assert iv_rank IS NULL AND iv_rank_label = 'provisional'. After 252-day boundary: Claude-in-Chrome `marketchameleon.com/Overview/GME/IV/`, ±5% (closes reviewer finding 6).                                              |

### Comparator fetch protocol

For each Tier 1 external comparator:

1. Use Claude-in-Chrome MCP (`mcp__Claude_in_Chrome__*`). `WebFetch`
   returns 403 on JS-rendered finance pages and is not acceptable here.
2. Navigate to the comparator URL; capture page text or DOM-extract.
3. Save screenshot to
   `examples/gme-options-mart/test-results-evidence/T1.X-comparator-YYYYMMDDTHHMM.png`.
4. Record extracted value, timestamp, URL in `test-results.md`.
5. Compute delta vs dashboard value; PASS if within tolerance, FAIL otherwise.
6. If comparator is paywalled / blocked / unavailable: document as
   `T1.X waived — comparator unavailable [timestamp, URL, error]`.
   Two such waivers max for grade B.

## Tier 2 — Data freshness (BLOCKING)

A single freshness threshold is used by both the test gate and the
dashboard banner so they cannot disagree (closes reviewer finding 7).

- **T2.1** `pull_age <= 26h since most_recent_session_close` on market
  days, where `most_recent_session_close = 21:00 UTC on the last
  trading_day per dim_date`.
- **T2.2** Dashboard banner shows `last_pull_ts_utc` + `pull_age_hours`.
- **T2.3** If `pull_age > 26h since most_recent_session_close`, the
  dashboard renders a STALE banner — same threshold as T2.1, so a pull
  that passes T2.1 cannot simultaneously be flagged STALE.

## Tier 3 — Internal consistency (BLOCKING)

- **T3.1** `Σ(call_oi) + Σ(put_oi) = total_oi` by strike.
- **T3.2** `pc_ratio_displayed == Σ(put_oi) / Σ(call_oi)` (within float epsilon).
- **T3.3** `max_pain_strike_displayed` matches hand-recomputed
  (deduplicate strikes first, unexpired-only, both call+put). Must
  explicitly fix the cross-join cardinality bug from `bae4af2`.
- **T3.4** `dealer_net_gamma` is computed from the **front-month
  expiry only** while `net_gex` is computed from the **full chain**.
  The test asserts the structural scope distinction by checking the
  computation provenance (which source rows fed each metric) and the
  numerical implication: `abs(dealer_net_gamma - net_gex /
  (spot² · 0.01)) > epsilon` whenever back-month expiries carry
  non-zero OI (which is always true for GME). Replaces the
  predecessor's weak inequality test that was satisfied trivially by
  the unit factor alone (closes reviewer finding 2).
- **T3.5** `iv_rank` is null OR has corresponding `iv_rank_lookback_days
  >= 252` AND `iv_rank_label = 'final'`. Predecessor `bae4af2` shipped
  null iv_rank without the provisional label.

## Tier 4 — Coverage manifest honesty (BLOCKING)

- **T4.1** Every dashboard tile has a BRD §B-3 row.
- **T4.2** Every dashboard tile has a TDD §T-3 row + column-level spec.
- **T4.3** Link-status badge in sidebar is a CLICKABLE hyperlink to
  the comparator URL when the metric's **active** `link_status ∈
  {exact, proxy}`. For iv_rank specifically, the badge is grey/unsupported
  while `iv_rank_lookback_days < 252` and flips to the clickable proxy
  badge thereafter (closes reviewer finding 6 + finding 3 dashboard
  follow-through).
- **T4.4** `unsupported` metrics have §6.3 exhaustion evidence in BRD.

## Tier 5 — Dogfood evidence (BLOCKING)

- **T5.1** `examples/gme-options-mart/.skill-invocations.jsonl` records
  `source-discovery`, `mart-brd`, `mart-tdd`, `mart-bootstrap`, and
  `mart-dqc` each firing at least once.
- **T5.2** Every committed artifact under `examples/gme-options-mart/`
  has a corresponding entry.
- **T5.3** Zero `"reconstructed": true`.
- **T5.4** `skill_name` in each entry exists in `./skills/`;
  `input_artifact` and `output_artifact` paths exist on disk.

## Tier 6 — Confidentiality (PUBLIC repo, BLOCKING)

- **T6.1** `python3 scripts/confidentiality_scan.py examples/gme-options-mart`
  finds zero violations on the full subtree.
- **T6.2** No operator-specific position data (no concrete share counts,
  warrant counts, broker account references, or per-trade sizing).
- **T6.3** No private-org references — the scanner's
  `internal_project`, `internal_persona`, and `user_id` rule classes
  must report zero hits.

## Tier 7 — UX / dashboard runtime (BLOCKING)

- **T7.1** Dashboard renders `200 OK` on `localhost:8503`.
- **T7.2** Live MotherDuck mode renders "Connected to MotherDuck" banner.
- **T7.3** Local fallback renders "local DuckDB fixture mode" banner.
- **T7.4** Sidebar link-status badges are clickable hyperlinks (not bare text)
  for metrics whose **active** link_status ∈ {exact, proxy}; grey
  for unsupported (including phase-gated iv_rank during cold start).
- **T7.5** `Refresh` action re-queries warehouse (no stale Streamlit cache).

## Tier 8 — CI gate (BLOCKING)

- **T8.1** `.github/workflows/gme-mart-ci.yml`:
  `dbt seed && dbt run && dbt test` exits 0.
- **T8.2** All Python tests pass (≥ Tier 1-7 tests count).
- **T8.3** All adversarial probes pass per `feedback-gate-adversarial-probe`.
- **T8.4** Dashboard smoke test fires (headless Streamlit + HTTP probe).

## Grade calculation

| Grade | Criteria                                                                 | Action                  |
|-------|--------------------------------------------------------------------------|-------------------------|
| **A** | All 8 Tiers PASS, zero waivers, reviewer `approve`                       | Auto-merge              |
| **B** | All Tiers PASS except ≤2 waivers in Tier 1 with documented unavailability + tracked fix | Auto-merge with note    |
| **C** | 6 of 8 Tiers PASS                                                        | Do NOT merge — iterate  |
| **F** | < 6 Tiers PASS                                                           | Halt + notify operator  |

## Reporting

- `examples/gme-options-mart/test-results.md` records the per-tier outcome,
  delta vs comparator, waiver evidence, and final grade.
- `examples/gme-options-mart/test-results-evidence/` holds comparator
  screenshots and any DOM dumps.
- Grade and waiver list are summarized in the PR description.

## Reviewer

Adversarial review is performed by the designated maintainer reviewer
agent on each phase artifact (A0, A, B, C, D, E, F) and on the full PR
before merge. Per the Ralph Wiggum loop spec, no forward motion past
phase N is allowed until phase N.5 returns `approve`.
