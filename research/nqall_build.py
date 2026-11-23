"""Build 1-minute bars of every NQ outright contract from Ben's Databento download (job GLBX-20260102-E4RLSRJ8B7:
GLBX.MDP3 ohlcv-1m, parent NQ.FUT, 6 Jun 2010 to 31 Dec 2025, one CSV per day).

Calendar spreads (symbols with "-") are dropped. Bars after 1 Nov 2025 belong to the holdout year and are written to a
separate file that research code does not read. Output: data/bars/NQALL_1m.parquet (UTC index; instrument_id, symbol,
open, high, low, close, volume).
Run: python research/nqall_build.py <dir with the unzipped glbx-mdp3-*.ohlcv-1m.csv.zst files>
"""
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "bars"
HOLDOUT = pd.Timestamp("2025-11-01 05:00", tz="UTC")  # 1 Nov 2025 00:00 CT


def one(p):
    d = pd.read_csv(p, usecols=["ts_event", "instrument_id", "open", "high", "low", "close", "volume", "symbol"])
    return d[~d["symbol"].str.contains("-", regex=False)]


def main(src):
    files = sorted(Path(src).glob("glbx-mdp3-*.ohlcv-1m.csv.zst"))
    with ProcessPoolExecutor() as ex:
        df = pd.concat(ex.map(one, files, chunksize=50), ignore_index=True)
    df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
    df = df.drop_duplicates(["ts_event", "instrument_id"], keep="last").set_index("ts_event").sort_index()
    OUT.mkdir(parents=True, exist_ok=True)
    df[df.index < HOLDOUT].to_parquet(OUT / "NQALL_1m.parquet")
    df[df.index >= HOLDOUT].to_parquet(OUT / "NQALL_1m_HOLDOUT.parquet")
    print(len(files), "files;", len(df), "outright bars;", df["symbol"].nunique(), "contracts;", df.index.min(), "to", df.index.max())


if __name__ == "__main__":
    main(sys.argv[1])
