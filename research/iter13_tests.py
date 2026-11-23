"""Iteration 13: PERIOD-01 (same-half-hour continuation), CAL-04 (expiration-day pinning), GOAL-01 (state-dependent sizing).
Hypotheses are in reports/SECOND_EDGE_LOG.md, committed before this ran. Development data only, except the single
walk-forward check of GOAL-01 behind --wf. Run: python research/iter13_tests.py [--wf]
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from sniper.data import DEV_END, WALK_FORWARD_END, load_bars  # noqa: E402
from sniper.montecarlo import block_bootstrap  # noqa: E402
from sniper.rules import load_rules  # noqa: E402
from sniper.session_rule import build_session, run_session  # noqa: E402

MICRO = {"ES": ("MES", 5.0, 0.495), "NQ": ("MNQ", 2.0, 1.11)}


def tstat(x):
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std() * np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else float("nan")


def news():
    return set(pd.read_csv(ROOT / "calendar_data" / "events.csv", parse_dates=["date"])["date"])


def bars(sym, end):
    df = load_bars(sym, end=str(end.date()))
    bad = set(json.loads((ROOT / "data/degraded_days.json").read_text()))
    return df[~df["trading_day"].astype(str).isin(bad)]


def period01(sd, sym, skip):
    name, pv, cost = MICRO[sym]
    k = np.arange(0, sd.n + 1, 30)
    seg = np.diff(sd.px[:, k], axis=1)  # days x intervals, points
    ret = seg / sd.px[:, k[:-1]]
    sig = pd.DataFrame(ret, index=sd.days).rolling(20, min_periods=15).mean().shift(1).to_numpy()
    dvol = np.where(np.isfinite(sd.prev_close), sd.prev_close, sd.px[:, 0]) * sd.rv20
    keep = ~sd.days.isin(list(skip)) & np.isfinite(dvol) & (dvol > 0)
    ics = []
    for i in np.where(keep)[0]:
        if np.isfinite(sig[i]).all():
            ics.append(spearmanr(sig[i], ret[i])[0])
    pos = np.sign(sig)
    net = pos * seg - cost * (pos != 0)
    gross = pos * seg
    day_net = pd.Series(np.nansum(net, axis=1) / dvol, index=sd.days)[keep & np.isfinite(sig).all(axis=1)]
    day_gross = pd.Series(np.nansum(gross, axis=1) / dvol, index=sd.days)[day_net.index]
    yr = day_net.groupby(day_net.index.year).mean()
    g = float(np.nanmean(gross[keep]))
    return {"test": f"PERIOD-01 {sd.name}", "symbol": name, "days": int(len(day_net)), "ic": float(np.nanmean(ics)), "ic_t": tstat(ics),
            "gross_pts_per_trade": g, "gross_x_cost": g / cost, "t_gross": tstat(day_gross), "t_net": tstat(day_net),
            "years_pos": float((yr > 0).mean()), "passes": bool(tstat(day_net) >= 3 and (yr > 0).mean() >= 0.7 and g >= 2 * cost)}


def third_friday(days):
    d = pd.DatetimeIndex(days)
    return (d.dayofweek == 4) & (d.day >= 15) & (d.day <= 21)


def stream(end, skip):
    """Frozen breakout rule, NQ New York, MNQ costs, per MNQ per day in dollars."""
    tr, dd = run_session(build_session(bars("NQ", end), "NY"), 1.11, skip_days=skip)
    dd = dd[dd["dvol_pts"].notna() & (dd["dvol_pts"] > 0)]
    return dd


def simulate(dd, policy, idx, rules, flip=None, size="50K", max_days=30):
    spec = rules.account(size)
    pnl, mae, mfe = dd["net_pts"].to_numpy() * 2, dd["mae_pts"].to_numpy() * 2, dd["mfe_pts"].to_numpy() * 2
    rts = dd["round_trips"].to_numpy()
    cost = rts * 1.11 * 2
    traded, dvol = rts > 0, dd["dvol_pts"].to_numpy() * 2
    n_paths = idx.shape[0]
    start = spec.starting_balance
    b = np.full(n_paths, float(start)); m = np.full(n_paths, float(start - spec.mll))
    best = np.zeros(n_paths); tdays = np.zeros(n_paths, int)
    alive = np.ones(n_paths, bool); passed = np.zeros(n_paths, bool); days = np.full(n_paths, max_days)
    for t in range(max_days):
        d = idx[:, t]
        p, a = pnl[d].copy(), mae[d].copy()
        if flip is not None:  # random-direction control: reverse the gross result on flipped days
            f = flip[:, t]
            p = np.where(f, -(pnl[d] + cost[d]) - cost[d], p)
            a = np.where(f, np.minimum(-mfe[d] - cost[d], 0), a)
        need = np.maximum(np.maximum(spec.profit_target, best / spec.consistency_fraction) - (b - start), 0)
        c = np.clip(np.floor(policy(b - m, need, max_days - t, dvol[d])), 1, 50)
        tr = traded[d] & alive
        hit = tr & (b + a * c <= m + 1e-9)
        b = np.where(hit, m, b)
        ok = tr & ~hit
        b = np.where(ok, b + p * c, b)
        best = np.where(ok, np.maximum(best, p * c), best)
        tdays += ok
        m = np.where(alive & ~hit, np.minimum(np.maximum(m, b - spec.mll), start), m)
        target = np.maximum(spec.profit_target, best / spec.consistency_fraction)
        win = alive & ~hit & (tdays >= spec.min_trading_days) & (b - start >= target - 1e-9)
        passed |= win
        done = hit | win
        days = np.where(done & alive, t + 1, days)
        alive &= ~done
    return float(passed.mean()), float(np.median(days[passed])) if passed.any() else float("nan")


def policies(typ):
    """typ = typical |daily result| per MNQ as a fraction of the expected daily move (from development data)."""
    return {
        "F8 fixed 8 MNQ": lambda cush, need, left, dv: np.full_like(cush, 8.0),
        "C0.75": lambda cush, need, left, dv: 0.75 * cush / dv,
        "C1.25": lambda cush, need, left, dv: 1.25 * cush / dv,
        "B Browne-style": lambda cush, need, left, dv: np.minimum(need / (np.sqrt(left) * typ * dv), 1.5 * cush / dv),
        "CL lock-in": lambda cush, need, left, dv: np.where(need <= 0.25 * 3000, np.minimum(1.0 * cush / dv, np.ceil(need / (typ * dv))), 1.0 * cush / dv),
    }


def goal01(dd, label, typ, rules, n_paths=20000, payout=None):
    rng = np.random.default_rng(1)
    idx = block_bootstrap(len(dd), n_paths, 30, 5, rng)
    flip = rng.random(idx.shape) < 0.5
    spec = rules.account("50K")
    cost = 2 * (spec.combine_monthly_standard + rules.api_monthly)  # 30 trading days span two billing months
    out = []
    for name, pol in policies(typ).items():
        p, dy = simulate(dd, pol, idx, rules)
        pc, _ = simulate(dd, pol, idx, rules, flip=flip)
        r = {"data": label, "policy": name, "pass30": p, "median_days": dy, "control_pass30": pc, "edge_gain": p - pc}
        if payout is not None:
            r["ev_per_attempt"] = p * (payout - spec.activation_fee_standard) - cost
            r["control_ev"] = pc * (payout - spec.activation_fee_standard) - cost
        out.append(r)
        print(f"  {label:4s} {name:16s} pass in 30d {p:6.1%} (median {dy:4.1f} d) | random control {pc:6.1%} | gain {p - pc:+6.1%}"
              + (f" | EV ${r['ev_per_attempt']:+,.0f} (control ${r['control_ev']:+,.0f})" if payout is not None else ""))
    return out


def main():
    skip = news()
    rules = load_rules()
    res = {"period": [], "cal04": {}, "goal": []}
    dev_end = DEV_END.tz_localize(None)
    if "--wf" in sys.argv:
        dd = stream(WALK_FORWARD_END, skip)
        dev, wf = dd[dd.index < dev_end], dd[dd.index >= dev_end]
        typ = float((dev["net_pts"].abs() / dev["dvol_pts"])[dev["round_trips"] > 0].mean())
        res["goal"] = goal01(wf, "WF", typ, rules)
        (ROOT / "reports/iter_13_wf.json").write_text(json.dumps(res, indent=1))
        return
    for sym in ("ES", "NQ"):
        df = bars(sym, DEV_END)
        for w in ("NY", "ASIA", "LONDON"):
            r = period01(build_session(df, w), sym, skip)
            res["period"].append(r)
            print(f"{r['test']:18s} {r['symbol']}: days {r['days']} IC {r['ic']:+.4f} (t {r['ic_t']:+.2f}) gross {r['gross_pts_per_trade']:+.3f} pts/trade "
                  f"({r['gross_x_cost']:+.2f}x cost) t gross {r['t_gross']:+.2f} t net {r['t_net']:+.2f} yrs+ {r['years_pos']:.2f} {'PASS' if r['passes'] else 'FAIL'}")
    # CAL-04: frozen rule, news days kept out, third Fridays vs the rest
    dd = stream(DEV_END, skip)
    d = dd[dd["round_trips"] > 0]
    vu = d["net_pts"] / d["dvol_pts"]
    of = third_friday(d.index)
    fri = (d.index.dayofweek == 4) & ~of
    se = np.sqrt(vu[of].var() / of.sum() + vu[~of].var() / (~of).sum())
    half = d.index < d.index[len(d) // 2]
    res["cal04"] = {"n_opex": int(of.sum()), "mean_opex": float(vu[of].mean()), "mean_other": float(vu[~of].mean()), "mean_other_fridays": float(vu[fri].mean()),
                    "t_diff": float((vu[of].mean() - vu[~of].mean()) / se), "usd_opex": float(d["net_pts"][of].mean() * 2), "usd_other": float(d["net_pts"][~of].mean() * 2),
                    "diff_first_half": float(vu[of & half].mean() - vu[~of & half].mean()), "diff_second_half": float(vu[of & ~half].mean() - vu[~of & ~half].mean())}
    print("CAL-04", json.dumps(res["cal04"]))
    # GOAL-01
    typ = float((d["net_pts"].abs() / d["dvol_pts"]).mean())
    print(f"typical |result| / expected daily move: {typ:.3f}; days {len(dd)}, traded {len(d)}")
    from sniper.propscore import score_stream
    s8 = score_stream(dd["net_pts"].to_numpy() * 2 * 8, dd["mae_pts"].to_numpy() * 2 * 8, (dd["round_trips"] > 0).to_numpy())
    print("fixed 8 MNQ, existing scorer:", {k: round(v, 3) if isinstance(v, float) else v for k, v in s8.items()})
    res["typ"], res["payout"] = typ, s8["payout"]
    res["goal"] = goal01(dd, "DEV", typ, rules, payout=s8["payout"])
    (ROOT / "reports/iter_13.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
