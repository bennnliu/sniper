"""Iteration 22: RISK-01 constant-risk sizing. Hypothesis and procedure in reports/SECOND_EDGE_LOG.md.
Run: python research/iter22_constant_risk.py           (steps 1-2, development data)
     python research/iter22_constant_risk.py --wf R    (step 3, walk-forward year, with the R chosen in step 1)"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.iter12_second_edge import news  # noqa: E402
from research.iter13_tests import simulate, stream  # noqa: E402
from research.iter15_regime_start import sim_paths  # noqa: E402
from sniper.data import DEV_END, WALK_FORWARD_END  # noqa: E402
from sniper.montecarlo import block_bootstrap  # noqa: E402
from sniper.rules import load_rules  # noqa: E402

F8 = lambda c, need, left, dv: np.full_like(c, 8.0)  # noqa: E731


def risk(R):
    return lambda c, need, left, dv: R / dv


def evaluate(s, pols, seed, label, out):
    rules = load_rules()
    rng = np.random.default_rng(seed)
    idx = block_bootstrap(len(s), 20000, 30, 5, rng)
    flip = rng.random(idx.shape) < 0.5
    for name, pf in pols.items():
        p, d = simulate(s, pf, idx, rules)
        pc, _ = simulate(s, pf, idx, rules, flip=flip)
        out[f"{label}|{name}"] = {"pass30": p, "control": pc, "gain": p - pc, "median_days": d}
        print(f"{label:24s} {name:14s} pass30 {p:6.1%} control {pc:6.1%} gain {p - pc:+6.1%} median days {d}")
    # real consecutive 30-day windows as well (no shuffling)
    if len(s) > 60:
        st = np.arange(0, len(s) - 30)
        ix = st[:, None] + np.arange(30)[None, :]
        for name, pf in pols.items():
            p = sim_paths(s, lambda c, n, l, dv, pf=pf: pf(c, n, l, dv), ix, rules).mean()
            out[f"{label}|{name}"]["pass30_real_windows"] = float(p)
            print(f"{'':24s} {name:14s} real consecutive windows: {p:6.1%} of {len(st)} starts")


def main():
    out = {}
    cut = pd.Timestamp("2021-01-01")
    dev_end = DEV_END.tz_localize(None)
    if "--wf" in sys.argv:
        R = float(sys.argv[sys.argv.index("--wf") + 1])
        dd = stream(WALK_FORWARD_END, news())
        wf = dd[dd.index >= dev_end]
        print("WF days", len(wf), "median contracts", float(np.median(np.clip(np.floor(R / (wf["dvol_pts"] * 2)), 1, 50))))
        evaluate(wf, {"fixed 8 MNQ": F8, f"risk {R:.0f}": risk(R)}, 5, "WF Nov 2024-Oct 2025", out)
        (ROOT / "reports/iter_22_wf.json").write_text(json.dumps(out, indent=1))
        return
    dd = stream(DEV_END, news())
    tr, te = dd[dd.index < cut], dd[dd.index >= cut]
    grid = {f"risk {R}": risk(float(R)) for R in (1000, 1500, 2000, 3000, 4000)}
    evaluate(tr, {"fixed 8 MNQ": F8, **grid}, 3, "train to 2020", out)
    best = max(grid, key=lambda k: out[f"train to 2020|{k}"]["gain"])
    print("chosen on train:", best)
    out["chosen"] = best
    evaluate(te, {"fixed 8 MNQ": F8, best: grid[best]}, 4, "test 2021-Oct 2024", out)
    print("median contracts in test:", float(np.median(np.clip(np.floor(float(best.split()[1]) / (te["dvol_pts"] * 2)), 1, 50))))
    (ROOT / "reports/iter_22.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
