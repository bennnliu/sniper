"""Iteration 15: VOL-01 as a start rule. Start Combine attempts only in the high-volatility regime.
Hypothesis in reports/SECOND_EDGE_LOG.md. Run: python research/iter15_regime_start.py [--wf]"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.iter12_second_edge import news  # noqa: E402
from research.iter13_tests import simulate, stream  # noqa: E402
from sniper.data import DEV_END, WALK_FORWARD_END  # noqa: E402
from sniper.rules import load_rules  # noqa: E402


def main():
    wf = "--wf" in sys.argv
    dd = stream(WALK_FORWARD_END if wf else DEV_END, news())
    dev_end = DEV_END.tz_localize(None)
    rel = dd["dvol_pts"] / dd["net_pts"].index.map(lambda d: 1.0)  # placeholder to keep index
    rv = dd["dvol_pts"] / (dd["dvol_pts"].rolling(250, min_periods=120).median())
    med_dvol = float((dd["dvol_pts"][dd.index < dev_end] * 2).median())
    n = len(dd)
    starts = np.arange(250, n - 30)
    if wf:
        starts = starts[dd.index[starts] >= dev_end]
    else:
        starts = starts[dd.index[starts] < dev_end]
    idx = starts[:, None] + np.arange(30)[None, :]
    high = (rv.to_numpy()[starts] > 1.0)
    rules = load_rules()
    pols = {"fixed 8 MNQ": lambda c, need, left, dv: np.full_like(c, 8.0),
            "volatility-scaled": lambda c, need, left, dv: 8.0 * med_dvol / dv}
    rng = np.random.default_rng(3)
    out = []
    for name, pol in pols.items():
        passed = sim_paths(dd, pol, idx, rules)
        ctrl = np.mean([sim_paths(dd, pol, idx, rules, flip=rng.random(idx.shape) < 0.5) for _ in range(20)], axis=0)
        for lab, m in (("high", high), ("low", ~high), ("all", np.ones_like(high))):
            k = max(1, int(m.sum() / 30))  # roughly independent windows
            p = float(passed[m].mean()); se = float(np.sqrt(p * (1 - p) / k))
            r = {"data": "WF" if wf else "DEV", "sizing": name, "start_regime": lab, "starts": int(m.sum()), "pass30": p, "se": se, "control": float(ctrl[m].mean())}
            out.append(r)
            print(f"{r['data']} {name:18s} start {lab:4s}: starts {r['starts']:4d} pass in 30d {p:6.1%} (se {se:.1%}) control {r['control']:6.1%} gain {p - r['control']:+6.1%}")
    # by year, high regime, fixed 8
    (ROOT / f"reports/iter_15{'_wf' if wf else ''}.json").write_text(json.dumps(out, indent=1))


def sim_paths(dd, pol, idx, rules, flip=None):
    """Like iter13.simulate but returns the per-path pass flag."""
    import research.iter13_tests as t
    spec = rules.account("50K")
    pnl, mae, mfe = dd["net_pts"].to_numpy() * 2, dd["mae_pts"].to_numpy() * 2, dd["mfe_pts"].to_numpy() * 2
    rts = dd["round_trips"].to_numpy(); cost = rts * 2.22; traded = rts > 0; dvol = dd["dvol_pts"].to_numpy() * 2
    P = idx.shape[0]; start = spec.starting_balance
    b = np.full(P, float(start)); m = np.full(P, float(start - spec.mll)); best = np.zeros(P); td = np.zeros(P, int)
    alive = np.ones(P, bool); passed = np.zeros(P, bool)
    for s in range(idx.shape[1]):
        d = idx[:, s]; p, a = pnl[d].copy(), mae[d].copy()
        if flip is not None:
            f = flip[:, s]; p = np.where(f, -(pnl[d] + cost[d]) - cost[d], p); a = np.where(f, np.minimum(-mfe[d] - cost[d], 0), a)
        c = np.clip(np.floor(pol(b - m, None, None, dvol[d])), 1, 50)
        tr = traded[d] & alive; hit = tr & (b + a * c <= m + 1e-9)
        b = np.where(hit, m, b); ok = tr & ~hit
        b = np.where(ok, b + p * c, b); best = np.where(ok, np.maximum(best, p * c), best); td += ok
        m = np.where(alive & ~hit, np.minimum(np.maximum(m, b - spec.mll), start), m)
        target = np.maximum(spec.profit_target, best / spec.consistency_fraction)
        win = alive & ~hit & (td >= spec.min_trading_days) & (b - start >= target - 1e-9)
        passed |= win; alive &= ~(hit | win)
    return passed.astype(float)


if __name__ == "__main__":
    main()
