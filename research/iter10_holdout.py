"""Iteration 10: the ONE-TIME holdout test of NOISE-01B on NQ. Approved by Ben on 22 Nov 2026.

This file was committed before the holdout bars were downloaded. Nothing here may be changed after the run
except to fix a crash, and any such fix must be listed in the report.

Frozen rule (unchanged since iteration 8): noise-area breakout, 14-day lookback, band multiplier 1.0,
band-or-VWAP trailing stop, decisions at the half-hour checks 9:00-14:30 CT, fills 1 minute later,
flat at 15:00 CT. Costs: 2.76 ticks all-in per NQ round trip (METHOD.md), and doubled.

Holdout: trading days from 1 Nov 2025 to 31 Oct 2026. Bars from Aug-Oct 2025 are used only to warm up the
14-day lookback and the prior close.

PASS requires ALL of:
  1. mean net result per traded day > 0 at 1x cost,
  2. mean net result per traded day > 0 at 2x cost,
  3. simulated $50K Combine pass rate at 2 MNQ (the size chosen on the walk-forward year), resampling holdout
     days in 5-day blocks, above 22% (the zero-edge baseline), using the lower end of the simulation's 95% interval.
Anything else is a FAIL and ends the candidate. The t-statistic of one year is reported but is not a condition:
with about 140 traded days it cannot reach 3 for an effect of the size seen so far.

Run: python research/iter10_holdout.py
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
from sniper import ACCOUNT_SIZES, load_rules  # noqa: E402
from sniper import features as F  # noqa: E402
from sniper.data import HOLDOUT_START, load_bars  # noqa: E402
from sniper.montecarlo import DayRecords, block_bootstrap, simulate_combine, simulate_xfa  # noqa: E402
from sniper.noise import run_rule  # noqa: E402

PV, COST, MNQ_PV, SLIP = 20.0, 2.76 * 0.25, 2.0, 0.5
HOLDOUT_FILE = ROOT / "data" / "bars" / "NQ_1m_holdout.parquet"
BASELINE = 0.22


def main():
    warm = load_bars("NQ", start="2025-08-01", end="2025-11-01")
    hold = load_bars("NQ", holdout=True, path=HOLDOUT_FILE)
    df = pd.concat([warm, hold[hold.index >= HOLDOUT_START]]).sort_index()
    df = df[~df.index.duplicated(keep="first")]
    p = F.day_grid(df)
    start = HOLDOUT_START.tz_localize(None)
    res = {"holdout_days": int((p.index >= start).sum())}
    for mult in (1, 2):
        r = run_rule(df, p, COST * mult, delay=1)
        r = r[r.index >= start]
        tr = r[r["round_trips"] > 0]
        usd = tr["net_pts"] * PV
        res[f"cost{mult}x"] = {"days": int(len(r)), "traded": int(len(tr)), "usd_per_traded_day": float(usd.mean()),
                               "t": float(usd.mean() / usd.std() * np.sqrt(len(usd))), "hit": float((usd > 0).mean()),
                               "total_usd": float(usd.sum()), "worst_day_usd": float(usd.min()),
                               "best_day_usd": float(usd.max()),
                               "by_month": {str(k): round(float(v), 0) for k, v in usd.groupby(usd.index.to_period("M")).sum().items()}}
    rules = load_rules()
    fee_rt = rules.commission_per_side["MNQ"] * 2
    s = run_rule(df, p, SLIP, delay=1)
    s = s[s.index >= start]
    traded = (s["round_trips"] > 0).to_numpy()
    extra = np.clip(s["round_trips"].to_numpy() - 1, 0, None) * fee_rt
    rec = DayRecords(traded, s["net_pts"].to_numpy() * MNQ_PV - extra, s["mae_pts"].to_numpy() * MNQ_PV - extra, "MNQ")
    idx = block_bootstrap(len(s), 4000, 500, 5, np.random.default_rng(0))
    res["montecarlo"] = {}
    for size in ACCOUNT_SIZES:
        spec = rules.account(size)
        for n in (2, 3, 5, 10):
            c = simulate_combine(rec, idx, n, size, rules).summary()
            xs = simulate_xfa(rec, idx, n, size, "standard", rules).summary()
            xc = simulate_xfa(rec, idx, n, size, "consistency", rules).summary()
            months = max(1.0, np.ceil(c["median_days_any"] / 21))
            ev = c["pass"] * (max(xs["mean_to_trader"], xc["mean_to_trader"]) - spec.activation_fee_standard) \
                - months * (spec.combine_monthly_standard + rules.api_monthly)
            res["montecarlo"][f"{size}|{n}"] = {"pass": c["pass"], "pass_lo": c["pass_lo"], "pass_hi": c["pass_hi"],
                                                "days": c["median_days_any"], "xfa_p_std": xs["p_payout"],
                                                "xfa_p_cons": xc["p_payout"], "ev": float(ev)}
    key = res["montecarlo"][f"{ACCOUNT_SIZES[0]}|2"]
    conds = {"mean_positive_1x": res["cost1x"]["usd_per_traded_day"] > 0,
             "mean_positive_2x": res["cost2x"]["usd_per_traded_day"] > 0,
             "combine_pass_above_baseline": key["pass_lo"] > BASELINE}
    res["conditions"] = conds
    res["verdict"] = "PASS" if all(conds.values()) else "FAIL"
    print(json.dumps(res, indent=1, default=float))
    (ROOT / "reports" / "iter_10_holdout.json").write_text(json.dumps(res, indent=1, default=float))
    commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    rows = list(csv.DictReader((ROOT / "experiments.csv").open()))
    total = int(rows[-1]["trials_total"]) + 1
    with (ROOT / "experiments.csv").open("a", newline="") as fh:
        csv.writer(fh).writerow(["it10-NOISE-01B-NQ-HOLDOUT", date.today().isoformat(), commit, "iter10", 1, total,
                                 "HOLDOUT %s: $%.0f/traded day, t %.2f, n %d; 50K pass at 2 MNQ %.1f%%" % (
                                     res["verdict"], res["cost1x"]["usd_per_traded_day"], res["cost1x"]["t"],
                                     res["cost1x"]["traded"], 100 * key["pass"])])


if __name__ == "__main__":
    main()
