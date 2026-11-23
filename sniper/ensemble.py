"""Nine-setting ensemble of the noise-area breakout (ENS-01), with a trade log and true combined intraday equity.

One "set" is one contract per setting (nine contracts when every setting is in the market). The daily record is
built from the summed minute-by-minute equity of all nine settings, so the worst open loss of the day is that of
the combined position, not the average of nine separate worst cases (which overstates it).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .session_rule import SessionData, run_session

SETTINGS = [(lb, vm) for lb in (7, 14, 28) for vm in (0.8, 1.0, 1.2)]


def run_ensemble(sd: SessionData, cost_pts: float, skip_days: set | None = None, settings=SETTINGS,
                 **kw) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (trades, days). ``trades`` has one row per trade of each setting (one contract), with ``lookback``
    and ``vm`` columns. ``days`` is per SET (sum of the settings, in points of one contract):
    net_pts, gross_pts, round_trips (total over settings), mae_pts, mfe_pts, max_pos (peak |net position|), dvol_pts.
    Days are those on which the middle setting (14, 1.0) could trade and the expected daily move is known."""
    base = run_session(sd, cost_pts, skip_days=skip_days, **kw)[1]
    base = base[base["dvol_pts"].notna() & (base["dvol_pts"] > 0)]
    parts = []
    for lb, vm in settings:
        t = run_session(sd, cost_pts, lookback=lb, vm=vm, skip_days=skip_days, **kw)[0]
        if len(t):
            parts.append(t.assign(lookback=lb, vm=vm))
    trades = pd.concat(parts, ignore_index=True)
    trades = trades[trades["day"].isin(base.index)].reset_index(drop=True)
    pos_of = {d: i for i, d in enumerate(sd.days)}
    half = cost_pts / 2
    rows = {}
    for day, g in trades.groupby("day"):
        c = sd.px[pos_of[day]]
        eq, pos = np.zeros(sd.n + 1), np.zeros(sd.n + 1)
        for dr, a, b, ep, net in zip(g["dir"], g["fill"], g["exit_min"], g["entry_px"], g["net_pts"]):
            eq[a:b] += dr * (c[a:b] - ep) - half
            eq[b:] += net
            pos[a:b] += dr
        rows[day] = (g["net_pts"].sum(), g["gross_pts"].sum(), float(len(g)), min(eq.min(), 0.0), max(eq.max(), 0.0),
                     float(np.abs(pos).max()))
    d = pd.DataFrame.from_dict(rows, orient="index", columns=["net_pts", "gross_pts", "round_trips", "mae_pts", "mfe_pts", "max_pos"])
    days = d.reindex(base.index).fillna(0.0)
    days["dvol_pts"] = base["dvol_pts"]
    return trades, days


def days_from_trades(trades: pd.DataFrame, index: pd.DatetimeIndex, px_days: pd.DatetimeIndex, px: np.ndarray,
                     net_col: str = "net_pts") -> pd.DataFrame:
    """Daily record (per set, points) for any subset of logged trades, with the combined intraday equity.
    ``index`` is the list of days to report; days without trades are zero."""
    pos_of = {d: i for i, d in enumerate(px_days)}
    n = px.shape[1] - 1
    rows = {}
    for day, g in trades.groupby("day"):
        c = px[pos_of[day]]
        eq, pos = np.zeros(n + 1), np.zeros(n + 1)
        for dr, a, b, ep, net, gross in zip(g["dir"], g["fill"], g["exit_min"], g["entry_px"], g[net_col], g["gross_pts"]):
            eq[a:b] += dr * (c[a:b] - ep) - (gross - net) / 2
            eq[b:] += net
            pos[a:b] += dr
        rows[day] = (g[net_col].sum(), g["gross_pts"].sum(), float(len(g)), min(eq.min(), 0.0), max(eq.max(), 0.0), float(np.abs(pos).max()))
    d = pd.DataFrame.from_dict(rows, orient="index", columns=["net_pts", "gross_pts", "round_trips", "mae_pts", "mfe_pts", "max_pos"])
    return d.reindex(index).fillna(0.0)
