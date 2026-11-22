import numpy as np

from sniper import load_rules
from sniper.montecarlo import DayRecords, block_bootstrap, simulate_combine, simulate_xfa

R = load_rules()


def rec(pnls, maes=None):
    p = np.array(pnls, float)
    return DayRecords(np.ones(len(p), bool), p, np.array(maes if maes else np.minimum(p, 0), float), "MNQ")


def test_combine_pass_breach_and_consistency():
    fee = 1.22
    win = rec([100.0])  # $100 per MNQ per day
    idx = np.zeros((1, 40), dtype=int)
    r = simulate_combine(win, idx, 10, "50K", R)  # ~$988/day -> needs 4 days: day 1-3 at 2964 < 3000
    assert r.passed[0] and r.days[0] == 4
    lose = rec([-50.0], [-210.0])  # open loss 10*210 = $2,100 > $2,000 MLL
    r = simulate_combine(lose, idx, 10, "50K", R)
    assert r.breached[0] and r.days[0] == 1
    # One huge day then small ones: target rises to best/0.55
    big = rec([300.0, 10.0])
    path = np.array([[0] + [1] * 60])
    r = simulate_combine(big, path, 10, "50K", R)
    best = 300 * 10 - fee * 10
    need = best / 0.55
    days_needed = 1 + int(np.ceil((need - best) / (100 - fee * 10)))
    assert r.passed[0] and r.days[0] == days_needed


def test_xfa_scaling_caps_contracts_and_pays_out():
    r = rec([20.0])  # $20 per MNQ; 50K starts at 2 lots = 20 MNQ
    idx = np.zeros((1, 5), dtype=int)
    x = simulate_xfa(r, idx, 50, "50K", "standard", R)
    # Capped at 20 MNQ: $400 - $24.40 fees = $375.60/day; 5 winning days -> $1,878; payout 50% = $939
    assert x.first_payout[0] and x.days_to_first[0] == 5 and x.n_payouts[0] == 1
    assert abs(x.to_trader[0] - 0.9 * 939.0) < 1e-6


def test_block_bootstrap_shape_and_range():
    idx = block_bootstrap(100, 50, 20, 5, np.random.default_rng(0))
    assert idx.shape == (50, 20) and idx.min() >= 0 and idx.max() < 100
