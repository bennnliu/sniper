"""STRAT-01 (iteration 26): Ben's combined strategy. Rule and pass criteria are in reports/SECOND_EDGE_LOG.md,
committed before this file was first run. Writes the dashboard files to reports/dash04/.
  trade New York middle- and high-volatility days; logistic filter on middle days only;
  baseline size on middle days, baseline x (1.2828 / ratio) on high days.
Run: python research/strat01.py
"""
import pickle
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.dash01_analyze import NSET, PV, bucket_stats, drawdown, kpis, mc_row, tstat  # noqa: E402
from research.dl01_eval import sharpe  # noqa: E402
from research.sv01 import GRID, sim  # noqa: E402
from sniper.ensemble import days_from_trades  # noqa: E402

V2 = "v2" in sys.argv  # iteration 27: low-volatility days added, unfiltered, at baseline size
OUT = ROOT / "reports" / ("dash05" if V2 else "dash04")
OOF_START = pd.Timestamp("2016-01-01"); DEV_END = pd.Timestamp("2024-11-01")
SRC = {("dev", 1): "Test years 2016 to Oct 2024", ("dev", 2): "Test years at double cost", ("wf", 1): "Walk-forward year"}
NAMES = {"strat": "The strategy", "noreduce": "Same, no size reduction", "nofilter": "Same, no filter", "prev": "Without low-volatility days (previous version)", "bench": "All days, filter everywhere, fixed size", "raw": "All days, unfiltered, fixed size"}
SCALE = ["net_pts", "gross_pts", "mae_pts", "mfe_pts", "max_pos"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = pickle.load(open(ROOT / "data/cache/dl01.pkl", "rb"))
    sc = pd.read_pickle(ROOT / "data/cache/sv01_scored.pkl")
    cut = d["high_cut"]; alld = d["days"]; px_days, px = d["px"]["days"], d["px"]["px"]
    cal = {"dev": alld.index[(alld.index >= OOF_START) & (alld.index < DEV_END)], "wf": alld.index[alld.index >= DEV_END]}
    reg, ratio = alld["regime"], alld["ratio"]
    reduced = pd.Series(np.where(reg == "high", np.minimum(1.0, cut / ratio), np.where(reg == "mid", 1.0, 0.0)), index=alld.index)
    flat = pd.Series(np.where(reg.isin(["mid", "high"]), 1.0, 0.0), index=alld.index)
    one = pd.Series(1.0, index=alld.index)
    k = sc["keep"] == 1; mid = sc.regime == "mid"; high = sc.regime == "high"
    V = {"strat": ((mid & k) | high, reduced), "noreduce": ((mid & k) | high, flat), "nofilter": (mid | high, reduced), "bench": (k, one), "raw": (pd.Series(True, index=sc.index), one)}
    if V2:
        every = pd.Series(True, index=sc.index)
        reduced_all = pd.Series(np.where(reg == "high", np.minimum(1.0, cut / ratio), 1.0), index=alld.index)
        V = {"strat": (~mid | k, reduced_all), "noreduce": (~mid | k, one), "nofilter": (every, reduced_all), "prev": ((mid & k) | high, reduced), "bench": (k, one), "raw": (every, one)}
    S, T = {}, {}
    for v, (mask, mult) in V.items():
        for p in cal:
            for cm, col in ((1, "net_pts"), (2, "net2_pts")):
                tt = sc[mask & (sc.period == p)].copy()
                dd = days_from_trades(tt, cal[p], px_days, px, col)
                m = mult.reindex(cal[p]).to_numpy()
                for c in SCALE:
                    dd[c] = dd[c] * m
                dd.loc[m == 0, "round_trips"] = 0
                dd["mult"] = m; dd["regime"] = reg.reindex(cal[p]).to_numpy(); dd["ratio"] = ratio.reindex(cal[p]).to_numpy()
                dd["exp_usd"] = alld["dvol_pts"].reindex(cal[p]).to_numpy() * PV
                dd["dvol_pts"] = alld["dvol_pts"].reindex(cal[p]).to_numpy()
                S[v, p, cm] = dd
                tm = mult.reindex(tt["day"]).to_numpy()
                tt["mult"] = tm; tt["net_pts"] = tt[col] * tm
                for c in ("gross_pts", "mae_pts", "mfe_pts"):
                    tt[c] = tt[c] * tm
                T[v, p, cm] = tt[tm > 0]

    # ---------------- summary by variant
    R = []
    for v in V:
        for (p, cm), src in SRC.items():
            dd = S[v, p, cm]; u = dd["net_pts"] * PV; tr = dd["round_trips"] > 0; t = T[v, p, cm]
            R.append({"id": f"{v}|{src}", "variant": NAMES[v], "key": v, "source": src, "days": len(dd), "traded_days": int(tr.sum()), "trades": len(t), "total": float(u.sum()), "per_day": float(u.mean()),
                      "per_traded_day": float(u[tr].mean()), "std_day": float(u.std()), "sharpe": sharpe(u), "t": tstat(u), "drawdown": drawdown(u)[1], "win_days": float((u[tr] > 0).mean()),
                      "per_trade": float(t["net_pts"].mean() * PV), "win_trades": float((t["net_pts"] > 0).mean()), "worst_day": float(u.min()), "best_day": float(u.max()),
                      "avg_size": float(dd["mult"][tr].mean()), "profit_over_drawdown": float(u.sum() / abs(drawdown(u)[1])) if drawdown(u)[1] < 0 else np.nan})
    summ = pd.DataFrame(R); summ.to_csv(OUT / "summary.csv", index=False)
    pd.set_option("display.width", 250)
    print(summ[["variant", "source", "traded_days", "trades", "total", "sharpe", "t", "drawdown", "per_trade", "avg_size"]].round(2).to_string(index=False))

    # ---------------- full statistics table for the strategy
    cols = []
    for lab, v, p, cm in (("dev", "strat", "dev", 1), ("dev_2x", "strat", "dev", 2), ("wf", "strat", "wf", 1), ("dev_noreduce", "noreduce", "dev", 1), ("dev_bench", "bench", "dev", 1), ("dev_raw", "raw", "dev", 1)):
        cols.append(kpis(S[v, p, cm], T[v, p, cm], lab)[0])
    kp = cols[0]
    for c in cols[1:]:
        kp = kp.merge(c.drop(columns=["group", "unit"]), on="metric")
    kp.to_csv(OUT / "kpis.csv", index=False)

    # ---------------- contribution of each environment inside the strategy
    E = []
    for (p, cm), src in SRC.items():
        dd = S["strat", p, cm]; t = T["strat", p, cm]
        for e, en in (("low", "Low volatility, unfiltered, baseline size" if V2 else "Low volatility, not traded"), ("mid", "Middle volatility, filtered, baseline size"), ("high", "High volatility, unfiltered, reduced size")):
            g = dd[dd.regime == e]; u = g["net_pts"] * PV; tt = t[t.regime == e]; raw = S["raw", p, cm]; ru = raw.loc[g.index, "net_pts"] * PV
            E.append({"id": f"{src}|{e}", "source": src, "env": en, "env_key": e, "days": len(g), "trades": len(tt), "total": float(u.sum()), "per_day": float(u.mean()) if len(g) else np.nan, "std_day": float(u.std()),
                      "sharpe": sharpe(u) if u.std() > 0 else np.nan, "t": tstat(u) if u.std() > 0 else np.nan, "avg_size": float(g["mult"].mean()), "min_size": float(g["mult"].min()),
                      "per_trade": float(tt["net_pts"].mean() * PV) if len(tt) else np.nan, "win_trades": float((tt["net_pts"] > 0).mean()) if len(tt) else np.nan,
                      "unfiltered_full_size_total": float(ru.sum()), "unfiltered_full_size_std": float(ru.std())})
    pd.DataFrame(E).to_csv(OUT / "environments.csv", index=False)

    # ---------------- daily, yearly, monthly
    frames = []
    for p in ("dev", "wf"):
        f = pd.DataFrame({"date": cal[p].strftime("%Y-%m-%d"), "period": p, "regime": S["strat", p, 1]["regime"].to_numpy(), "ratio": S["strat", p, 1]["ratio"].round(3).to_numpy(), "size": S["strat", p, 1]["mult"].round(3).to_numpy()})
        for v in V:
            f[f"pnl_{v}"] = (S[v, p, 1]["net_pts"] * PV).round(2).to_numpy(); f[f"pnl2x_{v}"] = (S[v, p, 2]["net_pts"] * PV).round(2).to_numpy()
        f["trades"] = S["strat", p, 1]["round_trips"].astype(int).to_numpy()
        frames.append(f)
    daily = pd.concat(frames, ignore_index=True)
    for v in V:
        e = daily[f"pnl_{v}"].cumsum(); daily[f"eq_{v}"] = e.round(0); daily[f"eq2x_{v}"] = daily[f"pnl2x_{v}"].cumsum().round(0); daily[f"dd_{v}"] = (e - e.cummax()).round(0)
    daily.to_csv(OUT / "daily.csv", index=False)
    dt = pd.to_datetime(daily["date"])
    Y = []
    for (y, p), g in daily.groupby([dt.dt.year, daily.period], sort=True):
        r = {"id": f"{y}|{p}", "year": y, "period": p, "days": len(g), "traded_days": int((g["trades"] > 0).sum()), "trades": int(g["trades"].sum()), "avg_size_high": float(g.loc[g.regime == "high", "size"].mean())}
        for v in V:
            r[f"pnl_{v}"] = float(g[f"pnl_{v}"].sum()); r[f"sharpe_{v}"] = sharpe(g[f"pnl_{v}"])
        r["worst_day"] = float(g["pnl_strat"].min()); r["best_day"] = float(g["pnl_strat"].max())
        Y.append(r)
    pd.DataFrame(Y).to_csv(OUT / "yearly.csv", index=False)
    mo = daily.assign(y=dt.dt.year, m=dt.dt.month).groupby(["y", "m"], as_index=False)["pnl_strat"].sum().rename(columns={"pnl_strat": "pnl"})
    mo["id"] = mo.y.astype(str) + "-" + mo.m.astype(str).str.zfill(2); mo.to_csv(OUT / "monthly.csv", index=False)

    # ---------------- size against volatility on high days, and histograms
    hd = daily[(daily.regime == "high")]
    q = pd.cut(hd["ratio"], [cut, 1.5, 1.75, 2.0, 2.5, 3.0, 100], labels=["1.28 to 1.5", "1.5 to 1.75", "1.75 to 2", "2 to 2.5", "2.5 to 3", "above 3"])
    Z = []
    for i, (lab, g) in enumerate(hd.groupby(q, observed=True)):
        for p in ("dev", "wf"):
            gg = g[g.period == p]
            if len(gg):
                Z.append({"id": f"{lab}|{p}", "bucket": lab, "order": i, "period": p, "days": len(gg), "avg_size": float(gg["size"].mean()), "per_day": float(gg["pnl_strat"].mean()), "std_day": float(gg["pnl_strat"].std()),
                          "per_day_full": float(gg["pnl_noreduce"].mean()), "std_day_full": float(gg["pnl_noreduce"].std()), "total": float(gg["pnl_strat"].sum()), "total_full": float(gg["pnl_noreduce"].sum())})
    pd.DataFrame(Z).to_csv(OUT / "sizing.csv", index=False)
    H = []; edges = np.arange(-3000, 3001, 250.0)
    for p in ("dev", "wf"):
        for v in ("strat", "raw"):
            x = daily.loc[(daily.period == p) & (daily["pnl_" + v] != 0), "pnl_" + v]
            c, _ = np.histogram(np.clip(x, edges[0], edges[-1] - 1e-9), edges)
            for i, n in enumerate(c):
                H.append({"period": p, "variant": NAMES[v], "key": v, "lo": edges[i], "hi": edges[i + 1], "count": int(n), "share": n / max(len(x), 1)})
    pd.DataFrame(H).to_csv(OUT / "histograms.csv", index=False)

    # ---------------- trade breakdowns for the strategy
    t = pd.concat([T["strat", "dev", 1], T["strat", "wf", 1]]); t["u"] = t["net_pts"] * PV; t["grp"] = np.where(t.period == "dev", "Test years", "Walk-forward year")
    et = t["ct_minute"] + 60; t["entry_time"] = (et // 60).astype(str) + ":" + (et % 60).astype(str).str.zfill(2)
    B = [bucket_stats(t.u, t.regime.map({"low": "Low volatility", "mid": "Middle volatility", "high": "High volatility"}).fillna("Unknown"), "Environment", ["Low volatility", "Middle volatility", "High volatility"], t.grp),
         bucket_stats(t.u, np.where(t["dir"] > 0, "Long", "Short"), "Direction", ["Long", "Short"], t.grp),
         bucket_stats(t.u, t.entry_time, "Entry time (New York time)", sorted(t.entry_time.unique(), key=lambda s: int(s.split(":")[0]) * 60 + int(s.split(":")[1])), t.grp),
         bucket_stats(t.u, t["exit_reason"].map({"stop": "Back inside the band", "flip": "Reversed to the other side", "session_end": "Held to the close"}), "How the trade ended", ["Held to the close", "Back inside the band", "Reversed to the other side"], t.grp),
         bucket_stats(t.u, "lookback " + t["lookback"].astype(str) + ", width " + t["vm"].astype(str), "Setting", [f"lookback {lb}, width {vm}" for lb in (7, 14, 28) for vm in (0.8, 1.0, 1.2)], t.grp),
         bucket_stats(t.u, t["day"].dt.day_name(), "Weekday", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], t.grp)]
    br = pd.concat(B, ignore_index=True).rename(columns={"period": "group"}); br["id"] = br["dimension"] + "|" + br["bucket"] + "|" + br["group"]
    br.to_csv(OUT / "breakdowns.csv", index=False)

    # ---------------- Monte Carlo
    M = []; t0 = time.time()
    for size, grid in GRID.items():
        for (p, cm), src in SRC.items():
            for v in V:
                for n in grid:
                    dd = S[v, p, cm]
                    r = mc_row(dd, n, size, src, n_paths=4000)
                    s = sim(dd, np.full(len(dd), n), size)
                    r.update({"id": f"{size}|{src}|{v}|{n}", "variant": NAMES[v], "key": v, "pass_30d_se": s["pass_30d_se"], "breach_30d": s["breach_30d"], "daily_std_usd": s["daily_std_usd"], "std_over_limit": s["std_over_limit"],
                              "fees_per_pass_30d": s["fees_per_pass_30d"]})
                    M.append(r)
        print("mc", size, round(time.time() - t0), flush=True)
    mc = pd.DataFrame(M)
    mc["chosen"] = 0
    for (size, v), g in mc[mc.days_from == SRC["dev", 1]].groupby(["account", "key"]):
        n = g.loc[g["pass_30d"].idxmax(), "contracts"]
        mc.loc[(mc.account == size) & (mc.key == v) & (mc.contracts == n), "chosen"] = 1
    mc.to_csv(OUT / "montecarlo.csv", index=False)
    ch = mc[(mc.chosen == 1)]
    print(ch[["account", "days_from", "variant", "contracts", "pass", "pass_30d", "pass_30d_se", "control_pass_30d", "breach", "median_days_to_pass", "payout_rate_standard", "profit_per_account", "profit_per_account_30d", "ben_score_30d"]].round(3).to_string(index=False))

    # ---------------- criteria
    g = lambda v, src, c: ch[(ch.account == "50K") & (ch.key == v) & (ch.days_from == src)][c].iloc[0]
    s = lambda v, src, c: summ[(summ.key == v) & (summ.source == src)][c].iloc[0]
    A, A2, W = SRC["dev", 1], SRC["dev", 2], SRC["wf", 1]
    C = [("1. Test years: profit positive, daily t at least 2", s("strat", A, "total") > 0 and s("strat", A, "t") >= 2, f"total ${s('strat', A, 'total'):,.0f} per baseline set, t {s('strat', A, 't'):.2f}, Sharpe {s('strat', A, 'sharpe'):.2f}"),
         ("2. The same at double cost", s("strat", A2, "total") > 0 and s("strat", A2, "t") >= 2, f"total ${s('strat', A2, 'total'):,.0f}, t {s('strat', A2, 't'):.2f}"),
         ("3. 30-day pass rate at least 2 points above the fixed-size, all-days benchmark", g("strat", A, "pass_30d") >= g("bench", A, "pass_30d") + 0.02, f"{g('strat', A, 'pass_30d'):.1%} at {int(g('strat', A, 'contracts'))} MNQ against {g('bench', A, 'pass_30d'):.1%} at {int(g('bench', A, 'contracts'))} MNQ (simulated)"),
         ("4. Beats the coin control by more than twice the simulation error", g("strat", A, "pass_30d") - g("strat", A, "control_pass_30d") > 2 * g("strat", A, "pass_30d_se"), f"{g('strat', A, 'pass_30d'):.1%} against control {g('strat', A, 'control_pass_30d'):.1%}"),
         ("5. Size reduction: 30-day pass rate not lower than without it", g("strat", A, "pass_30d") >= g("noreduce", A, "pass_30d"), f"{g('strat', A, 'pass_30d'):.1%} with the reduction against {g('noreduce', A, 'pass_30d'):.1%} without"),
         ("6. Walk-forward year: 30-day pass rate above the control", g("strat", W, "pass_30d") > g("strat", W, "control_pass_30d"), f"{g('strat', W, 'pass_30d'):.1%} against control {g('strat', W, 'control_pass_30d'):.1%} at {int(g('strat', W, 'contracts'))} MNQ")]
    cr = pd.DataFrame([{"id": c[0][:2].strip("."), "criterion": c[0], "result": "PASS" if c[1] else "FAIL", "evidence": c[2]} for c in C])
    cr.loc[len(cr)] = {"id": "all", "criterion": "All six", "result": "PASS" if all(c[1] for c in C) else "FAIL", "evidence": f"{sum(c[1] for c in C)} of 6 met"}
    cr.to_csv(OUT / "criteria.csv", index=False); pd.set_option("display.max_colwidth", 150); print(cr.to_string(index=False))


if __name__ == "__main__":
    main()
