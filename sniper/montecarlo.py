"""Monte Carlo of Topstep outcomes over resampled trading days (METHOD.md §8).

Each strategy is reduced to one record per trading day: whether it traded,
the per-contract P&L at the exit, and the per-contract worst open P&L during
the trade (from 1-minute highs and lows). Paths of days are drawn with a
stationary block bootstrap, so streaks and volatility clustering survive.

The day-level engine below is vectorized across paths for speed. It applies
the same rules as TopstepSim for a strategy that holds at most one position
per day, and ``validate_against_topstepsim`` checks that the two agree.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .rules import RuleSpec, load_rules


@dataclass
class DayRecords:
    """Per-day strategy outcome per contract, in dollars, before commissions."""
    traded: np.ndarray  # bool
    pnl: np.ndarray  # P&L at exit per contract (incl. slippage)
    mae: np.ndarray  # worst open P&L per contract during the trade (<= 0 typically)
    symbol: str  # contract the dollars refer to, e.g. "MNQ"


def block_bootstrap(n_days: int, n_paths: int, length: int, mean_block: int, rng) -> np.ndarray:
    """Stationary bootstrap indices, shape (n_paths, length)."""
    idx = np.empty((n_paths, length), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n_days, n_paths)
    p = 1.0 / mean_block
    for t in range(1, length):
        new = rng.random(n_paths) < p
        idx[:, t] = np.where(new, rng.integers(0, n_days, n_paths), (idx[:, t - 1] + 1) % n_days)
    return idx


@dataclass
class CombineResult:
    passed: np.ndarray
    breached: np.ndarray
    days: np.ndarray  # trading days until pass/breach (or horizon)

    def summary(self) -> dict:
        n = len(self.passed)
        p = self.passed.mean()
        se = np.sqrt(p * (1 - p) / n)
        return {
            "pass": p, "pass_lo": max(0.0, p - 1.96 * se), "pass_hi": min(1.0, p + 1.96 * se),
            "breach": self.breached.mean(), "undecided": 1 - p - self.breached.mean(),
            "median_days_to_pass": float(np.median(self.days[self.passed])) if self.passed.any() else float("nan"),
            "median_days_any": float(np.median(self.days)),
        }


def simulate_combine(rec: DayRecords, idx: np.ndarray, contracts: int, size: str,
                     rules: RuleSpec | None = None, cost_mult: float = 1.0) -> CombineResult:
    rules = rules or load_rules()
    spec = rules.account(size)
    fee = rules.commission_per_side[rec.symbol] * 2 * contracts * cost_mult
    n_paths, length = idx.shape
    start, mll_amt = spec.starting_balance, spec.mll
    b = np.full(n_paths, start)
    m = np.full(n_paths, start - mll_amt)
    best = np.zeros(n_paths)
    tdays = np.zeros(n_paths, dtype=int)
    alive = np.ones(n_paths, bool)
    passed = np.zeros(n_paths, bool)
    breached = np.zeros(n_paths, bool)
    days = np.full(n_paths, length)
    for t in range(length):
        d = idx[:, t]
        tr = rec.traded[d] & alive
        worst = b + rec.mae[d] * contracts - fee / 2
        hit = tr & (worst <= m + 1e-9)
        b = np.where(hit, m - fee / 2, b)  # liquidated at the MLL, pay the exit fee
        breached |= hit
        ok = tr & ~hit
        pnl = rec.pnl[d] * contracts - fee
        b = np.where(ok, b + pnl, b)
        best = np.where(ok, np.maximum(best, pnl), best)
        tdays += ok
        m = np.where(alive & ~hit, np.minimum(np.maximum(m, b - mll_amt), start), m)
        target = np.maximum(spec.profit_target, best / spec.consistency_fraction)
        win = alive & ~hit & (tdays >= spec.min_trading_days) & (b - start >= target - 1e-9)
        passed |= win
        done = hit | win
        days = np.where(done & alive, t + 1, days)
        alive &= ~done
        if not alive.any():
            break
    return CombineResult(passed, breached, days)


@dataclass
class XfaResult:
    first_payout: np.ndarray  # bool: at least one payout before breach
    n_payouts: np.ndarray
    to_trader: np.ndarray  # dollars received by the trader
    breached: np.ndarray
    days_to_first: np.ndarray
    days_alive: np.ndarray | None = None  # trading days until breach or the end of the path

    def summary(self) -> dict:
        n = len(self.first_payout)
        p = self.first_payout.mean()
        se = np.sqrt(p * (1 - p) / n)
        return {
            "p_payout": p, "p_payout_lo": max(0.0, p - 1.96 * se),
            "mean_to_trader": float(self.to_trader.mean()),
            "mean_payouts": float(self.n_payouts.mean()),
            "breach": float(self.breached.mean()),
            "median_days_to_first": float(np.median(self.days_to_first[self.first_payout])) if p > 0 else float("nan"),
        }


def simulate_xfa(rec: DayRecords, idx: np.ndarray, contracts: int, size: str, path: str = "standard",
                 rules: RuleSpec | None = None, cost_mult: float = 1.0, max_payouts: int = 99) -> XfaResult:
    """XFA from $0 with the Scaling Plan, trailing MLL locking at $0, payouts
    requested as soon as allowed (max allowed amount), MLL $0 after a payout."""
    rules = rules or load_rules()
    spec = rules.account(size)
    pay = rules.payout
    mini_eq = 0.1 if rec.symbol in ("MNQ", "MES") else 1.0
    n_paths, length = idx.shape
    b = np.zeros(n_paths)
    m = np.full(n_paths, -spec.xfa_mll)
    paid_once = np.zeros(n_paths, bool)
    alive = np.ones(n_paths, bool)
    breached = np.zeros(n_paths, bool)
    n_pay = np.zeros(n_paths, dtype=int)
    to_trader = np.zeros(n_paths)
    days_first = np.full(n_paths, length)
    win_days = np.zeros(n_paths, dtype=int)
    win_sum = np.zeros(n_paths)
    win_max = np.zeros(n_paths)
    win_n = np.zeros(n_paths, dtype=int)
    win_start = np.zeros(n_paths)
    days_alive = np.zeros(n_paths, dtype=int)
    cap = spec.payout_cap_standard if path == "standard" else spec.payout_cap_consistency
    for t in range(length):
        # contracts allowed by the Scaling Plan at the start of the day
        lots = np.zeros(n_paths)
        for tier in spec.scaling_plan:
            ok_tier = (b >= tier.min_balance - 1e-6) if tier.inclusive else (b > tier.min_balance + 1e-6)
            lots = np.where(ok_tier, tier.max_lots, lots)
        n = np.minimum(contracts, np.floor(lots / mini_eq + 1e-9))
        fee = rules.commission_per_side[rec.symbol] * 2 * n * cost_mult
        d = idx[:, t]
        days_alive += alive
        tr = rec.traded[d] & alive & (n > 0)
        worst = b + rec.mae[d] * n - fee / 2
        hit = tr & (worst <= m + 1e-9)
        b = np.where(hit, m - fee / 2, b)
        breached |= hit
        alive &= ~hit
        ok = tr & ~hit
        pnl = rec.pnl[d] * n - fee
        b = np.where(ok, b + pnl, b)
        win_days += ok & (pnl >= pay.standard_winning_day_min - 1e-9)
        win_n += ok
        win_max = np.where(ok, np.maximum(win_max, pnl), win_max)
        m = np.where(alive, np.where(paid_once, 0.0, np.minimum(np.maximum(m, b - spec.xfa_mll), 0.0)), m)
        net = b - win_start
        if path == "standard":
            elig = alive & (win_days >= pay.standard_winning_days) & (~paid_once | (net > 0))
        else:
            elig = alive & (win_n >= pay.consistency_min_days) & (net > 0) & (win_max <= pay.consistency_max_fraction * net + 1e-9)
        amt = np.minimum(cap, pay.max_fraction_of_balance * b)
        elig &= (amt >= pay.minimum - 1e-9) & (n_pay < max_payouts)
        b = np.where(elig, b - amt, b)
        to_trader += np.where(elig, amt * pay.trader_split, 0.0)
        days_first = np.where(elig & ~paid_once, t + 1, days_first)
        paid_once |= elig
        n_pay += elig
        m = np.where(elig, 0.0, m)
        win_days = np.where(elig, 0, win_days)
        win_n = np.where(elig, 0, win_n)
        win_max = np.where(elig, 0.0, win_max)
        win_start = np.where(elig, b, win_start)
        if not alive.any():
            break
    return XfaResult(paid_once, n_pay, to_trader, breached, days_first, days_alive)


def validate_against_topstepsim(day_events: list, rec: DayRecords, idx_row: np.ndarray, contracts: int,
                                size: str, rules: RuleSpec | None = None) -> tuple[str, str]:
    """Replay one bootstrap path through TopstepSim (event level) and through
    the fast engine; return both statuses. ``day_events[i]`` is a function
    (date, contracts) -> list of Fill/Mark for day i."""
    from datetime import date, timedelta

    from .sim import TopstepSim

    rules = rules or load_rules()
    sim = TopstepSim(size, mode="combine", rules=rules)
    d0 = date(2030, 1, 7)
    k = 0
    for i, di in enumerate(idx_row):
        day = d0 + timedelta(days=k)
        while day.weekday() >= 5:
            k += 1
            day = d0 + timedelta(days=k)
        k += 1
        for ev in day_events[di](day, contracts):
            sim.process(ev)
        if sim.status != "active":
            break
    res = sim.finish()
    fast = simulate_combine(rec, idx_row[None, :], contracts, size, rules)
    fstat = "passed" if fast.passed[0] else ("breached" if fast.breached[0] else "active")
    return res.status, fstat
