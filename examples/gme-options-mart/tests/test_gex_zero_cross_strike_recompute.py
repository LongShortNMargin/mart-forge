"""TC-15 — Tier 1.7 `gex_zero_cross_strike` recompute, Python validator.

Independently recomputes the front-month per-strike cumulative GEX (using
Black-Scholes γ from raw ODS inputs at `r = 0.045`) and locates the
zero-crossing strike using the same algorithm the producer documents in
TDD §T-13 step 4:

  1. Group by strike; sum (γ · OI · 100 · spot² · 0.01 · sign_dealer).
  2. Cumulate over strike.
  3. Find every adjacent (K_below, K_above) strike pair whose effective
     signs disagree (treating zero as the next non-zero sign — "exact-
     zero touches that do not change running sign do not crossing").
  4. Linearly interpolate between cum_gex_below and cum_gex_above; if
     one endpoint is exactly zero, K* is that endpoint.
  5. Deterministic tie-break: closest to spot, lower strike on
     equidistant ties.

Asserts the producer's `gex_zero_cross_strike` either:
  - matches the independent recompute within ±$0.50 (per BRD §B-3 / T1.7), or
  - is NULL on both sides (no crossing).
"""
from __future__ import annotations

import math

import pandas as pd


RISK_FREE_RATE = 0.045
STRIKE_TOLERANCE = 0.50  # ±$0.50 per BRD §B-3 / T1.7


def _bs_gamma(spot: float, strike: float, sigma: float, t: float, r: float) -> float:
    if sigma is None or sigma <= 0 or t is None or t <= 0 or strike is None or strike <= 0:
        return float("nan")
    d1 = (math.log(spot / strike) + (r + 0.5 * sigma * sigma) * t) / (sigma * math.sqrt(t))
    return math.exp(-0.5 * d1 * d1) / (sigma * spot * math.sqrt(2.0 * math.pi * t))


def _zero_cross_for_date(rows: pd.DataFrame) -> float | None:
    """Return K* (interpolated zero-crossing strike) for one trading_date, or None."""
    if rows.empty:
        return None

    spot = float(rows["spot"].iloc[0])

    rows = rows.copy()
    rows["sign_dealer"] = rows["option_type"].map({"call": -1, "put": 1})
    rows["gamma_bs"] = [
        _bs_gamma(spot, k, sig, t, RISK_FREE_RATE)
        for k, sig, t in zip(
            rows["strike"], rows["sigma"], rows["time_to_expiry_years"]
        )
    ]
    rows["per_row_gex"] = (
        rows["gamma_bs"]
        * rows["open_interest"]
        * 100.0
        * (spot ** 2)
        * 0.01
        * rows["sign_dealer"]
    )
    rows = rows.dropna(subset=["per_row_gex"])
    if rows.empty:
        return None

    per_strike = (
        rows.groupby("strike", as_index=False)["per_row_gex"]
        .sum()
        .sort_values("strike")
        .reset_index(drop=True)
    )
    per_strike["cum_gex"] = per_strike["per_row_gex"].cumsum()

    cum = per_strike["cum_gex"].tolist()
    strikes = per_strike["strike"].tolist()
    n = len(cum)
    if n < 2:
        return None

    # Effective sign-at-or-before and sign-at-or-after for each row, treating
    # zeros as transparent (take the nearest non-zero neighbor).
    sign_before: list[float | None] = [None] * n
    last_nz = None
    for i in range(n):
        if cum[i] != 0:
            last_nz = math.copysign(1.0, cum[i])
        sign_before[i] = last_nz

    sign_after: list[float | None] = [None] * n
    next_nz = None
    for i in range(n - 1, -1, -1):
        if cum[i] != 0:
            next_nz = math.copysign(1.0, cum[i])
        sign_after[i] = next_nz

    candidates: list[float] = []
    for i in range(1, n):
        k_below, k_above = strikes[i - 1], strikes[i]
        c_below, c_above = cum[i - 1], cum[i]
        s_below_eff = sign_before[i - 1]
        s_above_eff = sign_after[i]
        if s_below_eff is None or s_above_eff is None:
            continue
        if s_below_eff * s_above_eff >= 0:
            continue
        if c_above == 0:
            k_star = k_above
        elif c_below == 0:
            k_star = k_below
        else:
            k_star = k_below - c_below * (k_above - k_below) / (c_above - c_below)
        candidates.append(k_star)

    if not candidates:
        return None

    # Deterministic tie-break: closest to spot, then lower strike.
    candidates.sort(key=lambda k: (abs(k - spot), k))
    return candidates[0]


def test_gex_zero_cross_strike_within_50c_of_producer(warehouse) -> None:
    chain = warehouse.execute(
        """
        SELECT
            c.trading_date,
            c.expiry_date,
            c.strike,
            c.option_type,
            c.open_interest,
            c.implied_volatility AS sigma,
            CAST(c.expiry_date - c.trading_date AS DOUBLE) / 365.0
                AS time_to_expiry_years,
            p.close_px AS spot
        FROM gme_dwd_options_chain c
        INNER JOIN gme_dwd_price_eod p USING (trading_date)
        WHERE c.front_expiry_flag = TRUE
          AND c.pull_ts_utc <= now()
          AND p.pull_ts_utc <= now()
        """
    ).fetchdf()

    if chain.empty:
        import pytest

        pytest.skip("no real-pull front-month rows available; fixture-only warehouse.")

    producer = warehouse.execute(
        """
        SELECT trading_date, gex_zero_cross_strike
        FROM gme_dws_perf_dealer_gamma_front_month
        WHERE date_sk <= CAST(strftime(now(), '%Y%m%d') AS INTEGER)
        """
    ).fetchdf()

    mismatches: list[str] = []
    for td, group in chain.groupby("trading_date"):
        recomputed = _zero_cross_for_date(group)
        prod_row = producer[producer["trading_date"] == td]
        prod_val = (
            None if prod_row.empty or pd.isna(prod_row["gex_zero_cross_strike"].iloc[0])
            else float(prod_row["gex_zero_cross_strike"].iloc[0])
        )

        if recomputed is None and prod_val is None:
            continue
        if recomputed is None or prod_val is None:
            mismatches.append(
                f"  trading_date={td} recomputed={recomputed} producer={prod_val} "
                "(one side is NULL, the other is not)"
            )
            continue
        delta = abs(prod_val - recomputed)
        if delta > STRIKE_TOLERANCE:
            mismatches.append(
                f"  trading_date={td} recomputed={recomputed:.4f} producer={prod_val:.4f} "
                f"delta={delta:.4f} > ±${STRIKE_TOLERANCE:.2f}"
            )

    assert not mismatches, (
        "Tier 1.7 gex_zero_cross_strike recompute violations:\n" + "\n".join(mismatches)
    )
