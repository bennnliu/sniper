"""Iteration 11, part 4: one check of the iteration-11 choices on the walk-forward year (Nov 2024 - Oct 2025).

The holdout year is NOT loaded here. Committed before running. Fixed in advance:
  - rule: frozen NOISE-01B, New York session, NQ signal, MNQ costs for the Topstep scoring
  - news filter: skip CPI, payrolls and FOMC days (Ben's constraint 4)
  - ML filter: logistic model of iteration 11 trained on ALL development trades; keep a trade when its score is
    above the 30th percentile of the development scores
  - sizes: 8 and 10 MNQ on the $50K account (the sizes that pass within 30 days on development data)
The ML filter is adopted only if, in this year, kept trades have a higher mean result (daily-move units) than
skipped trades AND the kept total is at least the unfiltered total. Otherwise it stays unadopted.
Run: python research/iter11_wf_check.py [--log]
"""
import csv
import json
import subprocess
import sys
import warnings
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.iter11_ml import FEATS, KEEP_Q, MNQ_EXTRA_COST, tstat  # noqa: E402
from sniper.data import DEV_END, WALK_FORWARD_END, load_bars  # noqa: E402
from sniper.propscore import score_stream  # noqa: E402
from sniper.session_rule import build_session, run_session  # noqa: E402


def main():
    df = load_bars("NQ", end=str(WALK_FORWARD_END.date()))
    bad = set(json.loads((ROOT / "data/degraded_days.json").read_text()))
    df = df[~df["trading_day"].astype(str).isin(bad)]
    news = set(pd.read_csv(ROOT / "calendar_data" / "events.csv", parse_dates=["date"])["date"])
    tr, dd = run_session(build_session(df, "NY"), 3.78 / 20 + 0.5)
    tr = tr[tr["dvol_pts"].notna()].copy()
    tr["news_day"] = tr["day"].isin(news).astype(int)
    tr["y"] = tr["net_pts"] / tr["dvol_pts"]
    dev_end = DEV_END.tz_localize(None)
    dev, wf = tr[tr["day"] < dev_end], tr[tr["day"] >= dev_end].copy()
    med = dev[FEATS].median()
    m = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=500)).fit(dev[FEATS].fillna(med), (dev["y"] > 0).astype(int))
    thr = np.quantile(m.predict_proba(dev[FEATS].fillna(med))[:, 1], KEEP_Q)
    wf["score"] = m.predict_proba(wf[FEATS].fillna(med))[:, 1]
    wf["keep"] = wf["score"] > thr
    days = dd.index[dd.index >= dev_end]
    out = {"wf_trades": int(len(wf)), "wf_days": int(len(days)), "groups": {}, "prop": {}}

    def grp(g):
        return {"n": int(len(g)), "usd_per_trade": float((g["net_pts"] * 20).mean()), "mean_vol_units": float(g["y"].mean()),
                "t": tstat(g["y"]), "hit": float((g["y"] > 0).mean()), "sum_vol_units": float(g["y"].sum())}

    nn = wf[wf["news_day"] == 0]
    out["groups"] = {"all": grp(wf), "news_days": grp(wf[wf["news_day"] == 1]), "non_news": grp(nn),
                     "kept": grp(wf[wf["keep"]]), "skipped": grp(wf[~wf["keep"]]),
                     "non_news_kept": grp(nn[nn["keep"]]), "non_news_skipped": grp(nn[~nn["keep"]])}
    out["ml_adopted"] = bool(out["groups"]["kept"]["mean_vol_units"] > out["groups"]["skipped"]["mean_vol_units"]
                             and out["groups"]["kept"]["sum_vol_units"] >= out["groups"]["all"]["sum_vol_units"])
    for label, sel in (("base", wf), ("skip_news", nn), ("skip_news_ml", nn[nn["keep"]])):
        g = sel.assign(net=sel["net_pts"] - MNQ_EXTRA_COST)
        pnl = g.groupby("day")["net"].sum().reindex(days, fill_value=0) * 2
        mae = np.minimum((g.groupby("day")["mae_pts"].min().reindex(days, fill_value=0) - 2 * MNQ_EXTRA_COST) * 2, pnl.clip(upper=0))
        traded = g.groupby("day").size().reindex(days, fill_value=0).to_numpy() > 0
        for k in (8, 10):
            s = score_stream(pnl.to_numpy() * k, mae.to_numpy() * k, traded, "50K")
            out["prop"][f"{label}|{k}"] = {x: s[x] for x in ("pass", "pass_lo", "pass_hi", "days_to_pass", "accounts_needed", "payout", "score", "ev_per_attempt", "within_30_days")}
    print(json.dumps(out, indent=1, default=float))
    (ROOT / "reports" / "iter_11_wf_check.json").write_text(json.dumps(out, indent=1, default=float))
    if "--log" in sys.argv:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
        rows = list(csv.DictReader((ROOT / "experiments.csv").open()))
        total = int(rows[-1]["trials_total"]) + 1
        g = out["groups"]
        with (ROOT / "experiments.csv").open("a", newline="") as fh:
            csv.writer(fh).writerow(["it11-WF-check-news-ml", date.today().isoformat(), commit, "iter11", 1, total,
                                     f"WF year: kept ${g['kept']['usd_per_trade']:.0f} vs skipped ${g['skipped']['usd_per_trade']:.0f} per trade; ML adopted: {out['ml_adopted']}"])
        print("trials total", total)


if __name__ == "__main__":
    main()
