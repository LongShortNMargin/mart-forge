"""TC-14 — Tier 1.6b Net GEX rate sensitivity, Python validator.

Sweeps `r ∈ {0.03, 0.045, 0.06}` over the same ODS rowset and recomputes
net_gex three times. Asserts the rate-insensitivity claim in BRD §B-4
L-4: the per-trading_date spread `max(net_gex_r) − min(net_gex_r)`
divided by `max(abs(producer_net_gex), 1e6 USD)` (item D denominator
floor) stays within 1% (TEST PLAN T1.6b tolerance band) because gamma
is approximately r-insensitive at short-dated maturities.

This is the dbt-side NA in the Phase D scorecard
(`business_recon_t1_6b_rate_floor`): a single dbt test cannot sweep a
parameter that's pinned via `vars.risk_free_rate` at run time. The
Python harness owns the parametric assertion per TDD §T-21 / TL-2.
"""
from __future__ import annotations

import math

import pandas as pd


RATES = (0.03, 0.045, 0.06)
SPREAD_TOLERANCE = 0.01      # 1% of denominator (TEST PLAN T1.6b + BRD §B-4 L-4)
ABSOLUTE_FLOOR_USD = 1.0e6   # item D denominator floor


def _bs_gamma(spot: float, strike: float, sigma: float, t: float, r: float) -> float:
    if sigma is None or sigma <= 0 or t is None or t <= 0 or strike is None or strike <= 0:
        return float("nan")
    d1 = (math.log(spot / strike) + (r + 0.5 * sigma * sigma) * t) / (sigma * math.sqrt(t))
    return math.exp(-0.5 * d1 * d1) / (sigma * spot * math.sqrt(2.0 * math.pi * t))


def _net_gex_at_rate(rows: pd.DataFrame, r: float) -> pd.DataFrame:
    rows = rows.copy()
    rows["sign_dealer"] = rows["option_type"].map({"call": -1, "put": 1})
    rows["gamma_bs"] = [
        _bs_gamma(s, k, sig, t, r)
        for s, k, sig, t in zip(
            rows["spot"], rows["strike"], rows["sigma"], rows["time_to_expiry_years"]
        )
    ]
    rows["per_row"] = (
        rows["gamma_bs"]
        * rows["open_interest"]
        * 100.0
        * (rows["spot"] ** 2)
        * 0.01
        * rows["sign_dealer"]
    )
    rows = rows.dropna(subset=["per_row"])
    return (
        rows.groupby("trading_date", as_index=False)["per_row"]
        .sum()
        .rename(columns={"per_row": f"net_gex_r_{r:.3f}"})
    )


def test_net_gex_rate_spread_within_floor(warehouse) -> None:
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
        WHERE c.pull_ts_utc <= now()
          AND p.pull_ts_utc <= now()
        """
    ).fetchdf()

    if chain.empty:
        import pytest

        pytest.skip("no real-pull rows available; warehouse only carries fixture data.")

    sweeps = [_net_gex_at_rate(chain, r) for r in RATES]
    df = sweeps[0]
    for s in sweeps[1:]:
        df = df.merge(s, on="trading_date", how="inner")

    rate_cols = [c for c in df.columns if c.startswith("net_gex_r_")]
    df["spread"] = df[rate_cols].max(axis=1) - df[rate_cols].min(axis=1)

    producer = warehouse.execute(
        """
        SELECT trading_date, net_gex
        FROM gme_dws_perf_dealer_gamma
        WHERE date_sk <= CAST(strftime(now(), '%Y%m%d') AS INTEGER)
        """
    ).fetchdf()

    merged = df.merge(producer, on="trading_date", how="inner")
    merged["denominator"] = merged["net_gex"].abs().clip(lower=ABSOLUTE_FLOOR_USD)
    merged["rel_spread"] = merged["spread"] / merged["denominator"]

    bad = merged[merged["rel_spread"] > SPREAD_TOLERANCE]
    assert bad.empty, (
        "trading_date(s) violate Tier 1.6b rate-sensitivity bound:\n"
        f"{bad[['trading_date'] + rate_cols + ['spread', 'denominator', 'rel_spread']].to_string(index=False)}"
    )
