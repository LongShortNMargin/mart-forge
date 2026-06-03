# gme-options-mart — open questions

Issues, deferrals, and follow-up dispatches deliberately scoped out of
the current revision. Each entry names the precondition that unblocks
it and the expected outcome once executed.

---

## OQ-1 — Phase F-redo: fetch Tier 1.1–1.5 external comparators

**Status**: open
**Opened**: 2026-06-02 (commit landing this entry)
**Scope**: TEST PLAN Tier 1.1–1.5 (`spot`, `max_pain`, `pc_ratio_oi`,
`iv30`, `hv20`) external-comparator deltas vs the materialised
`gme_ads_market_dashboard` values.
**Reason for deferral**: the orchestrator session on 2026-06-02
attempted the Tier 1.1–1.5 fetches and reports that the
`mcp__Claude_in_Chrome__*` surface disconnected mid-session and that
`WebFetch` returns 503 on every JS-rendered finance comparator. See
EMB-323 comment `c2d08bb2-0bf0-4538-9a8f-a30799dfe458` (2026-06-02T09:07Z)
for the orchestrator's blocker statement and the kin-scope final
directive that closed Phase F at grade C with this OQ recorded.

### Precondition to unblock

Re-arm `mcp__Claude_in_Chrome__*` on the operator's host and confirm
the namespace responds to a no-op `navigate("about:blank")` probe.
Alternative unblock paths (in priority order):

1. Operator re-arms Chrome MCP from the AppleScript launcher / desktop
   chrome session and re-dispatches an orchestrator pass scoped to
   Tier 1.1–1.5 only.
2. (Not preferred.) Substitute yfinance-only fetches for T1.1 only;
   yfinance is the mart's *own* upstream so it doesn't count as an
   independent comparator for the TEST PLAN §D protocol — but it can
   serve as a smoke-grade sanity check while the real comparators
   come back online.
3. (Not preferred.) Accept the current grade C as the landed state
   and ship without the comparator evidence; the README would lose
   the "external comparator-verified" framing the example is built
   to demonstrate.

### Execution outline (Phase F-redo dispatch)

For each Tier 1.1–1.5 comparator URL listed in
`docs/business-requirements.md §B-3 candidate_verification_evidence`:

1. `mcp__Claude_in_Chrome__navigate` to the comparator URL.
2. Extract the headline metric value (DOM lookup or page-text scrape).
3. Capture a timestamped screenshot under
   `examples/gme-options-mart/test-results-evidence/T1.X-comparator-YYYYMMDDTHHMM.png`.
4. Compute the delta against the dashboard's `2026-06-01` snapshot
   row (or whatever the live `trading_date` is at re-run time;
   accept ±1 trading-day comparator-side slip per the comparator's
   own EOD-snapshot policy).
5. Mark **PASS** if within tolerance, **FAIL** otherwise. Two FAILs
   max for landed grade B; three or more FAILs return the run to
   grade C and require either a tolerance revisit (BRD touch) or a
   model touch (TDD revisit).
6. Update `test-results.md` Tier 1.1–1.5 block: replace each
   WAIVED row with the PASS/FAIL outcome + comparator URL + delta
   + screenshot path.
7. Recompute the grade per TEST PLAN §C and update the bottom of
   `test-results.md` accordingly.
8. Open the same DRAFT PR for **ready-for-review** conversion;
   request Phase F.5 final reviewer pass (the reviewer).

### Expected outcome

Per the Phase D.5 / Phase F.5 reviewer carry-over notes:

- **T1.1 spot**: exact-match expected (yfinance is the same upstream).
- **T1.2 max_pain**: PASS expected on both max-pain.com and
  ChartExchange (≤ $1 from either is comfortable).
- **T1.3 pc_ratio_oi**: PASS expected (±5% is comfortable).
- **T1.4 iv30**: most likely waiver — Market Chameleon IV30 vs
  bracket-interpolated IV30 can drift past ±5% on GME's weekly
  term-structure curvature; one waiver permitted under grade B.
- **T1.5 hv20**: PASS expected (±10% is generous).

Predicted landed grade after Phase F-redo: **B** (0–2 waivers).
If the prediction holds, the PR moves from DRAFT → ready-for-review,
the reviewer approves the full surface, and the auto-merge rule
fires.

### Tracking

- Issue: EMB-323
- Branch: `phase-g/cp1-gme-options-mart`
- Orchestrator handoff comment: 2026-06-02T09:07Z
  (`mention://issue/0fc9d8af-b2b6-40f5-a182-5a4273db427e`)
- Reviewer context: Phase D.5 observation A, Phase F.5 risk-1
  (T1.4 tolerance carry-over)

---
