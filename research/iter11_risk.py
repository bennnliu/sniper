"""Iteration 11, part 2: news filter, entry/exit limits and sizing, scored under Topstep rules with Ben's
profitability measure. NQ signal traded in MNQ, New York session, development period only.

Costs per MNQ round trip: $1.22 fees + 2 ticks slippage ($1.00) = 1.11 points (assumed; NQ spread measured at 2 ticks).
Run: python research/iter11_risk.py [--log]
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
from sniper.data import DEV_END, load_bars  # noqa: E402
from sniper.propscore import score_stream  # noqa: E402
from sniper.session_rule import build_session, run_session  # noqa: E402

MNQ_PV, COST = 2.0, 1.11
FIXED = (2, 3, 5, 8, 10, 15)
RISK = (150, 250, 400, 600)  # vol-scaled: contracts = budget / (expected daily move in $ per MNQ)


def tstat(x):
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std() * np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else float("nan")


def news_sets():
    e = pd.read_csv(ROOT / "calendar_data" / "events.csv", parse_dates=["date"])
    return set(e["date"]), set(e[e["event"] == "FOMC"]["date"])


def variants():
    allnews, fomc = news_sets()
    return {
        "V0 base (frozen rule)": {},
        "V1 skip CPI/NFP/FOMC days": {"skip_days": allnews},
        "V2 skip FOMC days only": {"skip_days": fomc},
        "V3 one entry a day": {"max_entries": 1},
        "V4 two entries a day": {"max_entries": 2},
        "V5 9:00 CT check only": {"last_entry_min": 30},
        "V6 no entries after 11:00 CT": {"last_entry_min": 150},
        "V7 trade stop 0.25 daily moves": {"trade_stop_sigma": 0.25},
        "V8 trade stop 0.40 daily moves": {"trade_stop_sigma": 0.40},
        "V9 session stop 0.30 daily moves": {"session_stop_sigma": 0.30},
        "V10 session stop 0.50 daily moves": {"session_stop_sigma": 0.50},
        "V11 long only": {"allow_short": False},
        "V12 skip news + one entry": {"skip_days": allnews, "max_entries": 1},
        "V13 skip news + one entry + session stop 0.50": {"skip_days": allnews, "max_entries": 1, "session_stop_sigma": 0.50},
    }


def evaluate(dd, size="50K", sizings=None):
    """dd: daily frame from run_session (points per MNQ, net of costs). Returns stats and the scored sizings."""
    d = dd[dd["dvol_pts"].notna()]
    traded = (d["round_trips"] > 0).to_numpy()
    vu = (d["net_pts"] / d["dvol_pts"])[traded]
    usd1 = d["net_pts"].to_numpy() * MNQ_PV
    mae1 = d["mae_pts"].to_numpy() * MNQ_PV
    dv = d["dvol_pts"].to_numpy() * MNQ_PV
    yr = pd.Series(usd1[traded], index=d.index[traded]).groupby(d.index[traded].year).mean()
    st = {"days": int(len(d)), "traded": int(traded.sum()), "usd_per_mnq_day": float(usd1[traded].mean()), "t_vol_units": tstat(vu),
          "t_usd": tstat(usd1[traded]), "hit": float((usd1[traded] > 0).mean()), "years_pos": float((yr > 0).mean()),
          "worst_day_vol": float((d["net_pts"] / d["dvol_pts"]).min()), "p01_day_vol": float(vu.quantile(0.01))}
    rows = []
    for name, n in ([(f"{k} MNQ", np.full(len(d), k)) for k in FIXED] +
                    [(f"vol-scaled ${r}", np.clip(np.round(r / dv), 1, 50)) for r in RISK]):
        if sizings and name not in sizings:
            continue
        s = score_stream(usd1 * n, mae1 * n, traded, size)
        s.update(sizing=name, avg_contracts=float(n[traded].mean()), win_days_150=float((usd1 * n >= 150)[traded].mean()))
        rows.append(s)
    return st, rows


def best(rows):
    ok = [r for r in rows if r["within_30_days"]]
    return max(ok or rows, key=lambda r: r["score"]), bool(ok)


def main():
    df = load_bars("NQ", end=str(DEV_END.date()))
    bad = set(json.loads((ROOT / "data/degraded_days.json").read_text()))
    df = df[~df["trading_day"].astype(str).isin(bad)]
    sd = build_session(df, "NY")
    out = {}
    for name, kw in variants().items():
        tr, dd = run_session(sd, COST, **kw)
        st, rows = evaluate(dd)
        b, ok = best(rows)
        out[name] = {"stats": st, "sizings": rows, "best": b, "best_within_30": ok}
        print(f"{name:46s} n {st['traded']:4d} $/MNQ/day {st['usd_per_mnq_day']:6.2f} t(vu) {st['t_vol_units']:5.2f} hit {st['hit']:.2f} "
              f"worst {st['worst_day_vol']:.2f} | best {b['sizing']:>16s}: pass {b['pass']:.1%} days {b['days_to_pass']:.0f} accts {b['accounts_needed']:.1f} "
              f"payout ${b['payout']:.0f} score {b['score'] * 1000:.2f} EV ${b['ev_per_attempt']:.0f}{'' if ok else '  (none within 30 days)'}")
    (ROOT / "reports" / "iter_11_risk.json").write_text(json.dumps(out, indent=1, default=float))
    if "--log" in sys.argv:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
        rows = list(csv.DictReader((ROOT / "experiments.csv").open()))
        total = int(rows[-1]["trials_total"])
        with (ROOT / "experiments.csv").open("a", newline="") as fh:
            w = csv.writer(fh)
            for name, o in out.items():
                total += 1
                b = o["best"]
                w.writerow([f"it11-NOISE-NQ-NY-{name.split()[0]}", date.today().isoformat(), commit, "iter11", 1, total,
                            f"{name}: t(vu) {o['stats']['t_vol_units']:.2f}; best {b['sizing']} pass {b['pass']:.1%} in {b['days_to_pass']:.0f}d, score x1000 {b['score'] * 1000:.2f}"])
        print("trials total", total)


if __name__ == "__main__":
    main()
