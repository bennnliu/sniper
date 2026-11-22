"""Account economics: what a Combine attempt costs and what it must earn.

All outputs here are ASSUMED economics built from Topstep's published prices
(see topstep_rules.yaml). Nothing is measured from trading yet.

Model of one attempt
--------------------
* An attempt is one Combine run until it passes or breaches. It costs the
  monthly subscription for each month it runs (a reset costs the same as a
  month, so a breach-and-reset is a new attempt at the same price).
* The API subscription is a monthly cost of running the bot, shared by every
  account, so it is charged per month of research-to-payout time.
* If the Combine passes, the XFA costs the activation fee (standard path) or
  nothing (no-activation-fee path, which charges more per Combine month).
* V is the trader's share of all payouts from one XFA before it breaches.

Expected profit per attempt = p * (V - activation) - months * (monthly + api)
Break-even pass rate       p* = months * (monthly + api) / (V - activation)
Break-even XFA value       V* = activation + months * (monthly + api) / p
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass

from .rules import ACCOUNT_SIZES, RuleSpec, load_rules


@dataclass(frozen=True)
class PathCosts:
    size: str
    path: str  # "standard" or "no_activation"
    monthly: float
    activation: float
    api_monthly: float

    def attempt_cost(self, months: float = 1.0, include_api: bool = True) -> float:
        return months * (self.monthly + (self.api_monthly if include_api else 0.0))

    def expected_profit(self, pass_rate: float, xfa_value: float, months: float = 1.0) -> float:
        return pass_rate * (xfa_value - self.activation) - self.attempt_cost(months)

    def break_even_pass_rate(self, xfa_value: float, months: float = 1.0) -> float:
        margin = xfa_value - self.activation
        if margin <= 0:
            return float("inf")
        return self.attempt_cost(months) / margin

    def break_even_xfa_value(self, pass_rate: float, months: float = 1.0) -> float:
        if pass_rate <= 0:
            return float("inf")
        return self.activation + self.attempt_cost(months) / pass_rate


def path_costs(rules: RuleSpec, size: str, path: str) -> PathCosts:
    spec = rules.account(size)
    if path == "standard":
        return PathCosts(size, path, spec.combine_monthly_standard, spec.activation_fee_standard, rules.api_monthly)
    if path == "no_activation":
        return PathCosts(size, path, spec.combine_monthly_no_activation, 0.0, rules.api_monthly)
    raise ValueError(path)


def first_payout_value(rules: RuleSpec, size: str, payout_path: str = "standard") -> float:
    """Trader's share of one maximum first payout. Requires an XFA balance of
    twice the cap, because a payout is limited to 50% of the balance."""
    spec = rules.account(size)
    cap = spec.payout_cap_standard if payout_path == "standard" else spec.payout_cap_consistency
    return cap * rules.payout.trader_split


def markdown_report(rules: RuleSpec | None = None) -> str:
    rules = rules or load_rules()
    lines = [
        "| Size | Combine path | Monthly | Activation | Cost per 1-month attempt (with API) | "
        "Trader share of one max Standard payout (V) | XFA balance needed for it | Break-even pass rate at V | "
        "Break-even V at 20% pass rate |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for size in ACCOUNT_SIZES:
        spec = rules.account(size)
        v = first_payout_value(rules, size)
        for path in ("standard", "no_activation"):
            c = path_costs(rules, size, path)
            lines.append(
                f"| {size} | {path} | ${c.monthly:,.0f} | ${c.activation:,.0f} | ${c.attempt_cost():,.0f} | "
                f"${v:,.0f} | ${2 * spec.payout_cap_standard:,.0f} | {c.break_even_pass_rate(v):.1%} | "
                f"${c.break_even_xfa_value(0.20):,.0f} |"
            )
    return "\n".join(lines)


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(markdown_report())


if __name__ == "__main__":
    main()
