"""Shared pieces for the cross-market research (iteration 32 on, reports/NEW_STRATEGY_LOG.md)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from sniper.data import dbn_to_bars  # noqa: E402

RAW = ROOT / "data" / "raw" / "xm"
BARS = ROOT / "data" / "bars"
DEV_START, DEV_END, WF_END = pd.Timestamp("2018-01-01"), pd.Timestamp("2024-11-01"), pd.Timestamp("2025-11-01")

# traded contract, dollars per point, tick size (points), round-turn fee. Cost = fee + one tick per side.
SPEC = {
    "CL": ("MCL", 100.0, 0.01, 1.72),
    "GC": ("MGC", 10.0, 0.10, 1.92),
    "NG": ("MNG", 1000.0, 0.001, 1.92),
    "RTY": ("M2K", 5.0, 0.10, 1.22),
    "YM": ("MYM", 0.5, 1.0, 1.22),
    "ZN": ("ZN", 1000.0, 1 / 64, 2.62),
    "6E": ("M6E", 12500.0, 0.0001, 1.00),
    "6J": ("6J", 12_500_000.0, 0.0000005, 4.22),
    "6B": ("6B", 62500.0, 0.0001, 4.22),
    "NQ": ("MNQ", 2.0, 0.25, 1.22),
    "ES": ("MES", 5.0, 0.25, 1.22),
}
XM = ["CL", "GC", "NG", "RTY", "YM", "ZN", "6E", "6J", "6B"]


def cost_pts(sym, mult=1.0):
    _, pv, tick, fee = SPEC[sym]
    return mult * (fee / pv + 2 * tick)


def news():
    return set(pd.read_csv(ROOT / "calendar_data" / "events.csv", parse_dates=["date"])["date"])


def bars(sym, end=WF_END, start=None):
    """Clean 1-minute bars up to ``end`` (default: end of the walk-forward year; the holdout is never loaded)."""
    p = BARS / f"{sym}_1m.parquet"
    if not p.exists():
        files = sorted(RAW.glob(f"GLBX.MDP3_ohlcv-1m_{sym}.v.0_*.dbn.zst"))
        files = [f for f in files if "HOLDOUT" not in f.name]
        if not files:
            raise FileNotFoundError(sym)
        df = dbn_to_bars([str(f) for f in files], sym)
        BARS.mkdir(parents=True, exist_ok=True)
        df.drop(columns=["ts_ct"]).to_parquet(p)
    df = pd.read_parquet(p)
    if df["trading_day"].max() >= pd.Timestamp("2025-11-03"):
        df = df[df["trading_day"] < pd.Timestamp(end)]
    df = df[df["trading_day"] < pd.Timestamp(end)]
    if start is not None:
        df = df[df["trading_day"] >= pd.Timestamp(start)]
    dg = ROOT / "data" / "degraded_days.json"
    if dg.exists():
        df = df[~df["trading_day"].astype(str).isin(set(json.loads(dg.read_text())))]
    return df


def tstat(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return float(x.mean() / x.std(ddof=1) * np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else float("nan")


def sharpe(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return float(x.mean() / x.std(ddof=1) * np.sqrt(252)) if len(x) > 2 and x.std() > 0 else float("nan")
