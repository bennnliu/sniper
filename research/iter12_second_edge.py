"""Iteration 12: search for a second edge unrelated to the New York breakout. Development period only.

All tests hold for hours, so costs are small against the move. Every test is run per session, on ES and NQ,
in micro-contract costs (MES 0.495 pts, MNQ 1.11 pts per round trip, assumed), with CPI / payrolls / FOMC days
skipped (Ben's constraint 4). A news day is the trading day of the release, so the night before is skipped too.

ON-01   long through ASIA (18:00-01:00 CT), LONDON (02:00-08:30), whole OVERNIGHT (18:00-08:30), and NY (08:30-15:00)
ON-02   overnight position = minus the sign of the previous NY session's return; and long-only after a down NY session
ON-03   NY position = minus the sign of the overnight move (prior 15:00 close -> 08:30)
CAL-03  long on turn-of-month days (last trading day and first three), NY session and OVERNIGHT
FADE-01 fade the London noise-area breakout entries
Run: python research/iter12_second_edge.py [--log]
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
from sniper.data import DEV_END, load_bars  # noqa: E402
from sniper.session_rule import build_session, hold, run_session  # noqa: E402

MICRO = {"ES": ("MES", 5.0, 0.495), "NQ": ("MNQ", 2.0, 1.11)}


def tstat(x):
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std() * np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else float("nan")


def news():
    return set(pd.read_csv(ROOT / "calendar_data" / "events.csv", parse_dates=["date"])["date"])


def stats(dd, sym, label):
    name, pv, cost = MICRO[sym]
    d = dd[(dd["round_trips"] > 0) & dd["dvol_pts"].notna() & (dd["dvol_pts"] > 0)]
    vu = d["net_pts"] / d["dvol_pts"]
    yr = vu.groupby(d.index.year).mean()
    terc = pd.qcut(d["dvol_pts"] / d["dvol_pts"].rolling(250, min_periods=60).median(), 3, labels=["low", "mid", "high"])
    return {"test": label, "symbol": name, "n": int(len(d)), "mean_pts": float(d["net_pts"].mean()),
            "gross_x_cost": float((d["net_pts"].mean() + cost) / cost), "usd_per_micro": float(d["net_pts"].mean() * pv),
            "mean_vu": float(vu.mean()), "t": tstat(vu), "t_usd": tstat(d["net_pts"]), "hit": float((d["net_pts"] > 0).mean()),
            "years_pos": float((yr > 0).mean()), "t_to_2017": tstat(vu[d.index < "2018-01-01"]), "t_2018_on": tstat(vu[d.index >= "2018-01-01"]),
            "t_by_vol": {k: round(tstat(vu[terc == k]), 2) for k in ("low", "mid", "high")},
            "passes": bool(tstat(vu) >= 3 and (yr > 0).mean() >= 0.7 and (d["net_pts"].mean() + cost) >= 2 * cost)}


def main():
    skip = news()
    results, streams = [], {}
    for sym in ("ES", "NQ"):
        name, pv, cost = MICRO[sym]
        df = load_bars(sym, end=str(DEV_END.date()))
        bad = set(json.loads((ROOT / "data/degraded_days.json").read_text()))
        df = df[~df["trading_day"].astype(str).isin(bad)]
        sds = {w: build_session(df, w) for w in ("ASIA", "LONDON", "OVERNIGHT", "NY")}
        ny = sds["NY"]
        ny_ret = pd.Series(ny.px[:, -1] / ny.px[:, 0] - 1, index=ny.days)
        prev_ny = ny_ret.shift(1)
        on_move = pd.Series(ny.px[:, 0] / ny.prev_close - 1, index=ny.days)
        days = ny.days
        month = pd.Series(days.month, index=days)
        last = month != month.shift(-1)
        first3 = pd.Series(days, index=days).groupby([days.year, days.month]).cumcount() < 3
        tom = (last | first3)

        def add(label, dd):
            r = stats(dd, sym, label)
            results.append(r)
            streams[f"{label}|{name}"] = dd
            print(f"{label:34s} {name}: n {r['n']:4d} mean {r['mean_pts']:+7.2f} pts (gross {r['gross_x_cost']:5.1f}x cost) ${r['usd_per_micro']:+6.2f}/micro "
                  f"t {r['t']:+5.2f} hit {r['hit']:.2f} yrs+ {r['years_pos']:.2f} | to2017 {r['t_to_2017']:+.2f} 2018on {r['t_2018_on']:+.2f} | vol {r['t_by_vol']} {'PASS' if r['passes'] else ''}")

        for w in ("ASIA", "LONDON", "OVERNIGHT", "NY"):
            add(f"ON-01 long {w}", hold(sds[w], 1.0, cost, skip))
        on = sds["OVERNIGHT"]
        add("ON-02 fade prior NY overnight", hold(on, -np.sign(prev_ny.reindex(on.days)), cost, skip))
        add("ON-02 long after down NY", hold(on, (prev_ny.reindex(on.days) < 0).astype(float), cost, skip))
        add("ON-02 long after up NY (control)", hold(on, (prev_ny.reindex(on.days) > 0).astype(float), cost, skip))
        add("ON-03 NY fades overnight move", hold(ny, -np.sign(on_move), cost, skip))
        add("CAL-03 turn of month, NY", hold(ny, tom.astype(float), cost, skip))
        add("CAL-03 turn of month, OVERNIGHT", hold(on, tom.reindex(on.days).fillna(False).astype(bool).astype(float), cost, skip))
        add("CAL-03 other days, OVERNIGHT (control)", hold(on, (~tom.reindex(on.days).fillna(True).astype(bool)).astype(float), cost, skip))
        tr, dd = run_session(sds["LONDON"], cost, skip_days=skip)
        fade = dd.copy()
        g = tr.assign(f=-tr["gross_pts"] - cost).groupby("day")
        fade["net_pts"] = g["f"].sum().reindex(fade.index, fill_value=0.0)
        fade["mae_pts"] = np.minimum((-(g["mfe_pts"].max()) - cost).reindex(fade.index, fill_value=0.0), fade["net_pts"].clip(upper=0))
        add("FADE-01 London breakout fade", fade)
    (ROOT / "reports" / "iter_12_tests.json").write_text(json.dumps(results, indent=1, default=float))
    pd.to_pickle(streams, ROOT / "data" / "iter12_streams.pkl")
    if "--log" in sys.argv:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
        rows = list(csv.DictReader((ROOT / "experiments.csv").open()))
        total = int(rows[-1]["trials_total"])
        with (ROOT / "experiments.csv").open("a", newline="") as fh:
            w = csv.writer(fh)
            for r in results:
                total += 1
                w.writerow([f"it12-{r['test'].replace(' ', '_')}-{r['symbol']}", date.today().isoformat(), commit, "iter12", 1, total,
                            f"mean {r['mean_pts']:+.2f} pts, t(vu) {r['t']:+.2f}, n {r['n']}, years+ {r['years_pos']:.0%} -> {'PASS' if r['passes'] else 'FAIL'}"])
        print("trials total", total)


if __name__ == "__main__":
    main()
