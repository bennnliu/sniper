"""TIMING-01 (iteration 28): entry and exit timing methods on the unfiltered nine-setting ensemble.
Hypotheses and criteria are in reports/SECOND_EDGE_LOG.md, committed before this file was first run.
Writes reports/timing01/*.csv and data/cache/timing01.pkl. Run: python research/timing01.py
"""
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.dash01_analyze import PV, drawdown, tstat  # noqa: E402
from research.dl01_eval import sharpe  # noqa: E402
from research.iter13_tests import bars, news  # noqa: E402
from sniper.data import WALK_FORWARD_END  # noqa: E402
from sniper.ensemble import SETTINGS, days_from_trades  # noqa: E402
from sniper.session_rule import build_session  # noqa: E402
from sniper.timing import run_flex  # noqa: E402

OUT = ROOT / "reports" / "timing01"
COST = 1.11
DEV_END = pd.Timestamp("2024-11-01"); HALF = pd.Timestamp("2018-01-01")
METHODS = {
    "B0": ("Base rule: half-hour entries and exits", "Base", {}),
    "F1": ("Exits checked every 5 minutes", "Decision frequency", {"exit_step": 5}),
    "F2": ("Exits checked every minute", "Decision frequency", {"exit_step": 1}),
    "F3": ("Entries and exits every 15 minutes", "Decision frequency", {"entry_step": 15, "exit_step": 15}),
    "F4": ("Entries and exits every 5 minutes", "Decision frequency", {"entry_step": 5, "exit_step": 5}),
    "X1": ("Exit on VWAP alone", "Exit level", {"exit_mode": "vwap"}),
    "X2": ("Exit on the band alone", "Exit level", {"exit_mode": "band"}),
    "S1": ("Trailing stop, 0.25 daily moves", "Stops and targets", {"trail_k": 0.25}),
    "S2": ("Trailing stop, 0.5 daily moves", "Stops and targets", {"trail_k": 0.5}),
    "S3": ("Profit target, 1.0 daily move", "Stops and targets", {"target_k": 1.0}),
    "S4": ("Break-even stop after 0.25 daily moves", "Stops and targets", {"breakeven_k": 0.25}),
    "N1": ("Entry confirmed 5 minutes earlier", "Entry timing", {"confirm_lag": 5}),
    "N2": ("Pullback entry at the band", "Entry timing", {"pullback": True}),
    "N3": ("Only in the first half hour's direction", "Entry timing", {"first30": True}),
}


def stats(dd, tt, col):
    u = dd[col] * PV; tr = dd["round_trips"] > 0
    net = tt["net_pts"] if col == "net_pts" else tt["gross_pts"] - 2 * COST
    w, l = net[net > 0] * PV, net[net <= 0] * PV
    return {"days": len(dd), "trades": len(tt), "total": float(u.sum()), "per_day": float(u.mean()), "std_day": float(u.std()), "sharpe": sharpe(u), "t": tstat(u),
            "drawdown": drawdown(u)[1], "worst_day": float(u.min()), "best_day": float(u.max()), "win_days": float((u[tr] > 0).mean()),
            "avg_win_day": float(u[tr & (u > 0)].mean()), "avg_loss_day": float(u[tr & (u <= 0)].mean()),
            "win_trades": float((net > 0).mean()), "avg_win": float(w.mean()), "avg_loss": float(l.mean()), "payoff": float(w.mean() / -l.mean()),
            "profit_factor": float(w.sum() / -l.sum()), "per_trade": float(net.mean() * PV), "avg_open_loss_day": float((dd["mae_pts"][tr] * PV).mean()),
            "worst_open_loss": float((dd["mae_pts"] * PV).min()), "minutes_held": float(tt["minutes_held"].mean()), "held_to_close": float((tt["exit_reason"] == "session_end").mean()),
            "total_gains": float(w.sum()), "total_losses": float(l.sum())}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    skip = news()
    sd = build_session(bars("NQ", WALK_FORWARD_END), "NY")
    alld = pickle.load(open(ROOT / "data/cache/dl01.pkl", "rb"))["days"]
    index = alld.index
    res = {}
    for key, (name, fam, kw) in METHODS.items():
        t0 = time.time()
        tt = pd.concat([run_flex(sd, COST, lookback=lb, vm=vm, skip_days=skip, **kw).assign(lookback=lb, vm=vm) for lb, vm in SETTINGS], ignore_index=True)
        tt = tt[tt["day"].isin(index)].reset_index(drop=True)
        tt["net2_pts"] = tt["gross_pts"] - 2 * COST
        dd = days_from_trades(tt, index, sd.days, sd.px)
        dd["net2_pts"] = days_from_trades(tt, index, sd.days, sd.px, "net2_pts")["net_pts"]
        dd["regime"] = alld["regime"]; dd["dvol_pts"] = alld["dvol_pts"]
        res[key] = (tt, dd)
        print(key, name, len(tt), "trades", round(time.time() - t0), "s", flush=True)
    pickle.dump({"res": res, "px": {"days": sd.days, "px": sd.px}}, open(ROOT / "data/cache/timing01.pkl", "wb"))
    report(res)


def report(res):
    b_t, b_d = res["B0"]
    rows, crit, cuts = [], [], []
    S = {"dev": lambda i: i < DEV_END, "dev_h1": lambda i: i < HALF, "dev_h2": lambda i: (i >= HALF) & (i < DEV_END), "wf": lambda i: i >= DEV_END}
    for key, (name, fam, kw) in METHODS.items():
        tt, dd = res[key]
        r = {"key": key, "method": name, "family": fam}
        for s, f in S.items():
            m = f(dd.index); tm = f(tt["day"])
            for cm, col in ((1, "net_pts"), (2, "net2_pts")):
                st = stats(dd[m], tt[tm], col)
                diff = (dd.loc[m, col] - b_d.loc[m, col]) * PV
                st["diff_t"] = tstat(diff) if diff.std() > 0 else 0.0; st["diff_total"] = float(diff.sum())
                suf = f"{s}" + ("_2x" if cm == 2 else "")
                r.update({f"{suf}_{k}": v for k, v in st.items()})
            for e in ("low", "mid", "high"):
                me = m & (dd["regime"] == e).to_numpy(); u = dd.loc[me, "net_pts"] * PV
                cuts.append({"id": f"{key}|{s}|{e}", "key": key, "method": name, "sample": s, "env": e, "days": int(me.sum()), "total": float(u.sum()), "sharpe": sharpe(u), "std_day": float(u.std()),
                             "worst_day": float(u.min()), "diff_total": float(((dd.loc[me, "net_pts"] - b_d.loc[me, "net_pts"]) * PV).sum())})
        rows.append(r)
    R = pd.DataFrame(rows).set_index("key"); b = R.loc["B0"]
    for key in METHODS:
        if key == "B0":
            continue
        r = R.loc[key]
        C = [("1. Profit not lower", r.dev_total >= b.dev_total, f"${r.dev_total:,.0f} against ${b.dev_total:,.0f}"),
             ("2. Sharpe higher", r.dev_sharpe > b.dev_sharpe, f"{r.dev_sharpe:.2f} against {b.dev_sharpe:.2f}"),
             ("3. Drawdown not deeper", r.dev_drawdown >= b.dev_drawdown, f"${r.dev_drawdown:,.0f} against ${b.dev_drawdown:,.0f}"),
             ("4. Profit and Sharpe hold at double cost", r.dev_2x_total >= b.dev_2x_total and r.dev_2x_sharpe > b.dev_2x_sharpe, f"${r.dev_2x_total:,.0f}, Sharpe {r.dev_2x_sharpe:.2f} against ${b.dev_2x_total:,.0f}, {b.dev_2x_sharpe:.2f}"),
             ("5. Sharpe higher in both halves", r.dev_h1_sharpe > b.dev_h1_sharpe and r.dev_h2_sharpe > b.dev_h2_sharpe, f"to 2017: {r.dev_h1_sharpe:.2f} against {b.dev_h1_sharpe:.2f}; from 2018: {r.dev_h2_sharpe:.2f} against {b.dev_h2_sharpe:.2f}"),
             ("6. Daily difference t of at least 2", r.dev_diff_t >= 2, f"t {r.dev_diff_t:.2f}")]
        n_ok = sum(c[1] for c in C); dev_pass = n_ok == 6
        for cname, ok, ev in C:
            crit.append({"id": f"{key}|{cname[:1]}", "key": key, "method": r.method, "criterion": cname, "result": "PASS" if ok else "FAIL", "evidence": ev})
        wf_ok = bool(r.wf_sharpe >= b.wf_sharpe)
        crit.append({"id": f"{key}|7", "key": key, "method": r.method, "criterion": "7. Walk-forward year: Sharpe not lower", "result": ("PASS" if wf_ok else "FAIL") if dev_pass else "NOT CHECKED",
                     "evidence": f"{r.wf_sharpe:.2f} against {b.wf_sharpe:.2f}" if dev_pass else "development criteria not all met"})
        R.loc[key, "dev_criteria_met"] = n_ok; R.loc[key, "verdict"] = "ADOPT" if dev_pass and wf_ok else "REJECT"
    R.loc["B0", "dev_criteria_met"] = np.nan; R.loc["B0", "verdict"] = "BASE"
    R.reset_index().to_csv(OUT / "methods.csv", index=False); pd.DataFrame(crit).to_csv(OUT / "criteria.csv", index=False); pd.DataFrame(cuts).to_csv(OUT / "by_environment.csv", index=False)
    pd.set_option("display.width", 280); pd.set_option("display.max_columns", 40)
    show = ["method", "dev_trades", "dev_total", "dev_sharpe", "dev_drawdown", "dev_2x_total", "dev_2x_sharpe", "dev_h1_sharpe", "dev_h2_sharpe", "dev_diff_t", "dev_criteria_met", "verdict"]
    print(R[show].round(2).to_string())
    show2 = ["method", "dev_win_trades", "dev_avg_win", "dev_avg_loss", "dev_payoff", "dev_profit_factor", "dev_total_gains", "dev_total_losses", "dev_worst_day", "dev_avg_open_loss_day", "dev_worst_open_loss", "dev_minutes_held", "dev_held_to_close"]
    print(R[show2].round(2).to_string())


if __name__ == "__main__":
    if "--report" in sys.argv:
        report(pickle.load(open(ROOT / "data/cache/timing01.pkl", "rb"))["res"])
    else:
        main()
