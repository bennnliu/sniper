"""Iteration 2: robustness of IMOM-04 (late-day momentum on high-volatility days).
Development period only. Run: python research/iter02_robust.py"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "research"))
import iter01_stage1 as it  # noqa: E402
from sniper.data import DEV_END, load_bars, pivot_times  # noqa: E402

PV = {"NQ": 20.0, "ES": 50.0}


def table(sym):
    df = load_bars(sym, end=str(DEV_END.date()))
    t = it.daily_table(df)
    t = t[t.index < DEV_END.tz_localize(None)]
    p = pivot_times(df, [870, 871, 899, 900]).reindex(t.index)
    t["pts"] = np.sign(t.r_rod) * (p[900] - p[870])
    t["pts_delay"] = np.sign(t.r_rod) * (p[899] - p[871])  # enter 14:31, exit 14:59
    t["y_delay"] = np.log(p[899] / p[871])
    return t.dropna(subset=["r_rod", "y_last30", "pts", "rv20"])


def hi_mask(t, q):
    return t["rv20"] > t["rv20"].expanding(60).quantile(q).shift(1)


def stat(t, mask, y="y_last30", pts="pts"):
    h = t[mask]
    ic = stats.spearmanr(h.r_rod, h[y]).statistic
    n = len(h)
    tic = ic * np.sqrt((n - 2) / (1 - ic**2))
    m = h[pts].mean(); tp = m / h[pts].std() * np.sqrt(n)
    return n, ic, tic, m, tp


def main():
    tabs = {s: table(s) for s in ("NQ", "ES")}
    t = tabs["NQ"]
    print("Cut-off sweep (NQ): quantile, n, IC, t(IC), mean pts, t(pts)")
    for q in (0.5, 0.6, 2 / 3, 0.75, 0.8):
        n, ic, tic, m, tp = stat(t, hi_mask(t, q))
        print(f"  q={q:.2f} n={n} IC={ic:+.3f} t={tic:.2f} pts={m:.2f} t_pts={tp:.2f}")
    mask = hi_mask(t, 2 / 3)
    print("Leave-one-year-out (NQ, q=2/3): year dropped -> t(IC), t(pts)")
    for y in sorted(set(t.index.year)):
        keep = t.index.year != y
        n, ic, tic, m, tp = stat(t[keep], mask[keep])
        print(f"  -{y}: t_IC={tic:.2f} t_pts={tp:.2f}")
    n, ic, tic, m, tp = stat(t, mask, y="y_delay", pts="pts_delay")
    print(f"Entry delayed to 14:31, exit 14:59 (NQ): n={n} IC={ic:+.3f} t={tic:.2f} pts={m:.2f} t_pts={tp:.2f}")
    # ES + NQ together: same days' signals, dollar P&L of 1 ES + 1 NQ... use standardized pts
    e = tabs["ES"]; me = hi_mask(e, 2 / 3)
    both = pd.concat([t[mask].assign(usd=t.pts * PV["NQ"]), e[me].assign(usd=e.pts * PV["ES"])])
    daily = both.groupby(level=0)["usd"].sum()
    print(f"ES+NQ, 1 mini each, high-vol days: days={len(daily)} mean ${daily.mean():.0f}/day t={daily.mean()/daily.std()*np.sqrt(len(daily)):.2f}")
    h = t[mask]
    print(f"NQ high-vol 30-min P&L distribution (pts): sd {h.pts.std():.1f}, 5% {h.pts.quantile(.05):.1f}, 95% {h.pts.quantile(.95):.1f}, worst {h.pts.min():.1f}")
    print("Trades per year:", h.groupby(h.index.year).size().to_dict())


if __name__ == "__main__":
    main()
