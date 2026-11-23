"""META-02, step 1: trade table for the losing-trade filter. New York session, nine-setting ensemble, CPI /
payrolls / FOMC days skipped, MNQ costs. Every feature uses only prices and volume known at the decision minute
(the half-hour check); the order fills one minute later. Writes data/cache/dl01.pkl:
  trades  one row per trade with features, label (net_pts > 0) and the volatility regime of its day
  seq     trades x 60 array: the last 60 one-minute price changes before the decision, signed by trade direction
          and divided by the rule's noise width (zeros where the session had not yet opened)
  days    all days (per set) with regime, for the unfiltered benchmark
  px      minute prices by day, to rebuild intraday equity for any subset of trades
"""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.iter13_tests import bars, news  # noqa: E402
from sniper.data import WALK_FORWARD_END  # noqa: E402
from sniper.ensemble import run_ensemble  # noqa: E402
from sniper.session_rule import build_session  # noqa: E402

DEV_END = pd.Timestamp("2024-11-01")
SEQ = 60


def regime_ratio(days):
    return days["dvol_pts"] / days["dvol_pts"].rolling(250, min_periods=60).median().shift(1)


def main():
    skip = news()
    nq, es = bars("NQ", WALK_FORWARD_END), bars("ES", WALK_FORWARD_END)
    sd, se, so = build_session(nq, "NY"), build_session(es, "NY"), build_session(nq, "OVERNIGHT")
    out = {}
    for cost_mult in (1, 2):
        trades, days = run_ensemble(sd, 1.11 * cost_mult, skip)
        out[cost_mult] = (trades, days)
    trades, days = out[1]
    ratio = regime_ratio(days)
    dev = ratio[ratio.index < DEV_END].dropna()
    lo, hi = dev.quantile([1 / 3, 2 / 3])
    days["ratio"] = ratio
    days["regime"] = np.where(ratio.isna(), "unknown", np.where(ratio <= lo, "low", np.where(ratio <= hi, "mid", "high")))
    print("high-volatility cut: expected daily move over its trailing 250-day median >", round(float(hi), 4))

    di = {d: i for i, d in enumerate(sd.days)}
    ei = {d: i for i, d in enumerate(se.days)}
    oi = {d: i for i, d in enumerate(so.days)}
    prev_day = {d: sd.days[i - 1] for i, d in enumerate(sd.days) if i > 0}
    t = trades.copy()
    t["net2_pts"] = out[2][0]["net_pts"].to_numpy()  # same trades at double cost (decisions do not depend on cost)
    assert (out[2][0]["fill"].to_numpy() == t["fill"].to_numpy()).all()
    t["tid"] = np.arange(len(t))
    F = {k: np.full(len(t), np.nan) for k in ("g_dvol_ratio", "g_on_range", "g_on_ret", "g_prev_ret", "g_prev_range", "g_range_sofar", "g_pos_in_range",
                                               "g_first30", "g_vol_last30", "g_es_move", "g_rel_es", "g_last5", "g_pullback60", "g_time_left")}
    seq = np.zeros((len(t), SEQ), dtype=np.float32)
    for j, (day, chk, dr, sp, dv) in enumerate(zip(t["day"], t["check_min"], t["dir"], t["f_sigma_pct"], t["dvol_pts"])):
        i = di[day]; c = sd.px[i]; x = c[chk]; op = c[0]
        sig = op * sp / 100
        F["g_dvol_ratio"][j] = ratio.get(day, np.nan)
        F["g_time_left"][j] = (sd.n - chk) / sd.n
        seg = c[:chk + 1]
        rng = seg.max() - seg.min()
        F["g_range_sofar"][j] = rng / dv
        F["g_pos_in_range"][j] = ((x - seg.min()) if dr > 0 else (seg.max() - x)) / rng if rng > 0 else 0.5
        F["g_first30"][j] = dr * (c[30] - op) / dv
        F["g_last5"][j] = dr * (x - c[chk - 5]) / sig
        w = dr * (c[max(0, chk - 60):chk + 1] - x)  # signed distance of the last hour's prices from the current price
        F["g_pullback60"][j] = float(w.max()) / sig  # how far price was beyond the current price, against the trade
        cv = sd.cumvol[i]
        F["g_vol_last30"][j] = (cv[chk] - cv[chk - 30]) / cv[chk] * (chk / 30) if cv[chk] > 0 else np.nan
        d1 = dr * np.diff(c[max(0, chk - SEQ):chk + 1]) / sig
        seq[j, SEQ - len(d1):] = d1
        if day in ei:
            e = se.px[ei[day]]
            em = e[chk] / e[0] - 1
            F["g_es_move"][j] = dr * em / (sp / 100)
            F["g_rel_es"][j] = dr * ((x / op - 1) - em) / (sp / 100)
        if day in oi:
            o = so.px[oi[day]]
            F["g_on_range"][j] = (o.max() - o.min()) / dv
            F["g_on_ret"][j] = dr * (o[-1] - o[0]) / dv
        p = prev_day.get(day)
        if p is not None and (day - p).days <= 5:
            pc = sd.px[di[p]]
            F["g_prev_ret"][j] = dr * (pc[-1] - pc[0]) / dv
            F["g_prev_range"][j] = (pc.max() - pc.min()) / dv
    for k, v in F.items():
        t[k] = v
    # what the other settings are doing at the decision: already in the same direction, entering now, and the
    # set's closed result so far today
    t["g_others_in"] = 0.0; t["g_enter_now"] = 0.0; t["g_set_pnl"] = 0.0
    for day, g in t.groupby("day"):
        chk, fill, ex, dr, net = (g[c].to_numpy() for c in ("check_min", "fill", "exit_min", "dir", "net_pts"))
        dv = g["dvol_pts"].iloc[0]
        a = np.zeros(len(g)); b = np.zeros(len(g)); pnl = np.zeros(len(g))
        for k in range(len(g)):
            a[k] = ((fill < chk[k]) & (ex > chk[k]) & (dr == dr[k])).sum()
            b[k] = ((chk == chk[k]) & (dr == dr[k])).sum() - 1
            pnl[k] = net[ex <= chk[k]].sum() / dv
        t.loc[g.index, "g_others_in"] = a; t.loc[g.index, "g_enter_now"] = b; t.loc[g.index, "g_set_pnl"] = pnl
    t["regime"] = days["regime"].reindex(t["day"]).to_numpy()
    t["win"] = (t["net_pts"] > 0).astype(int)
    t["period"] = np.where(t["day"] < DEV_END, "dev", "wf")
    days["period"] = np.where(days.index < DEV_END, "dev", "wf")
    pickle.dump({"trades": t, "seq": seq, "days": days, "days2": out[2][1], "px": {"days": sd.days, "px": sd.px, "n": sd.n}, "high_cut": float(hi)},
                open(ROOT / "data/cache/dl01.pkl", "wb"))
    h = t[t.regime == "high"]
    print("trades", len(t), "high-vol trades", len(h), h.groupby("period").size().to_dict(), "win rate high", round(h.win.mean(), 3))
    print(h.groupby(h["day"].dt.year).size().to_dict())


if __name__ == "__main__":
    main()
