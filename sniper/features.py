"""Daily-level feature library (iteration 8 onward).

Every function takes the cleaned 1-minute bar frame from ``sniper.data`` and returns values indexed by
trading day. A value for day t uses only bars up to the decision time named in its docstring; rolling
statistics are shifted so that they end on day t-1. tests/test_features.py checks this by truncation.

Times are CT minutes of the day (510 = 8:30, 900 = 15:00).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import flag_days, pivot_times

CHECKS = list(range(540, 871, 30))  # 9:00 ... 14:30 CT, the half-hour decision times


def day_grid(df: pd.DataFrame, minutes: list[int] | None = None) -> pd.DataFrame:
    """Closes at the given CT minutes for full day sessions traded in one contract, plus prev_close.

    prev_close is the previous full day's 15:00 CT close when it is the same contract, else NaN.
    """
    minutes = sorted(set((minutes or []) + [60, 120, 510, 515, 540, 840, 855, 870, 900, 915] + CHECKS))
    days = flag_days(df)
    full = days.index[(~days["half_day"]) & (days["first_rth_minute"] == 510) & (days["last_rth_minute"] == 899)]
    p = pivot_times(df, minutes)
    p = p.loc[p.index.isin(full)].dropna(subset=[510, 900])
    inst = df[df["rth"]].groupby("trading_day")["instrument_id"].agg(["first", "last"])
    p = p.join(inst)
    p = p[p["first"] == p["last"]]
    same = p["last"].shift(1) == p["first"]
    p["prev_close"] = p[900].shift(1).where(same)
    p["prev_1415"] = p[855].shift(1).where(same)
    p["prev_1515"] = p[915].shift(1).where(same)
    cc = np.log(p[900] / p["prev_close"])
    p["rv20"] = cc.rolling(20, min_periods=15).std().shift(1)  # daily sigma known before the day
    return p


def eod_reversal(p: pd.DataFrame) -> pd.Series:
    """EOD-01. Return from the prior close to 14:00 CT. Known at 14:00 CT."""
    return np.log(p[840] / p["prev_close"])


def gtbr_first30(p: pd.DataFrame, k: float = 1.0) -> pd.Series:
    """IMOM-07. First half-hour return, kept only when |prior close -> 14:30| > k daily sigma. Known at 14:30 CT."""
    hit = np.log(p[870] / p["prev_close"]).abs() > k * p["rv20"]
    return np.log(p[540] / p[510]).where(hit)


def overnight_drift_condition(p: pd.DataFrame) -> pd.Series:
    """OD-01. Previous day's 14:15 -> 15:15 CT return (bars-only proxy for closing order imbalance).
    Known at 15:15 CT the day before the 1:00-2:00 CT window."""
    return np.log(p["prev_1515"] / p["prev_1415"])


def opening_regime(df: pd.DataFrame, p: pd.DataFrame, q: float = 0.67, lookback: int = 20) -> pd.Series:
    """REG-01. True when |gap|, |first 30-minute return| and first-5-minute volume are each above their
    trailing ``lookback``-day ``q`` quantile (quantiles end on day t-1). Known at 9:00 CT."""
    rth = df[df["rth"] & (df["minute_ct"] < 515)]
    v5 = rth.groupby("trading_day")["volume"].sum().reindex(p.index)
    gap = np.log(p[510] / p["prev_close"]).abs()
    m30 = np.log(p[540] / p[510]).abs()
    flags = [x > x.rolling(lookback, min_periods=15).quantile(q).shift(1) for x in (gap, m30, v5)]
    return flags[0] & flags[1] & flags[2]


def noise_bands(p: pd.DataFrame, lookback: int = 14, vm: float = 1.0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """NOISE-01. Upper and lower noise-area bounds at each half-hour check (columns = CT minute).

    sigma(m) is the mean over the previous ``lookback`` days of |close(m) / open - 1|; the open is the
    8:30 CT price. Bounds for day t use sigma through day t-1, today's open and the prior close.
    """
    move = pd.DataFrame({m: (p[m] / p[510] - 1).abs() for m in CHECKS})
    sigma = move.rolling(lookback, min_periods=lookback).mean().shift(1)
    hi = np.maximum(p[510], p["prev_close"].fillna(p[510]))
    lo = np.minimum(p[510], p["prev_close"].fillna(p[510]))
    ub = (1 + vm * sigma).mul(hi, axis=0)
    lb = (1 - vm * sigma).mul(lo, axis=0)
    return ub, lb


def session_vwap(df: pd.DataFrame, days: pd.Index) -> pd.DataFrame:
    """Day-session VWAP (typical price) at each half-hour check, using bars that ended by that minute."""
    d = df[df["rth"]]
    tp = (d["high"] + d["low"] + d["close"]) / 3
    pv = (tp * d["volume"]).groupby(d["trading_day"]).cumsum()
    vv = d["volume"].groupby(d["trading_day"]).cumsum()
    v = pd.DataFrame({"vwap": pv / vv, "trading_day": d["trading_day"], "minute_ct": d["minute_ct"]})
    return pivot_times(v, CHECKS, col="vwap").reindex(days)
