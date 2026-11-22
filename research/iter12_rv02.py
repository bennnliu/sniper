"""Iteration 12: RV-02. NQ's out-performance of ES from 08:30 to 10:30 CT predicts further out-performance from
10:30 to 15:00 CT (+). Traded as long MNQ / short MES in equal dollar amounts (or the reverse); both legs pay costs.
Development period, news days skipped. Run: python research/iter12_rv02.py [--log]"""
import csv
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from sniper.data import DEV_END, load_bars, pivot_times  # noqa: E402


def main():
    bad = set(json.loads((ROOT / "data/degraded_days.json").read_text()))
    news = set(pd.read_csv(ROOT / "calendar_data" / "events.csv", parse_dates=["date"])["date"])
    p = {}
    for sym in ("ES", "NQ"):
        df = load_bars(sym, end=str(DEV_END.date()))
        df = df[~df["trading_day"].astype(str).isin(bad)]
        p[sym] = pivot_times(df, [510, 630, 900]).dropna()
    j = p["ES"].join(p["NQ"], lsuffix="_es", rsuffix="_nq", how="inner")
    j = j[~j.index.isin(news)]
    x = np.log(j["630_nq"] / j["510_nq"]) - np.log(j["630_es"] / j["510_es"])
    y = np.log(j["900_nq"] / j["630_nq"]) - np.log(j["900_es"] / j["630_es"])
    ic, _ = stats.spearmanr(x, y)
    n = len(x)
    t = ic * np.sqrt((n - 2) / (1 - ic ** 2))
    cost = 1.11 / j["630_nq"] + 0.495 / j["630_es"]  # both legs, as a fraction of notional
    pnl = np.sign(x) * y - cost
    yr = pnl.groupby(pnl.index.year).mean()
    ics = [stats.spearmanr(x[x.index.year == k], y[y.index.year == k])[0] for k in sorted(set(x.index.year))]
    res = {"n": int(n), "ic": float(ic), "t": float(t), "years_ic_pos": float(np.mean(np.array(ics) > 0)),
           "gross_bp": float((np.sign(x) * y).mean() * 1e4), "cost_bp": float(cost.mean() * 1e4), "net_bp": float(pnl.mean() * 1e4),
           "t_net": float(pnl.mean() / pnl.std() * np.sqrt(n)), "years_pos": float((yr > 0).mean())}
    print(json.dumps(res, indent=1))
    if "--log" in sys.argv:
        (ROOT / "reports" / "iter_12_rv02.json").write_text(json.dumps(res, indent=1))
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
        rows = list(csv.DictReader((ROOT / "experiments.csv").open()))
        total = int(rows[-1]["trials_total"]) + 1
        with (ROOT / "experiments.csv").open("a", newline="") as fh:
            csv.writer(fh).writerow(["it12-RV-02", date.today().isoformat(), commit, "iter12", 1, total,
                                     f"IC {res['ic']:+.3f} t {res['t']:+.2f}; net {res['net_bp']:+.2f} bp (cost {res['cost_bp']:.2f}), t {res['t_net']:+.2f}"])
        print("trials total", total)


if __name__ == "__main__":
    main()
