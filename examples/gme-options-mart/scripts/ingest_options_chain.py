"""
Ingest GME options chain from Yahoo Finance via yfinance.
Writes a Parquet staging file for the ODS dbt model.

Usage:
    python ingest_options_chain.py [--output staging/gme_options_chain.parquet]
"""
import argparse
import datetime as dt

import pandas as pd

try:
    import yfinance as yf
except ImportError:
    raise SystemExit("yfinance is required: pip install yfinance")


def fetch_gme_options(ticker_symbol: str = "GME") -> pd.DataFrame:
    ticker = yf.Ticker(ticker_symbol)
    spot = ticker.fast_info.get("lastPrice", ticker.fast_info.get("previousClose"))
    expirations = ticker.options

    frames = []
    now = dt.datetime.utcnow()
    run_id = f"run_{now.strftime('%Y%m%d_%H%M')}"

    for exp_str in expirations:
        chain = ticker.option_chain(exp_str)
        for otype, df in [("call", chain.calls), ("put", chain.puts)]:
            df = df.copy()
            df["option_type"] = otype
            df["expiry"] = pd.to_datetime(exp_str)
            frames.append(df)

    if not frames:
        raise SystemExit("No options data returned from Yahoo Finance")

    combined = pd.concat(frames, ignore_index=True)

    result = pd.DataFrame({
        "pull_date": dt.date.today(),
        "ticker": ticker_symbol,
        "option_symbol": combined["contractSymbol"],
        "expiry": combined["expiry"],
        "strike": combined["strike"],
        "option_type": combined["option_type"],
        "last_trade_price": combined["lastPrice"],
        "bid": combined["bid"],
        "ask": combined["ask"],
        "volume": combined.get("volume", 0),
        "open_interest": combined.get("openInterest", 0),
        "iv": combined["impliedVolatility"],
        "in_the_money": combined["inTheMoney"],
        "underlying_close": spot,
        "provider": "yahoo_finance",
        "pull_ts_utc": now,
        "quote_ts_utc": now,
        "run_id": run_id,
    })

    return result


def main():
    parser = argparse.ArgumentParser(description="Ingest GME options chain")
    parser.add_argument(
        "--output",
        default="staging/gme_options_chain.parquet",
        help="Output parquet path",
    )
    args = parser.parse_args()

    df = fetch_gme_options()
    df.to_parquet(args.output, index=False)
    print(f"Wrote {len(df)} rows to {args.output}")


if __name__ == "__main__":
    main()
