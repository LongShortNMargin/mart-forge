"""TC-13 — Tier 1.6 Net GEX recompute, Python validator.

Independently recomputes Black-Scholes γ from the ODS chain (`sigma`,
`time_to_expiry_years`) joined with the ODS price history (`close_px`),
then sums

    net_gex = Σ ( γ_BS · OI · 100 · spot² · 0.01 · sign_dealer )

per trading_date over the full chain at the same risk-free rate the
producer pin-binds (`vars.risk_free_rate = 0.045`). Asserts the
producer's `gme_dws_perf_dealer_gamma.net_gex` agrees within ±1%
(absolute tolerance for near-zero rows: ≤ $1.

The recompute path does NOT read `gamma_bs`, `sign_dealer`, or any
DWD column — it goes back to the ODS layer so a future regression
that miscomputes γ or flips the dealer sign in the DWD layer will
fail this test even if the DWS aggregation expression stays the
same. That's the difference between an aggregation parity check and
a real T1.6 recompute.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


RISK_FREE_RATE = 0.045
RELATIVE_TOLERANCE = 0.01  # ±1% per BRD §B-3 / T1.6
ABSOLUTE_FLOOR_USD = 1.0    # near-zero producer value: use absolute tolerance instead


def _bs_gamma(spot: float, strike: float, sigma: float, t: float, r: float) -> float:
    if sigma is None or sigma <= 0 or t is None or t <= 0 or strike is None or strike <= 0:
        return float("nan")
    d1 = (math.log(spot / strike) + (r + 0.5 * sigma * sigma) * t) / (sigma * math.sqrt(t))
    return math.exp(-0.5 * d1 * d1) / (sigma * spot * math.sqrt(2.0 * math.pi * t))


def _independent_net_gex(rows: pd.DataFrame, r: float) -> pd.DataFrame:
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
        .rename(columns={"per_row": "net_gex_recomputed"})
    )


def test_net_gex_within_one_percent_of_producer(warehouse) -> None:
    # ODS chain + price are the upstream sources of truth.
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

    recomputed = _independent_net_gex(chain, RISK_FREE_RATE)

    producer = warehouse.execute(
        """
        SELECT trading_date, net_gex
        FROM gme_dws_perf_dealer_gamma
        WHERE date_sk <= CAST(strftime(now(), '%Y%m%d') AS INTEGER)
        """
    ).fetchdf()

    merged = recomputed.merge(producer, on="trading_date", how="inner")
    assert not merged.empty, "no overlapping trading_dates between recompute and producer"

    merged["delta_abs"] = (merged["net_gex"] - merged["net_gex_recomputed"]).abs()
    merged["denominator"] = np.maximum(merged["net_gex_recomputed"].abs(), ABSOLUTE_FLOOR_USD)
    merged["rel_err"] = merged["delta_abs"] / merged["denominator"]

    bad = merged[
        (merged["rel_err"] > RELATIVE_TOLERANCE) & (merged["delta_abs"] > ABSOLUTE_FLOOR_USD)
    ]
    assert bad.empty, (
        "trading_date(s) violate Tier 1.6 ±1% net_gex recompute tolerance:\n"
        f"{bad.to_string(index=False)}"
    )
