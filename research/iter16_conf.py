"""Iteration 16: CONF-01, NQ breakouts confirmed by ES. Hypothesis in reports/SECOND_EDGE_LOG.md.
Run: python research/iter16_conf.py [--wf]"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.iter12_second_edge import news, tstat  # noqa: E402
from research.iter13_tests import bars  # noqa: E402
from research.iter15_regime_start import sim_paths  # noqa: E402
from sniper.data import DEV_END, WALK_FORWARD_END  # noqa: E402
from sniper.montecarlo import block_bootstrap  # noqa: E402
from sniper.rules import load_rules  # noqa: E402
from sniper.session_rule import build_session, run_session  # noqa: E402


def es_score(end):
    sd = build_session(bars("ES", end), "NY")
    checks = np.arange(30, sd.n, 30)
    mv = sd.px[:, checks] / sd.px[:, :1] - 1
    sig = pd.DataFrame(np.abs(mv)).rolling(14, min_periods=14).mean().shift(1).to_numpy()
    return pd.DataFrame(mv / sig, index=sd.days, columns=checks)


def main():
    wf = "--wf" in sys.argv
    end = WALK_FORWARD_END if wf else DEV_END
    dev_end = DEV_END.tz_localize(None)
    skip = news()
    tr, dd = run_session(build_session(bars("NQ", end), "NY"), 1.11, skip_days=skip)
    tr = tr[tr["dvol_pts"].notna() & (tr["dvol_pts"] > 0)].copy()
    sc = es_score(end)
    tr["es"] = [sc.at[d, c] * s if (d in sc.index and c in sc.columns) else np.nan for d, c, s in zip(tr["day"], tr["check_min"], tr["dir"])]
    tr = tr[tr["es"].notna()]
    tr = tr[(tr["day"] >= dev_end) if wf else (tr["day"] < dev_end)]
    tr["y"] = tr["net_pts"] / tr["dvol_pts"]
    conf = tr["es"] >= 1
    def g(x):
        return {"n": int(len(x)), "mean_vu": float(x["y"].mean()), "t": tstat(x["y"]), "usd_per_mnq": float(x["net_pts"].mean() * 2), "sum_vu": float(x["y"].sum())}
    a, b = tr[conf], tr[~conf]
    se = np.sqrt(a["y"].var() / len(a) + b["y"].var() / max(len(b), 1))
    out = {"data": "WF" if wf else "DEV", "confirmed": g(a), "unconfirmed": g(b), "all": g(tr), "t_diff": float((a["y"].mean() - b["y"].mean()) / se),
           "ic_es_score": float(tr[["es", "y"]].corr(method="spearman").iloc[0, 1])}
    for lab, m in (("to_2017", tr["day"] < "2018-01-01"), ("2018_on", tr["day"] >= "2018-01-01")):
        out[f"diff_{lab}"] = float(tr[m & conf]["y"].mean() - tr[m & ~conf]["y"].mean()) if (m & ~conf).sum() > 5 and (m & conf).sum() > 5 else None
    for q in (0.5, 0.75, 1.0, 1.25, 1.5):
        out[f"share_below_{q}"] = float((tr["es"] < q).mean())
    print(json.dumps(out, indent=1))
    if not wf:
        # daily streams: all trades vs confirmed only (dropping trades; MAE approximated by the sum of trade MAEs, conservative)
        dd = dd[(dd.index < dev_end) & dd["dvol_pts"].notna() & (dd["dvol_pts"] > 0)]
        def daily(t):
            x = t.groupby("day").agg(net_pts=("net_pts", "sum"), mae_pts=("mae_pts", "min"), mfe_pts=("mfe_pts", "max"), round_trips=("net_pts", "size"))
            return x.reindex(dd.index).fillna(0.0).assign(dvol_pts=dd["dvol_pts"])
        rules = load_rules()
        idx = block_bootstrap(len(dd), 20000, 30, 5, np.random.default_rng(1))
        pol = lambda c, need, left, dv: np.full_like(c, 8.0)
        for lab, t in (("all trades", tr), ("confirmed only", a)):
            s = daily(t)
            vu = (s["net_pts"] / s["dvol_pts"])[s["round_trips"] > 0]
            p = sim_paths(s, pol, idx, rules).mean()
            out[f"daily_{lab}"] = {"traded_days": int(len(vu)), "t_vu": tstat(vu), "usd_per_day_mnq": float(s["net_pts"][s["round_trips"] > 0].mean() * 2), "pass30_8mnq": float(p)}
            print(lab, out[f"daily_{lab}"])
    (ROOT / f"reports/iter_16{'_wf' if wf else ''}.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
