"""Generate fixture parquet for CI: ~20 rows of synthetic GME options chain data."""
import datetime as dt
import duckdb

rows = []
pull_date = dt.date(2026, 5, 27)
pull_ts = dt.datetime(2026, 5, 27, 20, 30, 0)
spot = 28.50

strikes = [25.0, 26.0, 27.0, 28.0, 29.0, 30.0, 31.0, 32.0, 33.0, 35.0]
expiry = dt.date(2026, 6, 20)

for s in strikes:
    for otype in ("call", "put"):
        moneyness = spot - s if otype == "call" else s - spot
        itm = moneyness > 0
        iv = round(0.60 + abs(s - spot) * 0.02, 4)
        if otype == "call":
            bid = round(max(moneyness, 0) + iv * 0.5, 2)
            ask = round(bid + 0.10, 2)
        else:
            bid = round(max(moneyness, 0) + iv * 0.5, 2)
            ask = round(bid + 0.10, 2)
        sym = f"GME260620{'C' if otype == 'call' else 'P'}{int(s * 1000):08d}"
        rows.append({
            "pull_date": pull_date,
            "ticker": "GME",
            "option_symbol": sym,
            "expiry": expiry,
            "strike": s,
            "option_type": otype,
            "last_trade_price": round((bid + ask) / 2, 2),
            "bid": bid,
            "ask": ask,
            "volume": 100 + int(abs(s - spot) * 50),
            "open_interest": 500 + int(abs(s - spot) * 200),
            "iv": iv,
            "in_the_money": itm,
            "underlying_close": spot,
            "provider": "yahoo_finance",
            "pull_ts_utc": pull_ts,
            "quote_ts_utc": pull_ts,
            "run_id": "fixture_run_20260527",
        })

import pandas as pd

df = pd.DataFrame(rows)
df["pull_date"] = pd.to_datetime(df["pull_date"])
df["expiry"] = pd.to_datetime(df["expiry"])
df["pull_ts_utc"] = pd.to_datetime(df["pull_ts_utc"])
df["quote_ts_utc"] = pd.to_datetime(df["quote_ts_utc"])

out = "examples/gme-options-mart/fixtures/gme_options_chain.parquet"
df.to_parquet(out, index=False)
print(f"Wrote {len(rows)} rows to {out}")
