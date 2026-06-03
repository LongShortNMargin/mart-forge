"""Generate synthetic seed CSVs for the gme-options-mart canonical example.

Creates two seed files:
- gme_seed_price_history.csv (60 trading days ending 2026-06-02 — enough for HV20
  and to exercise the dim_date OFFSET-251 percentile join shape even though
  iv_rank stays NULL/provisional with only 60 days of iv30 history)
- gme_seed_options_chain_snapshot.csv (chain snapshots for 2026-06-01 and
  2026-06-02, three expiries each, strikes 20.0..30.0 step 1.0)

Run from the example root: `python3 scripts/generate_seeds.py`
"""
from __future__ import annotations

import csv
import math
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

random.seed(20260602)

ROOT = Path(__file__).resolve().parents[1]
SEEDS = ROOT / "seeds"


def trading_days(end: date, count: int) -> list[date]:
    days: list[date] = []
    d = end
    while len(days) < count:
        if d.weekday() < 5:
            days.append(d)
        d -= timedelta(days=1)
    return list(reversed(days))


def write_price_history() -> None:
    dates = trading_days(date(2026, 6, 2), 60)
    rows = []
    close = 22.00
    for i, d in enumerate(dates):
        drift = 0.0006
        shock = random.gauss(0, 0.025)
        close_next = max(5.0, close * math.exp(drift + shock))
        open_px = round(close * (1 + random.gauss(0, 0.004)), 2)
        high_px = round(max(open_px, close_next) * (1 + abs(random.gauss(0, 0.008))), 2)
        low_px = round(min(open_px, close_next) * (1 - abs(random.gauss(0, 0.008))), 2)
        volume = int(random.uniform(4_000_000, 12_000_000))
        rows.append(
            {
                "trading_date": d.isoformat(),
                "open_px": open_px,
                "high_px": high_px,
                "low_px": low_px,
                "close_px": round(close_next, 2),
                "volume": volume,
                "provider": "yfinance",
                "pull_ts_utc": f"{d.isoformat()}T21:05:14",
            }
        )
        close = close_next
    out = SEEDS / "gme_seed_price_history.csv"
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_chain() -> None:
    rows = []
    snapshot_dates = [date(2026, 6, 1), date(2026, 6, 2)]
    expiries_by_date = {
        date(2026, 6, 1): [date(2026, 6, 5), date(2026, 6, 12), date(2026, 6, 20)],
        date(2026, 6, 2): [date(2026, 6, 5), date(2026, 6, 12), date(2026, 6, 20)],
    }
    spot_by_date = {date(2026, 6, 1): 24.40, date(2026, 6, 2): 24.85}
    for trading_d in snapshot_dates:
        spot = spot_by_date[trading_d]
        for expiry in expiries_by_date[trading_d]:
            t_years = (expiry - trading_d).days / 365.0
            if t_years <= 0:
                continue
            for k_int in range(20, 31):
                strike = float(k_int)
                moneyness = abs(strike / spot - 1.0)
                base_iv = 0.85 + 0.50 * moneyness + (0.10 if expiry == date(2026, 6, 5) else 0)
                for opt in ("call", "put"):
                    iv = max(0.10, base_iv * (1 + random.gauss(0, 0.04)))
                    oi_center = 800 if abs(strike - spot) < 1.5 else 200
                    if opt == "call" and strike >= spot:
                        oi_center = int(oi_center * 1.6)
                    if opt == "put" and strike <= spot:
                        oi_center = int(oi_center * 1.4)
                    open_interest = max(0, int(random.gauss(oi_center, oi_center * 0.3)))
                    rows.append(
                        {
                            "trading_date": trading_d.isoformat(),
                            "expiry_date": expiry.isoformat(),
                            "strike": strike,
                            "option_type": opt,
                            "open_interest": open_interest,
                            "implied_volatility": round(iv, 4),
                            "provider": "yfinance",
                            "pull_ts_utc": f"{trading_d.isoformat()}T21:05:12",
                        }
                    )
    out = SEEDS / "gme_seed_options_chain_snapshot.csv"
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    write_price_history()
    write_chain()
    print("seeds written under", SEEDS)
