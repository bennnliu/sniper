"""Iteration 11, part 1: trade log, winners vs losers, sessions, news days. Development period only.

Run: python research/iter11_trades.py
Writes reports/trades_noise_NQ_<SESSION>_dev.csv and reports/iter_11_part1.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from sniper.data import DEV_END, load_bars  # noqa: E402
from sniper.session_rule import SESSIONS, build_session, run_session  # noqa: E402

PV, TICK, FEE_PTS = 20.0, 0.25, 3.78 / 20.0
FEATS = ["f_sigma_pct", "f_excess", "f_dist_vwap", "f_move_open", "f_efficiency", "f_relvol", "f_rv20", "f_gap",
         "f_prior_pnl", "f_last30", "f_dow", "check_min", "entry_no", "dir"]


def tstat(x):
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std() * np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else float("nan")


def events():
    e = pd.read_csv(ROOT / "calendar_data" / "events.csv", parse_dates=["date"])
    return {k: set(g["date"]) for k, g in e.groupby("event")}, set(e["date"])


def measured_spread():
    """Median gap (ticks) between buyer- and seller-initiated prices in the 10 s after each fill time, per session."""
    from research.iter05_orderflow import load_trades
    tt = load_trades("NQ")
    tt = tt[tt["instrument_id"] == tt.groupby("instrument_id")["size"].sum().idxmax()]
    ts = tt["ts"].to_numpy()
    price, side = tt["price"].to_numpy(), tt["side"].to_numpy()
    days = pd.DatetimeIndex(pd.to_datetime(ts, utc=True).tz_convert("America/Chicago").normalize().unique())
    out = {}
    for name, (start, end) in SESSIONS.items():
        n = (end - start) % 1440
        vals = []
        for d in days:
            for chk in range(30, n, 30):
                t0 = (d + pd.Timedelta(minutes=(start + chk) % 1440 + 1)).tz_convert("UTC").value
                i, j = np.searchsorted(ts, t0), np.searchsorted(ts, t0 + 10_000_000_000)
                b, s = price[i:j][side[i:j] == b"B"], price[i:j][side[i:j] == b"A"]
                if len(b) >= 2 and len(s) >= 2:
                    vals.append((b.mean() - s.mean()) / TICK)
        v = pd.Series(vals)
        out[name] = {"windows": int(len(v)), "median_ticks": float(v.median()), "mean_ticks": float(v.mean()), "p90_ticks": float(v.quantile(0.9))}
    return out


def summarize(tr, label):
    tr = tr[tr["dvol_pts"].notna()].copy()
    tr["net_vol"] = tr["net_pts"] / tr["dvol_pts"]
    usd = tr["net_pts"] * PV
    by_day = usd.groupby(tr["day"]).sum()
    yr = by_day.groupby(by_day.index.year).mean()
    return {"label": label, "trades": int(len(tr)), "days": int(len(by_day)), "usd_per_trade": float(usd.mean()),
            "usd_per_traded_day": float(by_day.mean()), "t_day_usd": tstat(by_day),
            "t_day_vol_units": tstat(tr.groupby("day")["net_vol"].sum()), "hit": float((usd > 0).mean()),
            "years_pos": float((yr > 0).mean()), "worst_day_usd": float(by_day.min())}


def main():
    df = load_bars("NQ", end=str(DEV_END.date()))
    bad = set(json.loads((ROOT / "data/degraded_days.json").read_text()))
    df = df[~df["trading_day"].astype(str).isin(bad)]
    ev, allnews = events()
    out = {"spread": measured_spread(), "sessions": {}, "features": {}, "extremes": {}}
    print("measured spread (ticks):", json.dumps(out["spread"]))
    for name in SESSIONS:
        sd = build_session(df, name)
        slip = max(2.0, round(out["spread"][name]["median_ticks"], 2)) * TICK  # never below the 2 ticks assumed so far
        cost = FEE_PTS + slip
        tr, dd = run_session(sd, cost)
        tr["news_day"] = tr["day"].isin(allnews)
        for k, s in ev.items():
            tr[f"is_{k}"] = tr["day"].isin(s)
        tr.to_csv(ROOT / "reports" / f"trades_noise_NQ_{name}_dev.csv", index=False)
        tv = tr[tr["dvol_pts"].notna()].copy()
        terc = pd.qcut(tv["f_rv20"], 3, labels=["low", "mid", "high"])
        res = {"cost_pts": cost, "slip_ticks": slip / TICK, "all": summarize(tr, "all"),
               "cost_2x": summarize(tr.assign(net_pts=tr["net_pts"] - cost), "2x cost"),
               "by_vol": {k: summarize(tv[terc == k], k) for k in ("low", "mid", "high")},
               "news_days": summarize(tr[tr["news_day"]], "news days"), "non_news_days": summarize(tr[~tr["news_day"]], "non-news"),
               "by_event": {k: summarize(tr[tr[f"is_{k}"]], k) for k in ev},
               "since_2018": summarize(tr[tr["day"] >= "2018-01-01"], "2018 on"), "before_2018": summarize(tr[tr["day"] < "2018-01-01"], "to 2017")}
        out["sessions"][name] = res
        a = res["all"]
        print(f"\n== {name}: cost {cost:.3f} pts ({slip / TICK:.1f} ticks slip). trades {a['trades']}, $/traded day {a['usd_per_traded_day']:.1f}, "
              f"t$ {a['t_day_usd']:.2f}, t vol-units {a['t_day_vol_units']:.2f}, hit {a['hit']:.2f}, years+ {a['years_pos']:.2f}; 2x cost t$ {res['cost_2x']['t_day_usd']:.2f}")
        for k in ("low", "mid", "high"):
            b = res["by_vol"][k]
            print(f"   vol {k}: $/day {b['usd_per_traded_day']:.1f} t$ {b['t_day_usd']:.2f} t vu {b['t_day_vol_units']:.2f}")
        print(f"   news days: $/day {res['news_days']['usd_per_traded_day']:.1f} (t {res['news_days']['t_day_usd']:.2f}, worst {res['news_days']['worst_day_usd']:.0f}); "
              f"non-news: {res['non_news_days']['usd_per_traded_day']:.1f} (t {res['non_news_days']['t_day_usd']:.2f}, worst {res['non_news_days']['worst_day_usd']:.0f})")
        print("   by event:", {k: (round(v["usd_per_traded_day"], 0), round(v["t_day_usd"], 2), v["days"]) for k, v in res["by_event"].items()})
        print(f"   before 2018 t vu {res['before_2018']['t_day_vol_units']:.2f}; since 2018 t vu {res['since_2018']['t_day_vol_units']:.2f}")
        if name != "NY":
            continue
        # ---- winners vs losers (NY) ----
        tv["net_vol"] = tv["net_pts"] / tv["dvol_pts"]
        tv["win"] = tv["net_pts"] > 0
        rows = {}
        for f in FEATS:
            k = tv[f].notna()
            ic, p = stats.spearmanr(tv.loc[k, f], tv.loc[k, "net_vol"])
            n = k.sum()
            q = pd.qcut(tv.loc[k, f].rank(method="first"), 5, labels=False)
            rows[f] = {"ic": float(ic), "t": float(ic * np.sqrt((n - 2) / (1 - ic ** 2))), "mean_win": float(tv.loc[k & tv["win"], f].mean()),
                       "mean_loss": float(tv.loc[k & ~tv["win"], f].mean()),
                       "quintile_usd": [round(float(v), 0) for v in (tv.loc[k, "net_pts"] * PV).groupby(q).mean()]}
        out["features"] = rows
        print("\n   feature vs trade result (IC, t, mean $ by quintile low->high):")
        for f, r in sorted(rows.items(), key=lambda kv: -abs(kv[1]["t"])):
            print(f"     {f:14s} IC {r['ic']:+.3f} t {r['t']:+.2f}  {r['quintile_usd']}")
        usd = (tv["net_pts"] * PV).sort_values()
        tot = usd.sum()
        cols = ["day", "ct_minute", "dir", "entry_no", "net_pts", "mae_pts", "mfe_pts", "minutes_held", "exit_reason", "f_excess", "f_move_open", "f_rv20", "f_relvol", "news_day"]
        top, bot = tv.loc[usd.index[-20:]], tv.loc[usd.index[:20]]
        ext = {"total_usd": float(tot), "top5pct_share": float(usd[usd >= usd.quantile(0.95)].sum() / tot),
               "bottom5pct_usd": float(usd[usd <= usd.quantile(0.05)].sum()), "without_top20_usd": float(tot - usd.iloc[-20:].sum()),
               "exit_reason": {k: {"n": int(len(g)), "usd": round(float((g["net_pts"] * PV).mean()), 1), "hit": round(float(g["win"].mean()), 2)} for k, g in tv.groupby("exit_reason")},
               "long_short": {str(k): {"n": int(len(g)), "usd": round(float((g["net_pts"] * PV).mean()), 1), "t": round(tstat(g["net_vol"]), 2)} for k, g in tv.groupby("dir")},
               "entry_no": {str(k): {"n": int(len(g)), "usd": round(float((g["net_pts"] * PV).mean()), 1), "t": round(tstat(g["net_vol"]), 2)} for k, g in tv.groupby(tv["entry_no"].clip(upper=3))},
               "by_check": {str(k): {"n": int(len(g)), "usd": round(float((g["net_pts"] * PV).mean()), 1), "t": round(tstat(g["net_vol"]), 2)} for k, g in tv.groupby("ct_minute")},
               "dow": {str(k): {"n": int(len(g)), "usd": round(float((g["net_pts"] * PV).mean()), 1)} for k, g in tv.groupby("f_dow")},
               "top20": json.loads(top[cols].assign(day=top["day"].astype(str)).to_json(orient="records")),
               "bottom20": json.loads(bot[cols].assign(day=bot["day"].astype(str)).to_json(orient="records")),
               "top20_profile": {c: float(top[c].mean()) for c in ["minutes_held", "f_excess", "f_move_open", "f_rv20", "f_relvol", "ct_minute", "entry_no", "news_day"]},
               "bottom20_profile": {c: float(bot[c].mean()) for c in ["minutes_held", "f_excess", "f_move_open", "f_rv20", "f_relvol", "ct_minute", "entry_no", "news_day"]},
               "all_profile": {c: float(tv[c].mean()) for c in ["minutes_held", "f_excess", "f_move_open", "f_rv20", "f_relvol", "ct_minute", "entry_no", "news_day"]},
               "mae_of_winners_median_vol": float((tv.loc[tv["win"], "mae_pts"] / tv.loc[tv["win"], "dvol_pts"]).median()),
               "mae_of_losers_median_vol": float((tv.loc[~tv["win"], "mae_pts"] / tv.loc[~tv["win"], "dvol_pts"]).median()),
               "winners_mae_p10_vol": float((tv.loc[tv["win"], "mae_pts"] / tv.loc[tv["win"], "dvol_pts"]).quantile(0.1))}
        out["extremes"] = ext
        for k in ("total_usd", "top5pct_share", "bottom5pct_usd", "without_top20_usd", "exit_reason", "long_short", "entry_no", "by_check", "dow",
                  "top20_profile", "bottom20_profile", "all_profile", "mae_of_winners_median_vol", "mae_of_losers_median_vol", "winners_mae_p10_vol"):
            print("  ", k, ext[k])
    (ROOT / "reports" / "iter_11_part1.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
