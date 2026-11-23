"""META-02, step 4: test the filters against the criteria written in iteration 24, and write the dashboard files
to reports/dash02/. Out-of-fold development trades (2016 to Oct 2024) and the walk-forward year, New York
high-volatility days only. One set = one MNQ per setting. Costs 1.11 points per round trip, and double."""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.dash01_analyze import PV, bucket_stats, drawdown, kpis, mc_row, tstat  # noqa: E402
from research.dl01_model import FEATS, LABELS, MODELS, PRIMARY  # noqa: E402
from sniper.ensemble import days_from_trades  # noqa: E402

OUT = ROOT / "reports" / "dash02"
NAMES = {"none": "Unfiltered", "cnn": "Convolutional network (primary)", "mlp": "Neural network on the table", "boosted": "Boosted trees", "logistic": "Logistic regression"}
OOF_START = pd.Timestamp("2016-01-01"); DEV_END = pd.Timestamp("2024-11-01")


def cluster_diff(t, keep, col, n=1000, seed=0):
    """Kept minus skipped average result, with a standard error from resampling whole days."""
    u = t[col].to_numpy() * PV; k = keep.to_numpy(bool); day = t["day"].to_numpy()
    ud, inv = np.unique(day, return_inverse=True)
    sk = np.bincount(inv, u * k, len(ud)); nk = np.bincount(inv, k, len(ud)); ss = np.bincount(inv, u * ~k, len(ud)); ns = np.bincount(inv, ~k, len(ud))
    est = sk.sum() / nk.sum() - ss.sum() / ns.sum()
    rng = np.random.default_rng(seed); bs = []
    for _ in range(n):
        p = rng.integers(0, len(ud), len(ud))
        if nk[p].sum() > 0 and ns[p].sum() > 0:
            bs.append(sk[p].sum() / nk[p].sum() - ss[p].sum() / ns[p].sum())
    return est, est / np.std(bs)


def auc_ci(t, col, n=500, seed=0):
    y = t["win"].to_numpy(); x = t[col].to_numpy(); day = t["day"].to_numpy()
    ud, inv = np.unique(day, return_inverse=True); by = [np.where(inv == k)[0] for k in range(len(ud))]
    rng = np.random.default_rng(seed); bs = []
    for _ in range(n):
        p = np.concatenate([by[k] for k in rng.integers(0, len(ud), len(ud))])
        bs.append(roc_auc_score(y[p], x[p]))
    return roc_auc_score(y, x), np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def sharpe(u):
    return float(u.mean() / u.std() * np.sqrt(252)) if u.std() > 0 else np.nan


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = pickle.load(open(ROOT / "data/cache/dl01.pkl", "rb"))
    sc = pd.read_pickle(ROOT / "data/cache/dl01_scored.pkl")
    px_days, px = d["px"]["days"], d["px"]["px"]
    alld = d["days"]
    cal = {"dev": alld.index[(alld.index >= OOF_START) & (alld.index < DEV_END)], "wf": alld.index[alld.index >= DEV_END]}
    high = {p: cal[p][(alld.loc[cal[p], "regime"] == "high").to_numpy()] for p in cal}
    # test years only: high-volatility days whose trades were scored out of fold
    scored_days = {p: pd.DatetimeIndex(sorted(sc.loc[sc.period == p, "day"].unique())) for p in cal}
    keepers = {"none": pd.Series(True, index=sc.index)}
    for m in MODELS:
        keepers[m] = sc[f"keep_{m}"] == 1
    streams = {}
    for m, k in keepers.items():
        for p in cal:
            for cm, col in ((1, "net_pts"), (2, "net2_pts")):
                tt = sc[k & (sc.period == p)]
                dd = days_from_trades(tt, cal[p], px_days, px, col)
                dd["dvol_pts"] = alld["dvol_pts"].reindex(cal[p]); dd["regime"] = alld["regime"].reindex(cal[p])
                streams[m, p, cm] = dd

    # ------------- model table and criteria
    rows, crit = [], []
    rng = np.random.default_rng(11)
    for m in MODELS:
        r = {"model": NAMES[m], "key": m, "primary": int(m == PRIMARY)}
        for p in ("dev", "wf"):
            t = sc[sc.period == p]; k = keepers[m][t.index]
            a, lo, hi = auc_ci(t, f"score_{m}")
            est, tt = cluster_diff(t, k, "net_pts"); est2, tt2 = cluster_diff(t, k, "net2_pts")
            hd = high[p]
            base, filt = streams["none", p, 1].loc[hd, "net_pts"] * PV, streams[m, p, 1].loc[hd, "net_pts"] * PV
            base2, filt2 = streams["none", p, 2].loc[hd, "net_pts"] * PV, streams[m, p, 2].loc[hd, "net_pts"] * PV
            u = t["net_pts"].to_numpy() * PV; share = 1 - k.mean()
            rand = np.array([u[rng.random(len(u)) >= share].sum() for _ in range(2000)])
            u2 = t["net2_pts"].to_numpy() * PV
            rand2 = np.array([u2[rng.random(len(u2)) >= share].sum() for _ in range(2000)])
            r.update({f"{p}_auc": a, f"{p}_auc_lo": lo, f"{p}_auc_hi": hi, f"{p}_skipped_share": share, f"{p}_kept_avg": u[k].mean(), f"{p}_skipped_avg": u[~k].mean(),
                      f"{p}_diff_t": tt, f"{p}_total_unfiltered": base.sum(), f"{p}_total_filtered": filt.sum(), f"{p}_per_day_unfiltered": base.mean(), f"{p}_per_day_filtered": filt.mean(),
                      f"{p}_sharpe_unfiltered": sharpe(base), f"{p}_sharpe_filtered": sharpe(filt), f"{p}_random_pctile": float((rand < filt.sum()).mean()),
                      f"{p}_kept_avg_2x": u2[k].mean(), f"{p}_skipped_avg_2x": u2[~k].mean(), f"{p}_diff_t_2x": tt2, f"{p}_total_unfiltered_2x": base2.sum(), f"{p}_total_filtered_2x": filt2.sum(),
                      f"{p}_sharpe_unfiltered_2x": sharpe(base2), f"{p}_sharpe_filtered_2x": sharpe(filt2), f"{p}_random_pctile_2x": float((rand2 < filt2.sum()).mean()),
                      f"{p}_winners_kept": float(k[t.win == 1].mean()), f"{p}_losers_skipped": float((~k[t.win == 0]).mean()),
                      f"{p}_dd_unfiltered": drawdown(base)[1], f"{p}_dd_filtered": drawdown(filt)[1]})
        mcb = mc_row(streams["none", "dev", 1].assign(), 9, "50K", "oof"); mcf = mc_row(streams[m, "dev", 1], 9, "50K", "oof")
        r.update({"pass30_unfiltered": mcb["pass_30d"], "pass30_filtered": mcf["pass_30d"], "pass_unfiltered": mcb["pass"], "pass_filtered": mcf["pass"]})
        rows.append(r)
        C = [("1. AUC at least 0.53 and interval above 0.50", r["dev_auc"] >= 0.53 and r["dev_auc_lo"] > 0.5, f"AUC {r['dev_auc']:.3f}, interval {r['dev_auc_lo']:.3f} to {r['dev_auc_hi']:.3f}"),
             ("2. Skipped trades lose money and kept minus skipped has t of at least 2", r["dev_skipped_avg"] < 0 and r["dev_diff_t"] >= 2, f"skipped average ${r['dev_skipped_avg']:.2f}, kept ${r['dev_kept_avg']:.2f}, t {r['dev_diff_t']:.2f}"),
             ("3. More dollars, higher Sharpe, and above 95% of random filters", r["dev_total_filtered"] >= r["dev_total_unfiltered"] and r["dev_sharpe_filtered"] > r["dev_sharpe_unfiltered"] and r["dev_random_pctile"] >= 0.95,
              f"total ${r['dev_total_filtered']:,.0f} against ${r['dev_total_unfiltered']:,.0f}; Sharpe {r['dev_sharpe_filtered']:.2f} against {r['dev_sharpe_unfiltered']:.2f}; beats {r['dev_random_pctile']:.0%} of random filters"),
             ("4. The same at double cost", r["dev_skipped_avg_2x"] < 0 and r["dev_diff_t_2x"] >= 2 and r["dev_total_filtered_2x"] >= r["dev_total_unfiltered_2x"] and r["dev_sharpe_filtered_2x"] > r["dev_sharpe_unfiltered_2x"] and r["dev_random_pctile_2x"] >= 0.95,
              f"total ${r['dev_total_filtered_2x']:,.0f} against ${r['dev_total_unfiltered_2x']:,.0f}; t {r['dev_diff_t_2x']:.2f}; beats {r['dev_random_pctile_2x']:.0%} of random filters"),
             ("5. 30-day Combine pass rate not lower", r["pass30_filtered"] >= r["pass30_unfiltered"], f"{r['pass30_filtered']:.1%} against {r['pass30_unfiltered']:.1%} (simulated)"),
             ("6. Walk-forward year: kept trades average more than skipped", r["wf_kept_avg"] > r["wf_skipped_avg"], f"kept ${r['wf_kept_avg']:.2f}, skipped ${r['wf_skipped_avg']:.2f}")]
        for name, ok, ev in C:
            crit.append({"id": f"{m}|{name[:2]}", "model": NAMES[m], "key": m, "criterion": name, "result": "PASS" if ok else "FAIL", "evidence": ev})
        crit.append({"id": f"{m}|all", "model": NAMES[m], "key": m, "criterion": "All six", "result": "ADOPT" if all(c[1] for c in C) else "REJECT", "evidence": f"{sum(c[1] for c in C)} of 6 passed"})
    mt = pd.DataFrame(rows); mt.to_csv(OUT / "models.csv", index=False)
    cr = pd.DataFrame(crit); cr.to_csv(OUT / "criteria.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 120)
    print(cr[["model", "criterion", "result", "evidence"]].to_string(index=False))

    # ------------- daily series on high-volatility days (test years + walk-forward year)
    frames = []
    for p in ("dev", "wf"):
        hd = high[p]
        f = pd.DataFrame({"date": hd.strftime("%Y-%m-%d"), "period": p})
        for m in keepers:
            f[f"pnl_{m}"] = (streams[m, p, 1].loc[hd, "net_pts"] * PV).round(2).to_numpy()
            f[f"pnl2x_{m}"] = (streams[m, p, 2].loc[hd, "net_pts"] * PV).round(2).to_numpy()
        f["trades"] = streams["none", p, 1].loc[hd, "round_trips"].astype(int).to_numpy()
        f["trades_kept_cnn"] = streams["cnn", p, 1].loc[hd, "round_trips"].astype(int).to_numpy()
        frames.append(f)
    daily = pd.concat(frames, ignore_index=True)
    for m in keepers:
        daily[f"equity_{m}"] = daily[f"pnl_{m}"].cumsum().round(2)
        daily[f"equity2x_{m}"] = daily[f"pnl2x_{m}"].cumsum().round(2)
        e = daily[f"equity_{m}"]; daily[f"drawdown_{m}"] = (e - e.cummax()).round(2)
    daily["n"] = np.arange(len(daily))
    daily.to_csv(OUT / "daily.csv", index=False)

    # ------------- KPI table: unfiltered against the primary filter
    cols = []
    for lab, m, p, cm in (("dev_base", "none", "dev", 1), ("dev_filter", PRIMARY, "dev", 1), ("dev_base_2x", "none", "dev", 2), ("dev_filter_2x", PRIMARY, "dev", 2), ("wf_base", "none", "wf", 1), ("wf_filter", PRIMARY, "wf", 1)):
        dd = streams[m, p, cm].loc[high[p]]
        tt = sc[keepers[m] & (sc.period == p)].copy()
        if cm == 2:
            tt["net_pts"] = tt["net2_pts"]
        cols.append(kpis(dd, tt, lab)[0])
    kp = cols[0]
    for c in cols[1:]:
        kp = kp.merge(c.drop(columns=["group", "unit"]), on="metric")
    kp["metric"] = kp["metric"].str.replace("all days", "all high-volatility days").str.replace("Trading days in sample", "High-volatility days in sample")
    kp.to_csv(OUT / "kpis.csv", index=False)

    # ------------- by year
    yr = []
    for p in ("dev", "wf"):
        for y in sorted(set(high[p].year)):
            hd = high[p][high[p].year == y]
            r = {"id": f"{y}|{p}", "year": y, "period": p, "days": len(hd)}
            for m in keepers:
                u = streams[m, p, 1].loc[hd, "net_pts"] * PV
                r[f"pnl_{m}"] = u.sum(); r[f"sharpe_{m}"] = sharpe(u)
            t = sc[(sc.period == p) & (sc["day"].dt.year == y)]
            r["trades"] = len(t); r["skipped_cnn"] = int((~keepers["cnn"][t.index]).sum())
            r["auc_cnn"] = roc_auc_score(t.win, t["score_cnn"]) if 0 < t.win.mean() < 1 else np.nan
            r["auc_boosted"] = roc_auc_score(t.win, t["score_boosted"]) if 0 < t.win.mean() < 1 else np.nan
            yr.append(r)
    pd.DataFrame(yr).to_csv(OUT / "yearly.csv", index=False)

    # ------------- score fifths: does a higher score mean a better trade?
    rows = []
    for m in MODELS:
        for p in ("dev", "wf"):
            t = sc[sc.period == p]
            q = pd.qcut(t[f"score_{m}"].rank(method="first"), 5, labels=["Lowest fifth", "2nd", "3rd", "4th", "Highest fifth"])
            for i, (lab, g) in enumerate(t.groupby(q, observed=True)):
                rows.append({"id": f"{m}|{lab}|{p}", "model": NAMES[m], "key": m, "period": p, "fifth": lab, "order": i, "n": len(g), "win_rate": g.win.mean(), "avg_usd": g.net_pts.mean() * PV,
                             "total_usd": g.net_pts.sum() * PV, "avg_win": g.net_pts[g.win == 1].mean() * PV, "avg_loss": g.net_pts[g.win == 0].mean() * PV})
    pd.DataFrame(rows).to_csv(OUT / "score_fifths.csv", index=False)

    # ------------- kept against skipped, by the usual cuts (primary model)
    t = sc.copy(); t["u"] = t["net_pts"] * PV; t["grp"] = np.where(keepers[PRIMARY], "Kept", "Skipped") + np.where(t.period == "dev", ", test years", ", walk-forward")
    et = t["ct_minute"] + 60
    t["entry_time"] = (et // 60).astype(str) + ":" + (et % 60).astype(str).str.zfill(2)
    B = [bucket_stats(t.u, np.where(t["dir"] > 0, "Long", "Short"), "Direction", ["Long", "Short"], t.grp),
         bucket_stats(t.u, t.entry_time, "Entry time (New York time)", sorted(t.entry_time.unique(), key=lambda s: int(s.split(":")[0]) * 60 + int(s.split(":")[1])), t.grp),
         bucket_stats(t.u, t["exit_reason"].map({"stop": "Back inside the band", "flip": "Reversed to the other side", "session_end": "Held to the close"}), "How the trade ended", ["Held to the close", "Back inside the band", "Reversed to the other side"], t.grp),
         bucket_stats(t.u, "lookback " + t["lookback"].astype(str) + ", width " + t["vm"].astype(str), "Setting", [f"lookback {lb}, width {vm}" for lb in (7, 14, 28) for vm in (0.8, 1.0, 1.2)], t.grp),
         bucket_stats(t.u, t["day"].dt.year.astype(str), "Year", sorted(t["day"].dt.year.astype(str).unique()), t.grp),
         bucket_stats(t.u, np.where(t.win == 1, "Winners", "Losers"), "Winners and losers", ["Winners", "Losers"], t.grp)]
    br = pd.concat(B, ignore_index=True).rename(columns={"period": "group"})
    br["id"] = br["dimension"] + "|" + br["bucket"] + "|" + br["group"]
    br.to_csv(OUT / "breakdowns.csv", index=False)

    # ------------- histograms of the daily result, unfiltered against filtered
    H = []
    edges = np.arange(-3000, 3001, 250.0)
    for p in ("dev", "wf"):
        for m in ("none", PRIMARY):
            x = (streams[m, p, 1].loc[high[p], "net_pts"] * PV); x = x[streams["none", p, 1].loc[high[p], "round_trips"] > 0]
            c, _ = np.histogram(np.clip(x, edges[0], edges[-1] - 1e-9), edges)
            for i, n in enumerate(c):
                H.append({"period": p, "variant": NAMES[m], "lo": edges[i], "hi": edges[i + 1], "count": int(n), "share": n / max(len(x), 1)})
    pd.DataFrame(H).to_csv(OUT / "histograms.csv", index=False)

    # ------------- Monte Carlo: calendar of test years (days outside the regime are days without a trade)
    rows = []
    grid = {"50K": [3, 6, 9, 12, 18, 27], "100K": [9, 18, 27, 36, 54], "150K": [9, 18, 27, 36, 54, 81]}
    base_n = {"50K": 9, "100K": 18, "150K": 27}
    for size, ns in grid.items():
        for m in keepers:
            for src, p, cm in (("Test years 2016 to Oct 2024 (out-of-fold)", "dev", 1), ("Test years at double cost", "dev", 2), ("Walk-forward year (seen before)", "wf", 1)):
                for n in ns:
                    if m not in ("none", PRIMARY, "boosted") and n != base_n[size]:
                        continue
                    r = mc_row(streams[m, p, cm], n, size, src)
                    r.update({"variant": NAMES[m], "key": m, "id": f"{size}|{n}|{src}|{m}", "base": int(n == base_n[size])})
                    rows.append(r)
        print("mc", size, flush=True)
    pd.DataFrame(rows).to_csv(OUT / "montecarlo.csv", index=False)
    print(mt.T.round(3).to_string())
    m = pd.DataFrame(rows); print(m[(m.base == 1) & (m.account == "50K")][["variant", "days_from", "pass", "pass_30d", "control_pass_30d", "median_days_to_pass", "profit_per_account"]].round(3).to_string())
    print(kp.round(2).to_string())


if __name__ == "__main__":
    main()
