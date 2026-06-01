# TEST PLAN — gme-options-mart

> **Scope.** This file is the binding acceptance contract for the canonical
> mart-forge example `examples/gme-options-mart/`. It is committed as the
> **first commit on the feature branch**, before any source-catalog,
> BRD, TDD, scaffold, dashboard, or test code lands. Every tier below
> must have a corresponding executable test in
> `examples/gme-options-mart/tests/` or top-level `tests/`. CI runs all
> of them on every push and on the merge gate.

## Provenance

- Source dispatch: EMB-323 (`MFOR-003: Build GME options mart example —
  dogfooded, comparator-verified, grade A or B`).
- Predecessor: `bae4af2` (Phase G CP2-5) shipped a GME mart at grade C
  due to a cross-join cardinality bug in max-pain, null IV-rank with no
  provisional label, dealer_net_gamma identical to net_gex, and
  non-clickable link-status badges. This plan exists so the rebuild
  cannot ship those defects again.
- Grading rubric is fixed: A = all 8 tiers PASS, zero waivers;
  B = all tiers PASS with at most two documented Tier 1 waivers;
  C = six of eight tiers PASS (do not merge); F = fewer than six.

## Tier 1 — Per-metric correctness vs external comparators (BLOCKING)

| ID   | Metric        | Comparator                                    | Tolerance                   | Method                                                                          |
|------|---------------|-----------------------------------------------|-----------------------------|---------------------------------------------------------------------------------|
| T1.1 | Spot          | Yahoo Finance close                            | exact (penny)               | yfinance Python lib or Claude-in-Chrome `finance.yahoo.com/quote/GME`            |
| T1.2 | Max Pain      | max-pain.com + ChartExchange (both)            | ≤ $1 from either            | Claude-in-Chrome navigate + scrape; internal recompute cross-check               |
| T1.3 | P/C Ratio     | Barchart P/C OI Ratio                          | ±5%                         | Claude-in-Chrome `barchart.com/stocks/quotes/GME/put-call-ratios`                |
| T1.4 | IV30          | Market Chameleon GME                           | ±5%                         | Claude-in-Chrome `marketchameleon.com/Overview/GME/`                             |
| T1.5 | HV20          | Barchart 20-day HV                             | ±10%                        | Claude-in-Chrome                                                                  |
| T1.6 | Net GEX       | Recompute: Σ(γ·OI·100·spot²·0.01·sign)         | ±1%                         | Python validator: `tests/test_net_gex_recompute.py`                              |
| T1.7 | Gamma Flip    | Recompute from per-strike GEX, find zero-cross | ±$0.50                      | Python validator: `tests/test_gamma_flip_recompute.py`                           |
| T1.8 | IV Rank       | (252d rolling IV30 percentile)                 | null OK if <252d history    | Coverage logic; must be labeled "provisional" with `iv_rank_lookback_days` field |

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

- **T2.1** `last_pull_date ≥ last_trading_day − 1` on market days.
- **T2.2** Dashboard banner shows pull timestamp + age in hours.
- **T2.3** If `pull_age > 72h`, dashboard renders a STALE banner.

## Tier 3 — Internal consistency (BLOCKING)

- **T3.1** `Σ(call_oi) + Σ(put_oi) = total_oi` by strike.
- **T3.2** `pc_ratio_displayed == Σ(put_oi) / Σ(call_oi)` (within float epsilon).
- **T3.3** `max_pain_strike_displayed` matches hand-recomputed
  (deduplicate strikes first, unexpired-only, both call+put). Must
  explicitly fix the cross-join cardinality bug from `bae4af2`.
- **T3.4** `dealer_net_gamma ≠ net_gex` (different definitions; identical
  values = bug).
- **T3.5** `iv_rank` is null OR has corresponding ≥252d history.

## Tier 4 — Coverage manifest honesty (BLOCKING)

- **T4.1** Every dashboard tile has a BRD §B-3 row.
- **T4.2** Every dashboard tile has a TDD §T-3 row + column-level spec.
- **T4.3** Link-status badge in sidebar is a CLICKABLE hyperlink to the
  comparator URL when `link_status ∈ {exact, proxy}`.
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
- **T7.4** Sidebar link-status badges are clickable hyperlinks (not bare text).
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
before merge.
