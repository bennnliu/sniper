"""Iteration 4 (bars, no spend): IMOM-06 (30-minute opening-range breakout) and
TREND-03 (prior session return -> today's day-session return). Development only.
Run: python research/iter04_bars.py [--log]"""
import csv
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "research"))
import iter01_stage1 as it  # noqa: E402
from sniper.data import DEV_END, load_bars, pivot_times  # noqa: E402
from sniper.signal import passes_stage1, signal_test  # noqa: E402

COST_PTS = {"ES": 1.30 * 0.25, "NQ": 2.76 * 0.25}


def orb(df, t):
    d = df[df["rth"] & df["trading_day"].isin(t.index)]
    rng = d[d["minute_ct"] < 540].groupby("trading_day").agg(h=("high", "max"), l=("low", "min"))
    after = d[(d["minute_ct"] >= 540) & (d["minute_ct"] < 840)].join(rng, on="trading_day")
    up = after[after["close"] > after["h"]].groupby("trading_day").head(1)
    dn = after[after["close"] < after["l"]].groupby("trading_day").head(1)
    ev = pd.concat([up.assign(sig=1.0), dn.assign(sig=-1.0)]).sort_index().groupby("trading_day").head(1)
    close15 = pivot_times(df, [900])[900]
    ev = ev.join(close15.rename("c15"), on="trading_day")
    ev = ev[ev["instrument_id"].notna()]
    ev["y"] = np.log(ev["c15"] / ev["close"])
    ev["pts"] = ev["sig"] * (ev["c15"] - ev["close"])
    return ev.set_index("trading_day")


def main():
    res = []
    for sym in ("ES", "NQ"):
        df = load_bars(sym, end=str(DEV_END.date()))
        t = it.daily_table(df)
        t = t[t.index < DEV_END.tz_localize(None)]
        yr = lambda idx: {"year": pd.Series(pd.DatetimeIndex(idx).year, index=idx)}
        ev = orb(df, t).dropna(subset=["y"])
        rep = signal_test(ev["sig"], ev[["y"]], horizon_bars={"y": 1}, slices=yr(ev.index), name=f"IMOM-06:{sym}")
        ok, why = passes_stage1(rep, +1)
        p = ev["pts"]
        res.append(("IMOM-06", sym, rep.horizons["y"], ok, p))
        # TREND-03: prior 15:00->15:00 return predicts today's 8:30->15:00 return
        p2 = pivot_times(df, [510, 900]).reindex(t.index)
        y = np.log(p2[900] / p2[510])
        x = (t["r_rod"] + t["y_last30"]).shift(1)  # prior day's close-to-close (prev 15:00 -> 15:00)
        x = x.where(t["r_rod"].shift(1).notna())
        dd = pd.DataFrame({"x": x, "y": y}).dropna()
        rep2 = signal_test(dd["x"], dd[["y"]], horizon_bars={"y": 1}, slices=yr(dd.index), name=f"TREND-03:{sym}")
        ok2, _ = passes_stage1(rep2, +1)
        pts2 = np.sign(dd["x"]) * (p2[900] - p2[510]).reindex(dd.index)
        res.append(("TREND-03", sym, rep2.horizons["y"], ok2, pts2))
    out = []
    for fid, sym, h, ok, pts in res:
        tt = pts.mean() / pts.std() * np.sqrt(len(pts))
        row = {"feature": fid, "symbol": sym, "ic": h.ic, "t": h.t, "n": h.n, "stage1": ok,
               "mean_pts": pts.mean(), "x_cost": pts.mean() / COST_PTS[sym], "t_dollar": tt, "hit": float((pts > 0).mean())}
        out.append(row)
        print(f"{fid:8s} {sym} n={h.n} IC={h.ic:+.4f} t={h.t:+.2f} stage1={'PASS' if ok else 'fail'} | "
              f"mean {pts.mean():.2f} pts = {row['x_cost']:.2f}x cost, t$ {tt:.2f}, hit {row['hit']:.1%}")
    if "--log" in sys.argv:
        (ROOT / "reports" / "iter_04_bars.json").write_text(json.dumps(out, indent=1, default=float))
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
        rows = list(csv.DictReader((ROOT / "experiments.csv").open()))
        total = int(rows[-1]["trials_total"])
        with (ROOT / "experiments.csv").open("a", newline="") as fh:
            w = csv.writer(fh)
            for r in out:
                total += 1
                w.writerow([f"it04-{r['feature']}-{r['symbol']}", date.today().isoformat(), commit, "iter04", 1, total,
                            f"IC {r['ic']:+.4f} t {r['t']:+.2f} -> {'PASS' if r['stage1'] else 'FAIL'}; "
                            f"{r['x_cost']:.2f}x cost, t$ {r['t_dollar']:.2f}"])
        print("trials total", total)


if __name__ == "__main__":
    main()
