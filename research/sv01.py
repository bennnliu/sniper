"""SIZEVOL-01 (iteration 25): volatility and contract size with the logistic filter, all New York hours.
Hypothesis and pass bar are in reports/SECOND_EDGE_LOG.md, committed before this file was first run.
Writes the dashboard files to reports/dash03/. Run: python research/sv01.py
"""
import pickle
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.dash01_analyze import NSET, PV, RULES, combine_sim, drawdown, mc_row, tstat  # noqa: E402
from research.dl01_eval import auc_ci, cluster_diff, sharpe  # noqa: E402
from research.dl01_model import FEATS, FIRST_TEST_YEAR, HOLD, LABELS, SKIP_Q, prep  # noqa: E402
from sniper.ensemble import days_from_trades  # noqa: E402
from sniper.montecarlo import block_bootstrap  # noqa: E402

OUT = ROOT / "reports" / "dash03"
OOF_START = pd.Timestamp("2016-01-01"); DEV_END = pd.Timestamp("2024-11-01")
GRID = {"50K": [3, 6, 9, 12, 18, 27, 36, 50], "100K": [9, 18, 27, 36, 54, 72, 100], "150K": [9, 18, 27, 36, 54, 81, 108, 150]}
CAP = {"50K": 50, "100K": 100, "150K": 150}
RISK = [0.125, 0.25, 0.375, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0]  # expected move of the whole position, as a multiple of the loss limit
ENVS = [("low", "Low volatility"), ("mid", "Middle volatility"), ("high", "High volatility"), ("all", "All days")]
VAR = {"none": "Unfiltered", "logit": "Logistic filter"}
SRC = {("dev", 1): "Test years 2016 to Oct 2024", ("dev", 2): "Test years at double cost", ("wf", 1): "Walk-forward year"}
NP = 4000


def walk_forward_logit(t):
    t = t.reset_index(drop=True).copy()
    X = t[FEATS].to_numpy(float); y = t["win"].to_numpy()
    year = t["day"].dt.year.to_numpy(); isdev = (t["period"] == "dev").to_numpy()
    folds = [(isdev & (year < yv), isdev & (year == yv)) for yv in sorted(set(year[isdev])) if yv >= FIRST_TEST_YEAR] + [(isdev, ~isdev)]
    t["score"] = np.nan; t["keep"] = np.nan
    for tr, te in folds:
        days = np.sort(t.loc[tr, "day"].unique()); cut = days[int(len(days) * (1 - HOLD))]
        a = tr & (t["day"] < cut).to_numpy(); b = tr & (t["day"] >= cut).to_numpy()
        f = prep(X[a]); m = LogisticRegression(C=0.1, max_iter=1000).fit(f(X[a]), y[a])
        thr = np.quantile(m.predict_proba(f(X[b]))[:, 1], SKIP_Q)
        s = m.predict_proba(f(X[te]))[:, 1]
        t.loc[te, "score"] = s; t.loc[te, "keep"] = (s >= thr).astype(float)
    f = prep(X[isdev]); m = LogisticRegression(C=0.1, max_iter=1000).fit(f(X[isdev]), y[isdev])
    w = pd.DataFrame({"feature": [LABELS[c] for c in FEATS], "weight": m.coef_[0]}).sort_values("weight", key=abs, ascending=False)
    return t[t["score"].notna()].copy(), w


def sim(dd, contracts, size, seed=0, horizon=400):
    """Combine only. contracts: MNQ held when every setting is in, one number per day (0 = no trading that day)."""
    spec = RULES.account(size)
    k = np.asarray(contracts, float) / NSET * PV
    pnl, mae, mfe = dd["net_pts"].to_numpy() * k, dd["mae_pts"].to_numpy() * k, dd["mfe_pts"].to_numpy() * k
    cost = (dd["gross_pts"] - dd["net_pts"]).to_numpy() * k
    traded = (dd["round_trips"] > 0).to_numpy() & (k > 0)
    rng = np.random.default_rng(seed)
    idx = block_bootstrap(len(dd), NP, horizon, 5, rng)
    flip = rng.random(idx.shape) < 0.5
    passed, breached, days, _ = combine_sim(pnl, mae, mfe, cost, traded, idx, spec)
    cp, _, cd, _ = combine_sim(pnl, mae, mfe, cost, traded, idx, spec, flip=flip)
    p = float(passed.mean()); p30 = float((passed & (days <= 30)).mean())
    month = spec.combine_monthly_standard + RULES.api_monthly
    fees = float(np.ceil(days / 21).mean() * month); fees30 = float(np.ceil(np.minimum(days, 30) / 21).mean() * month)
    return {"pass": p, "pass_se": float(np.sqrt(p * (1 - p) / NP)), "pass_30d": p30, "pass_30d_se": float(np.sqrt(p30 * (1 - p30) / NP)),
            "breach": float(breached.mean()), "breach_30d": float((breached & (days <= 30)).mean()),
            "control_pass": float(cp.mean()), "control_pass_30d": float((cp & (cd <= 30)).mean()),
            "median_days_to_pass": float(np.median(days[passed])) if passed.any() else np.nan,
            "fees_per_attempt": fees, "fees_per_pass": fees / p if p > 0 else np.nan, "fees_per_pass_30d": fees30 / p30 if p30 > 0 else np.nan,
            "daily_std_usd": float(pnl.std()), "std_over_limit": float(pnl.std() / spec.mll)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = pickle.load(open(ROOT / "data/cache/dl01.pkl", "rb"))
    sc, weights = walk_forward_logit(d["trades"])
    sc.to_pickle(ROOT / "data/cache/sv01_scored.pkl")
    weights.to_csv(OUT / "weights.csv", index=False)
    px_days, px = d["px"]["days"], d["px"]["px"]; alld = d["days"]
    cal = {"dev": alld.index[(alld.index >= OOF_START) & (alld.index < DEV_END)], "wf": alld.index[alld.index >= DEV_END]}
    keep = {"none": pd.Series(True, index=sc.index), "logit": sc["keep"] == 1}
    S = {}
    for v, k in keep.items():
        for p in cal:
            for cm, col in ((1, "net_pts"), (2, "net2_pts")):
                dd = days_from_trades(sc[k & (sc.period == p)], cal[p], px_days, px, col)
                for c in ("dvol_pts", "regime", "ratio"):
                    dd[c] = alld[c].reindex(cal[p])
                dd["exp_usd"] = dd["dvol_pts"] * PV  # expected daily move of one MNQ, dollars
                S[v, p, cm] = dd
    envmask = lambda dd, e: np.ones(len(dd), bool) if e == "all" else (dd["regime"] == e).to_numpy()

    # ---------------- filter check
    F = []
    for p in ("dev", "wf"):
        for e, en in ENVS:
            t = sc[sc.period == p]; t = t if e == "all" else t[t.regime == e]
            k = keep["logit"][t.index]
            a, lo, hi = auc_ci(t, "score"); est, tt = cluster_diff(t, k, "net_pts"); est2, tt2 = cluster_diff(t, k, "net2_pts")
            u = t["net_pts"] * PV
            F.append({"id": f"{p}|{e}", "period": p, "env": en, "env_key": e, "trades": len(t), "skipped_share": float(1 - k.mean()), "auc": a, "auc_lo": lo, "auc_hi": hi,
                      "kept_avg": float(u[k].mean()), "skipped_avg": float(u[~k].mean()), "diff": est, "diff_t": tt, "diff_t_2x": tt2,
                      "total_unfiltered": float(u.sum()), "total_filtered": float(u[k].sum()), "win_unfiltered": float(t.win.mean()), "win_filtered": float(t.win[k].mean())})
    ft = pd.DataFrame(F); ft.to_csv(OUT / "filter.csv", index=False)
    print(ft[["period", "env", "trades", "auc", "auc_lo", "kept_avg", "skipped_avg", "diff_t", "total_unfiltered", "total_filtered"]].round(3).to_string(index=False))

    # ---------------- environments
    E = []
    for (p, cm), src in SRC.items():
        for v in VAR:
            dd0 = S[v, p, cm]
            for e, en in ENVS:
                dd = dd0[envmask(dd0, e)]; u = dd["net_pts"] * PV; tr = dd["round_trips"] > 0
                t = sc[keep[v] & (sc.period == p)]; t = t if e == "all" else t[t.regime == e]
                col = "net_pts" if cm == 1 else "net2_pts"
                var = float(u.var())
                E.append({"id": f"{src}|{v}|{e}", "source": src, "variant": VAR[v], "variant_key": v, "env": en, "env_key": e, "days": len(dd), "traded_days": int(tr.sum()), "trades": len(t),
                          "exp_move_usd": float(dd["exp_usd"].median()), "exp_move_set_usd": float(dd["exp_usd"].median() * NSET), "ratio_median": float(dd["ratio"].median()),
                          "total": float(u.sum()), "per_day": float(u.mean()), "std_day": float(u.std()), "sharpe": sharpe(u), "t": tstat(u),
                          "std_over_exp": float(u.std() / (dd["exp_usd"].median() * NSET)), "win_days": float((u[tr] > 0).mean()), "avg_win_day": float(u[tr & (u > 0)].mean()), "avg_loss_day": float(u[tr & (u <= 0)].mean()),
                          "worst_day": float(u.min()), "best_day": float(u.max()), "p05_day": float(u.quantile(0.05)), "avg_open_loss": float((dd["mae_pts"][tr] * PV).mean()), "worst_open_loss": float((dd["mae_pts"] * PV).min()),
                          "drawdown": drawdown(u)[1], "per_trade": float(t[col].mean() * PV), "win_trades": float((t[col] > 0).mean()), "avg_contracts": float(dd["max_pos"][tr].mean()),
                          "edge_over_var": float(u.mean() / var * 1e3) if var > 0 else np.nan,
                          "mnq_for_500_std": float(500 / u.std() * NSET) if u.std() > 0 else np.nan})
    env = pd.DataFrame(E)
    for src in env.source.unique():  # growth-optimal size relative to all days of the same variant
        for v in VAR.values():
            m = (env.source == src) & (env.variant == v); base = env.loc[m & (env.env_key == "all"), "edge_over_var"].iloc[0]
            env.loc[m, "relative_optimal_size"] = env.loc[m, "edge_over_var"] / base
    env.to_csv(OUT / "environments.csv", index=False)
    print(env[env.source == SRC["dev", 1]][["variant", "env", "days", "exp_move_set_usd", "per_day", "std_day", "sharpe", "t", "std_over_exp", "relative_optimal_size", "mnq_for_500_std"]].round(2).to_string(index=False))

    # ---------------- risk against expected move: ten equal groups of days by expected move in dollars
    B = []; facts = []
    for v in VAR:
        dd = S[v, "dev", 1]; q = pd.qcut(dd["exp_usd"].rank(method="first"), 10, labels=False)
        for i, g in dd.groupby(q):
            u = g["net_pts"] * PV
            B.append({"id": f"{v}|{i}", "variant": VAR[v], "variant_key": v, "group": int(i) + 1, "days": len(g), "exp_move_set_usd": float(g["exp_usd"].median() * NSET), "exp_lo": float(g["exp_usd"].min() * NSET), "exp_hi": float(g["exp_usd"].max() * NSET),
                      "std_day": float(u.std()), "per_day": float(u.mean()), "abs_day": float(u.abs().mean()), "sharpe": sharpe(u), "first_day": str(g.index.min().date()), "last_day": str(g.index.max().date()),
                      "mnq_for_500_std": float(500 / u.std() * NSET)})
        b = pd.DataFrame([r for r in B if r["variant_key"] == v])
        slope, icpt = np.polyfit(np.log(b.exp_move_set_usd), np.log(b.std_day), 1)
        trd = dd[dd.round_trips > 0]; rho = float(np.corrcoef(np.log(trd.exp_usd), np.log((trd.net_pts * PV).abs().clip(lower=1)))[0, 1])
        facts.append({"variant": VAR[v], "variant_key": v, "loglog_slope": float(slope), "std_per_exp_dollar": float(np.exp(icpt)), "corr_abs_result_exp_move": rho,
                      "sharpe_corr_with_exp": float(np.corrcoef(b.exp_move_set_usd.rank(), b.sharpe.rank())[0, 1])})
    pd.DataFrame(B).to_csv(OUT / "volbins.csv", index=False); fx = pd.DataFrame(facts); fx.to_csv(OUT / "facts.csv", index=False); print(fx.round(3).to_string(index=False))

    # ---------------- daily series
    frames = []
    for p in ("dev", "wf"):
        f = pd.DataFrame({"date": cal[p].strftime("%Y-%m-%d"), "period": p, "regime": S["none", p, 1]["regime"].to_numpy(), "ratio": S["none", p, 1]["ratio"].round(3).to_numpy(),
                          "exp_move_set_usd": (S["none", p, 1]["exp_usd"] * NSET).round(0).to_numpy()})
        for v in VAR:
            f[f"pnl_{v}"] = (S[v, p, 1]["net_pts"] * PV).round(2).to_numpy(); f[f"pnl2x_{v}"] = (S[v, p, 2]["net_pts"] * PV).round(2).to_numpy()
        frames.append(f)
    daily = pd.concat(frames, ignore_index=True)
    for v in VAR:
        daily[f"eq_{v}_all"] = daily[f"pnl_{v}"].cumsum().round(0)
        for e in ("low", "mid", "high"):
            daily[f"eq_{v}_{e}"] = (daily[f"pnl_{v}"] * (daily.regime == e)).cumsum().round(0)
    # constant-risk equity for the picture: contracts so that one set-equivalent has the same expected move every day
    ref = daily.loc[daily.period == "dev", "exp_move_set_usd"].median()
    daily["scale"] = (ref / daily["exp_move_set_usd"]).round(3)
    for v in VAR:
        daily[f"eq_{v}_scaled"] = (daily[f"pnl_{v}"] * daily["scale"]).cumsum().round(0)
    daily.to_csv(OUT / "daily.csv", index=False)

    # ---------------- Combine by size inside each environment (days drawn from that environment only)
    M = []
    for size, grid in GRID.items():
        for (p, cm), src in SRC.items():
            for v in VAR:
                dd0 = S[v, p, cm]
                for e, en in ENVS:
                    dd = dd0[envmask(dd0, e)]
                    for n in grid:
                        r = sim(dd, np.full(len(dd), n), size)
                        M.append({"id": f"{size}|{src}|{v}|{e}|{n}", "account": size, "source": src, "variant": VAR[v], "variant_key": v, "env": en, "env_key": e, "contracts": n, **r})
    mc = pd.DataFrame(M); mc.to_csv(OUT / "mc_env.csv", index=False)
    best = []
    for (size, src, v, e), g in mc.groupby(["account", "source", "variant_key", "env_key"]):
        for metric, lab in (("pass_30d", "Pass within 30 trading days"), ("pass", "Pass with no time limit")):
            r = g.loc[g[metric].idxmax()]; dd0 = S[v, "dev" if "Test" in src else "wf", 1]; dd = dd0[envmask(dd0, e)]
            best.append({"id": f"{size}|{src}|{v}|{e}|{metric}", "account": size, "source": src, "variant": VAR[v], "variant_key": v, "env": dict(ENVS)[e], "env_key": e, "objective": lab, "objective_key": metric,
                         "best_contracts": int(r.contracts), "pass": r["pass"], "pass_30d": r["pass_30d"], "control_pass": r["control_pass"], "control_pass_30d": r["control_pass_30d"], "breach": r["breach"], "median_days_to_pass": r["median_days_to_pass"],
                         "std_over_limit": r["std_over_limit"], "daily_std_usd": r["daily_std_usd"], "exp_move_position_usd": float(dd["exp_usd"].median() * r.contracts), "at_cap": int(r.contracts == CAP[size])})
    bt = pd.DataFrame(best); bt.to_csv(OUT / "best.csv", index=False)
    print(bt[(bt.source == SRC["dev", 1])][["account", "variant", "env", "objective_key", "best_contracts", "pass", "pass_30d", "control_pass_30d", "std_over_limit"]].round(3).to_string(index=False))

    # ---------------- full Topstep path (Combine + funded account) at the base size, per environment
    X = []
    for size, n in (("50K", 9), ("100K", 18), ("150K", 27)):
        for v in VAR:
            for e, en in ENVS:
                dd0 = S[v, "dev", 1]; dd = dd0[envmask(dd0, e)]
                r = mc_row(dd, n, size, SRC["dev", 1], n_paths=NP)
                X.append({"id": f"{size}|{v}|{e}", "variant": VAR[v], "variant_key": v, "env": en, "env_key": e, **r})
    pd.DataFrame(X).to_csv(OUT / "funded.csv", index=False)

    # ---------------- policies over the full calendar
    P = []
    for size in GRID:
        mll = RULES.account(size).mll
        for (p, cm), src in SRC.items():
            for v in VAR:
                dd = S[v, p, cm]; exp = dd["exp_usd"].to_numpy(); reg = dd["regime"].to_numpy()
                hi = reg == "high"; notlow = (reg == "high") | (reg == "mid")
                def crisk(x):
                    return np.clip(np.round(x * mll / exp), 1, CAP[size])
                pol = [("fixed", "Fixed size, every day", "MNQ", [(n, np.full(len(dd), float(n))) for n in GRID[size]]),
                       ("risk", "Constant risk, every day", "expected move over loss limit", [(x, crisk(x)) for x in RISK]),
                       ("fixed_high", "Fixed size, high-volatility days only", "MNQ", [(n, np.where(hi, float(n), 0.0)) for n in GRID[size]]),
                       ("risk_high", "Constant risk, high-volatility days only", "expected move over loss limit", [(x, np.where(hi, crisk(x), 0.0)) for x in RISK]),
                       ("fixed_notlow", "Fixed size, skip low-volatility days", "MNQ", [(n, np.where(notlow, float(n), 0.0)) for n in GRID[size]])]
                for key, name, unit, grid in pol:
                    for par, c in grid:
                        r = sim(dd, c, size)
                        act = c[c > 0]
                        P.append({"id": f"{size}|{src}|{v}|{key}|{par}", "account": size, "source": src, "variant": VAR[v], "variant_key": v, "policy": name, "policy_key": key, "parameter": par, "unit": unit,
                                  "avg_contracts": float(act.mean()), "min_contracts": float(act.min()), "max_contracts": float(act.max()), "days_at_cap": float((act >= CAP[size]).mean()), "days_traded_share": float((c > 0).mean()), **r})
    pol = pd.DataFrame(P)
    # the parameter chosen on test years (assumed cost) is the one carried to double cost and the walk-forward year
    pol["chosen"] = 0
    for (size, v, key), g in pol[pol.source == SRC["dev", 1]].groupby(["account", "variant_key", "policy_key"]):
        par = g.loc[g["pass_30d"].idxmax(), "parameter"]
        pol.loc[(pol.account == size) & (pol.variant_key == v) & (pol.policy_key == key) & (pol.parameter == par), "chosen"] = 1
    pol.to_csv(OUT / "policies.csv", index=False)
    ch = pol[(pol.chosen == 1) & (pol.variant_key == "logit")]
    print(ch[["account", "source", "policy", "parameter", "avg_contracts", "pass", "pass_30d", "pass_30d_se", "control_pass_30d", "breach_30d", "median_days_to_pass", "fees_per_pass_30d"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
