"""Topstep scoring of a daily dollar P&L stream, including Ben's profitability measure (22 Nov 2026).

score = payout / (cost of an evaluation account x average accounts needed x days required)
  payout            expected dollars paid to the trader from one funded account (better of the two payout paths)
  cost of account   Combine subscription paid during one attempt (monthly fee x months the attempt lasts) + API fee
  accounts needed   1 / Combine pass rate
  days required     median trading days to pass, among attempts that pass
Units: payout dollars per dollar of evaluation fees per trading day. Higher is better. Plans whose median days
to pass exceed 30 trading days are flagged low priority (Ben's rule).
"""
from __future__ import annotations

import numpy as np

from .montecarlo import DayRecords, block_bootstrap, simulate_combine, simulate_xfa
from .rules import load_rules

MAX_DAYS = 30


def score_stream(pnl_usd: np.ndarray, mae_usd: np.ndarray, traded: np.ndarray, size: str = "50K", rules=None,
                 n_paths: int = 3000, horizon: int = 400, block: int = 5, seed: int = 0) -> dict:
    """pnl_usd / mae_usd: per-day dollars for the whole position, net of ALL costs and commissions."""
    rules = rules or load_rules()
    fee = rules.commission_per_side["MNQ"] * 2  # the engine charges this once per traded day; neutralise it
    rec = DayRecords(np.asarray(traded, bool), np.asarray(pnl_usd, float) + fee, np.asarray(mae_usd, float) + fee, "MNQ")
    idx = block_bootstrap(len(rec.pnl), n_paths, horizon, block, np.random.default_rng(seed))
    spec = rules.account(size)
    c = simulate_combine(rec, idx, 1, size, rules)
    cs = c.summary()
    xs = simulate_xfa(rec, idx, 1, size, "standard", rules).summary()
    xc = simulate_xfa(rec, idx, 1, size, "consistency", rules).summary()
    p = float(c.passed.mean())
    days_pass = float(np.median(c.days[c.passed])) if c.passed.any() else float("nan")
    mean_days = float(c.days.mean())
    months = max(1.0, np.ceil(mean_days / 21))
    cost = months * (spec.combine_monthly_standard + rules.api_monthly)
    payout = max(xs["mean_to_trader"], xc["mean_to_trader"])
    score = payout / (cost * (1 / p) * days_pass) if p > 0 and days_pass > 0 else 0.0
    ev = p * (payout - spec.activation_fee_standard) - cost
    return {"size": size, "pass": p, "pass_lo": cs["pass_lo"], "pass_hi": cs["pass_hi"], "breach": float(c.breached.mean()),
            "days_to_pass": days_pass, "within_30_days": bool(days_pass <= MAX_DAYS), "accounts_needed": 1 / p if p > 0 else float("inf"),
            "cost_per_account": float(cost), "payout": float(payout), "xfa_p_std": xs["p_payout"], "xfa_p_cons": xc["p_payout"],
            "score": float(score), "ev_per_attempt": float(ev)}
