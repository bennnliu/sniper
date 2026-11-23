"""Iteration 33: implied-volatility signals (IV-01..IV-04). Pre-registered in reports/NEW_STRATEGY_LOG.md.
Run: python research/iv01.py -> reports/iv01/results.csv"""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.xm_common import DEV_END, bars, cost_pts, news, tstat  # noqa: E402
from sniper.session_rule import build_session, hold, run_session  # noqa: E402

RAWD = ROOT / "data/raw/yf_iv"
START = pd.Timestamp("2011-06-01")


def vix_data():
    p = RAWD / "iv_daily.csv"
    if not p.exists():
        import yfinance as yf
        d = {t: yf.download("^" + t, start="2009-01-01", end="2025-11-01", progress=False, auto_adjust=False)["Close"].squeeze()
             for t in ["VIX", "VIX3M", "VVIX", "VXN", "VIX9D"]}
        pd.DataFrame(d).to_csv(p)
    return pd.read_csv(p, index_col=0, parse_dates=True)


def pct_rank(s, w=250):
    return s.rolling(w, min_periods=120).apply(lambda x: (x[-1] > x[:-1]).mean(), raw=True)


def reg(y, x, days):
    """OLS slope t of y on x, plus share of years with the same sign as the slope, and tercile spread."""
    m = np.isfinite(y) & np.isfinite(x)
    y, x, days = y[m], x[m], days[m]
    xc = x - x.mean()
    b = (xc * y).sum() / (xc ** 2).sum()
    e = y - y.mean() - b * xc
    se = np.sqrt((xc ** 2 * e ** 2).sum()) / (xc ** 2).sum()  # White
    yrs = []
    for yr in np.unique(days.year):
        k = days.year == yr
        if k.sum() > 60:
            xx = x[k] - x[k].mean(); yrs.append(np.sign((xx * y[k]).sum()))
    hi, lo = y[x >= 2 / 3], y[x <= 1 / 3]
    return {"n": int(m.sum()), "slope": b, "t": b / se, "years_same_sign": float((np.array(yrs) == np.sign(b)).mean()),
            "mean_top": hi.mean(), "mean_bottom": lo.mean(), "t_top": tstat(hi), "t_bottom": tstat(lo), "mean_all": y.mean()}


def main():
    iv = vix_data()
    sig = pd.DataFrame({"slope": pct_rank(iv["VIX"] / iv["VIX3M"]), "vvix": pct_rank(iv["VVIX"])})
    skip = news(); rows = []
    for sym in ["ES", "NQ"]:
        df = bars(sym, end=DEV_END)
        ny = build_session(df, "NY"); asia = build_session(df, "ASIA")
        _, bo = run_session(ny, cost_pts(sym), skip_days=skip)
        bo = bo[(bo.index >= START) & np.isfinite(bo["dvol_pts"])]
        c = cost_pts(sym)
        # daily close series aligned to the VIX calendar for the IV-04 residual
        cl = pd.Series(ny.px[:, -1], index=ny.days)
        ret = np.log(cl / cl.shift(1)); dv = np.log(iv["VIX"]).diff().reindex(ret.index)
        beta = ret.rolling(250, min_periods=120).cov(dv) / ret.rolling(250, min_periods=120).var()
        resid = dv - beta.shift(1) * ret
        resid_rank = pct_rank(resid)

        def prev(s, days):  # value from the last calendar day strictly before the trading day
            s = s.dropna()
            pos = s.index.searchsorted(days, side="left") - 1
            return np.where(pos >= 0, s.to_numpy()[np.maximum(pos, 0)], np.nan)

        y = (bo["net_pts"] / bo["dvol_pts"]).to_numpy()
        for name, col in [("IV-01", "slope"), ("IV-02", "vvix")]:
            r = reg(y, prev(sig[col], bo.index), bo.index); r.update(test=name, market=sym, session="NY breakout", cost_r=float((c / bo["dvol_pts"]).mean())); rows.append(r)
        for name, sd, col_s in [("IV-03", ny, sig["slope"]), ("IV-04", ny, resid_rank), ("IV-04", asia, resid_rank)]:
            h = hold(sd, np.ones(len(sd.days)), c, skip_days=skip)
            h = h[(h.index >= START) & np.isfinite(h["dvol_pts"]) & (h["dvol_pts"] > 0) & (h["pos"] != 0)]
            yy = (h["net_pts"] / h["dvol_pts"]).to_numpy()
            # Asia session of trading day D starts the evening of D-1: the signal must be from D-2's close or earlier
            days_for_signal = h.index - pd.Timedelta(days=1) if sd.name == "ASIA" else h.index
            r = reg(yy, prev(col_s, days_for_signal), h.index); r.update(test=name, market=sym, session=sd.name + " long", cost_r=float((c / h["dvol_pts"]).mean())); rows.append(r)
    out = pd.DataFrame(rows)[["test", "market", "session", "n", "slope", "t", "years_same_sign", "mean_all", "mean_top", "t_top", "mean_bottom", "t_bottom", "cost_r"]]
    out.to_csv(ROOT / "reports/iv01/results.csv", index=False)
    pd.set_option("display.width", 220); print(out.round(3))


if __name__ == "__main__":
    main()
