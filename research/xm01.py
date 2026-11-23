"""XM-01 (iteration 32): the frozen NQ noise-area breakout on nine other markets, New York hours.
Hypothesis, rule, costs and pass rule are in reports/NEW_STRATEGY_LOG.md, committed before this file was run.
Run: python research/xm01.py  -> reports/xm01/*.csv, data/cache/xm01_days.pkl
Only development days (2018-01-01 to 2024-10-31) are reported; the walk-forward year is computed only if the
four pre-written development criteria pass.
"""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.xm_common import DEV_END, DEV_START, SPEC, XM, bars, cost_pts, news, sharpe, tstat  # noqa: E402
from sniper.session_rule import build_session, run_session  # noqa: E402

OUT = ROOT / "reports" / "xm01"


def market_days(sym, skip):
    sd = build_session(bars(sym), "NY")
    out = {}
    for mult in (1, 2):
        _, dd = run_session(sd, cost_pts(sym, mult), skip_days=skip)
        out[mult] = dd
    d = out[1].copy()
    d["net2_pts"] = out[2]["net_pts"]
    d["r"] = d["net_pts"] / d["dvol_pts"]
    d["r2"] = d["net2_pts"] / d["dvol_pts"]
    d["usd"] = d["net_pts"] * SPEC[sym][1]
    return d


def summarize(r, r2, days):
    yrs = pd.Series(r, index=days).groupby(days.year).sum()
    return {"days": int(np.isfinite(r).sum()), "mean_r": float(np.nanmean(r)), "t": tstat(r), "sharpe": sharpe(r),
            "t_2x": tstat(r2), "mean_r_2x": float(np.nanmean(r2)), "years_pos": int((yrs > 0).sum()), "years": int(len(yrs))}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    skip = news()
    cache = ROOT / "data/cache/xm01_days.pkl"
    D = pickle.load(open(cache, "rb")) if cache.exists() else {}
    for s in XM:
        if s not in D:
            D[s] = market_days(s, skip); print(s, "done", flush=True)
            pickle.dump(D, open(cache, "wb"))
    rows = []
    R, R2 = {}, {}
    for s in XM:
        d = D[s]
        d = d[(d.index >= DEV_START) & (d.index < DEV_END) & np.isfinite(d["r"])]
        R[s], R2[s] = d["r"], d["r2"]
        st = summarize(d["r"].to_numpy(), d["r2"].to_numpy(), d.index)
        st.update(market=s, contract=SPEC[s][0], cost_pts=cost_pts(s), traded_share=float((d["round_trips"] > 0).mean()),
                  usd_per_day_1c=float(d["usd"].mean()), dvol_usd_1c=float((d["dvol_pts"] * SPEC[s][1]).mean()))
        rows.append(st)
    R, R2 = pd.DataFrame(R), pd.DataFrame(R2)
    port, port2 = R.mean(axis=1, skipna=True), R2.mean(axis=1, skipna=True)
    p = summarize(port.to_numpy(), port2.to_numpy(), port.index); p.update(market="PORTFOLIO", contract="equal risk")
    rows.append(p)
    tab = pd.DataFrame(rows).set_index("market")
    tab.to_csv(OUT / "markets.csv")
    R.corr().round(3).to_csv(OUT / "corr.csv")
    yr = R.groupby(R.index.year).sum().assign(PORTFOLIO=port.groupby(port.index.year).sum())
    yr.round(3).to_csv(OUT / "yearly.csv")
    pd.set_option("display.width", 220)
    print(tab.round(3)); print(R.corr().round(2)); print(yr.round(2))
    crit = {"1 portfolio t>=3": p["t"] >= 3, "2 double cost t>=2": p["t_2x"] >= 2 and p["mean_r_2x"] > 0,
            "3 >=5 of 7 years positive": p["years_pos"] >= 5, "4 >=6 of 9 markets positive": int((tab.loc[XM, "mean_r"] > 0).sum()) >= 6}
    print(crit)
    pd.Series(crit).to_csv(OUT / "criteria.csv")


if __name__ == "__main__":
    main()
