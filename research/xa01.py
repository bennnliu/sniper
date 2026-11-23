"""Iteration 34: XA-01 cross-asset lead-lag into ES/NQ. Pre-registered in reports/NEW_STRATEGY_LOG.md.
Run: python research/xa01.py -> reports/xa01/results.csv"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.xm_common import DEV_END, DEV_START, bars, cost_pts, news  # noqa: E402
from sniper.session_rule import build_session  # noqa: E402


def px(sym):
    sd = build_session(bars(sym, end=DEV_END, start=DEV_START), "NY")
    return pd.DataFrame(sd.px, index=sd.days)


def main():
    P = {s: px(s) for s in ["ES", "NQ", "ZN", "6J", "CL", "GC"]}
    skip = news(); rows = []
    for tgt in ["ES", "NQ"]:
        for pred in ["ZN", "6J", "CL", "GC"]:
            days = P[tgt].index.intersection(P[pred].index); days = days[~days.isin(list(skip))]
            Y, X = np.log(P[tgt].loc[days].to_numpy()), np.log(P[pred].loc[days].to_numpy())
            lvl = P[tgt].loc[days].to_numpy()
            for k in (1, 5, 15):
                g = np.arange(0, Y.shape[1], k)
                ry, rx = np.diff(Y[:, g], axis=1), np.diff(X[:, g], axis=1)  # days x intervals
                pts = np.diff(lvl[:, g], axis=1)
                # trailing 20-day same-horizon beta of target on predictor, known before the day
                sxy = pd.Series((rx * ry).sum(axis=1)).rolling(20, min_periods=15).sum().shift(1).to_numpy()
                sxx = pd.Series((rx * rx).sum(axis=1)).rolling(20, min_periods=15).sum().shift(1).to_numpy()
                beta = sxy / sxx
                sig = beta[:, None] * rx[:, :-1]; fwd = ry[:, 1:]; fpts = pts[:, 1:]
                ok = np.isfinite(beta)
                ics = np.array([np.corrcoef(rankdata(sig[i]), rankdata(fwd[i]))[0, 1] for i in np.nonzero(ok)[0]])
                d_ok = days[ok]
                yr = pd.Series(ics, index=d_ok).groupby(d_ok.year).mean()
                s, f = sig[ok].ravel(), fpts[ok].ravel()
                lo, hi = np.quantile(s, [0.1, 0.9])
                edge = (f[s >= hi].mean() - f[s <= lo].mean()) / 2  # points per trade, trading both tails
                rows.append({"target": tgt, "predictor": pred, "k_min": k, "days": int(ok.sum()), "ic": float(np.nanmean(ics)),
                             "t": float(np.nanmean(ics) / np.nanstd(ics, ddof=1) * np.sqrt(np.isfinite(ics).sum())),
                             "years_pos": float((yr > 0).mean()), "decile_edge_pts": float(edge), "cost_pts": cost_pts(tgt),
                             "edge_over_cost": float(edge / cost_pts(tgt))})
    out = pd.DataFrame(rows); out.to_csv(ROOT / "reports/xa01/results.csv", index=False)
    pd.set_option("display.width", 220); print(out.round(4).to_string())


if __name__ == "__main__":
    main()
