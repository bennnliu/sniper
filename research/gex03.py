"""Iteration 36: GEX-03 tests G1-G3. Pre-registered in reports/NEW_STRATEGY_LOG.md. Needs data/cache/gex_daily.csv."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.iv01 import pct_rank, reg  # noqa: E402
from research.xm_common import DEV_END, DEV_START, bars, cost_pts, news  # noqa: E402
from sniper.session_rule import build_session, run_session  # noqa: E402


def main():
    gex = pd.read_csv(ROOT / "data/cache/gex_daily.csv", index_col=0, parse_dates=True)
    sig = pct_rank(gex["ratio"]).dropna()
    skip = news(); rows = []
    for sym in ["ES", "NQ"]:
        sd = build_session(bars(sym, end=DEV_END, start="2017-06-01"), "NY")
        c = cost_pts(sym)
        _, bo = run_session(sd, c, skip_days=skip)
        _, g0 = run_session(sd, 0.0, skip_days=skip)
        rng = pd.Series(sd.px.max(axis=1) - sd.px.min(axis=1), index=sd.days)
        bo = bo[(bo.index >= DEV_START) & np.isfinite(bo["dvol_pts"]) & (bo["dvol_pts"] > 0)]
        pos = sig.index.searchsorted(bo.index, side="left") - 1  # last gamma day strictly before the session
        x = np.where(pos >= 0, sig.to_numpy()[np.maximum(pos, 0)], np.nan)
        stale = (bo.index - sig.index[np.maximum(pos, 0)]).days > 5
        x[stale] = np.nan
        dv = bo["dvol_pts"]
        fade = (-g0["net_pts"].reindex(bo.index) - (g0["net_pts"].reindex(bo.index) - bo["net_pts"])) / dv  # opposite side, costs paid
        for name, y in [("G1 range", (rng.reindex(bo.index) / dv)), ("G2 breakout", bo["net_pts"] / dv), ("G3 fade", fade)]:
            r = reg(y.to_numpy(), x, bo.index); r.update(test=name, market=sym); rows.append(r)
    out = pd.DataFrame(rows)[["test", "market", "n", "slope", "t", "years_same_sign", "mean_all", "mean_top", "t_top", "mean_bottom", "t_bottom"]]
    out.to_csv(ROOT / "reports/gex03/results.csv", index=False)
    pd.set_option("display.width", 220); print(out.round(3).to_string())


if __name__ == "__main__":
    main()
