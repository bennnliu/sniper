"""Iteration 3: stage 1 and 2 on TREND-01, TREND-02, MR-02, MR-04, RV-01.

Development period only. Intraday features are evaluated on day-session bars
(8:30-15:00 CT), sampled every 5 minutes; forward returns never cross a
contract roll or a trading day. Stage 2 uses the METHOD gate: the naive rule's
dollar t-statistic must be >= 3 and its mean must beat 2x assumed cost.

Run: python research/iter03_stage1.py
"""
import csv
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from sniper.data import DEV_END, flag_days, load_bars  # noqa: E402
from sniper.signal import forward_returns, passes_stage1, signal_test  # noqa: E402

PV = {"ES": 50.0, "NQ": 20.0}
COST_PTS = {"ES": 1.30 * 0.25, "NQ": 2.76 * 0.25}  # assumed all-in round trip, minis
SIGN = {"TREND-01": +1, "TREND-02": +1, "MR-02": -1, "MR-04": -1, "RV-01": -1}


def prep(sym):
    df = load_bars(sym, end=str(DEV_END.date()))
    days = flag_days(df)
    full = days.index[~days["half_day"]]
    df = df[df["trading_day"].isin(full)]
    return df


def by_contract(s: pd.Series, inst: pd.Series, fn):
    return s.groupby(inst, group_keys=False).apply(fn)


def features(sym, df):
    c, inst = df["close"], df["instrument_id"]
    out = {}
    # TREND-01: EMA(60) - EMA(240) on 1-minute closes, per contract, in units of 60-bar return std
    ema_f = by_contract(c, inst, lambda x: x.ewm(span=60, adjust=False).mean())
    ema_s = by_contract(c, inst, lambda x: x.ewm(span=240, adjust=False).mean())
    vol = by_contract(np.log(c).diff(), inst, lambda x: x.rolling(240, min_periods=120).std()) * c
    out["TREND-01"] = (ema_f - ema_s) / (vol * np.sqrt(60))
    # TREND-02: close beyond the prior 60-minute high/low -> +1/-1 (0 otherwise)
    hh = by_contract(df["high"], inst, lambda x: x.rolling(60).max().shift(1))
    ll = by_contract(df["low"], inst, lambda x: x.rolling(60).min().shift(1))
    out["TREND-02"] = pd.Series(np.where(c > hh, 1.0, np.where(c < ll, -1.0, 0.0)), index=df.index).where(hh.notna())
    # MR-02: first touch of the overnight high (+1) or low (-1) between 8:30 and 10:00 CT
    on = df[~df["rth"] & (df["minute_ct"] >= 17 * 60) | (~df["rth"] & (df["minute_ct"] < 8 * 60 + 30))]
    onr = on.groupby("trading_day").agg(onh=("high", "max"), onl=("low", "min"))
    d = df.join(onr, on="trading_day")
    win = d["rth"] & (d["minute_ct"] < 600)
    up = win & (d["high"] >= d["onh"])
    dn = win & (d["low"] <= d["onl"])
    first_up = up & (up.groupby(d["trading_day"]).cumsum() == 1)
    first_dn = dn & (dn.groupby(d["trading_day"]).cumsum() == 1)
    out["MR-02"] = pd.Series(np.where(first_up & ~first_dn, 1.0, np.where(first_dn & ~first_up, -1.0, np.nan)), index=df.index)
    # MR-04: 5-minute return scaled by the trailing 20-day std of 5-minute returns at the same minute
    r5 = by_contract(np.log(c), inst, lambda x: x.diff(5))
    key = df["minute_ct"]
    sd = r5.groupby(key, group_keys=False).apply(lambda x: x.rolling(20, min_periods=15).std().shift(1))
    out["MR-04"] = r5 / sd
    return out


def rv01():
    cols = ["close", "instrument_id", "rth", "minute_ct", "trading_day"]
    es = prep("ES")[cols]
    nq = prep("NQ")[["close", "instrument_id"]]
    j = es[es["rth"]].join(nq, rsuffix="_nq", how="inner")
    del es, nq
    seg = (j["instrument_id"].astype(np.int64) * 1_000_003 + j["instrument_id_nq"].astype(np.int64) * 7
           + j["trading_day"].dt.dayofyear + j["trading_day"].dt.year * 400).to_numpy()
    newseg = np.r_[True, seg[1:] != seg[:-1]]
    segid = np.cumsum(newseg)
    pos_in_seg = pd.Series(np.ones(len(j)), index=j.index).groupby(segid).cumsum().to_numpy()
    le, ln = np.log(j["close"]), np.log(j["close_nq"])
    re_ = le.diff().where(~newseg)
    rn = ln.diff().where(~newseg)
    W = 60
    valid = pos_in_seg > W
    beta = (rn.rolling(W, min_periods=30).cov(re_) / re_.rolling(W, min_periods=30).var()).where(valid).shift(1)
    spread = ln - beta.ffill() * le  # level used only within a segment via rolling stats below
    sp_ret = (rn - beta * re_).fillna(0.0)
    cum = pd.Series(sp_ret.to_numpy(), index=j.index).groupby(segid).cumsum()
    z = ((cum - cum.rolling(W, min_periods=30).mean()) / cum.rolling(W, min_periods=30).std()).where(valid)
    fwd = {}
    sid = pd.Series(segid, index=j.index)
    for h in (15, 30, 60):
        same = sid.shift(-h) == sid
        fn = (ln.shift(-h) - ln).where(same)
        fe = (le.shift(-h) - le).where(same)
        fwd[h] = (fn - beta * fe).where(j["minute_ct"] + h <= 900)
    fwd = pd.DataFrame(fwd)
    keep = (j["minute_ct"] >= 540) & (j["minute_ct"] % 5 == 0)
    return z[keep], fwd[keep], j[keep], beta[keep]


def slices(idx, day):
    return {"year": pd.Series(idx.year, index=idx)}


def dollar_rule(feat, fwd_pts, sign, sym, thresh=None):
    """Naive rule: trade in the expected direction when the feature is non-zero
    (discrete) or beyond its 80th/20th percentile (continuous)."""
    f = feat.dropna()
    if thresh:
        hi, lo = f.quantile(0.8), f.quantile(0.2)
        pos = np.where(f >= hi, 1, np.where(f <= lo, -1, 0))
    else:
        pos = np.sign(f.to_numpy())
    pos = pd.Series(pos * sign, index=f.index)
    pnl = (pos * fwd_pts.reindex(f.index)).where(pos != 0).dropna()
    # keep at most one trade per horizon window: sample non-overlapping by day-level aggregation
    daily = pnl.groupby(pnl.index.date).mean()
    t = daily.mean() / daily.std() * np.sqrt(len(daily)) if len(daily) > 2 else np.nan
    return {"trades": int(len(pnl)), "mean_pts": float(pnl.mean()), "cost_pts": COST_PTS[sym],
            "x_cost": float(pnl.mean() / COST_PTS[sym]), "t_daily": float(t), "days": int(len(daily))}


def run_symbol(sym):
    results = []
    df = prep(sym)
    df = df.drop(columns=["ts_ct"])
    feats = features(sym, df)
    rth = df["rth"]
    seg = df["segment"]
    fwd = forward_returns(df["close"], [5, 15, 30, 60], seg)
    for h in fwd.columns:  # no horizon may run past Topstep's 3:10 PM CT flat time
        fwd.loc[df["minute_ct"] + h > 910, h] = np.nan
    keep = rth & (df["minute_ct"] % 5 == 0) & (df["minute_ct"] >= 540)
    for fid, f in feats.items():
        k = keep if fid != "MR-02" else rth
        horizons = {"MR-02": [15, 30], "MR-04": [5, 15], "TREND-01": [30, 60], "TREND-02": [15, 30, 60]}[fid]
        ff, fw = f[k], fwd.loc[k, horizons]
        rep = signal_test(ff, fw, horizon_bars={h: (max(h // 5, 1) if fid != "MR-02" else 1) for h in horizons},
                          slices=slices(ff.index, None), name=f"{fid}:{sym}")
        ok, why = passes_stage1(rep, SIGN[fid])
        best = rep.best(SIGN[fid])
        pts = (df["close"].groupby(seg).shift(-best.horizon) - df["close"]).where(df["minute_ct"] + best.horizon <= 910)[k]
        dr = dollar_rule(ff, pts, SIGN[fid], sym, thresh=fid in ("TREND-01", "MR-04"))
        yrs = rep.slices["year"]
        results.append({"feature": fid, "symbol": sym, "h": best.horizon, "ic": best.ic, "t": best.t,
                        "yrs_right": float(np.mean([np.sign(v[best.horizon]) == SIGN[fid] for v in yrs.values()
                                                    if np.isfinite(v[best.horizon])])),
                        "stage1": ok, "why": why, "dollar": dr})
    return results


def run_rv():
    z, fw, j, beta = rv01()
    rep = signal_test(z, fw, horizon_bars={15: 3, 30: 6, 60: 12}, slices=slices(z.index, None), name="RV-01")
    ok, why = passes_stage1(rep, SIGN["RV-01"])
    best = rep.best(-1)
    spread_usd = fw[best.horizon] * j["close_nq"] * PV["NQ"]  # spread return on one NQ of notional
    f = z.dropna()
    pos = np.where(f >= 2, -1, np.where(f <= -2, 1, 0))
    pnl = (pd.Series(pos, index=f.index) * spread_usd.reindex(f.index))[pos != 0].dropna()
    daily = pnl.groupby(pnl.index.date).mean()
    # assumed cost: one NQ round trip plus the ES hedge (beta x NQ notional / ES notional, ~0.4-0.6 ES)
    cost_usd = COST_PTS["NQ"] * PV["NQ"] + COST_PTS["ES"] * PV["ES"] * 0.5
    return [{"feature": "RV-01", "symbol": "NQ/ES", "h": best.horizon, "ic": best.ic, "t": best.t,
             "yrs_right": float(np.mean([np.sign(v[best.horizon]) == -1 for v in rep.slices["year"].values()
                                         if np.isfinite(v[best.horizon])])),
             "stage1": ok, "why": why,
             "dollar": {"trades": int(len(pnl)), "mean_usd": float(pnl.mean()), "cost_usd": cost_usd,
                        "x_cost": float(pnl.mean() / cost_usd),
                        "t_daily": float(daily.mean() / daily.std() * np.sqrt(len(daily)))}}]


def show(results):
    for r in results:
        d = r["dollar"]
        print(f"{r['feature']:9s} {r['symbol']:6s} h={r['h']:>3} IC={r['ic']:+.4f} t={r['t']:+.2f} yrs={r['yrs_right']:.0%} "
              f"stage1={'PASS' if r['stage1'] else 'fail'} | rule: n={d['trades']} x_cost={d['x_cost']:.2f} t$={d['t_daily']:.2f}")


def log_all():
    results = []
    for part in ("ES", "NQ", "RV"):
        results += json.loads((ROOT / "reports" / f"iter_03_part_{part}.json").read_text())
    (ROOT / "reports" / "iter_03_stage1.json").write_text(json.dumps(results, indent=1, default=float))
    commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    rows = list(csv.DictReader((ROOT / "experiments.csv").open()))
    total = int(rows[-1]["trials_total"])
    with (ROOT / "experiments.csv").open("a", newline="") as fh:
        w = csv.writer(fh)
        for r in results:
            total += 1
            w.writerow([f"it03-{r['feature']}-{r['symbol']}", date.today().isoformat(), commit, "iter03", 1, total,
                        f"stage1 IC {r['ic']:+.4f} t {r['t']:+.2f} h {r['h']} -> {'PASS' if r['stage1'] else 'FAIL'}; "
                        f"rule x_cost {r['dollar']['x_cost']:.2f} t$ {r['dollar']['t_daily']:.2f}"])
    show(results)
    print("trials total", total)


if __name__ == "__main__":
    part = sys.argv[1]
    if part == "log":
        log_all()
    else:
        res = run_rv() if part == "RV" else run_symbol(part)
        (ROOT / "reports" / f"iter_03_part_{part}.json").write_text(json.dumps(res, indent=1, default=float))
        show(res)
