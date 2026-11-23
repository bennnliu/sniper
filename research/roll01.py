"""ROLL-01 (iteration 31): does the final rule's record depend on how the NQ series is rolled?

Uses Ben's download of every NQ contract (research/nqall_build.py) to build two continuous series with roll rules
fixed before testing, then runs the frozen final rule (ENS-01 + LOSS-01 C3) and the base rule on each, next to
Databento's own NQ.v.0 series that all earlier iterations used. Development (to 31 Oct 2024) and the walk-forward year
(1 Nov 2024 to 31 Oct 2025) are reported separately. The holdout year is not read.

Roll rules (each chooses one contract per trading day from information known before that day starts):
  CAL  quarterly contract, switching on the trading day that starts 8 calendar days before expiry (CME's usual roll
       Thursday; expiry is the third Friday of Mar/Jun/Sep/Dec).
  VOLP the contract with the most volume on the previous trading day (yesterday's volume leader).
Databento's v.0 chooses the volume leader too, but its exact timing is the vendor's.
Run: python research/roll01.py   (needs data/bars/NQALL_1m.parquet and the two NQ v.0 DBN files)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.dash01_analyze import drawdown, tstat  # noqa: E402
from research.dl01_eval import sharpe  # noqa: E402
from research.sv01 import sim  # noqa: E402
from sniper.data import add_session_columns, dbn_to_bars  # noqa: E402
from sniper.ensemble import SETTINGS, days_from_trades  # noqa: E402
from sniper.session_rule import build_session  # noqa: E402
from sniper.timing import run_flex  # noqa: E402

RAW = Path("/mnt/project-files/data/raw")
OUT = ROOT / "reports" / "roll01"
COST, PV = 1.11, 2.0
DEV_END, WF_END = pd.Timestamp("2024-11-01"), pd.Timestamp("2025-11-01")
SIM_START = pd.Timestamp("2016-01-01")
RULES = {"base": {}, "final": {"confirm_lag": 5, "first30": True, "trail_k": 0.5}}
MONTHS = {3: "H", 6: "M", 9: "U", 12: "Z"}


def third_friday(y, m):
    d = pd.Timestamp(y, m, 1)
    return d + pd.Timedelta(days=(4 - d.dayofweek) % 7 + 14)


def cal_symbol(day):
    """Front quarterly contract for a trading day under the CAL rule."""
    y, m = day.year, day.month
    for k in range(6):
        mm = ((m - 1) // 3 * 3 + 3 + 3 * k - 1) % 12 + 1
        yy = y + ((m - 1) // 3 * 3 + 3 + 3 * k - 1) // 12
        roll = third_friday(yy, mm) - pd.Timedelta(days=8)
        if day < roll:
            return f"NQ{MONTHS[mm]}{yy % 10}", yy
    raise ValueError(day)


def choose(all_df, rule):
    d = add_session_columns(all_df)
    vol = d.groupby(["trading_day", "symbol"])["volume"].sum().unstack()
    days = vol.index
    if rule == "CAL":
        pick = pd.Series([cal_symbol(t)[0] for t in days], index=days)
    else:
        lead = vol.idxmax(axis=1)
        pick = lead.shift(1).dropna()
        # a contract code repeats every 10 years; yesterday's leader is always live today, so the code is unique
    key = pd.MultiIndex.from_arrays([d["trading_day"], d["symbol"]])
    want = pd.MultiIndex.from_arrays([pick.index, pick.values])
    return d[key.isin(want)].copy(), pick


def load_v0():
    files = [RAW / "GLBX.MDP3_ohlcv-1m_NQ.v.0_20100606_20170529_partial.dbn.zst", RAW / "GLBX.MDP3_ohlcv-1m_NQ.v.0_20170529_20251101.dbn.zst"]
    df = dbn_to_bars([str(f) for f in files], "NQ")
    return df[df.index < pd.Timestamp("2025-11-01 05:00", tz="UTC")]


def stats(u):
    return {"total": float(u.sum()), "sharpe": sharpe(u), "t": tstat(u), "drawdown": float(drawdown(u)[1]), "worst_day": float(u.min()),
            "losing_days_sum": float(u[u < 0].sum()), "days": int(len(u)), "share_150": float((u >= 150).mean())}


def run(df, label, skip, bad):
    df = df[~df["trading_day"].astype(str).isin(bad)]
    sd = build_session(df, "NY")
    ok = np.isfinite(sd.prev_close) & np.isfinite(sd.rv20) & (sd.prev_close * sd.rv20 > 0)
    index = sd.days[ok & ~sd.days.isin(list(skip)) & (sd.days >= pd.Timestamp("2010-08-01")) & (sd.days < WF_END)]
    res = {}
    for name, kw in RULES.items():
        tt = pd.concat([run_flex(sd, COST, lookback=lb, vm=vm, skip_days=skip, **kw).assign(lookback=lb, vm=vm) for lb, vm in SETTINGS], ignore_index=True)
        tt = tt[tt["day"].isin(index)].reset_index(drop=True)
        tt["net2_pts"] = tt["gross_pts"] - 2 * COST
        dd = days_from_trades(tt, index, sd.days, sd.px)
        dd["net2_pts"] = days_from_trades(tt, index, sd.days, sd.px, "net2_pts")["net_pts"]
        res[name] = (tt, dd)
        print(label, name, len(tt), "trades", flush=True)
    return sd, res


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    skip = set(pd.read_csv(ROOT / "calendar_data" / "events.csv", parse_dates=["date"])["date"])
    bad = set(json.loads((RAW / "degraded_days.json").read_text()))
    allc = pd.read_parquet(ROOT / "data" / "bars" / "NQALL_1m.parquet")
    v0 = load_v0()
    series = {"V0": v0}
    picks = {}
    for rule in ("CAL", "VOLP"):
        series[rule], picks[rule] = choose(allc, rule)
    # agreement of contract choice with v.0, and of prices on the same contract and minute
    v0day = v0.groupby("trading_day")["instrument_id"].agg(lambda x: x.value_counts().index[0])
    v0sym = allc.drop_duplicates("instrument_id").set_index("instrument_id")["symbol"]
    v0name = v0day.map(v0sym)
    agree = {r: float((picks[r].reindex(v0name.index) == v0name).mean()) for r in picks}
    j = v0[["instrument_id", "close"]].reset_index().merge(allc[["instrument_id", "close"]].reset_index(), on=["ts_event", "instrument_id"], suffixes=("_v0", "_all"))
    price = {"matched_bars": int(len(j)), "v0_bars": int(len(v0)), "identical_close_share": float((j.close_v0 == j.close_all).mean()), "max_abs_diff": float((j.close_v0 - j.close_all).abs().max())}
    rows, combine = [], []
    for label, df in series.items():
        sd, res = run(df, label, skip, bad)
        for name, (tt, dd) in res.items():
            for per, m in (("dev", dd.index < DEV_END), ("wf", dd.index >= DEV_END)):
                for cc, col in (("1x", "net_pts"), ("2x", "net2_pts")):
                    r = {"series": label, "rule": name, "period": per, "cost": cc, "trades": int((tt["day"].isin(dd.index[m])).sum())}
                    r.update(stats(dd.loc[m, col] * PV)); rows.append(r)
            for per, m in (("dev", (dd.index >= SIM_START) & (dd.index < DEV_END)), ("wf", dd.index >= DEV_END)):
                s = sim(dd[m], np.full(int(m.sum()), 9.0), "50K")
                combine.append({"series": label, "rule": name, "period": per, **{k: s[k] for k in ("pass", "pass_30d", "pass_30d_se", "breach", "control_pass_30d", "median_days_to_pass")}})
    R = pd.DataFrame(rows); Cb = pd.DataFrame(combine)
    R.to_csv(OUT / "results.csv", index=False); Cb.to_csv(OUT / "combine.csv", index=False)
    (OUT / "series_check.json").write_text(json.dumps({"contract_agreement_with_v0": agree, "price_check": price,
                                                        "cal_rolls": int((picks["CAL"] != picks["CAL"].shift()).sum() - 1), "volp_rolls": int((picks["VOLP"] != picks["VOLP"].shift()).sum() - 1)}, indent=1))
    pd.set_option("display.width", 250)
    print(json.dumps({"agree": agree, "price": price}, indent=1))
    print(R[R.cost == "1x"].round(2).to_string()); print(R[R.cost == "2x"][["series", "rule", "period", "total", "sharpe", "drawdown"]].round(2).to_string()); print(Cb.round(3).to_string())


if __name__ == "__main__":
    main()
