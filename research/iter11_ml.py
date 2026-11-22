"""Iteration 11, part 3: META-01, a machine-learning filter on the breakout trades (meta-labelling).

Trades: NQ New York session, frozen rule, development period. Features are the entry-time columns of the trade
log. Validation is walk-forward by calendar year: the model for year Y is trained only on trades from years
before Y (at least 5 years), so every prediction is out of sample. Trades are intraday and flat by 15:00 CT, so
labels never overlap across the year boundary and no further purging is needed.

Two models: logistic regression (win / loss) and a small gradient-boosted regressor (result in daily-move
units, clipped at the 1st/99th percentile of the training years). A trade is kept when its score is above the
30th percentile of the training-year scores (skip the worst-looking 30%).
Run: python research/iter11_ml.py [--log]
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
from scipy import stats
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from sniper.propscore import score_stream  # noqa: E402

FEATS = ["f_sigma_pct", "f_excess", "f_dist_vwap", "f_move_open", "f_efficiency", "f_relvol", "f_rv20", "f_gap",
         "f_prior_pnl", "f_last30", "f_dow", "check_min", "entry_no", "dir", "news_day"]
KEEP_Q = 0.30
MNQ_EXTRA_COST = 1.11 - (3.78 / 20 + 0.5)  # MNQ round trip costs 1.11 pts; the NQ log was built with 0.689


def tstat(x):
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std() * np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else float("nan")


def main():
    tr = pd.read_csv(ROOT / "reports" / "trades_noise_NQ_NY_dev.csv", parse_dates=["day"])
    tr = tr[tr["dvol_pts"].notna()].reset_index(drop=True)
    tr["news_day"] = tr["news_day"].astype(int)
    tr["y"] = tr["net_pts"] / tr["dvol_pts"]
    tr["year"] = tr["day"].dt.year
    X = tr[FEATS].fillna(tr[FEATS].median())
    models = {"logistic": lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=500)),
              "boosted": lambda: HistGradientBoostingRegressor(max_depth=3, max_iter=150, learning_rate=0.03, min_samples_leaf=40, random_state=0)}
    out = {}
    years = [y for y in sorted(tr["year"].unique()) if (tr["year"] < y).sum() > 0 and y - tr["year"].min() >= 5]
    for name, make in models.items():
        score = pd.Series(np.nan, index=tr.index)
        keep = pd.Series(False, index=tr.index)
        imp = []
        for y in years:
            tr_i, te_i = tr.index[tr["year"] < y], tr.index[tr["year"] == y]
            m = make()
            if name == "logistic":
                m.fit(X.loc[tr_i], (tr.loc[tr_i, "y"] > 0).astype(int))
                s_tr, s_te = m.predict_proba(X.loc[tr_i])[:, 1], m.predict_proba(X.loc[te_i])[:, 1]
            else:
                lo, hi = tr.loc[tr_i, "y"].quantile([0.01, 0.99])
                m.fit(X.loc[tr_i], tr.loc[tr_i, "y"].clip(lo, hi))
                s_tr, s_te = m.predict(X.loc[tr_i]), m.predict(X.loc[te_i])
                if y == years[-1]:
                    pi = permutation_importance(m, X.loc[tr_i], tr.loc[tr_i, "y"].clip(lo, hi), n_repeats=5, random_state=0)
                    imp = sorted(zip(FEATS, pi.importances_mean.round(4)), key=lambda kv: -kv[1])[:8]
            score.loc[te_i] = s_te
            keep.loc[te_i] = s_te > np.quantile(s_tr, KEEP_Q)
        t = tr[score.notna()].assign(score=score, keep=keep)
        ic, _ = stats.spearmanr(t["score"], t["y"])
        n = len(t)
        ic_t = ic * np.sqrt((n - 2) / (1 - ic ** 2))
        yr_ic = [stats.spearmanr(g["score"], g["y"])[0] for _, g in t.groupby("year")]
        all_d, kept_d = t.groupby("day")["y"].sum(), t[t["keep"]].groupby("day")["y"].sum().reindex(t["day"].unique(), fill_value=0)
        diff = kept_d - all_d.reindex(kept_d.index)
        usd_all, usd_kept, usd_skip = t["net_pts"] * 20, t.loc[t["keep"], "net_pts"] * 20, t.loc[~t["keep"], "net_pts"] * 20
        res = {"oos_years": [int(years[0]), int(years[-1])], "oos_trades": int(n), "ic": float(ic), "ic_t": float(ic_t),
               "years_ic_pos": float(np.mean(np.array(yr_ic) > 0)), "kept_share": float(t["keep"].mean()),
               "usd_all": float(usd_all.mean()), "usd_kept": float(usd_kept.mean()), "usd_skipped": float(usd_skip.mean()),
               "t_skipped_trades": tstat(t.loc[~t["keep"], "y"]), "t_day_all": tstat(all_d), "t_day_kept": tstat(kept_d),
               "t_day_improvement": tstat(diff), "sum_vol_all": float(all_d.sum()), "sum_vol_kept": float(kept_d.sum()),
               "top_features": [(k, float(v)) for k, v in imp]}
        # Topstep score on the same out-of-sample years, MNQ costs, 8 and 10 MNQ
        for label, sel in (("all", t), ("kept", t[t["keep"]])):
            g = sel.assign(net=sel["net_pts"] - MNQ_EXTRA_COST)
            days = pd.Index(t["day"].unique())
            pnl = g.groupby("day")["net"].sum().reindex(days, fill_value=0) * 2
            mae = (g.groupby("day")["mae_pts"].min().reindex(days, fill_value=0) - 2 * MNQ_EXTRA_COST) * 2  # worst single-trade excursion
            mae = np.minimum(mae, pnl.clip(upper=0))
            traded = g.groupby("day").size().reindex(days, fill_value=0).to_numpy() > 0
            for k in (8, 10):
                s = score_stream(pnl.to_numpy() * k, mae.to_numpy() * k, traded, "50K")
                res[f"prop_{label}_{k}"] = {x: s[x] for x in ("pass", "days_to_pass", "score", "ev_per_attempt", "payout")}
        out[name] = res
        print(f"{name}: OOS {years[0]}-{years[-1]} n {n}, IC {ic:+.3f} (t {ic_t:+.2f}), years IC>0 {res['years_ic_pos']:.0%}; $/trade all {res['usd_all']:.0f}, "
              f"kept {res['usd_kept']:.0f}, skipped {res['usd_skipped']:.0f}; day t all {res['t_day_all']:.2f} -> kept {res['t_day_kept']:.2f}; "
              f"improvement t {res['t_day_improvement']:.2f}")
        for k in (8, 10):
            a, b = res[f"prop_all_{k}"], res[f"prop_kept_{k}"]
            print(f"   {k} MNQ: pass {a['pass']:.1%} -> {b['pass']:.1%}, days {a['days_to_pass']:.0f} -> {b['days_to_pass']:.0f}, score x1000 {a['score'] * 1000:.0f} -> {b['score'] * 1000:.0f}, EV ${a['ev_per_attempt']:.0f} -> ${b['ev_per_attempt']:.0f}")
        if imp:
            print("   top features (permutation importance, last fold):", imp)
    (ROOT / "reports" / "iter_11_ml.json").write_text(json.dumps(out, indent=1, default=float))
    if "--log" in sys.argv:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
        rows = list(csv.DictReader((ROOT / "experiments.csv").open()))
        total = int(rows[-1]["trials_total"])
        with (ROOT / "experiments.csv").open("a", newline="") as fh:
            w = csv.writer(fh)
            for name, r in out.items():
                total += 1
                w.writerow([f"it11-META-01-{name}", date.today().isoformat(), commit, "iter11", 1, total,
                            f"OOS IC {r['ic']:+.3f} t {r['ic_t']:+.2f}; kept ${r['usd_kept']:.0f} vs all ${r['usd_all']:.0f} per trade; improvement t {r['t_day_improvement']:.2f}"])
        print("trials total", total)


if __name__ == "__main__":
    main()
