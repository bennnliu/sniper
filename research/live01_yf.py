"""LIVE-01 (trial 227): the frozen final strategy on the most recent days of Yahoo Finance NQ=F data.

Final strategy ("B, loss minimiser", LOSS-01 method C3): the nine-setting NQ noise-area breakout ensemble
(lookback 7/14/28 x band width 0.8/1.0/1.2), checks every 30 minutes from 10:00 to 15:30 ET, VWAP condition,
plus confirmed entry (price already beyond the band 5 minutes before the check), a trailing stop at half an expected
daily move from the trade's best point, and trades only in the direction of the first half hour. Flat 16:00 ET.

Data. Test days: Yahoo 1-minute bars (Yahoo serves only the last ~8 days at 1 minute). Band lookback (up to 28
days) and the 20-day volatility: Yahoo 5-minute bars. Every price the rule reads on a prior day sits on a 5-minute
boundary (checks every 30 minutes, confirmation 5 minutes earlier, the 15:00 CT close), so 5-minute bars give those
prices exactly. The Databento research file is only used to compare the two feeds; no strategy runs on it.

This is a sanity check on live data, not a test: five trading days say nothing statistical.
Run: python research/live01_yf.py [raw_dir]  (raw_dir holds nq_1m.pkl, nq_5m.pkl from yfinance)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from sniper.ensemble import SETTINGS, days_from_trades  # noqa: E402
from sniper.session_rule import SessionData  # noqa: E402
from sniper.timing import run_flex  # noqa: E402

CT = "America/Chicago"
COST = 1.11  # MNQ round trip, points
PV = 2.0  # MNQ dollars per point
S0, N = 510, 390  # NY session 8:30-15:00 CT
FINAL = {"confirm_lag": 5, "first30": True, "trail_k": 0.5}
NEWS_DAYS: set = set()  # Nov 16-20 2026: no CPI (Nov 10), NFP (Nov 6) or FOMC (Dec) per bls.gov / federalreserve.gov
OUT = ROOT / "reports" / "live01"


def flat(df):
    df = df.copy()
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    return df[["Open", "High", "Low", "Close", "Volume"]].rename(columns=str.lower)


def grid(df, step):
    """Per trading day, price/volume/typical price at session minutes 0..N from bars labelled by their start."""
    t = df.index.tz_convert(CT)
    end = t + pd.Timedelta(minutes=step)  # bar end time
    mct = end.hour * 60 + end.minute
    tday = (end + pd.Timedelta(hours=7)).normalize().tz_localize(None)  # 17:00 CT starts the next trading day
    s = mct - S0
    d = df.assign(s=s, day=tday)
    d = d[(d.s >= 0) & (d.s <= N)]
    cols = range(N + 1)
    close = d.pivot_table(index="day", columns="s", values="close", aggfunc="last").reindex(columns=cols)
    vol = d.pivot_table(index="day", columns="s", values="volume", aggfunc="sum").reindex(columns=cols).fillna(0)
    pv = d.assign(pv=(d.high + d.low + d.close) / 3 * d.volume).pivot_table(index="day", columns="s", values="pv", aggfunc="sum").reindex(columns=cols).fillna(0)
    return close, vol, pv, d


def build(c1, c5):
    """SessionData from 5-minute history plus 1-minute test days (1-minute wins where both exist)."""
    close5, vol5, pv5, _ = c5
    close1, vol1, pv1, _ = c1
    full1 = close1.index[close1[0].notna() & close1[N].notna()]
    full5 = close5.index[close5[0].notna() & close5[N].notna()]
    days = sorted(set(full5) | set(full1))
    close = pd.concat([close5.loc[[x for x in days if x not in full1]], close1.loc[[x for x in days if x in full1]]]).sort_index()
    vol = pd.concat([vol5.loc[[x for x in days if x not in full1]], vol1.loc[[x for x in days if x in full1]]]).sort_index()
    pv = pd.concat([pv5.loc[[x for x in days if x not in full1]], pv1.loc[[x for x in days if x in full1]]]).sort_index()
    close = close.ffill(axis=1)
    vol[0], pv[0] = 0.0, 0.0
    cv = vol.cumsum(axis=1).to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        vw = pv.cumsum(axis=1).to_numpy() / cv
    px = close.to_numpy()
    vw = np.where(np.isfinite(vw), vw, px)
    absmove = np.concatenate([np.zeros((len(days), 1)), np.abs(np.diff(px, axis=1)).cumsum(axis=1)], axis=1)
    c15 = close[N]
    prev = c15.shift(1)
    rv = np.log(c15 / c15.shift(1)).rolling(20, min_periods=15).std().shift(1)
    return SessionData("NY", pd.DatetimeIndex(close.index), px, vw, cv, absmove, prev.to_numpy(), rv.to_numpy(), N, S0), set(full1)


def minute_equity(trades, sd, day, col="net_pts"):
    pos_of = {d: i for i, d in enumerate(sd.days)}
    c = sd.px[pos_of[day]]
    eq = np.zeros(N + 1)
    for dr, a, b, ep, net, gross in zip(trades["dir"], trades["fill"], trades["exit_min"], trades["entry_px"], trades[col], trades["gross_pts"]):
        eq[a:b] += dr * (c[a:b] - ep) - (gross - net) / 2
        eq[b:] += net
    return eq


def feed_check(raw1, raw5, dbn):
    """Yahoo against Databento on overlapping minutes, and Yahoo 1m against Yahoo 5m on the test days."""
    out = {}
    y1 = flat(raw1)
    s1 = y1.index.tz_convert(CT)
    rth = (s1.hour * 60 + s1.minute >= S0) & (s1.hour * 60 + s1.minute < S0 + N) & (s1.dayofweek < 5)
    days = pd.Index(s1[rth].normalize().unique())
    exp = len(days) * N
    out["yahoo_1m_rth_minutes"] = int(rth.sum()); out["yahoo_1m_rth_expected"] = int(exp)
    out["yahoo_1m_zero_volume_rth"] = int((y1.volume[rth] == 0).sum())
    out["yahoo_1m_first"] = str(y1.index.min()); out["yahoo_1m_last"] = str(y1.index.max())
    y5 = flat(raw5)
    r5 = y1.close.resample("5min", label="left", closed="left").last().dropna()
    j = pd.concat([r5.rename("from1m"), y5.close.rename("y5")], axis=1, join="inner")
    j = j[j.index.tz_convert(CT).dayofweek < 5]
    out["yahoo_1m_vs_5m_bars"] = int(len(j)); out["yahoo_1m_vs_5m_max_abs_pts"] = float((j.from1m - j.y5).abs().max())
    if dbn is not None:
        import databento as db
        raw = db.DBNStore.from_file(str(dbn)).to_df()
        raw = raw[~raw.index.duplicated(keep="last")].sort_index()
        ids = raw.groupby(raw.index.normalize())["instrument_id"].agg(lambda x: x.value_counts().index[0])
        dc = raw[["close", "instrument_id", "symbol"]] if "symbol" in raw else raw[["close", "instrument_id"]]
        d5 = dc["close"].resample("5min", label="left", closed="left").last()
        y5u = y5.close.copy(); y5u.index = y5u.index.tz_convert("UTC")
        k = pd.concat([d5.rename("dbn"), y5u.rename("yahoo")], axis=1, join="inner").dropna()
        k = k[k.index >= pd.Timestamp("2026-10-01", tz="UTC")]  # after the September roll
        diff = (k.yahoo - k.dbn)
        kc = k.index.tz_convert(CT); krth = (kc.hour * 60 + kc.minute >= S0) & (kc.hour * 60 + kc.minute < S0 + N)
        out["dbn_overlap_5m_bars"] = int(len(k)); out["dbn_overlap_rth_bars"] = int(krth.sum())
        out["dbn_overlap_period"] = f"{k.index.min()} to {k.index.max()}"
        out["dbn_abs_diff_median_pts"] = float(diff.abs().median()); out["dbn_abs_diff_p99_pts"] = float(diff.abs().quantile(0.99))
        out["dbn_abs_diff_rth_median_pts"] = float(diff[krth].abs().median()); out["dbn_exact_match_share"] = float((diff.abs() < 1e-9).mean())
        out["dbn_symbols"] = sorted(map(str, raw["symbol"].unique())) if "symbol" in raw else []
        # timestamp alignment: is Yahoo shifted by one bar against Databento?
        for lag in (-1, 1):
            kk = pd.concat([d5.shift(lag).rename("dbn"), y5u.rename("yahoo")], axis=1, join="inner").dropna()
            kk = kk[kk.index >= pd.Timestamp("2026-10-01", tz="UTC")]
            out[f"dbn_abs_diff_median_if_shift_{lag}"] = float((kk.yahoo - kk.dbn).abs().median())
    return out


def main(raw_dir):
    raw_dir = Path(raw_dir)
    raw1, raw5 = pd.read_pickle(raw_dir / "nq_1m.pkl"), pd.read_pickle(raw_dir / "nq_5m.pkl")
    c1, c5 = grid(flat(raw1), 1), grid(flat(raw5), 5)
    sd, test_days = build(c1, c5)
    test_days = sorted(test_days)
    res = {}
    for label, kw in (("final", FINAL), ("base", {})):
        tt = pd.concat([run_flex(sd, COST, lookback=lb, vm=vm, skip_days=NEWS_DAYS, **kw).assign(lookback=lb, vm=vm) for lb, vm in SETTINGS], ignore_index=True)
        tt = tt[tt["day"].isin(test_days)].reset_index(drop=True)
        tt["net2_pts"] = tt["gross_pts"] - 2 * COST
        dd = days_from_trades(tt, pd.DatetimeIndex(test_days), sd.days, sd.px)
        dd["net2_pts"] = days_from_trades(tt, pd.DatetimeIndex(test_days), sd.days, sd.px, "net2_pts")["net_pts"]
        res[label] = (tt, dd)
    OUT.mkdir(parents=True, exist_ok=True)
    pos_of = {d: i for i, d in enumerate(sd.days)}
    # trade log (final)
    tt, dd = res["final"]
    def clock(day, m):
        return (pd.Timestamp(day).tz_localize(CT) + pd.Timedelta(minutes=S0 + int(m))).tz_convert("America/New_York").strftime("%H:%M")
    tl = tt.assign(date=tt["day"].dt.strftime("%Y-%m-%d"), side=np.where(tt["dir"] > 0, "long", "short"),
                   entry_et=[clock(d, m) for d, m in zip(tt["day"], tt["fill"])], exit_et=[clock(d, m) for d, m in zip(tt["day"], tt["exit_min"])],
                   setting=[f"N{lb} x{vm}" for lb, vm in zip(tt["lookback"], tt["vm"])], net_usd=tt["net_pts"] * PV, net2_usd=tt["net2_pts"] * PV,
                   mae_usd=tt["mae_pts"] * PV, mfe_usd=tt["mfe_pts"] * PV)
    tl[["date", "setting", "side", "entry_et", "exit_et", "entry_px", "exit_px", "gross_pts", "net_usd", "net2_usd", "mae_usd", "mfe_usd", "exit_reason", "minutes_held"]].round(2).to_csv(OUT / "trades.csv", index=False)
    # per day (both rules)
    rows = []
    for day in test_days:
        i = pos_of[day]; c = sd.px[i]
        r = {"date": day.strftime("%Y-%m-%d"), "open": c[0], "close": c[N], "day_move_pts": c[N] - c[0], "first30_pts": c[30] - c[0],
             "expected_move_pts": sd.prev_close[i] * sd.rv20[i]}
        for label, (t, d) in res.items():
            g = t[t["day"] == day]
            r.update({f"{label}_trades": len(g), f"{label}_net_usd": d.loc[day, "net_pts"] * PV, f"{label}_net2_usd": d.loc[day, "net2_pts"] * PV,
                      f"{label}_worst_open_usd": d.loc[day, "mae_pts"] * PV, f"{label}_best_open_usd": d.loc[day, "mfe_pts"] * PV, f"{label}_max_contracts": d.loc[day, "max_pos"]})
        rows.append(r)
    pd.DataFrame(rows).round(2).to_csv(OUT / "days.csv", index=False)
    # minute equity paths (final and base), per day, cumulative
    eq_rows, run = [], {"final": 0.0, "base": 0.0}
    for day in test_days:
        i = pos_of[day]
        eqs = {k: minute_equity(t[t["day"] == day], sd, day) * PV for k, (t, _) in res.items()}
        for m in range(0, N + 1, 5):
            eq_rows.append({"date": day.strftime("%Y-%m-%d"), "et": clock(day, m), "price": sd.px[i, m],
                            "ub14": None, **{f"{k}_day_usd": eqs[k][m] for k in eqs}, **{f"{k}_cum_usd": run[k] + eqs[k][m] for k in eqs}})
        for k in run:
            run[k] += eqs[k][N]
    # bands for the middle setting, for the price chart
    op = sd.px[:, 0]
    move = np.abs(sd.px / op[:, None] - 1)
    sig = pd.DataFrame(move).rolling(14, min_periods=14).mean().shift(1).to_numpy()
    pc = np.where(np.isfinite(sd.prev_close), sd.prev_close, op)
    ub = np.maximum(op, pc)[:, None] * (1 + sig); lb = np.minimum(op, pc)[:, None] * (1 - sig)
    E = pd.DataFrame(eq_rows)
    E["ub14"] = [ub[pos_of[pd.Timestamp(d)], int(j % 79) * 5] for j, d in enumerate(E["date"])]
    E["lb14"] = [lb[pos_of[pd.Timestamp(d)], int(j % 79) * 5] for j, d in enumerate(E["date"])]
    E["vwap"] = [sd.vwap[pos_of[pd.Timestamp(d)], int(j % 79) * 5] for j, d in enumerate(E["date"])]
    E.round(2).to_csv(OUT / "equity.csv", index=False)
    dbn = Path("/mnt/project-files/data/raw/GLBX.MDP3_ohlcv-1m_NQ.v.0_20251101_20261101_HOLDOUT.dbn.zst")
    fc = feed_check(raw1, raw5, dbn if dbn.exists() else None)
    summ = {"trial": 227, "test_days": [d.strftime("%Y-%m-%d") for d in test_days], "history_days_5m": int(len(sd.days) - len(test_days)),
            "first_history_day": sd.days[0].strftime("%Y-%m-%d")}
    for label, (t, d) in res.items():
        u, u2 = d["net_pts"] * PV, d["net2_pts"] * PV
        w = t["net_pts"] > 0
        summ[label] = {"trades": int(len(t)), "net_usd": float(u.sum()), "net2_usd": float(u2.sum()), "win_rate": float(w.mean()) if len(t) else None,
                       "avg_win_usd": float(t.loc[w, "net_pts"].mean() * PV) if w.any() else None, "avg_loss_usd": float(t.loc[~w, "net_pts"].mean() * PV) if (~w).any() else None,
                       "profit_factor": float(t.loc[w, "net_pts"].sum() / -t.loc[~w, "net_pts"].sum()) if (~w).any() and t.loc[~w, "net_pts"].sum() < 0 else None,
                       "worst_day_usd": float(u.min()), "best_day_usd": float(u.max()), "days_150": int((u >= 150).sum()), "worst_open_usd": float(d["mae_pts"].min() * PV),
                       "exit_reasons": t["exit_reason"].value_counts().to_dict()}
    summ["feed"] = fc
    (OUT / "summary.json").write_text(json.dumps(summ, indent=1, default=str))
    # flat tables for the dashboard
    k = []
    for label in ("final", "base"):
        x = summ[label]
        cum = E[f"{label}_cum_usd"]
        breach = E.loc[cum <= -2000, "date"]
        for m, v in (("net_usd", x["net_usd"]), ("net2_usd", x["net2_usd"]), ("trades", x["trades"]), ("win_rate", x["win_rate"]),
                     ("avg_win_usd", x["avg_win_usd"]), ("avg_loss_usd", x["avg_loss_usd"]), ("profit_factor", x["profit_factor"]),
                     ("worst_day_usd", x["worst_day_usd"]), ("best_day_usd", x["best_day_usd"]), ("days_150", x["days_150"]),
                     ("days_traded", int((dd["round_trips"] > 0).sum()) if label == "final" else int((res["base"][1]["round_trips"] > 0).sum())),
                     ("low_point_usd", float(cum.min())), ("combine50_breach_day", breach.iloc[0] if len(breach) else "none")):
            k.append({"key": f"{label}|{m}", "rule": label, "metric": m, "value": v})
    pd.DataFrame(k).to_csv(OUT / "kpis.csv", index=False)
    pd.DataFrame([{"check": a, "value": b} for a, b in fc.items()]).to_csv(OUT / "feed.csv", index=False)
    print(json.dumps(summ, indent=1, default=str))
    print(pd.DataFrame(rows).round(1).to_string())


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/mnt/project-files/data/raw/yfinance")
