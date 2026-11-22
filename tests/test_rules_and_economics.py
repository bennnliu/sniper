import pytest
import yaml

from sniper import ACCOUNT_SIZES, load_rules
from sniper.economics import first_payout_value, path_costs
from sniper.rules import DEFAULT_PATH

RULES = load_rules()


def _leaves(node, path=""):
    if isinstance(node, dict):
        if "value" in node:
            yield path, node
        else:
            for k, v in node.items():
                yield from _leaves(v, f"{path}.{k}")


def test_every_rule_value_has_source_and_date():
    raw = yaml.safe_load(DEFAULT_PATH.read_text())
    sources = raw["meta"]["sources"]
    leaves = list(_leaves({k: v for k, v in raw.items() if k != "meta"}))
    assert len(leaves) > 50
    for path, leaf in leaves:
        assert leaf.get("source") in sources, path
        assert leaf.get("verified"), path
        assert leaf.get("status") in {"verified", "secondary", "interpretation"}, path


@pytest.mark.parametrize(
    "size,target,mll,lots,dll",
    [("50K", 3000, 2000, 5, 1000), ("100K", 6000, 3000, 10, 2000), ("150K", 9000, 4500, 15, 3000)],
)
def test_combine_figures(size, target, mll, lots, dll):
    a = RULES.account(size)
    assert (a.profit_target, a.mll, a.max_lots, a.daily_loss_limit) == (target, mll, lots, dll)
    assert a.profit_target * a.consistency_fraction == pytest.approx({"50K": 1650, "100K": 3300, "150K": 4950}[size])


def test_scaling_plans_are_monotonic_and_end_at_combine_limit():
    for size in ACCOUNT_SIZES:
        a = RULES.account(size)
        lots = [t.max_lots for t in a.scaling_plan]
        assert lots == sorted(lots)
        assert lots[-1] == a.max_lots


def test_break_even_arithmetic():
    c = path_costs(RULES, "50K", "standard")
    assert c.attempt_cost() == 49 + 29
    v = first_payout_value(RULES, "50K")
    assert v == pytest.approx(1800)
    p = c.break_even_pass_rate(v)
    assert c.expected_profit(p, v) == pytest.approx(0, abs=1e-9)
    assert c.break_even_xfa_value(p) == pytest.approx(v)
    nf = path_costs(RULES, "50K", "no_activation")
    assert nf.activation == 0 and nf.monthly == 95
