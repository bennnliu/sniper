"""Iteration 8: NOISE-01B on MNQ through the Topstep rules (simulated), all three account sizes.

Day records come from the frozen rule (lookback 14, multiplier 1, VWAP stop, fills 1 minute after the check)
with 2 ticks of slippage per round trip; commissions come from the rule spec. Three day samples:
  dev      whole development period, Jun 2010 - Oct 2024 (headline: includes the flat 2010-2017 years)
  dev2018  development period from 2018 (chosen AFTER seeing the yearly table: optimistic, shown for range)
  wf       walk-forward year, Nov 2024 - Oct 2025 (one year: noisy)
Run: python research/iter08_montecarlo.py
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from sniper import ACCOUNT_SIZES, load_rules  # noqa: E402
from sniper import features as F  # noqa: E402
from sniper.data import DEV_END, WALK_FORWARD_END, load_bars  # noqa: E402
from sniper.montecarlo import DayRecords, block_bootstrap, simulate_combine, simulate_xfa  # noqa: E402
from sniper.noise import run_rule  # noqa: E402

MNQ_PV = 2.0
SLIP_PTS = 0.5  # 2 ticks per round trip, assumed


def main():
    rules = load_rules()
    fee_rt = rules.commission_per_side["MNQ"] * 2
    df = load_bars("NQ", end=str(WALK_FORWARD_END.date()))
    bad = set(json.loads((ROOT / "data/degraded_days.json").read_text()))
    df = df[~df["trading_day"].astype(str).isin(bad)]
    r = run_rule(df, F.day_grid(df), SLIP_PTS, delay=1)
    dev_end = DEV_END.tz_localize(None)
    samples = {"dev": r[r.index < dev_end], "dev2018": r[(r.index < dev_end) & (r.index >= "2018-01-01")],
               "wf": r[r.index >= dev_end]}
    out = {}
    for name, s in samples.items():
        traded = (s["round_trips"] > 0).to_numpy()
        extra = np.clip(s["round_trips"].to_numpy() - 1, 0, None) * fee_rt  # the engine charges one round trip
        rec = DayRecords(traded, s["net_pts"].to_numpy() * MNQ_PV - extra, s["mae_pts"].to_numpy() * MNQ_PV - extra, "MNQ")
        net = (rec.pnl - fee_rt)[traded]
        print(f"\n== {name}: {len(s)} days, {traded.sum()} traded, mean net ${net.mean():.2f}/MNQ per traded day, "
              f"sd ${net.std():.0f}, hit {np.mean(net > 0):.1%}, days >= $150 at 10 MNQ {np.mean(net * 10 >= 150):.1%}")
        idx = block_bootstrap(len(s), 4000, 500, 5, np.random.default_rng(0))
        out[name] = {"days": int(len(s)), "mean_net_per_mnq": float(net.mean()), "sizes": {}}
        for size in ACCOUNT_SIZES:
            spec = rules.account(size)
            best = None
            for n in (2, 3, 5, 8, 10, 15, 20, 30, 50):
                if n > spec.max_lots * 10:
                    continue
                c = simulate_combine(rec, idx, n, size, rules).summary()
                c2 = simulate_combine(rec, idx, n, size, rules, cost_mult=2.0).summary()
                xs = simulate_xfa(rec, idx, n, size, "standard", rules).summary()
                xc = simulate_xfa(rec, idx, n, size, "consistency", rules).summary()
                months = max(1.0, np.ceil(c["median_days_any"] / 21))
                v = max(xs["mean_to_trader"], xc["mean_to_trader"])
                ev = c["pass"] * (v - spec.activation_fee_standard) - months * (spec.combine_monthly_standard + rules.api_monthly)
                row = {"n": n, "pass": c["pass"], "pass_lo": c["pass_lo"], "pass_hi": c["pass_hi"], "pass_2x_fees": c2["pass"],
                       "days": c["median_days_any"], "xfa_p_std": xs["p_payout"], "xfa_p_cons": xc["p_payout"],
                       "xfa_usd_std": xs["mean_to_trader"], "xfa_usd_cons": xc["mean_to_trader"], "months": months, "ev": ev}
                out[name]["sizes"].setdefault(size, []).append(row)
                if best is None or ev > best["ev"]:
                    best = row
            b = best
            print(f"   {size}: best EV at {b['n']} MNQ: pass {b['pass']:.1%} [{b['pass_lo']:.1%},{b['pass_hi']:.1%}] "
                  f"(2x fees {b['pass_2x_fees']:.1%}), median {b['days']:.0f} days, XFA payout std {b['xfa_p_std']:.1%} / "
                  f"cons {b['xfa_p_cons']:.1%}, $ to trader std ${b['xfa_usd_std']:.0f} / cons ${b['xfa_usd_cons']:.0f}, "
                  f"EV per attempt ${b['ev']:.0f}")
    (ROOT / "reports" / "iter_08_montecarlo.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
