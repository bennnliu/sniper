"""Iteration 9: critique tests on NOISE-01B (NQ), development period only. No parameters are changed.

1. Volatility dependence: net result per traded day by tercile of the lagged 20-day daily volatility, in
   dollars and in units of that day's expected daily move (prior close x rv20).
2. Volatility units over time: yearly mean in volatility units (removes the effect of the index level).
3. Measured spread on the trade tape (Aug-Oct 2024) in the 10 seconds after each fill time: difference between
   the average buyer-initiated and seller-initiated trade price. Compared with the assumed 2 ticks of slippage.
Run: python research/iter09_critique.py [--log]
"""
import csv
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from sniper import features as F  # noqa: E402
from sniper.data import DEV_END, load_bars  # noqa: E402
from sniper.noise import run_rule  # noqa: E402

PV, COST = 20.0, 2.76 * 0.25


def t(x):
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std() * np.sqrt(len(x)))


def main():
    df = load_bars("NQ", end=str(DEV_END.date()))
    bad = set(json.loads((ROOT / "data/degraded_days.json").read_text()))
    df = df[~df["trading_day"].astype(str).isin(bad)]
    p = F.day_grid(df)
    r = run_rule(df, p, COST, delay=1)
    r = r.join(p[["rv20", "prev_close"]])
    tr = r[(r["round_trips"] > 0) & r["rv20"].notna()].copy()
    tr["usd"] = tr["net_pts"] * PV
    tr["vol_units"] = tr["net_pts"] / (tr["prev_close"] * tr["rv20"])  # share of one expected daily move
    tr["terc"] = pd.qcut(r["rv20"].dropna(), 3, labels=["low", "mid", "high"]).reindex(tr.index).astype(str)
    out = {"n": int(len(tr)), "vol_units_mean": float(tr["vol_units"].mean()), "vol_units_t": t(tr["vol_units"]),
           "usd_t": t(tr["usd"]), "by_tercile": {}, "by_year_vol_units": {}}
    for k, g in tr.groupby("terc"):
        out["by_tercile"][k] = {"n": int(len(g)), "usd": float(g["usd"].mean()), "t_usd": t(g["usd"]),
                                "vol_units": float(g["vol_units"].mean()), "t_vol_units": t(g["vol_units"])}
    yr = pd.DatetimeIndex(tr.index).year
    for y, g in tr.groupby(yr):
        out["by_year_vol_units"][int(y)] = round(float(g["vol_units"].mean()), 4)
    yv = pd.Series(out["by_year_vol_units"])
    out["years_pos_vol_units"] = float((yv > 0).mean())
    e, l = tr[yr <= 2017]["vol_units"], tr[yr >= 2018]["vol_units"]
    out["early_2010_2017"] = {"mean": float(e.mean()), "t": t(e)}
    out["late_2018_2024"] = {"mean": float(l.mean()), "t": t(l)}
    # 3. measured spread around fill times
    from research.iter05_orderflow import load_trades
    tt = load_trades("NQ")
    front = tt.groupby("instrument_id")["size"].sum().idxmax()
    tt = tt[tt["instrument_id"] == front]
    ts = tt["ts"].to_numpy()
    days = pd.DatetimeIndex(pd.to_datetime(ts, utc=True).tz_convert("America/Chicago").normalize().unique())
    spreads, counts = [], []
    for d in days:
        for chk in F.CHECKS:
            t0 = (d + pd.Timedelta(minutes=chk + 1)).tz_convert("UTC").value
            i, j = np.searchsorted(ts, t0), np.searchsorted(ts, t0 + 10_000_000_000)
            if j - i < 6:
                continue
            w = tt.iloc[i:j]
            b, s = w[w["side"] == b"B"]["price"], w[w["side"] == b"A"]["price"]
            if len(b) >= 3 and len(s) >= 3:
                spreads.append((b.mean() - s.mean()) / 0.25)
                counts.append(j - i)
    sp = pd.Series(spreads)
    out["spread_ticks"] = {"n_windows": int(len(sp)), "median": float(sp.median()), "mean": float(sp.mean()),
                           "p90": float(sp.quantile(0.9)), "median_trades_in_10s": float(np.median(counts))}
    print(json.dumps(out, indent=1))
    if "--log" in sys.argv:
        (ROOT / "reports" / "iter_09_critique.json").write_text(json.dumps(out, indent=1))
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
        rows = list(csv.DictReader((ROOT / "experiments.csv").open()))
        total = int(rows[-1]["trials_total"]) + 1
        with (ROOT / "experiments.csv").open("a", newline="") as fh:
            csv.writer(fh).writerow(["it09-NOISE-01B-NQ-vol-units", date.today().isoformat(), commit, "iter09", 1, total,
                                     "vol-unit t %.2f; early %.2f late %.2f" % (out["vol_units_t"], out["early_2010_2017"]["t"], out["late_2018_2024"]["t"])])
        print("trials total", total)


if __name__ == "__main__":
    main()
