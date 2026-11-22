"""Iteration 8 follow-up on NOISE-01B (NQ): honest fills, sensitivity, then the walk-forward year once.

Frozen rule: lookback 14 days, band multiplier 1.0, VWAP trailing stop, fills 1 minute after each check,
assumed costs from METHOD.md. Run: python research/iter08_noise_followup.py dev|wf [--log]
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
from sniper.data import DEV_END, WALK_FORWARD_END, load_bars  # noqa: E402
from sniper.noise import run_rule  # noqa: E402

PV = {"ES": 50.0, "NQ": 20.0}
COST = {"ES": 1.30 * 0.25, "NQ": 2.76 * 0.25}


def stats(r, sym):
    tr = r[r["round_trips"] > 0]
    usd = tr["net_pts"] * PV[sym]
    yr = usd.groupby(pd.DatetimeIndex(usd.index).year).mean()
    return {"days": int(len(r)), "traded": int(len(tr)), "usd_per_traded_day": float(usd.mean()),
            "t": float(usd.mean() / usd.std() * np.sqrt(len(usd))), "hit": float((usd > 0).mean()),
            "round_trips": float(tr["round_trips"].mean()), "years_pos": float((yr > 0).mean()),
            "worst_day_usd": float(usd.min()), "median_mae_usd": float((tr["mae_pts"] * PV[sym]).median()),
            "by_year": {int(k): round(float(v), 1) for k, v in yr.items()}}


def bars(sym, end):
    df = load_bars(sym, end=end)
    bad = set(json.loads((ROOT / "data/degraded_days.json").read_text()))
    return df[~df["trading_day"].astype(str).isin(bad)]


def main(mode):
    out = []
    if mode == "dev":
        for sym in ("ES", "NQ"):
            df = bars(sym, str(DEV_END.date()))
            p = F.day_grid(df)
            for name, kw, mult in [("base", {}, 1), ("cost2x", {}, 2), ("lookback11", {"lookback": 11}, 1),
                                   ("lookback17", {"lookback": 17}, 1), ("vm0.8", {"vm": 0.8}, 1), ("vm1.2", {"vm": 1.2}, 1),
                                   ("no_vwap", {"use_vwap": False}, 1)]:
                s = stats(run_rule(df, p, COST[sym] * mult, delay=1, **kw), sym)
                out.append({"run": f"it08-NOISE-01B-{sym}-{name}", "symbol": sym, "variant": name, **s})
    else:
        sym = "NQ"
        df = bars(sym, str(WALK_FORWARD_END.date()))
        p = F.day_grid(df)
        for mult in (1, 2):
            r = run_rule(df, p, COST[sym] * mult, delay=1)
            r = r[r.index >= DEV_END.tz_localize(None)]
            out.append({"run": f"it08-NOISE-01B-NQ-walkforward-cost{mult}x", "symbol": sym, "variant": f"wf cost {mult}x", **stats(r, sym)})
            if mult == 1:
                r.to_csv(ROOT / "reports" / "iter_08_noise_wf_days.csv")
    for o in out:
        print(o["run"], "| $/traded day %.1f, t %.2f, traded %d, hit %.2f, years+ %.2f" % (o["usd_per_traded_day"], o["t"], o["traded"], o["hit"], o["years_pos"]))
    if "--log" in sys.argv:
        (ROOT / "reports" / f"iter_08_noise_{mode}.json").write_text(json.dumps(out, indent=1))
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
        rows = list(csv.DictReader((ROOT / "experiments.csv").open()))
        total = int(rows[-1]["trials_total"])
        with (ROOT / "experiments.csv").open("a", newline="") as fh:
            w = csv.writer(fh)
            for o in out:
                if o["variant"] in ("cost2x", "wf cost 2x"):
                    continue  # same trades at another cost: not a new look
                total += 1
                w.writerow([o["run"], date.today().isoformat(), commit, "iter08", 1, total,
                            "$%.0f/traded day, t %.2f, n %d" % (o["usd_per_traded_day"], o["t"], o["traded"])])
        print("trials total", total)


if __name__ == "__main__":
    main(sys.argv[1])
