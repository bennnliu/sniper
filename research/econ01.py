"""ECON-01: prop-firm economics of the final rule (ENS-01 + LOSS-01 C3), all three account sizes.

For each size, period and rule: Combine pass rate, funded-account (XFA) payout rate, Combine accounts needed per
funded account that pays at least once, fees per account, dollars paid to the trader, and profit per account and per
trading day. Everything is SIMULATED: 4,000 block-bootstrapped paths of whole days (blocks of 5), up to 400 trading
days each, replayed under topstep_rules.yaml. The random-direction control flips each day's result with probability
one half and pays the same costs. No new strategy variant, so no new trial. The holdout year is not read.

Sizes: 9 / 18 / 27 MNQ (one, two, three sets) on $50K / $100K / $150K, the same proportional sizes as earlier reports.
Costs: Combine subscription + $29 API per 21 trading days (30 calendar days), $149 activation per pass (standard path).
"Trader total" is every payout an XFA makes before it breaches or the 400-day path ends, at the 90% split.
Run: python research/econ01.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.dash01_analyze import NSET, PV, RULES, combine_sim  # noqa: E402
from research.roll01 import RAW, RULES as STRATS, load_v0, run  # noqa: E402
from sniper.montecarlo import DayRecords, block_bootstrap, simulate_xfa  # noqa: E402

OUT = ROOT / "reports" / "econ01"
NP, HORIZON = 4000, 400
DEV_END, SIM_START = pd.Timestamp("2024-11-01"), pd.Timestamp("2016-01-01")
SIZES = {"50K": 9, "100K": 18, "150K": 27}


def econ(dd, n, size, control, seed=0):
    spec = RULES.account(size)
    N = len(dd)
    net, gross = dd["net_pts"].to_numpy(), dd["gross_pts"].to_numpy()
    mae, mfe = dd["mae_pts"].to_numpy(), dd["mfe_pts"].to_numpy()
    cost = gross - net
    # rows N..2N-1 are the same days traded in the opposite direction, paying the same costs
    net2 = np.concatenate([net, -gross - cost]); mae2 = np.concatenate([mae, np.minimum(-mfe - cost, 0)])
    traded = np.tile((dd["round_trips"] > 0).to_numpy(), 2)
    rng = np.random.default_rng(seed)
    idx = block_bootstrap(N, NP, HORIZON, 5, rng)
    if control:
        idx = idx + N * (rng.random(idx.shape) < 0.5)
    k = n / NSET * PV
    z = np.zeros(2 * N)
    passed, breached, days, _ = combine_sim(net2 * k, mae2 * k, z, z, traded, idx, spec)
    fee = RULES.commission_per_side["MNQ"] * 2  # the XFA engine charges this itself; add it back so it is not paid twice
    rec = DayRecords(traded, net2 * PV / NSET + fee, mae2 * PV / NSET + fee / 2, "MNQ")
    idx2 = block_bootstrap(N, NP, HORIZON, 5, np.random.default_rng(seed + 1))
    if control:
        idx2 = idx2 + N * (np.random.default_rng(seed + 2).random(idx2.shape) < 0.5)
    best = None
    for path in ("standard", "consistency"):
        x = simulate_xfa(rec, idx2, n, size, path, RULES)
        if best is None or x.to_trader.mean() > best[1].to_trader.mean():
            best = (path, x)
    path, x = best
    p = float(passed.mean()); q = float(x.first_payout.mean())
    month = spec.combine_monthly_standard + RULES.api_monthly
    fee_acct = float(np.ceil(days / 21).mean() * month)
    act = spec.activation_fee_standard
    trader = float(x.to_trader.mean())  # per funded account, including those that never pay
    days_c = float(days.mean()); days_x = float(x.days_alive.mean())
    profit_acct = p * (trader - act) - fee_acct
    days_acct = days_c + p * days_x
    need = 1 / (p * q) if p * q > 0 else np.inf
    return {"account": size, "contracts": n, "rule": "random direction" if control else "final",
            "combine_pass": p, "combine_pass_se": float(np.sqrt(p * (1 - p) / NP)), "combine_days_mean": days_c,
            "combine_days_to_pass_median": float(np.median(days[passed])) if passed.any() else np.nan,
            "xfa_path": path, "xfa_payout_rate": q, "xfa_payouts_mean": float(x.n_payouts.mean()),
            "xfa_trader_total_mean": trader, "xfa_trader_total_given_paid": float(x.to_trader[x.first_payout].mean()) if q > 0 else np.nan,
            "xfa_days_mean": days_x, "xfa_days_to_first_payout_median": float(np.median(x.days_to_first[x.first_payout])) if q > 0 else np.nan,
            "accounts_per_funded": 1 / p if p > 0 else np.inf, "accounts_per_paying_funded": need,
            "fee_per_account": fee_acct, "activation_fee": act, "cost_per_account_all_in": fee_acct + p * act,
            "payout_per_account": p * trader, "profit_per_account": profit_acct,
            "cost_per_paying_funded": need * (fee_acct + p * act), "payout_per_paying_funded": need * p * trader, "profit_per_paying_funded": need * profit_acct,
            "trading_days_per_account": days_acct, "profit_per_trading_day": profit_acct / days_acct}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    skip = set(pd.read_csv(ROOT / "calendar_data" / "events.csv", parse_dates=["date"])["date"])
    bad = set(json.loads((RAW / "degraded_days.json").read_text()))
    STRATS.pop("base", None)
    _, res = run(load_v0(), "V0", skip, bad)
    dd = res["final"][1]
    per = {"dev (2016 to Oct 2024)": dd[(dd.index >= SIM_START) & (dd.index < DEV_END)], "walk-forward (Nov 2024 to Oct 2025)": dd[dd.index >= DEV_END]}
    rows = []
    for pn, d in per.items():
        for size, n in SIZES.items():
            for control in (False, True):
                rows.append({"period": pn, "days_in_sample": len(d), **econ(d, n, size, control)})
    R = pd.DataFrame(rows); R.to_csv(OUT / "economics.csv", index=False)
    pd.set_option("display.width", 300); pd.set_option("display.max_columns", 40)
    print(R.drop(columns=["period"]).round(2).T.to_string())


if __name__ == "__main__":
    main()
