"""LOSS-01 (iteration 29): entry and exit methods judged on loss measures first.
Methods and criteria are in reports/SECOND_EDGE_LOG.md, committed before this file was first run.
Writes reports/loss01/*.csv and data/cache/loss01.pkl. Run: python research/loss01.py
The walk-forward year is only computed for methods that meet development criteria 1 to 7.
"""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.dash01_analyze import PV, drawdown, tstat  # noqa: E402
from research.dl01_eval import sharpe  # noqa: E402
from research.iter13_tests import bars, news  # noqa: E402
from research.sv01 import sim  # noqa: E402
from sniper.data import WALK_FORWARD_END  # noqa: E402
from sniper.ensemble import SETTINGS, days_from_trades  # noqa: E402
from sniper.session_rule import build_session  # noqa: E402
from sniper.timing import apply_day_stop, run_flex  # noqa: E402

OUT = ROOT / "reports" / "loss01"
COST = 1.11
DEV_END = pd.Timestamp("2024-11-01"); HALF = pd.Timestamp("2018-01-01"); SIM_START = pd.Timestamp("2016-01-01")
NEW = {
    "C1": ("Confirmed entry + trailing stop 0.5", {"confirm_lag": 5, "trail_k": 0.5}),
    "C2": ("Confirmed entry + first half hour's direction", {"confirm_lag": 5, "first30": True}),
    "C3": ("Confirmed entry + first half hour + trailing stop 0.5", {"confirm_lag": 5, "first30": True, "trail_k": 0.5}),
    "T1": ("Trailing stop, 0.35 daily moves", {"trail_k": 0.35}),
    "T2": ("Trailing stop, 0.75 daily moves", {"trail_k": 0.75}),
    "D1": ("Daily loss stop, 0.5 daily moves", {"day_stop": 0.5}),
    "D2": ("Daily loss stop, 0.75 daily moves", {"day_stop": 0.75}),
    "E1": ("No entries before 10:30 AM ET", {"first_entry_min": 60}),
}
REF = {"B0": "Base rule", "S2": "Trailing stop, 0.5 daily moves (iteration 28)", "N1": "Entry confirmed 5 minutes earlier (iteration 28)", "N3": "First half hour's direction only (iteration 28)"}


def to_days(tt, index, px_days, px, alld):
    tt = tt[tt["day"].isin(index)].reset_index(drop=True)
    tt["net2_pts"] = tt["gross_pts"] - 2 * COST
    dd = days_from_trades(tt, index, px_days, px)
    dd["net2_pts"] = days_from_trades(tt, index, px_days, px, "net2_pts")["net_pts"]
    dd["regime"] = alld["regime"]; dd["dvol_pts"] = alld["dvol_pts"]
    return tt, dd


def loss_stats(dd, col="net_pts"):
    u = dd[col] * PV
    return {"total": float(u.sum()), "sharpe": sharpe(u), "t": tstat(u), "drawdown": drawdown(u)[1], "worst_day": float(u.min()),
            "losing_days_sum": float(u[u < 0].sum()), "losing_days": int((u < 0).sum()), "avg_losing_day": float(u[u < 0].mean()),
            "worst5_avg": float(u.nsmallest(5).mean()), "p1_day": float(u.quantile(0.01)), "winning_days_sum": float(u[u > 0].sum()),
            "std_day": float(u.std()), "worst_open_loss": float((dd["mae_pts"] * PV).min()), "avg_open_loss": float((dd["mae_pts"][dd["round_trips"] > 0] * PV).mean())}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    c = pickle.load(open(ROOT / "data/cache/timing01.pkl", "rb"))
    px_days, px = c["px"]["days"], c["px"]["px"]
    alld = pickle.load(open(ROOT / "data/cache/dl01.pkl", "rb"))["days"]; index = alld.index
    res = {k: c["res"][k] for k in REF}
    cache = ROOT / "data/cache/loss01.pkl"
    if cache.exists():
        res.update(pickle.load(open(cache, "rb")))
    else:
        skip = news(); sd = build_session(bars("NQ", WALK_FORWARD_END), "NY"); new = {}
        for key, (name, kw) in NEW.items():
            if "day_stop" in kw:
                tt = apply_day_stop(c["res"]["B0"][0].drop(columns=["net2_pts"]), px_days, px, kw["day_stop"], COST, n_set=len(SETTINGS))
            else:
                tt = pd.concat([run_flex(sd, COST, lookback=lb, vm=vm, skip_days=skip, **kw).assign(lookback=lb, vm=vm) for lb, vm in SETTINGS], ignore_index=True)
            new[key] = to_days(tt, index, px_days, px, alld)
            print(key, name, len(new[key][0]), "trades", flush=True)
        pickle.dump(new, open(cache, "wb")); res.update(new)
    names = {**REF, **{k: v[0] for k, v in NEW.items()}}
    S = {"dev": lambda i: i < DEV_END, "dev_h1": lambda i: i < HALF, "dev_h2": lambda i: (i >= HALF) & (i < DEV_END)}
    rows = []
    for key in names:
        tt, dd = res[key]
        r = {"key": key, "method": names[key], "fresh_test": key in NEW, "dev_trades": int((tt["day"] < DEV_END).sum())}
        if "exit_reason" in tt:
            r["dev_stopped_days"] = int(tt.loc[(tt["day"] < DEV_END) & (tt["exit_reason"] == "day_stop"), "day"].nunique())
        for s, f in S.items():
            m = f(dd.index)
            r.update({f"{s}_{k}": v for k, v in loss_stats(dd[m]).items()})
            r.update({f"{s}_2x_{k}": v for k, v in loss_stats(dd[m], "net2_pts").items()})
        ms = (dd.index >= SIM_START) & (dd.index < DEV_END)
        sm = sim(dd[ms], np.full(int(ms.sum()), 9.0), "50K")
        r.update({f"c50_{k}": sm[k] for k in ("pass", "pass_30d", "pass_30d_se", "breach", "breach_30d", "control_pass_30d", "median_days_to_pass")})
        rows.append(r)
    R = pd.DataFrame(rows).set_index("key"); b = R.loc["B0"]; crit = []
    for key in names:
        if key == "B0":
            R.loc[key, "verdict"] = "BASE"; continue
        r = R.loc[key]
        dd_cut = 1 - r.dev_drawdown / b.dev_drawdown; ls_cut = 1 - r.dev_losing_days_sum / b.dev_losing_days_sum; dd2_cut = 1 - r.dev_2x_drawdown / b.dev_2x_drawdown
        C = [("1. Worst drawdown at least 15% shallower", dd_cut >= 0.15, f"${r.dev_drawdown:,.0f} against ${b.dev_drawdown:,.0f} ({dd_cut:+.0%})"),
             ("2. Sum of losing days at least 10% smaller", ls_cut >= 0.10, f"${r.dev_losing_days_sum:,.0f} against ${b.dev_losing_days_sum:,.0f} ({ls_cut:+.0%})"),
             ("3. Worst day not worse", r.dev_worst_day >= b.dev_worst_day, f"${r.dev_worst_day:,.0f} against ${b.dev_worst_day:,.0f}"),
             ("4. Profit at least 90% of base and Sharpe higher", r.dev_total >= 0.9 * b.dev_total and r.dev_sharpe > b.dev_sharpe, f"${r.dev_total:,.0f} ({r.dev_total / b.dev_total:.0%} of base), Sharpe {r.dev_sharpe:.2f} against {b.dev_sharpe:.2f}"),
             ("5. Criteria 1 and 4 hold at double cost", dd2_cut >= 0.15 and r.dev_2x_total >= 0.9 * b.dev_2x_total and r.dev_2x_sharpe > b.dev_2x_sharpe,
              f"drawdown ${r.dev_2x_drawdown:,.0f} against ${b.dev_2x_drawdown:,.0f} ({dd2_cut:+.0%}); profit ${r.dev_2x_total:,.0f} against ${b.dev_2x_total:,.0f}; Sharpe {r.dev_2x_sharpe:.2f} against {b.dev_2x_sharpe:.2f}"),
             ("6. Drawdown shallower in both halves", r.dev_h1_drawdown > b.dev_h1_drawdown and r.dev_h2_drawdown > b.dev_h2_drawdown,
              f"to 2017: ${r.dev_h1_drawdown:,.0f} against ${b.dev_h1_drawdown:,.0f}; from 2018: ${r.dev_h2_drawdown:,.0f} against ${b.dev_h2_drawdown:,.0f}"),
             ("7. $50K Combine at 9 MNQ: loss limit hit less often, 30-day pass not lower", r.c50_breach < b.c50_breach and r.c50_pass_30d >= b.c50_pass_30d,
              f"loss limit hit {r.c50_breach:.1%} against {b.c50_breach:.1%}; 30-day pass {r.c50_pass_30d:.1%} against {b.c50_pass_30d:.1%} (simulated)")]
        n_ok = sum(x[1] for x in C); dev_pass = n_ok == 7
        for cn, ok, ev in C:
            crit.append({"id": f"{key}|{cn[:1]}", "key": key, "method": r.method, "criterion": cn, "result": "PASS" if ok else "FAIL", "evidence": ev})
        wf_res, wf_ev = "NOT CHECKED", "development criteria not all met"
        if dev_pass:
            w = loss_stats(res[key][1][res[key][1].index >= DEV_END]); wb = loss_stats(res["B0"][1][res["B0"][1].index >= DEV_END])
            ok = w["drawdown"] >= wb["drawdown"] and w["sharpe"] >= wb["sharpe"]
            wf_res = "PASS" if ok else "FAIL"; wf_ev = f"drawdown ${w['drawdown']:,.0f} against ${wb['drawdown']:,.0f}; Sharpe {w['sharpe']:.2f} against {wb['sharpe']:.2f}; profit ${w['total']:,.0f} against ${wb['total']:,.0f}"
            for k, v in w.items():
                R.loc[key, f"wf_{k}"] = v
        crit.append({"id": f"{key}|8", "key": key, "method": r.method, "criterion": "8. Walk-forward year: drawdown not deeper, Sharpe not lower", "result": wf_res, "evidence": wf_ev})
        R.loc[key, "dev_criteria_met"] = n_ok
        R.loc[key, "verdict"] = ("ADOPT" if wf_res == "PASS" else "REJECT") if key in NEW else ("reference, " + ("all 7 met" if dev_pass else f"{n_ok} of 7"))
    R.reset_index().to_csv(OUT / "methods.csv", index=False); pd.DataFrame(crit).to_csv(OUT / "criteria.csv", index=False)
    pd.set_option("display.width", 300); pd.set_option("display.max_columns", 40); pd.set_option("display.max_colwidth", 200)
    print(R[["method", "dev_trades", "dev_total", "dev_sharpe", "dev_drawdown", "dev_losing_days_sum", "dev_worst_day", "dev_worst5_avg", "dev_2x_total", "dev_2x_drawdown", "dev_criteria_met", "verdict"]].round(2).to_string())
    print(R[["dev_h1_drawdown", "dev_h2_drawdown", "dev_avg_losing_day", "dev_losing_days", "dev_winning_days_sum", "dev_std_day", "c50_pass", "c50_pass_30d", "c50_breach", "c50_breach_30d", "c50_control_pass_30d", "dev_stopped_days"]].round(3).to_string())
    print(pd.DataFrame(crit)[["key", "criterion", "result", "evidence"]].to_string())


if __name__ == "__main__":
    main()
