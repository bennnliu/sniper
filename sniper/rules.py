"""Load the machine-readable Topstep rule spec (topstep_rules.yaml).

Every number the simulator uses comes from the YAML file, so that a rule
change at Topstep is a one-line edit with a source URL next to it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from pathlib import Path

import yaml

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "topstep_rules.yaml"
ACCOUNT_SIZES = ("50K", "100K", "150K")


def _v(node):
    """Rule entries are {value, source, verified} dicts; return the value."""
    if isinstance(node, dict) and "value" in node:
        return node["value"]
    return node


def _t(text: str) -> time:
    hh, mm = text.split(":")
    return time(int(hh), int(mm))


@dataclass(frozen=True)
class ScalingTier:
    min_balance: float  # tier applies when start-of-day balance is above this
    max_lots: float  # mini-equivalent contracts
    inclusive: bool = False  # True: applies at exactly min_balance too

    def applies(self, balance: float) -> bool:
        if self.inclusive:
            return balance >= self.min_balance - 1e-6
        return balance > self.min_balance + 1e-6


@dataclass(frozen=True)
class AccountSpec:
    size: str
    # Combine
    starting_balance: float
    profit_target: float
    mll: float
    max_lots: float  # mini-equivalent contracts
    daily_loss_limit: float  # optional; used only when enabled
    consistency_fraction: float
    min_trading_days: int
    # XFA
    xfa_mll: float
    scaling_plan: tuple[ScalingTier, ...]
    payout_cap_standard: float
    payout_cap_consistency: float
    # Fees
    combine_monthly_standard: float
    combine_monthly_no_activation: float
    activation_fee_standard: float


@dataclass(frozen=True)
class SessionSpec:
    timezone: str
    open_ct: time
    flat_by_ct: time
    no_new_positions_after_ct: time
    winning_day_locks_ct: time


@dataclass(frozen=True)
class PayoutSpec:
    standard_winning_days: int
    standard_winning_day_min: float
    consistency_min_days: int
    consistency_max_fraction: float
    max_fraction_of_balance: float
    minimum: float
    trader_split: float


@dataclass(frozen=True)
class RuleSpec:
    accounts: dict[str, AccountSpec]
    session: SessionSpec
    payout: PayoutSpec
    commission_per_side: dict[str, float]
    api_monthly: float
    raw: dict = field(repr=False, default_factory=dict)

    def account(self, size: str) -> AccountSpec:
        return self.accounts[size.upper()]


def load_rules(path: str | Path = DEFAULT_PATH) -> RuleSpec:
    raw = yaml.safe_load(Path(path).read_text())
    combine = raw["combine"]
    xfa = raw["xfa"]
    fees = raw["fees"]
    accounts: dict[str, AccountSpec] = {}
    for size in ACCOUNT_SIZES:
        c = combine["accounts"][size]
        x = xfa["accounts"][size]
        f = fees["accounts"][size]
        tiers = tuple(
            ScalingTier(float(t["min_balance"]), float(t["max_lots"]), bool(t.get("inclusive", False)))
            for t in _v(x["scaling_plan"])
        )
        accounts[size] = AccountSpec(
            size=size,
            starting_balance=float(_v(c["starting_balance"])),
            profit_target=float(_v(c["profit_target"])),
            mll=float(_v(c["mll"])),
            max_lots=float(_v(c["max_lots"])),
            daily_loss_limit=float(_v(c["daily_loss_limit_optional"])),
            consistency_fraction=float(_v(combine["consistency_fraction"])),
            min_trading_days=int(_v(combine["min_trading_days"])),
            xfa_mll=float(_v(x["mll"])),
            scaling_plan=tuple(sorted(tiers, key=lambda t: t.min_balance)),
            payout_cap_standard=float(_v(x["payout_cap_standard"])),
            payout_cap_consistency=float(_v(x["payout_cap_consistency"])),
            combine_monthly_standard=float(_v(f["combine_monthly_standard_path"])),
            combine_monthly_no_activation=float(_v(f["combine_monthly_no_activation_path"])),
            activation_fee_standard=float(_v(f["xfa_activation_standard_path"])),
        )
    s = raw["session"]
    session = SessionSpec(
        timezone=_v(s["timezone"]),
        open_ct=_t(_v(s["open_ct"])),
        flat_by_ct=_t(_v(s["flat_by_ct"])),
        no_new_positions_after_ct=_t(_v(s["no_new_positions_after_ct"])),
        winning_day_locks_ct=_t(_v(s["winning_day_locks_ct"])),
    )
    p = xfa["payout"]
    payout = PayoutSpec(
        standard_winning_days=int(_v(p["standard_winning_days"])),
        standard_winning_day_min=float(_v(p["standard_winning_day_min_net"])),
        consistency_min_days=int(_v(p["consistency_min_days"])),
        consistency_max_fraction=float(_v(p["consistency_max_day_fraction"])),
        max_fraction_of_balance=float(_v(p["max_fraction_of_balance"])),
        minimum=float(_v(p["minimum"])),
        trader_split=float(_v(p["trader_split"])),
    )
    commission = {k: float(_v(v)) for k, v in fees["round_turn_per_contract"].items()}
    per_side = {k: v / 2.0 for k, v in commission.items()}
    return RuleSpec(
        accounts=accounts,
        session=session,
        payout=payout,
        commission_per_side=per_side,
        api_monthly=float(_v(fees["api_monthly"])),
        raw=raw,
    )
