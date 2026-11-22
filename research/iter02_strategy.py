"""Iteration 2, stage 3: IMOM-04 on NQ as a strategy, replayed under Topstep rules.

Rule (frozen before the Monte Carlo):
  * High-volatility day: trailing 20-day close-to-close volatility above its
    expanding 2/3 quantile (both from data before the day).
  * At 14:30 CT, buy (sell) MNQ if the return from the prior 15:00 CT close to
    14:30 CT is positive (negative). Market order: fill = 14:30 close plus 1 tick.
  * Exit at 15:00 CT close minus 1 tick (before Topstep's 3:10 PM flat).
  * Variant B: protective stop 40 NQ points from the fill, filled 1 tick worse.
Costs: TopstepX fees (MNQ $1.22 round trip) plus the 2 ticks of slippage above.

Run: python research/iter02_strategy.py [dev|wf]
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "research"))
import iter01_stage1 as it  # noqa: E402
from sniper import ACCOUNT_SIZES, Fill, Mark, load_rules  # noqa: E402
from sniper.data import DEV_END, WALK_FORWARD_END, load_bars  # noqa: E402
from sniper.montecarlo import (DayRecords, block_bootstrap, simulate_combine, simulate_xfa,  # noqa: E402
                               validate_against_topstepsim)

TICK, PV_MNQ, SLIP = 0.25, 2.0, 0.25
CT = ZoneInfo("America/Chicago")


def build_days(period: str, stop_pts: float | None):
    df = load_bars("NQ", end=str(WALK_FORWARD_END.date()))
    t = it.daily_table(df)
    t["hi"] = t["rv20"] > t["rv20"].expanding(60).quantile(2 / 3).shift(1)
    lo, hi_ = (None, DEV_END.tz_localize(None)) if period == "dev" else (DEV_END.tz_localize(None), WALK_FORWARD_END.tz_localize(None))
    t = t[(t.index < hi_) & ((t.index >= lo) if lo is not None else True)]
    late = df[(df["minute_ct"] >= 869) & (df["minute_ct"] <= 899)]
    late = late[late["trading_day"].isin(t.index)]
    g = {d: x for d, x in late.groupby("trading_day")}
    rows, paths = [], []
    for d, r in t.iterrows():
        x = g.get(d)
        sig = np.sign(r["r_rod"]) if (bool(r["hi"]) and np.isfinite(r["r_rod"])) else 0
        if x is None or len(x) < 31 or sig == 0:
            rows.append((False, 0.0, 0.0)); paths.append(None); continue
        entry = x[x.minute_ct == 869]["close"].iloc[0] + sig * SLIP
        bars = x[x.minute_ct >= 870]
        adverse = (bars["low"] - entry) if sig > 0 else (entry - bars["high"])  # per-bar worst, points
        close_pnl = sig * (bars["close"] - entry)
        exit_pts = sig * (bars["close"].iloc[-1] - entry) - SLIP
        if stop_pts is not None and (adverse <= -stop_pts).any():
            k = int(np.argmax((adverse <= -stop_pts).to_numpy()))
            exit_pts = -stop_pts - SLIP
            adverse, close_pnl = adverse.iloc[: k + 1].clip(lower=-stop_pts - SLIP), close_pnl.iloc[: k + 1]
        rows.append((True, exit_pts * PV_MNQ, min(adverse.min(), 0.0) * PV_MNQ))
        paths.append((sig, entry, bars, exit_pts, stop_pts))
    arr = np.array(rows, dtype=object)
    rec = DayRecords(arr[:, 0].astype(bool), arr[:, 1].astype(float), arr[:, 2].astype(float), "MNQ")
    return t.index, rec, paths


def event_factory(path):
    """Turn one day's trade into TopstepSim events on a synthetic date."""
    def make(day, n):
        if path is None:
            return []
        sig, entry, bars, exit_pts, stop = path
        ev = [Fill(datetime(day.year, day.month, day.day, 14, 30, tzinfo=CT), "MNQ", int(sig * n), entry)]
        for _, b in bars.iterrows():
            mm = int(b.minute_ct) + 1
            ts = datetime(day.year, day.month, day.day, mm // 60, mm % 60, tzinfo=CT)
            adv = b["low"] if sig > 0 else b["high"]
            if stop is not None and sig * (adv - entry) <= -stop:
                ev.append(Mark(ts, "MNQ", entry - sig * (stop + SLIP)))
                ev.append(Fill(ts, "MNQ", int(-sig * n), entry - sig * (stop + SLIP)))
                return ev
            ev.append(Mark(ts, "MNQ", adv))
        last = bars.iloc[-1]
        ts = datetime(day.year, day.month, day.day, 15, 0, 30, tzinfo=CT)
        ev.append(Fill(ts, "MNQ", int(-sig * n), entry + sig * exit_pts))
        return ev
    return make


def main(period="dev"):
    rules = load_rules()
    rng = np.random.default_rng(0)
    out = {}
    for variant, stop in (("A_no_stop", None), ("B_stop40", 40.0)):
        idx_days, rec, paths = build_days(period, stop)
        tr = rec.traded
        pnl = rec.pnl[tr]
        fee = rules.commission_per_side["MNQ"] * 2
        net = pnl - fee
        daily = pd.Series(np.where(tr, rec.pnl - fee, 0.0), index=idx_days)
        print(f"\n== {variant} ({period}) per 1 MNQ: trades {tr.sum()} of {len(tr)} days, "
              f"mean net ${net.mean():.2f}, hit {np.mean(net > 0):.1%}, avg win ${net[net>0].mean():.1f}, "
              f"avg loss ${net[net<=0].mean():.1f}, PF {net[net>0].sum()/-net[net<=0].sum():.2f}, worst ${net.min():.0f}, "
              f"t {net.mean()/net.std()*np.sqrt(len(net)):.2f}, at 2x cost mean ${(pnl - 2*fee - 2*SLIP*PV_MNQ).mean():.2f}")
        res = {"trades": int(tr.sum()), "days": int(len(tr)), "mean_net_per_mnq": float(net.mean()),
               "hit": float(np.mean(net > 0)), "worst_per_mnq": float(net.min())}
        if period == "dev":
            # Validate the fast engine against TopstepSim on 30 paths
            makers = [event_factory(p) for p in paths]
            vidx = block_bootstrap(len(tr), 30, 400, 10, np.random.default_rng(1))
            agree = sum(a == b for a, b in (validate_against_topstepsim(makers, rec, vidx[i], 10, "50K", rules)
                                             for i in range(30)))
            print(f"   fast engine vs TopstepSim agreement: {agree}/30 paths")
            res["validation_agree_of_30"] = agree
            idx = block_bootstrap(len(tr), 2000, 750, 10, rng)
            res["sizes"] = {}
            for size in ACCOUNT_SIZES:
                spec = rules.account(size)
                res["sizes"][size] = {}
                for n in (2, 5, 10, 15, 20, 30, 40):
                    if n > spec.max_lots * 10:
                        continue
                    c = simulate_combine(rec, idx, n, size, rules).summary()
                    c2 = simulate_combine(rec, idx, n, size, rules, cost_mult=2.0).summary()
                    xs = simulate_xfa(rec, idx, n, size, "standard", rules).summary()
                    xc = simulate_xfa(rec, idx, n, size, "consistency", rules).summary()
                    months = max(1.0, np.ceil(c["median_days_any"] / 21))
                    v = max(xs["mean_to_trader"], xc["mean_to_trader"])
                    ev = c["pass"] * (v - spec.activation_fee_standard) - months * (spec.combine_monthly_standard + rules.api_monthly)
                    res["sizes"][size][n] = {"combine": c, "combine_2x_cost_pass": c2["pass"], "xfa_standard": xs,
                                             "xfa_consistency": xc, "ev_per_attempt": ev, "months_assumed": months}
                    print(f"   {size} {n:2d} MNQ: pass {c['pass']:.1%} [{c['pass_lo']:.1%},{c['pass_hi']:.1%}] "
                          f"breach {c['breach']:.1%} med days {c['median_days_to_pass']:.0f} | 2x cost pass {c2['pass']:.1%} | "
                          f"XFA payout std {xs['p_payout']:.1%} cons {xc['p_payout']:.1%} "
                          f"E[to trader] std ${xs['mean_to_trader']:.0f} cons ${xc['mean_to_trader']:.0f} | EV/attempt ${ev:.0f}")
        out[variant] = res
    (ROOT / "reports" / f"iter_02_strategy_{period}.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dev")
