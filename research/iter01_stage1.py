"""Iteration 1, stage 1 signal tests on the priority-1 hypotheses.

Development period only (METHOD.md §1). Features are computed from data up to
the feature time; targets start at or after it. Outputs a JSON and a markdown
table in reports/, and appends one row per (feature, symbol) to experiments.csv.

Run: python research/iter01_stage1.py ES NQ
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sniper.data import DEV_END, flag_days, load_bars, pivot_times  # noqa: E402
from sniper.signal import forward_returns, passes_stage1, signal_test  # noqa: E402

SEED = 0
REGISTRY_SIGN = {"IMOM-01": +1, "IMOM-02": +1, "IMOM-03": +1, "IMOM-05": +1, "MR-01": -1, "MR-03": -1}


def daily_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per full trading day with the closes needed by the daily features."""
    days = flag_days(df)
    full = days.index[(~days["half_day"]) & (days["first_rth_minute"] == 510) & (days["last_rth_minute"] == 899)]
    p = pivot_times(df, [510, 515, 540, 600, 870, 900])  # 8:30, 8:35, 9:00, 10:00, 14:30, 15:00 CT
    p = p.loc[p.index.isin(full)].dropna()
    # Same contract across the day, and previous day's 15:00 close from the same contract.
    inst = df[df["rth"]].groupby("trading_day")["instrument_id"].agg(["first", "last"])
    p = p.join(inst)
    p = p[p["first"] == p["last"]]
    p["prev_close"] = p[900].shift(1)
    p["prev_inst"] = p["last"].shift(1)
    same = p["prev_inst"] == p["first"]
    lg = np.log
    out = pd.DataFrame(index=p.index)
    out["r_first30"] = lg(p[540] / p[510])                  # 8:30 -> 9:00
    out["r_overnight_first30"] = lg(p[540] / p["prev_close"]).where(same)
    out["r_rod"] = lg(p[870] / p["prev_close"]).where(same)  # prev 15:00 -> 14:30
    out["r_first5"] = lg(p[515] / p[510])                    # 8:30 -> 8:35
    out["gap"] = lg(p[510] / p["prev_close"]).where(same)    # prev 15:00 -> 8:30
    out["y_last30"] = lg(p[900] / p[870])                    # 14:30 -> 15:00
    out["y_after5"] = lg(p[900] / p[515])                    # 8:35 -> 15:00
    out["y_gap90"] = lg(p[600] / p[510])                     # 8:30 -> 10:00
    out["y_gap30"] = lg(p[540] / p[510])                     # 8:30 -> 9:00
    # Volatility regime from data strictly before the day: trailing 20-day std of
    # close-to-close (15:00) returns, lagged one day.
    cc = lg(p[900] / p["prev_close"]).where(same)
    out["rv20"] = cc.rolling(20, min_periods=15).std().shift(1)
    return out


def slices_for(index: pd.Index, rv: pd.Series) -> dict:
    year = pd.Series(pd.DatetimeIndex(index).year, index=index)
    # Terciles of the lagged volatility measure. Cut points use the whole
    # development period: this only labels slices for the stability check.
    terc = pd.qcut(rv, 3, labels=["low", "mid", "high"])
    return {"year": year, "vol_tercile": terc.astype(object).reindex(index)}


def run_daily(sym: str, df: pd.DataFrame) -> list[dict]:
    t = daily_table(df)
    t = t[t.index < DEV_END.tz_localize(None)]
    res = []
    specs = [
        ("IMOM-01", "r_first30", {"last30": "y_last30"}),
        ("IMOM-02", "r_rod", {"last30": "y_last30"}),
        ("IMOM-03", "r_overnight_first30", {"last30": "y_last30"}),
        ("IMOM-05", "r_first5", {"to_close": "y_after5"}),
        ("MR-03", "gap", {"30m": "y_gap30", "90m": "y_gap90"}),
    ]
    for fid, feat, targets in specs:
        fwd = pd.DataFrame({k: t[v] for k, v in targets.items()})
        rep = signal_test(t[feat], fwd, horizon_bars={k: 1 for k in targets},
                          slices=slices_for(t.index, t["rv20"]), name=f"{fid}:{sym}")
        ok, why = passes_stage1(rep, REGISTRY_SIGN[fid])
        res.append(summarize(fid, sym, rep, ok, why, n_days=len(t)))
    return res


def run_mr01(sym: str, df: pd.DataFrame) -> dict:
    """MR-01: distance from session VWAP in units of trailing average daily range."""
    d = df[df["rth"] & (df.index < DEV_END)].copy()
    days = flag_days(df)
    d = d[d["trading_day"].isin(days.index[~days["half_day"]])]
    tp = (d["high"] + d["low"] + d["close"]) / 3
    pv = (tp * d["volume"]).groupby(d["trading_day"]).cumsum()
    vv = d["volume"].groupby(d["trading_day"]).cumsum()
    vwap = pv / vv
    rng = d.groupby("trading_day").agg(h=("high", "max"), l=("low", "min"))
    adr = (rng["h"] - rng["l"]).rolling(20, min_periods=15).mean().shift(1)  # prior days only
    feat = (d["close"] - vwap) / d["trading_day"].map(adr)
    seg = d["segment"]
    fwd = forward_returns(d["close"], [15, 30, 60], seg)
    # Skip the first 15 minutes (VWAP undefined-ish) and keep one sample every 5 minutes
    # to keep the run light; the t-statistics handle the remaining overlap.
    keep = (d["minute_ct"] >= 525) & (d["minute_ct"] % 5 == 0)
    feat, fwd = feat[keep], fwd[keep]
    rv = d["trading_day"].map(np.log(rng["h"] / rng["l"]).rolling(20, min_periods=15).mean().shift(1))[keep]
    sl = {"year": pd.Series(feat.index.year, index=feat.index),
          "vol_tercile": pd.qcut(rv, 3, labels=["low", "mid", "high"]).astype(object)}
    rep = signal_test(feat, fwd, horizon_bars={15: 3, 30: 6, 60: 12}, slices=sl, name=f"MR-01:{sym}")
    ok, why = passes_stage1(rep, REGISTRY_SIGN["MR-01"])
    return summarize("MR-01", sym, rep, ok, why, n_days=int(d["trading_day"].nunique()))


def summarize(fid, sym, rep, ok, why, n_days) -> dict:
    sign = REGISTRY_SIGN[fid]
    best = rep.best(sign)
    years = rep.slices.get("year", {})
    vols = rep.slices.get("vol_tercile", {})
    h = best.horizon
    return {
        "feature": fid, "symbol": sym, "n_days": n_days,
        "best_horizon": str(h), "ic": round(best.ic, 4), "t": round(best.t, 2),
        "t_nw": round(best.t_nw, 2), "t_nonoverlap": round(best.t_nonoverlap, 2),
        "p_holm": round(rep.p_holm.get(h, float("nan")), 4), "n": best.n,
        "all_horizons": {str(k): {"ic": round(v.ic, 4), "t": round(v.t, 2)} for k, v in rep.horizons.items()},
        "ic_by_year": {str(k): round(v[h], 4) for k, v in years.items()},
        "ic_by_vol": {str(k): round(v[h], 4) for k, v in vols.items()},
        "share_years_right_sign": round(float(np.mean([np.sign(v[h]) == sign for v in years.values()
                                                       if np.isfinite(v[h])])), 2) if years else None,
        "passed": ok, "fail_reasons": why,
    }


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def main(symbols):
    np.random.seed(SEED)
    results = []
    for sym in symbols:
        df = load_bars(sym, end=str(DEV_END.date()))
        results += run_daily(sym, df)
        results.append(run_mr01(sym, df))
    out_json = ROOT / "reports" / "iter_01_stage1.json"
    out_json.parent.mkdir(exist_ok=True)
    prev = json.loads(out_json.read_text()) if out_json.exists() else []
    keyed = {(r["feature"], r["symbol"]): r for r in prev}
    keyed.update({(r["feature"], r["symbol"]): r for r in results})
    out_json.write_text(json.dumps(list(keyed.values()), indent=1, default=str))

    cfg = json.dumps({"script": "iter01_stage1", "symbols": symbols, "dev_end": str(DEV_END), "seed": SEED})
    cfg_hash = hashlib.sha1(cfg.encode()).hexdigest()[:10]
    exp = ROOT / "experiments.csv"
    rows = list(csv.DictReader(exp.open()))
    total = int(rows[-1]["trials_total"]) if rows else 0
    with exp.open("a", newline="") as f:
        w = csv.writer(f)
        for r in results:
            total += 1
            w.writerow([f"it01-{r['feature']}-{r['symbol']}", date.today().isoformat(), git_commit(), cfg_hash, 1, total,
                        f"stage1 {r['feature']} {r['symbol']}: IC {r['ic']} t {r['t']} at {r['best_horizon']} -> "
                        f"{'PASS' if r['passed'] else 'FAIL'}"])
    for r in results:
        print(f"{r['feature']:8s} {r['symbol']}  h={r['best_horizon']:9s} IC={r['ic']:+.4f} t={r['t']:+.2f} "
              f"years-right={r['share_years_right_sign']} vol={r['ic_by_vol']} -> {'PASS' if r['passed'] else 'FAIL'}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["ES"])
