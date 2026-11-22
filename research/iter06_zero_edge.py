"""Iteration 6: zero-edge baseline. What do Topstep's rules alone give a strategy with no edge?

Strategy: once a day at 9:00 CT enter MNQ at market in a direction with no information, with a bracket
(stop and target in NQ points) and a time exit at 15:00 CT. Each development day is used twice, once long
and once short, so the edge before costs is exactly zero by construction. Real 1-minute NQ paths are used,
so intraday open losses are realistic.
Fills: entry 1 tick worse; stop 1 tick worse; target only if price trades THROUGH it; if stop and target
fall in the same bar the stop is assumed. Fees from the rule spec.

Run: python research/iter06_zero_edge.py
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from sniper import ACCOUNT_SIZES, load_rules  # noqa: E402
from sniper.data import DEV_END, flag_days, load_bars  # noqa: E402
from sniper.montecarlo import DayRecords, block_bootstrap, simulate_combine, simulate_xfa  # noqa: E402

TICK, PV = 0.25, 2.0
POLICIES = {"stop20_target20": (20, 20), "stop20_target40": (20, 40), "stop40_target20": (40, 20),
            "stop40_target80": (40, 80), "stop60_target30": (60, 30)}


def day_paths():
    df = load_bars("NQ", end=str(DEV_END.date()))
    days = flag_days(df)
    full = days.index[(~days["half_day"]) & (days["last_rth_minute"] == 899)]
    d = df[df["rth"] & (df["minute_ct"] >= 539) & df["trading_day"].isin(full)]
    out = []
    for _, x in d.groupby("trading_day"):
        if len(x) < 300 or x["instrument_id"].nunique() > 1:
            continue
        out.append((x["close"].iloc[0], x["high"].to_numpy()[1:], x["low"].to_numpy()[1:], x["close"].to_numpy()[-1]))
    return out


def records(paths, stop, target):
    pnl, mae = [], []
    for ref, hi, lo, last in paths:
        for sig in (1, -1):
            entry = ref + sig * TICK
            adv = (lo - entry) if sig > 0 else (entry - hi)      # worst excursion per bar (<=0 when adverse)
            fav = (hi - entry) if sig > 0 else (entry - lo)
            s_hit = np.nonzero(adv <= -stop)[0]
            t_hit = np.nonzero(fav > target)[0]
            si = s_hit[0] if s_hit.size else 10**9
            ti = t_hit[0] if t_hit.size else 10**9
            if si <= ti and si < 10**9:
                pts, worst = -stop - TICK, -stop - TICK
            elif ti < 10**9:
                pts, worst = target, min(adv[: ti + 1].min(), 0.0)
            else:
                pts, worst = sig * (last - entry) - TICK, min(adv.min(), 0.0)
            pnl.append(pts * PV); mae.append(worst * PV)
    n = len(pnl)
    return DayRecords(np.ones(n, bool), np.array(pnl), np.array(mae), "MNQ")


def main():
    rules = load_rules()
    paths = day_paths()
    out = {}
    for name, (stop, target) in POLICIES.items():
        rec = records(paths, stop, target)
        fee = rules.commission_per_side["MNQ"] * 2
        net = rec.pnl - fee
        print(f"\n== {name}: {len(net)} day-records, mean net ${net.mean():.2f}/MNQ (gross ${rec.pnl.mean():.2f}), "
              f"hit {np.mean(net > 0):.1%}, sd ${net.std():.0f}")
        idx = block_bootstrap(len(net), 4000, 500, 1, np.random.default_rng(0))  # zero edge: i.i.d. days
        out[name] = {"mean_net": float(net.mean()), "sizes": {}}
        for size in ACCOUNT_SIZES:
            spec = rules.account(size)
            best = None
            for n in (5, 10, 20, 30, 50, 75, 100, 150):
                if n > spec.max_lots * 10:
                    continue
                c = simulate_combine(rec, idx, n, size, rules).summary()
                xs = simulate_xfa(rec, idx, n, size, "standard", rules).summary()
                xc = simulate_xfa(rec, idx, n, size, "consistency", rules).summary()
                months = max(1.0, np.ceil(c["median_days_any"] / 21))
                v = max(xs["mean_to_trader"], xc["mean_to_trader"])
                ev = c["pass"] * (v - spec.activation_fee_standard) - months * (spec.combine_monthly_standard + rules.api_monthly)
                row = {"n": n, "pass": c["pass"], "pass_lo": c["pass_lo"], "pass_hi": c["pass_hi"], "days": c["median_days_any"],
                       "xfa_p_std": xs["p_payout"], "xfa_p_cons": xc["p_payout"], "xfa_usd_std": xs["mean_to_trader"],
                       "xfa_usd_cons": xc["mean_to_trader"], "months": months, "ev": ev}
                out[name]["sizes"].setdefault(size, []).append(row)
                if best is None or ev > best["ev"]:
                    best = row
            b = best
            print(f"   {size}: best EV at {b['n']} MNQ: pass {b['pass']:.1%} [{b['pass_lo']:.1%},{b['pass_hi']:.1%}], "
                  f"median {b['days']:.0f} days, XFA payout std {b['xfa_p_std']:.1%} / cons {b['xfa_p_cons']:.1%}, "
                  f"E[$ to trader | XFA] std ${b['xfa_usd_std']:.0f} / cons ${b['xfa_usd_cons']:.0f}, EV per attempt ${b['ev']:.0f}")
    (ROOT / "reports" / "iter_06_zero_edge.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
