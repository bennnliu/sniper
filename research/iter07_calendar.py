"""Iteration 7: event and calendar tests on 1-minute bars (development period only).

CAL-01  return from 8:30 CT to 12:55 CT on scheduled FOMC days (statement at 13:00 CT from March 2013) (+)
CAL-02  do CPI / payrolls / FOMC days differ in volatility, and does the MR-04 reversal behave differently?
CAL-05  continuation of the first reaction: 7:30-8:30 CT move on CPI and payrolls days -> 8:30-15:00 CT;
        13:00-13:30 CT move on FOMC days -> 13:30-15:00 CT (+)

Dates: calendar_data/events.csv. FOMC dates for 2021-2023 and Sep 2024 are marked unverified; the headline
uses verified dates only and the all-dates figure is shown beside it.
Run: python research/iter07_calendar.py [--log]
"""
import csv
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from sniper.data import DEV_END, load_bars, pivot_times  # noqa: E402

TICK = 0.25
PV = {"ES": 50.0, "NQ": 20.0}
COST_PTS = {"ES": 1.30 * TICK, "NQ": 2.76 * TICK}
FOMC_1PM_FROM = pd.Timestamp("2013-03-01").date()


def tstat(x):
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std() * np.sqrt(len(x))) if len(x) > 2 else float("nan")


def events():
    e = pd.read_csv(ROOT / "calendar_data" / "events.csv", parse_dates=["date"])
    e["date"] = e["date"].dt.date
    return e


def day_table(sym):
    df = load_bars(sym, end=str(DEV_END.date()))
    bad = set(json.loads((ROOT / "data/degraded_days.json").read_text()))
    df = df[~df["trading_day"].astype(str).isin(bad)]
    p = pivot_times(df, [450, 480, 510, 685, 775, 780, 810, 900])
    p.index = pd.to_datetime(p.index).date
    rth = df[df["rth"]]
    r1 = np.log(rth["close"]).groupby(rth["segment"]).diff()
    p["rv"] = np.sqrt((r1 ** 2).groupby(rth["trading_day"]).sum()).rename(index=lambda d: pd.Timestamp(d).date())
    # MR-04: 5-minute return z-score -> next 5-minute move, in points, fading the move
    r5 = np.log(rth["close"]).groupby(rth["segment"]).diff(5)
    sd = r5.groupby(rth["minute_ct"]).transform(lambda x: x.rolling(20, min_periods=15).std().shift(1))
    z = r5 / sd
    fwd = rth["close"].groupby(rth["segment"]).shift(-5) - rth["close"]
    k = (z.abs() >= 2) & fwd.notna() & (rth["minute_ct"] % 5 == 4) & (rth["minute_ct"] <= 890)
    mr = pd.DataFrame({"day": pd.to_datetime(rth.loc[k, "trading_day"]).dt.date.to_numpy(),
                       "pts": (-np.sign(z[k]) * fwd[k]).to_numpy()})
    return p, mr


def cal01(sym, p, ev):
    f = ev[ev["event"] == "FOMC"]
    ret = np.log(p[775] / p[510]) * 1e4  # basis points, 8:30 -> 12:55 CT
    out = {"feature": "CAL-01", "symbol": sym}
    for label, days in (("verified", f[(f["status"] == "verified")]["date"]), ("all", f["date"])):
        d = [x for x in days if x >= FOMC_1PM_FROM]
        r = ret.reindex(d).dropna()
        r15 = r[[x.year >= 2015 for x in r.index]]
        out[label] = {"n": int(len(r)), "mean_bp": float(r.mean()), "t": tstat(r), "hit": float((r > 0).mean()),
                      "n_2015on": int(len(r15)), "mean_bp_2015on": float(r15.mean()), "t_2015on": tstat(r15)}
    other = ret[~ret.index.isin(set(f["date"]))].dropna()
    other = other[[x >= FOMC_1PM_FROM for x in other.index]]
    out["other_days"] = {"n": int(len(other)), "mean_bp": float(other.mean()), "t": tstat(other)}
    v = ret.reindex([x for x in f[f["status"] == "verified"]["date"] if x >= FOMC_1PM_FROM]).dropna()
    out["diff_t"] = float(stats.ttest_ind(v, other, equal_var=False).statistic)
    pts = (p[775] - p[510]).reindex(v.index).dropna()
    usd = pts * PV[sym] - COST_PTS[sym] * PV[sym]
    out["usd_per_trade_net"] = float(usd.mean())
    out["t_dollar"] = tstat(usd)
    early = np.log(p[685] / p[510]) * 1e4  # 2010-2012, 8:30 -> 11:25 CT, before any statement time
    e = early.reindex([x for x in f["date"] if x < FOMC_1PM_FROM]).dropna()
    out["pre2013_to_1125"] = {"n": int(len(e)), "mean_bp": float(e.mean()), "t": tstat(e)}
    return out


def cal02(sym, p, mr, ev):
    out = {"feature": "CAL-02", "symbol": sym}
    alld = set(ev["date"])
    base = p[~p.index.isin(alld)]
    for name in ("CPI", "NFP", "FOMC"):
        d = set(ev[ev["event"] == name]["date"])
        if name == "FOMC":
            d = {x for x in d if x >= FOMC_1PM_FROM}
        e = p[p.index.isin(d)]
        a, b = (780, 810) if name == "FOMC" else (450, 480)
        mv_e = (np.log(e[b] / e[a]).abs() * 1e4).dropna()
        mv_o = (np.log(base[b] / base[a]).abs() * 1e4).dropna()
        m_e, m_o = mr[mr["day"].isin(d)]["pts"], mr[~mr["day"].isin(alld)]["pts"]
        out[name] = {"n_days": int(len(e)),
                     "rv_ratio": float(e["rv"].median() / base["rv"].median()),
                     "rv_mwu_p": float(stats.mannwhitneyu(e["rv"].dropna(), base["rv"].dropna()).pvalue),
                     "window": f"{a // 60}:{a % 60:02d}-{b // 60}:{b % 60:02d} CT",
                     "window_absmove_ratio": float(mv_e.median() / mv_o.median()),
                     "window_absmove_bp_event": float(mv_e.median()), "window_absmove_bp_other": float(mv_o.median()),
                     "mr04_n": int(len(m_e)), "mr04_x_cost_event": float(m_e.mean() / COST_PTS[sym]),
                     "mr04_x_cost_other": float(m_o.mean() / COST_PTS[sym]),
                     "mr04_diff_t": float(stats.ttest_ind(m_e, m_o, equal_var=False).statistic)}
    return out


def cal05(sym, p, ev):
    res = []
    for name in ("CPI", "NFP", "FOMC"):
        f = ev[ev["event"] == name]
        if name == "FOMC":
            f = f[(f["date"] >= FOMC_1PM_FROM) & (f["status"] == "verified")]
            a, b, c = 780, 810, 900
        else:
            a, b, c = 450, 510, 900
        e = p.reindex(list(f["date"])).dropna(subset=[a, b, c])
        x = np.log(e[b] / e[a])
        y = np.log(e[c] / e[b])
        ic, pval = stats.spearmanr(x, y)
        n = len(x)
        t = ic * np.sqrt((n - 2) / (1 - ic ** 2))
        pts = np.sign(x) * (e[c] - e[b])
        usd = pts * PV[sym] - COST_PTS[sym] * PV[sym]
        yrs = pd.Series([d.year for d in e.index], index=e.index)
        ys = [stats.spearmanr(x[yrs == yy], y[yrs == yy])[0] for yy in sorted(yrs.unique()) if (yrs == yy).sum() >= 6]
        res.append({"feature": "CAL-05", "event": name, "symbol": sym, "n": int(n), "ic": float(ic), "t": float(t),
                    "years_pos": float(np.mean(np.array(ys) > 0)) if ys else float("nan"),
                    "mean_pts": float(pts.mean()), "x_cost": float(pts.mean() / COST_PTS[sym]),
                    "usd_net": float(usd.mean()), "t_dollar": tstat(usd), "hit": float((pts > 0).mean()),
                    "stage1": bool(t >= 3 and ic > 0)})
    return res


def main():
    ev = events()
    ev = ev[ev["date"] < DEV_END.date()]
    results = []
    for sym in ("ES", "NQ"):
        p, mr = day_table(sym)
        results.append(cal01(sym, p, ev))
        results.append(cal02(sym, p, mr, ev))
        results += cal05(sym, p, ev)
    for r in results:
        print(json.dumps(r, default=float))
    if "--log" in sys.argv:
        (ROOT / "reports" / "iter_07_calendar.json").write_text(json.dumps(results, indent=1, default=float))
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
        rows = list(csv.DictReader((ROOT / "experiments.csv").open()))
        total = int(rows[-1]["trials_total"])
        with (ROOT / "experiments.csv").open("a", newline="") as fh:
            w = csv.writer(fh)
            for r in results:
                total += 1
                if r["feature"] == "CAL-01":
                    v = r["verified"]
                    head = f"FOMC 8:30-12:55 CT mean {v['mean_bp']:+.1f} bp, t {v['t']:+.2f}, n {v['n']}; t$ {r['t_dollar']:+.2f}"
                    rid = f"it07-CAL-01-{r['symbol']}"
                elif r["feature"] == "CAL-02":
                    head = "; ".join(f"{k} rv x{r[k]['rv_ratio']:.2f}, MR-04 {r[k]['mr04_x_cost_event']:.2f}x cost" for k in ("CPI", "NFP", "FOMC"))
                    rid = f"it07-CAL-02-{r['symbol']}"
                else:
                    head = f"IC {r['ic']:+.3f} t {r['t']:+.2f} n {r['n']} -> {'PASS' if r['stage1'] else 'FAIL'}; t$ {r['t_dollar']:+.2f}"
                    rid = f"it07-CAL-05-{r['event']}-{r['symbol']}"
                w.writerow([rid, date.today().isoformat(), commit, "iter07", 1, total, head])
        print("trials total", total)


if __name__ == "__main__":
    main()
