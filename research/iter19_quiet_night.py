"""Iteration 19: VOL-05, skip the breakout rule after a quiet overnight session. Hypothesis in reports/SECOND_EDGE_LOG.md.
Run: python research/iter19_quiet_night.py [--wf]"""
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


def main():
    wf = "--wf" in sys.argv
    df = bars("NQ", WALK_FORWARD_END if wf else DEV_END)
    dev_end = DEV_END.tz_localize(None)
    ny, on = build_session(df, "NY"), build_session(df, "OVERNIGHT")
    _, dd = run_session(ny, 1.11, skip_days=news())
    dd = dd[dd["dvol_pts"].notna() & (dd["dvol_pts"] > 0)]
    onr = pd.Series(on.px.max(axis=1) - on.px.min(axis=1), index=on.days).reindex(dd.index) / dd["dvol_pts"]
    pct = onr.rolling(250, min_periods=120).rank(pct=True)
    dd = dd.assign(pct=pct, quiet=pct <= 1 / 3)
    dd = dd[dd["pct"].notna()]
    dd = dd[dd.index >= dev_end] if wf else dd[dd.index < dev_end]
    t = dd[dd["round_trips"] > 0]
    vu = t["net_pts"] / t["dvol_pts"]
    q = t["quiet"]
    out = {"data": "WF" if wf else "DEV", "days": int(len(dd)), "traded": int(len(t)), "quiet_traded": int(q.sum()),
           "mean_quiet": float(vu[q].mean()), "mean_kept": float(vu[~q].mean()), "t_diff": float((vu[~q].mean() - vu[q].mean()) / np.sqrt(vu[q].var() / q.sum() + vu[~q].var() / (~q).sum())),
           "sum_all_vu": float(vu.sum()), "sum_kept_vu": float(vu[~q].sum()), "usd_all_per_mnq": float(t["net_pts"].sum() * 2), "usd_kept_per_mnq": float(t["net_pts"][~q].sum() * 2),
           "t_all": tstat(vu), "t_kept": tstat(vu[~q]), "rank_ic_pct_vs_result": float(t["pct"].corr(vu, method="spearman"))}
    if not wf:
        for lab, m in (("to_2017", t.index < "2018-01-01"), ("2018_on", t.index >= "2018-01-01")):
            out[f"diff_{lab}"] = float(vu[m & ~q].mean() - vu[m & q].mean())
        out["by_tercile"] = {k: float(v) for k, v in vu.groupby(pd.cut(t["pct"], [0, 1 / 3, 2 / 3, 1], labels=["low", "mid", "high"]), observed=True).mean().items()}
        out["by_year_diff"] = {int(y): float(g[~t.loc[g.index, "quiet"]].mean() - g[t.loc[g.index, "quiet"]].mean()) for y, g in vu.groupby(t.index.year)}
    rules = load_rules()
    rng = np.random.default_rng(1)
    idx = block_bootstrap(len(dd), 20000, 30, 5, rng)
    flip = rng.random(idx.shape) < 0.5
    filt = dd.copy()
    for c in ("net_pts", "mae_pts", "mfe_pts", "round_trips"):
        filt.loc[filt["quiet"], c] = 0.0
    for n in (8, 12):
        pol = lambda c, need, left, dv, n=n: np.full_like(c, float(n))
        for lab, s in (("all days", dd), ("quiet nights skipped", filt)):
            out[f"pass30_{n}mnq_{lab}"] = float(sim_paths(s, pol, idx, rules).mean())
            out[f"control_{n}mnq_{lab}"] = float(sim_paths(s, pol, idx, rules, flip=flip).mean())
    print(json.dumps(out, indent=1))
    (ROOT / f"reports/iter_19{'_wf' if wf else ''}.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
