"""Iteration 1 follow-ups: IMOM-04 (rROD conditional on high volatility) and
stage 2 cost tests for IMOM-04 and IMOM-05. Development period only.

High-volatility days: trailing 20-day close-to-close volatility above its
expanding 2/3 quantile, both computed from data before the day.
Run: python research/iter01_followups.py
"""
import sys
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "research"))
import iter01_stage1 as it  # noqa: E402
from sniper.data import DEV_END, load_bars, pivot_times  # noqa: E402

COST_PTS = {"NQ": {"NQ": 2.76 * 0.25, "MNQ": 4.44 * 0.25}, "ES": {"ES": 1.30 * 0.25, "MES": 1.98 * 0.25}}


def main():
    for sym in ("NQ", "ES"):
        df = load_bars(sym, end=str(DEV_END.date()))
        t = it.daily_table(df)
        t = t[t.index < DEV_END.tz_localize(None)]
        p = pivot_times(df, [515, 870, 900]).reindex(t.index)
        hi = t["rv20"] > t["rv20"].expanding(60).quantile(2 / 3).shift(1)
        d = t.assign(hi=hi, pts=np.sign(t.r_rod) * (p[900] - p[870])).dropna(subset=["r_rod", "y_last30", "pts"])
        h, r = d[d.hi], d[~d.hi]
        i1, i0 = stats.spearmanr(h.r_rod, h.y_last30).statistic, stats.spearmanr(r.r_rod, r.y_last30).statistic
        z = (np.arctanh(i1) - np.arctanh(i0)) / np.sqrt(1 / (len(h) - 3) + 1 / (len(r) - 3))
        print(f"{sym} IMOM-04: IC high-vol {i1:+.3f} (n={len(h)}, t={i1*np.sqrt((len(h)-2)/(1-i1**2)):.2f}) "
              f"vs rest {i0:+.3f}; diff z={z:.2f}")
        yr = h.groupby(h.index.year).apply(lambda x: stats.spearmanr(x.r_rod, x.y_last30).statistic)
        print(f"  years right sign {np.mean(yr > 0):.0%}")
        for name, pts in (("IMOM-04 last 30m, high-vol days", h.pts),
                          ("IMOM-05 8:35-15:00", (np.sign(t.r_first5) * (p[900] - p[515]))[t.r_first5 != 0].dropna())):
            tt = pts.mean() / pts.std() * np.sqrt(len(pts))
            print(f"  {name}: n={len(pts)} mean {pts.mean():.2f} pts hit {np.mean(pts > 0):.1%} t {tt:.2f}")
            for c, cp in COST_PTS[sym].items():
                print(f"    {c}: {pts.mean()/cp:.1f}x cost; net at 2x cost {pts.mean()-2*cp:+.2f} pts")


if __name__ == "__main__":
    main()
