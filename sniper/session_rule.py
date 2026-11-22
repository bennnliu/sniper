"""Noise-area breakout in any session, with a trade-by-trade log and optional risk limits.

A session is [start, end] in CT minutes of the day; it may cross midnight (Asia). Every quantity is anchored to
the session open (the price at ``start``). For the New York session the bands also use the prior 15:00 CT close,
exactly as in sniper.noise, and the two engines agree on that session (tests/test_session_rule.py).

Decisions happen at ``step``-minute checks from prices known then; fills are ``delay`` minutes later; the
position is closed at ``end``. All entry-time features in the trade log use only data known at the decision.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

SESSIONS = {"NY": (510, 900), "ASIA": (18 * 60, 60), "LONDON": (120, 510)}  # CT minutes; ASIA crosses midnight
DAY0 = 17 * 60  # the trading day starts at 17:00 CT


def _smin(minute_ct):
    """Minutes since the 17:00 CT start of the trading day."""
    return (np.asarray(minute_ct) - DAY0) % 1440


@dataclass
class SessionData:
    name: str
    days: pd.DatetimeIndex
    px: np.ndarray  # days x (n+1): price at session minute 0..n (column 0 = session open)
    vwap: np.ndarray  # days x (n+1)
    cumvol: np.ndarray
    absmove: np.ndarray  # cumulative sum of |1-minute change|
    prev_close: np.ndarray  # prior full day's 15:00 CT close, same contract (NaN otherwise)
    rv20: np.ndarray  # trailing 20-day std of 15:00-15:00 log returns, known before the trading day
    n: int
    start_ct: int


def build_session(df: pd.DataFrame, name: str, min_coverage: float = 0.8) -> SessionData:
    start, end = SESSIONS[name]
    s0, s1 = int(_smin(start)), int(_smin(end))
    n = s1 - s0
    d = df.assign(s_end=_smin(df["minute_ct"].to_numpy()) + 1)
    # the bar ending exactly at the session start gives the open
    d = d[(d["s_end"] >= s0) & (d["s_end"] <= s1)]
    cols = range(s0, s1 + 1)
    close = d.pivot_table(index="trading_day", columns="s_end", values="close", aggfunc="last").reindex(columns=cols)
    vol = d.pivot_table(index="trading_day", columns="s_end", values="volume", aggfunc="sum").reindex(columns=cols).fillna(0)
    tp = ((d["high"] + d["low"] + d["close"]) / 3 * d["volume"])
    pv = d.assign(pv=tp).pivot_table(index="trading_day", columns="s_end", values="pv", aggfunc="sum").reindex(columns=cols).fillna(0)
    inst = d.groupby("trading_day")["instrument_id"].agg(["first", "last", "size"])
    ok = (inst["first"] == inst["last"]) & (inst["size"] >= min_coverage * n) & close[s0].notna().reindex(inst.index) \
        & close[s1].notna().reindex(inst.index)
    days = inst.index[ok]
    close = close.loc[days].ffill(axis=1)
    vol, pv = vol.loc[days].copy(), pv.loc[days].copy()
    vol[s0], pv[s0] = 0.0, 0.0  # volume before the open does not count
    cv = vol.cumsum(axis=1).to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        vw = pv.cumsum(axis=1).to_numpy() / cv
    px = close.to_numpy()
    vw = np.where(np.isfinite(vw), vw, px)
    absmove = np.concatenate([np.zeros((len(days), 1)), np.abs(np.diff(px, axis=1)).cumsum(axis=1)], axis=1)
    # prior 15:00 CT close and daily volatility, from the day session
    rth = df[df["minute_ct"] == 899].groupby("trading_day").agg(c=("close", "last"), i=("instrument_id", "last"))
    cc = np.log(rth["c"] / rth["c"].shift(1)).where(rth["i"] == rth["i"].shift(1))
    rv = cc.rolling(20, min_periods=15).std()
    prev_c = rth["c"].shift(1).where(rth["i"].shift(1).reindex(rth.index) == inst["first"].reindex(rth.index))
    return SessionData(name, pd.DatetimeIndex(days), px, vw, cv, absmove,
                       prev_c.reindex(days).to_numpy(), rv.shift(1).reindex(days).ffill().to_numpy(), n, start)


def run_session(sd: SessionData, cost_pts: float, lookback: int = 14, vm: float = 1.0, delay: int = 1, step: int = 30,
                use_prev_close: bool | None = None, use_vwap: bool = True, max_entries: int | None = None,
                last_entry_min: int | None = None, first_entry_min: int | None = None,
                session_stop_sigma: float | None = None, trade_stop_sigma: float | None = None,
                allow_long: bool = True, allow_short: bool = True, skip_days: set | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (trades, days). Points are for one contract; ``net`` includes ``cost_pts`` per round trip.

    Optional risk limits (all off by default, which reproduces the frozen rule):
      max_entries         stop opening new positions after this many entries in the session
      first/last_entry_min  only open positions at checks within [first, last] minutes after the session open
      session_stop_sigma  flatten and stop for the session once the session's net loss exceeds this multiple of
                          the expected daily move (prev_close x rv20), checked every minute
      trade_stop_sigma    close a trade once its own open loss exceeds this multiple of the expected daily move,
                          checked every minute; later checks may open a new trade
      allow_long/short    one-sided versions
    """
    use_prev_close = sd.name == "NY" if use_prev_close is None else use_prev_close
    checks = np.arange(step, sd.n, step)
    px, vwm = sd.px, sd.vwap
    op = px[:, 0]
    move = np.abs(px[:, checks] / op[:, None] - 1)
    sigma = pd.DataFrame(move).rolling(lookback, min_periods=lookback).mean().shift(1).to_numpy()
    pc = np.where(np.isfinite(sd.prev_close), sd.prev_close, op) if use_prev_close else op
    hi, lo = np.maximum(op, pc), np.minimum(op, pc)
    ub, lb = hi[:, None] * (1 + vm * sigma), lo[:, None] * (1 - vm * sigma)
    relvol_base = pd.DataFrame(sd.cumvol[:, checks]).rolling(20, min_periods=10).mean().shift(1).to_numpy()
    half = cost_pts / 2
    trades, drows = [], []
    skip = skip_days or set()
    for di, day in enumerate(sd.days):
        if not np.isfinite(sigma[di, 0]) or (use_prev_close and not np.isfinite(sd.prev_close[di])) or day in skip:
            continue
        c = px[di]
        dvol = (sd.prev_close[di] if np.isfinite(sd.prev_close[di]) else op[di]) * (sd.rv20[di] if np.isfinite(sd.rv20[di]) else np.nan)
        pos, entries, stopped = 0, 0, False
        eq_real, cur = 0.0, None
        day_trades = []

        def close_trade(t_min, reason):
            nonlocal eq_real, cur
            exit_px = c[t_min]
            path = cur["dir"] * (c[cur["fill"]:t_min + 1] - cur["entry_px"])
            gross = cur["dir"] * (exit_px - cur["entry_px"])
            cur.pop("checked", None)
            cur.update(exit_min=t_min, exit_px=exit_px, gross_pts=gross, net_pts=gross - cost_pts,
                       mae_pts=float(min(path.min(), 0)), mfe_pts=float(max(path.max(), 0)), exit_reason=reason,
                       minutes_held=t_min - cur["fill"])
            eq_real += gross - cost_pts
            day_trades.append(cur)
            cur = None

        def risk_stops(upto, pos_now):
            """Minute-level stops on the open trade between its fill and ``upto``. Returns (pos, session_stopped)."""
            if cur is None or not np.isfinite(dvol) or (session_stop_sigma is None and trade_stop_sigma is None):
                return pos_now, False
            a = max(cur["fill"], cur.get("checked", cur["fill"]))
            if upto < a:
                return pos_now, False
            open_pnl = cur["dir"] * (c[a:upto + 1] - cur["entry_px"]) - cost_pts
            cur["checked"] = upto
            hits = []
            if session_stop_sigma is not None:
                h = np.nonzero(open_pnl + eq_real <= -session_stop_sigma * dvol)[0]
                if h.size:
                    hits.append((h[0], "session_stop"))
            if trade_stop_sigma is not None:
                h = np.nonzero(open_pnl <= -trade_stop_sigma * dvol)[0]
                if h.size:
                    hits.append((h[0], "trade_stop"))
            if not hits:
                return pos_now, False
            k, why = min(hits)
            close_trade(min(a + k + delay, sd.n), why)
            return 0, why == "session_stop"

        for i, chk in enumerate(checks):
            if stopped:
                break
            pos, stopped = risk_stops(chk, pos)
            if stopped:
                break
            x, u, l, v = c[chk], ub[di, i], lb[di, i], vwm[di, chk]
            new = pos
            if x > u and (not use_vwap or x >= v):
                new = 1
            elif x < l and (not use_vwap or x <= v):
                new = -1
            elif pos == 1 and x < (max(u, v) if use_vwap else u):
                new = 0
            elif pos == -1 and x > (min(l, v) if use_vwap else l):
                new = 0
            if (new == 1 and not allow_long) or (new == -1 and not allow_short):
                new = 0 if pos != 0 else pos
            if new != pos and new != 0:
                allowed = (max_entries is None or entries < max_entries) and \
                          (last_entry_min is None or chk <= last_entry_min) and \
                          (first_entry_min is None or chk >= first_entry_min)
                if not allowed:
                    new = 0 if pos != 0 and ((pos == 1 and x < u) or (pos == -1 and x > l) or new == -pos) else pos
            if new == pos:
                continue
            fill = min(chk + delay, sd.n)
            if cur is not None:
                close_trade(fill, "flip" if new != 0 else "stop")
            if new != 0:
                band = u if new == 1 else l
                sig_pts = op[di] * sigma[di, i]
                cur = {"session": sd.name, "day": day, "check_min": int(chk), "ct_minute": int((sd.start_ct + chk) % 1440),
                       "dir": new, "fill": fill, "entry_px": c[fill], "entry_no": entries + 1,
                       # ---- features known at the decision ----
                       "f_sigma_pct": sigma[di, i] * 100,
                       "f_excess": new * (x - band) / sig_pts,
                       "f_dist_vwap": new * (x - v) / sig_pts,
                       "f_move_open": new * (x - op[di]) / sig_pts,
                       "f_efficiency": abs(x - op[di]) / sd.absmove[di, chk] if sd.absmove[di, chk] > 0 else 0.0,
                       "f_relvol": sd.cumvol[di, chk] / relvol_base[di, i] if np.isfinite(relvol_base[di, i]) and relvol_base[di, i] > 0 else np.nan,
                       "f_rv20": sd.rv20[di] * 100 if np.isfinite(sd.rv20[di]) else np.nan,
                       "f_gap": new * (op[di] - sd.prev_close[di]) / dvol if np.isfinite(dvol) and dvol > 0 else np.nan,
                       "f_prior_pnl": eq_real / dvol if np.isfinite(dvol) and dvol > 0 else 0.0,
                       "f_last30": new * (x - c[chk - step]) / sig_pts,
                       "f_dow": day.dayofweek, "dvol_pts": dvol}
                entries += 1
            pos = new
        if cur is not None:
            pos, stopped = risk_stops(sd.n, pos)
        if cur is not None:
            close_trade(sd.n, "session_end")
        trades += day_trades
        # daily record: net points, intraday equity extremes (minute level, realised + open)
        if day_trades:
            eq = np.zeros(sd.n + 1)
            for tr in day_trades:
                a, b = tr["fill"], tr["exit_min"]
                eq[a:b] += tr["dir"] * (c[a:b] - tr["entry_px"]) - half  # open: entry cost paid
                eq[b:] += tr["net_pts"]  # closed: full round trip paid
            net = sum(tr["net_pts"] for tr in day_trades)
            drows.append((day, net, len(day_trades), min(eq.min(), 0.0), max(eq.max(), 0.0), dvol))
        else:
            drows.append((day, 0.0, 0, 0.0, 0.0, dvol))
    tdf = pd.DataFrame(trades)
    ddf = pd.DataFrame(drows, columns=["day", "net_pts", "round_trips", "mae_pts", "mfe_pts", "dvol_pts"]).set_index("day")
    return tdf, ddf
