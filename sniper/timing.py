"""Noise-area breakout with separate entry and exit timing, minute-level stops and alternative entries.

``run_flex`` with its defaults reproduces ``session_rule.run_session`` trade for trade (tests/test_timing.py).
Everything is decided from prices known at the decision minute; fills are ``delay`` minutes later at that
minute's close. Stops and targets are watched every minute and also fill ``delay`` minutes after they trigger.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .session_rule import SessionData


def run_flex(sd: SessionData, cost_pts: float, lookback: int = 14, vm: float = 1.0, delay: int = 1,
             entry_step: int = 30, exit_step: int = 30, exit_mode: str = "both",
             trail_k: float | None = None, target_k: float | None = None, breakeven_k: float | None = None,
             confirm_lag: int | None = None, pullback: bool = False, first30: bool = False,
             first_entry_min: int | None = None,
             skip_days: set | None = None) -> pd.DataFrame:
    """Trade log for one setting (points of one contract).

    exit_mode    "both": long exits below max(band, VWAP) (the frozen rule); "vwap": below VWAP; "band": below band
    trail_k      close when the trade gives back this many expected daily moves from its best price
    target_k     close when the trade is this many expected daily moves in profit
    breakeven_k  once the trade has been this far in profit, close if it returns to its entry price
    confirm_lag  entry also needs price beyond the band this many minutes before the check
    pullback     enter with a limit at the band level, valid until the next entry check; no fill, no trade
    first30      only trades in the direction of the first half hour's move
    first_entry_min  no new positions at checks earlier than this many minutes after the open
    After a stop or target, no re-entry in that direction until an entry check finds price back inside the band.
    """
    n = sd.n
    px, vwm = sd.px, sd.vwap
    op = px[:, 0]
    move = np.abs(px / op[:, None] - 1)
    sigma = pd.DataFrame(move).rolling(lookback, min_periods=lookback).mean().shift(1).to_numpy()
    pc = np.where(np.isfinite(sd.prev_close), sd.prev_close, op)
    hi, lo = np.maximum(op, pc), np.minimum(op, pc)
    UB, LB = hi[:, None] * (1 + vm * sigma), lo[:, None] * (1 - vm * sigma)
    eset = set(range(entry_step, n, entry_step)); xset = set(range(exit_step, n, exit_step))
    events = sorted(eset | xset)
    egrid = sorted(eset)
    nxt = {t: (egrid[i + 1] if i + 1 < len(egrid) else n) for i, t in enumerate(egrid)}
    skip = skip_days or set()
    stops = trail_k is not None or target_k is not None or breakeven_k is not None
    trades = []
    for di, day in enumerate(sd.days):
        if not np.isfinite(sigma[di, 30]) or not np.isfinite(sd.prev_close[di]) or day in skip:
            continue
        ca = px[di]; c = ca.tolist(); ub = UB[di].tolist(); lb = LB[di].tolist(); vw = vwm[di].tolist()
        dvol = sd.prev_close[di] * sd.rv20[di] if np.isfinite(sd.rv20[di]) else np.nan
        f30 = np.sign(c[30] - c[0])
        pos, cur, blocked, entries = 0, None, 0, 0

        def close(t_min, reason):
            nonlocal cur
            ex = c[t_min]
            path = cur["dir"] * (ca[cur["fill"]:t_min + 1] - cur["entry_px"])
            gross = cur["dir"] * (ex - cur["entry_px"])
            cur.pop("stop_min"); cur.pop("stop_why")
            cur.update(exit_min=t_min, exit_px=ex, gross_pts=gross, net_pts=gross - cost_pts, mae_pts=float(min(path.min(), 0)),
                       mfe_pts=float(max(path.max(), 0)), exit_reason=reason, minutes_held=t_min - cur["fill"])
            trades.append(cur)
            cur = None

        def open_(d, fill, entry_px, chk):
            nonlocal cur, entries
            entries += 1
            cur = {"day": day, "check_min": chk, "dir": d, "fill": fill, "entry_px": entry_px, "entry_no": entries, "dvol_pts": dvol, "stop_min": None, "stop_why": None}
            if stops and np.isfinite(dvol) and fill < n:
                path = d * (ca[fill:] - entry_px)
                best = []
                if trail_k is not None:
                    h = np.nonzero(np.maximum.accumulate(np.maximum(path, 0)) - path >= trail_k * dvol)[0]
                    if h.size:
                        best.append((int(h[0]), "trail"))
                if target_k is not None:
                    h = np.nonzero(path >= target_k * dvol)[0]
                    if h.size:
                        best.append((int(h[0]), "target"))
                if breakeven_k is not None:
                    h = np.nonzero(path >= breakeven_k * dvol)[0]
                    if h.size:
                        g = np.nonzero(path[h[0]:] <= 0)[0]
                        if g.size:
                            best.append((int(h[0] + g[0]), "breakeven"))
                if best:
                    k, why = min(best)
                    cur["stop_min"], cur["stop_why"] = fill + k, why

        for t in events:
            if cur is not None and cur["stop_min"] is not None and cur["stop_min"] <= t:
                blocked = cur["dir"]
                close(min(cur["stop_min"] + delay, n), cur["stop_why"]); pos = 0
            x, u, l, v = c[t], ub[t], lb[t], vw[t]
            new = pos
            sgn = 0
            if t in eset:
                if blocked == 1 and not x > u:
                    blocked = 0
                elif blocked == -1 and not x < l:
                    blocked = 0
                if x > u and x >= v:
                    sgn = 1
                elif x < l and x <= v:
                    sgn = -1
            if sgn != 0:
                ok = sgn != blocked
                if ok and confirm_lag is not None:
                    q = t - confirm_lag
                    ok = (c[q] > ub[q]) if sgn == 1 else (c[q] < lb[q])
                if ok and first30:
                    ok = t >= 30 and f30 == sgn
                if ok and first_entry_min is not None:
                    ok = t >= first_entry_min
                new = sgn if ok else (0 if pos == -sgn else pos)
            elif t in xset or t in eset:
                if pos == 1:
                    lev = max(u, v) if exit_mode == "both" else (v if exit_mode == "vwap" else u)
                    if x < lev:
                        new = 0
                elif pos == -1:
                    lev = min(l, v) if exit_mode == "both" else (v if exit_mode == "vwap" else l)
                    if x > lev:
                        new = 0
            if new == pos:
                continue
            fill = min(t + delay, n)
            if cur is not None:
                close(fill, "flip" if new != 0 else "stop")
            pos = 0
            if new != 0:
                if pullback:
                    level = u if new == 1 else l
                    seg = new * (ca[fill:nxt[t] + 1] - level)
                    h = np.nonzero(seg <= 0)[0]
                    if h.size:
                        open_(new, fill + int(h[0]), level, t); pos = new
                else:
                    open_(new, fill, c[fill], t); pos = new
        if cur is not None:
            if cur["stop_min"] is not None and cur["stop_min"] < n:
                close(min(cur["stop_min"] + delay, n), cur["stop_why"])
            else:
                close(n, "session_end")
    return pd.DataFrame(trades)


def apply_day_stop(trades: pd.DataFrame, px_days: pd.DatetimeIndex, px: np.ndarray, k: float, cost_pts: float, n_set: int = 9, delay: int = 1) -> pd.DataFrame:
    """Daily loss stop on the combined position of all settings. Once the set's result for the day, open positions
    included and costs paid, is at or below -k x expected daily move x n_set (points), everything is closed
    ``delay`` minutes later and nothing more is opened that day. Returns the changed trade log."""
    pos_of = {d: i for i, d in enumerate(px_days)}
    n = px.shape[1] - 1
    half = cost_pts / 2
    out = []
    for day, g in trades.groupby("day", sort=False):
        c = px[pos_of[day]]
        dvol = g["dvol_pts"].iloc[0]
        if not np.isfinite(dvol):
            out.append(g); continue
        eq = np.zeros(n + 1)
        for dr, a, b, ep, gross in zip(g["dir"], g["fill"], g["exit_min"], g["entry_px"], g["gross_pts"]):
            eq[a:b] += dr * (c[a:b] - ep) - half
            eq[b:] += gross - cost_pts
        h = np.nonzero(eq <= -k * dvol * n_set)[0]
        if not h.size:
            out.append(g); continue
        s = min(int(h[0]) + delay, n)
        g = g[g["fill"] < s].copy()
        cutm = (g["exit_min"] > s).to_numpy()
        if cutm.any():
            for ix in g.index[cutm]:
                dr, a, ep = g.at[ix, "dir"], int(g.at[ix, "fill"]), g.at[ix, "entry_px"]
                path = dr * (c[a:s + 1] - ep)
                g.at[ix, "exit_min"] = s; g.at[ix, "exit_px"] = c[s]; g.at[ix, "gross_pts"] = dr * (c[s] - ep); g.at[ix, "net_pts"] = dr * (c[s] - ep) - cost_pts
                g.at[ix, "mae_pts"] = float(min(path.min(), 0)); g.at[ix, "mfe_pts"] = float(max(path.max(), 0)); g.at[ix, "exit_reason"] = "day_stop"; g.at[ix, "minutes_held"] = s - a
        out.append(g)
    return pd.concat(out, ignore_index=True)
