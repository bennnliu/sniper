"""Iterations 20-21: ENS-01 (parameter ensemble), ENS-02 (ES+NQ), DP-01 (optimal sizing by dynamic programming).
Hypotheses in reports/SECOND_EDGE_LOG.md. Development data only."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.iter12_second_edge import news, tstat  # noqa: E402
from research.iter13_tests import bars, simulate  # noqa: E402
from sniper.data import DEV_END  # noqa: E402
from sniper.montecarlo import block_bootstrap  # noqa: E402
from sniper.rules import load_rules  # noqa: E402
from sniper.session_rule import build_session, run_session  # noqa: E402


def main():
    skip = news()
    rules = load_rules()
    out = {}
    nq, es = build_session(bars("NQ", DEV_END), "NY"), build_session(bars("ES", DEV_END), "NY")
    base = run_session(nq, 1.11, skip_days=skip)[1]
    base = base[base["dvol_pts"].notna() & (base["dvol_pts"] > 0)]
    runs = [run_session(nq, 1.11, lookback=lb, vm=vm, skip_days=skip)[1].reindex(base.index) for lb in (7, 14, 28) for vm in (0.8, 1.0, 1.2)]
    ens = base.copy()
    for c in ("net_pts", "mae_pts", "mfe_pts", "round_trips"):
        ens[c] = np.mean([r[c].fillna(0).to_numpy() for r in runs], axis=0)
    e = run_session(es, 0.495, skip_days=skip)[1].reindex(base.index)
    both = base.copy()  # per "MNQ-equivalent" of an 8-lot: (4 MNQ + 6 MES) / 8, in MNQ points ($2)
    for c in ("net_pts", "mae_pts", "mfe_pts"):
        both[c] = (4 * 2 * base[c] + 6 * 5 * e[c].fillna(0)) / 16
    both["round_trips"] = (4 * base["round_trips"] + 6 * e["round_trips"].fillna(0)) / 10
    corr = np.corrcoef([r["net_pts"].fillna(0) for r in runs])
    out["ens_mean_pairwise_corr"] = float(corr[np.triu_indices(9, 1)].mean())
    out["es_nq_corr"] = float(base["net_pts"].corr(e["net_pts"].fillna(0)))
    rng = np.random.default_rng(1)
    idx = block_bootstrap(len(base), 20000, 30, 5, rng)
    flip = rng.random(idx.shape) < 0.5
    f8 = lambda c, need, left, dv: np.full_like(c, 8.0)
    for lab, s in (("frozen single setting", base), ("ENS-01 nine settings", ens), ("ENS-02 4 MNQ + 6 MES", both)):
        act = s["round_trips"] > 0
        vu = (s["net_pts"] / s["dvol_pts"])[act]
        p, d = simulate(s, f8, idx, rules)
        pc, _ = simulate(s, f8, idx, rules, flip=flip)
        out[lab] = {"t_daily": tstat(vu), "t_daily_2018_on": tstat(vu[vu.index >= "2018-01-01"]), "usd_per_day_8lot": float(s["net_pts"].mean() * 16), "days_active": int(act.sum()),
                    "std_usd_8lot": float(s["net_pts"].std() * 16), "pass30": p, "control": pc, "median_days": d}
        print(lab, json.dumps(out[lab]))
    print("mean pairwise corr of nine settings", out["ens_mean_pairwise_corr"], "ES/NQ rule corr", out["es_nq_corr"])

    # DP-01
    cut = pd.Timestamp("2021-01-01")
    tr, te = base[base.index < cut], base[base.index >= cut]
    x = (tr["net_pts"] / tr["dvol_pts"]).to_numpy(); a = (tr["mae_pts"] / tr["dvol_pts"]).to_numpy()
    U = np.array([250, 500, 1000, 1500, 2000, 3000, 4000, 6000, 9000.0])  # dollars of expected daily move carried
    G = np.arange(-2000, 3001, 100.0); H = np.arange(0, 2001, 100.0)
    gi = lambda g: np.clip(np.round((g + 2000) / 100).astype(int), 0, len(G) - 1)
    hi_ = lambda h: np.clip(np.round(h / 100).astype(int), 0, len(H) - 1)
    V = np.zeros((len(G), len(H)))
    pol = np.zeros((31, len(G), len(H)))
    gg, hh = np.meshgrid(G, H, indexing="ij")
    floor = np.minimum(hh - 2000, 0.0)
    valid = (gg > floor) & (gg <= np.maximum(hh, gg))
    for left in range(1, 31):
        best = np.full(V.shape, -1.0); arg = np.zeros(V.shape)
        for u in U:
            pnl = u * x[None, None, :]; worst = gg[..., None] + u * a[None, None, :]
            fail = worst <= floor[..., None]
            g2 = gg[..., None] + pnl
            win = ~fail & (g2 >= 3000)
            h2 = np.maximum(hh[..., None], g2)
            cont = V[gi(g2), hi_(np.minimum(h2, 2000))]
            val = np.where(fail, 0.0, np.where(win, 1.0, cont)).mean(axis=2)
            upd = val > best + 1e-12
            best = np.where(upd, val, best); arg = np.where(upd, u, arg)
        V = np.where(valid, best, 0.0); pol[left] = arg
    out["dp_value_at_start_train"] = float(V[gi(np.array(0.0)), 0])
    out["dp_first_day_risk_units"] = float(pol[30][gi(np.array(0.0)), 0])

    def dp_policy(cush, need, left, dv):
        g = 3000 - need
        fl = g - cush
        h = np.where(fl < 0, fl + 2000, 2000.0)
        return pol[int(left)][gi(g), hi_(h)] / dv
    med = float((tr["dvol_pts"] * 2).median())
    rng = np.random.default_rng(2)
    for lab, s in (("train to 2020", tr), ("test 2021 to Oct 2024", te)):
        idx = block_bootstrap(len(s), 20000, 30, 5, rng); flip = rng.random(idx.shape) < 0.5
        for pn, pf in (("fixed 8 MNQ", f8), ("DP policy", dp_policy), ("fixed 2000 risk units", lambda c, need, left, dv: 2000.0 / dv)):
            p, d = simulate(s, pf, idx, rules); pc, _ = simulate(s, pf, idx, rules, flip=flip)
            out[f"DP {lab} {pn}"] = {"pass30": p, "control": pc, "median_days": d}
            print(f"DP-01 {lab:22s} {pn:22s} pass30 {p:6.1%} control {pc:6.1%} gain {p - pc:+6.1%} median days {d}")
    print("DP value at start (train, model):", out["dp_value_at_start_train"], "first-day risk units:", out["dp_first_day_risk_units"], "median dvol $/MNQ train:", med)
    (ROOT / "reports/iter_20_21.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
