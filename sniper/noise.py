"""NOISE-01: noise-area breakout rule (Zarattini, Aziz and Barbon), simulated minute by minute.

Decisions are made at the half-hour checks from prices known at that minute. Orders fill ``delay`` minutes
later at the 1-minute close (delay=1 is the honest default: a market order sent after the check). Any open
position is closed at 15:00 CT. Costs are charged per position change, half a round trip per unit.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import features as F


def minute_matrix(df: pd.DataFrame, days: pd.Index) -> pd.DataFrame:
    """Day-session closes, one row per day, columns = CT minute at which the bar ENDS (511..900)."""
    d = df[df["rth"]]
    m = d.pivot_table(index="trading_day", columns="minute_ct", values="close", aggfunc="last")
    m.columns = [c + 1 for c in m.columns]
    return m.reindex(index=days, columns=range(511, 901)).ffill(axis=1)


def run_rule(df: pd.DataFrame, p: pd.DataFrame, cost_pts: float, lookback: int = 14, vm: float = 1.0,
             delay: int = 1, use_vwap: bool = True) -> pd.DataFrame:
    """Daily results for one contract: net points, gross points, round trips, worst intraday net drawdown
    (mae_pts, <= 0) and best intraday net gain."""
    ub, lb = F.noise_bands(p, lookback=lookback, vm=vm)
    vw = F.session_vwap(df, p.index)
    mm = minute_matrix(df, p.index)
    ok = ub[F.CHECKS[0]].notna() & p["prev_close"].notna() & mm[900].notna()
    half = cost_pts / 2
    rows = {}
    mins = np.arange(511, 901)
    for d in p.index[ok]:
        c = mm.loc[d].to_numpy()
        u, l, v = ub.loc[d].to_numpy(), lb.loc[d].to_numpy(), vw.loc[d].to_numpy()
        pos_at = np.zeros(len(c))  # position held over the minute ENDING at mins[i]
        pos, changes = 0, []
        for i, chk in enumerate(F.CHECKS):
            x = c[chk - 511]
            new = pos
            if x > u[i] and (not use_vwap or x >= v[i]):
                new = 1
            elif x < l[i] and (not use_vwap or x <= v[i]):
                new = -1
            elif pos == 1 and x < (max(u[i], v[i]) if use_vwap else u[i]):
                new = 0
            elif pos == -1 and x > (min(l[i], v[i]) if use_vwap else l[i]):
                new = 0
            if new != pos:
                fill_min = chk + delay
                changes.append((fill_min, abs(new - pos)))
                pos_at[mins > fill_min] = new
                pos = new
        if not changes:
            rows[d] = (0.0, 0.0, 0.0, 0.0, 0.0)
            continue
        step = np.diff(c, prepend=c[0]) * pos_at
        cost = np.zeros(len(c))
        for fm, n in changes:
            cost[fm - 511] += n * half
        cost[-1] += abs(pos) * half  # close at 15:00
        eq = np.cumsum(step - cost)
        units = sum(n for _, n in changes) + abs(pos)
        rows[d] = (eq[-1], step.sum(), units / 2, min(eq.min(), 0.0), max(eq.max(), 0.0))
    return pd.DataFrame.from_dict(rows, orient="index", columns=["net_pts", "gross_pts", "round_trips", "mae_pts", "mfe_pts"])
