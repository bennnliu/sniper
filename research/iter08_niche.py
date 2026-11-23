"""Iteration 8: niche features from the 2024+ literature pass (development period only).

EOD-01    prior close -> 14:00 CT return predicts 14:30-15:00 CT (-)                      [BDS2023]
IMOM-07   first 30 min predicts last 30 min when |prior close -> 14:30| > 1 daily sigma (+) [GTBR2024]
OD-01     1:00-2:00 CT return is positive, more after a falling 14:15-15:15 CT (+)        [BLW2022]
REG-01    high gap + high first-30 move + high opening volume -> 9:00-15:00 reverses (-)  [MES2026]
NOISE-01  noise-area breakout at half-hour checks continues to the close (+)              [ZAB2025]
          A: first breakout held to 15:00 CT.  B: the paper's rule (band or VWAP trailing stop).

Run: python research/iter08_niche.py [--log]
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
from sniper import features as F  # noqa: E402
from sniper.data import DEV_END, load_bars  # noqa: E402
from sniper.signal import passes_stage1, signal_test  # noqa: E402

TICK = 0.25
PV = {"ES": 50.0, "NQ": 20.0}
COST_PTS = {"ES": 1.30 * TICK, "NQ": 2.76 * TICK}  # assumed all-in round trip, METHOD.md section 4


def tstat(x):
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std() * np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else float("nan")


def slices(p):
    year = pd.Series(pd.DatetimeIndex(p.index).year, index=p.index)
    terc = pd.qcut(p["rv20"], 3, labels=["low", "mid", "high"]).astype(object)
    return {"year": year, "vol_tercile": terc}


def dollars(sym, pts):
    """Per-trade summary of a points series (already signed), with assumed costs at 1x and 2x."""
    pts = pd.Series(pts).dropna()
    usd = pts * PV[sym]
    c = COST_PTS[sym] * PV[sym]
    yr = (usd - c).groupby(pd.DatetimeIndex(usd.index).year).mean()
    return {"n": int(len(pts)), "mean_pts": float(pts.mean()), "x_cost": float(pts.mean() / COST_PTS[sym]),
            "usd_net": float((usd - c).mean()), "usd_net_2x": float((usd - 2 * c).mean()),
            "t_dollar": tstat(usd - c), "t_gross": tstat(usd), "hit": float((pts > 0).mean()),
            "years_pos": float((yr > 0).mean())}


def ic_test(fid, sym, feat, target, pts, sign, p):
    k = feat.notna() & target.notna()
    rep = signal_test(feat[k], pd.DataFrame({"h": target[k]}), horizon_bars={"h": 1},
                      slices={n: s[k] for n, s in slices(p).items()}, name=f"{fid}:{sym}")
    ok, why = passes_stage1(rep, sign)
    b = rep.best(sign)
    ys = [v["h"] for v in rep.slices["year"].values() if np.isfinite(v["h"])]
    rule = dollars(sym, (sign * np.sign(feat[k]) * pts[k]))
    return {"feature": fid, "symbol": sym, "kind": "ic", "n": int(b.n), "ic": float(b.ic), "t": float(b.t),
            "years_right": float(np.mean(np.sign(ys) == sign)), "stage1": bool(ok), "why": why, "rule": rule}


def noise(sym, df, p):
    ub, lb = F.noise_bands(p)
    vw = F.session_vwap(df, p.index)
    px = p[F.CHECKS]
    sig = pd.DataFrame(np.where(px > ub, 1, np.where(px < lb, -1, 0)), index=p.index, columns=F.CHECKS).where(ub.notna())
    ok = ub[540].notna() & p["prev_close"].notna()
    a, b, ntr = {}, {}, []
    half = COST_PTS[sym] / 2
    for d in p.index[ok]:
        s, x, u, l, v = sig.loc[d].to_numpy(), px.loc[d].to_numpy(), ub.loc[d].to_numpy(), lb.loc[d].to_numpy(), vw.loc[d].to_numpy()
        close = p.at[d, 900]
        nz = np.nonzero(s)[0]
        if nz.size:  # A: first breakout, hold to the close
            a[d] = s[nz[0]] * (close - x[nz[0]])
        pos, pnl, trades = 0, 0.0, 0  # B: the paper's rule, evaluated only at the half-hour checks
        for i in range(len(x)):
            new = pos
            if s[i] != 0:
                new = int(s[i])
            elif pos == 1 and x[i] < max(u[i], v[i]):
                new = 0
            elif pos == -1 and x[i] > min(l[i], v[i]):
                new = 0
            if pos == 1 and s[i] == 1 and x[i] < v[i]:
                new = 0
            if pos == -1 and s[i] == -1 and x[i] > v[i]:
                new = 0
            nxt = x[i + 1] if i + 1 < len(x) else close
            trades += abs(new - pos)
            pnl += new * (nxt - x[i])
            pos = new
        trades += abs(pos)
        if trades:
            b[d] = pnl - trades * half + COST_PTS[sym]  # dollars() subtracts one round trip; keep the rest here
            ntr.append(trades / 2)
    ra = dollars(sym, pd.Series(a))
    rb = dollars(sym, pd.Series(b))
    rb["round_trips_per_day"] = float(np.mean(ntr))
    share = float(len(a) / ok.sum())
    return [{"feature": "NOISE-01A", "symbol": sym, "kind": "rule", "days_tested": int(ok.sum()), "breakout_share": share, "rule": ra,
             "stage1": bool(ra["t_gross"] >= 3)},
            {"feature": "NOISE-01B", "symbol": sym, "kind": "rule", "days_tested": int(ok.sum()), "rule": rb,
             "stage1": bool(rb["t_dollar"] >= 3)}]


def run(sym):
    df = load_bars(sym, end=str(DEV_END.date()))
    bad = set(json.loads((ROOT / "data/degraded_days.json").read_text()))
    df = df[~df["trading_day"].astype(str).isin(bad)]
    p = F.day_grid(df)
    out = []
    last30 = np.log(p[900] / p[870])
    last30_pts = p[900] - p[870]
    # EOD-01
    r = ic_test("EOD-01", sym, F.eod_reversal(p), last30, last30_pts, -1, p)
    neg = F.eod_reversal(p).where(F.eod_reversal(p) < 0)
    k = neg.notna() & last30.notna()
    r["down_days"] = {"n": int(k.sum()), "ic": float(neg[k].rank().corr(last30[k].rank())),
                      "rule": dollars(sym, last30_pts[k])}  # buy the last half hour after a down day
    out.append(r)
    # IMOM-07
    out.append(ic_test("IMOM-07", sym, F.gtbr_first30(p), last30, last30_pts, +1, p))
    # OD-01
    od_pts = p[120] - p[60]
    od = np.log(p[120] / p[60]) * 1e4
    cond = F.overnight_drift_condition(p)
    yr = od.groupby(pd.DatetimeIndex(od.index).year).mean()
    out.append({"feature": "OD-01", "symbol": sym, "kind": "mean", "n": int(od.notna().sum()), "mean_bp": float(od.mean()),
                "t": tstat(od), "years_pos": float((yr > 0).mean()), "rule": dollars(sym, od_pts),
                "after_falling_close": {"mean_bp": float(od[cond < 0].mean()), "t": tstat(od[cond < 0]),
                                        "rule": dollars(sym, od_pts[cond < 0])},
                "after_rising_close": {"mean_bp": float(od[cond > 0].mean()), "t": tstat(od[cond > 0])},
                "since_2019": {"mean_bp": float(od[od.index >= "2019"].mean()), "t": tstat(od[od.index >= "2019"])},
                "stage1": bool(tstat(od) >= 3)})
    # REG-01
    reg = F.opening_regime(df, p).reindex(p.index).fillna(False)
    rev_pts = (-np.sign(p[540] - p[510]) * (p[900] - p[540]))[reg]
    rr = dollars(sym, rev_pts)
    out.append({"feature": "REG-01", "symbol": sym, "kind": "rule", "regime_days": int(reg.sum()), "share": float(reg.mean()),
                "rule": rr, "stage1": bool(rr["t_gross"] >= 3)})
    out += noise(sym, df, p)
    return out


def headline(r):
    ru = r.get("rule", {})
    tail = f"net ${ru.get('usd_net', float('nan')):+.0f}/trade, t$ {ru.get('t_dollar', float('nan')):+.2f}, {ru.get('x_cost', float('nan')):.2f}x cost"
    if r["kind"] == "ic":
        return f"IC {r['ic']:+.3f} t {r['t']:+.2f} n {r['n']} -> {'PASS' if r['stage1'] else 'FAIL'}; {tail}"
    if r["kind"] == "mean":
        return f"mean {r['mean_bp']:+.2f} bp t {r['t']:+.2f} n {r['n']}; {tail}"
    return f"n {ru['n']}; {tail}"


def main():
    results = []
    for sym in ("ES", "NQ"):
        results += run(sym)
    for r in results:
        print(r["feature"], r["symbol"], "|", headline(r))
    print(json.dumps(results, default=float)[:0])
    if "--log" in sys.argv:
        (ROOT / "reports" / "iter_08_niche.json").write_text(json.dumps(results, indent=1, default=float))
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
        rows = list(csv.DictReader((ROOT / "experiments.csv").open()))
        total = int(rows[-1]["trials_total"])
        with (ROOT / "experiments.csv").open("a", newline="") as fh:
            w = csv.writer(fh)
            for r in results:
                total += 1
                w.writerow([f"it08-{r['feature']}-{r['symbol']}", date.today().isoformat(), commit, "iter08", 1, total, headline(r)])
        print("trials total", total)
    return results


if __name__ == "__main__":
    main()
