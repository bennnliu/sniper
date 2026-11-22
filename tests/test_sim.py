"""Hand-built unit tests: one per Topstep rule, run for all three account sizes."""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from sniper import ACCOUNT_SIZES, EventKind, Fill, Mark, TopstepSim, load_rules

CT = ZoneInfo("America/Chicago")
RULES = load_rules()
# Weekdays starting Monday 23 Nov 2026 (the simulator has no holiday calendar).
DAYS = [datetime(2026, 11, 23) + timedelta(days=d) for d in range(40)]
DAYS = [d for d in DAYS if d.weekday() < 5]


def ct(day: datetime, hh: int, mm: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hh, mm, tzinfo=CT)


def es_round_trip(sim, day, net_dollars, qty=1, at=(9, 0)):
    """Buy qty ES and sell it later the same day for a net of `net_dollars`
    (fees must be off, i.e. commission_multiplier=0, for this to be exact)."""
    entry = 5000.0
    points = net_dollars / (50.0 * qty)
    out = []
    out += sim.process(Fill(ct(day, *at), "ES", qty, entry))
    out += sim.process(Fill(ct(day, at[0] + 1, at[1]), "ES", -qty, entry + points))
    return out


def sim_nofee(size, mode="combine", **kw):
    return TopstepSim(size, mode=mode, rules=RULES, commission_multiplier=0.0, **kw)


# ----------------------------------------------------------------- the clock
def test_trading_day_starts_at_5pm_ct():
    sim = sim_nofee("50K")
    # Sunday 5:00 PM CT belongs to Monday's trading day.
    assert sim._session_clock(datetime(2026, 11, 22, 17, 0, tzinfo=CT))[0].isoformat() == "2026-11-23"
    assert sim._session_clock(datetime(2026, 11, 23, 15, 9, tzinfo=CT))[0].isoformat() == "2026-11-23"
    assert sim._session_clock(datetime(2026, 11, 23, 16, 59, tzinfo=CT))[0].isoformat() == "2026-11-23"
    assert sim._session_clock(datetime(2026, 11, 23, 17, 0, tzinfo=CT))[0].isoformat() == "2026-11-24"


def test_utc_timestamps_are_converted():
    sim = sim_nofee("50K")
    # 22:00 UTC on 23 Nov = 4:00 PM CST, still the 23 Nov trading day.
    utc = datetime(2026, 11, 23, 22, 0, tzinfo=ZoneInfo("UTC"))
    assert sim._session_clock(utc)[0].isoformat() == "2026-11-23"


def test_naive_and_out_of_order_timestamps_rejected():
    sim = sim_nofee("50K")
    with pytest.raises(ValueError):
        sim.process(Mark(datetime(2026, 11, 23, 9, 0), "ES", 5000))
    sim.process(Mark(ct(DAYS[0], 9), "ES", 5000))
    with pytest.raises(ValueError):
        sim.process(Mark(ct(DAYS[0], 8), "ES", 5000))


# --------------------------------------------------------- MLL: intraday breach
@pytest.mark.parametrize("size", ACCOUNT_SIZES)
def test_intraday_breach_on_unrealized_loss(size):
    spec = RULES.account(size)
    sim = sim_nofee(size)
    d = DAYS[0]
    sim.process(Fill(ct(d, 9), "NQ", 1, 20000.0))
    # NQ is $20/point, so an open loss of exactly the MLL is MLL/20 points.
    drop = spec.mll / 20.0
    ev = sim.process(Mark(ct(d, 9, 30), "NQ", 20000.0 - drop + 0.25))
    assert not ev and sim.status == "active"  # $5 above the line
    ev = sim.process(Mark(ct(d, 9, 31), "NQ", 20000.0 - drop))
    assert [e.kind for e in ev] == [EventKind.BREACH_MLL]
    assert sim.status == "breached"
    assert sim.open_lots() == 0
    assert sim.balance == pytest.approx(spec.starting_balance - spec.mll)
    # Nothing trades after a breach.
    ev = sim.process(Fill(ct(d, 10), "NQ", 1, 19000.0))
    assert ev[0].kind == EventKind.REJECTED


@pytest.mark.parametrize("size", ACCOUNT_SIZES)
def test_mll_does_not_trail_intraday(size):
    spec = RULES.account(size)
    sim = sim_nofee(size)
    d = DAYS[0]
    sim.process(Fill(ct(d, 9), "ES", 1, 5000.0))
    sim.process(Mark(ct(d, 10), "ES", 5020.0))  # +$1,000 open, never banked
    assert sim.mll == spec.starting_balance - spec.mll
    # Give it all back and more: the MLL is still the original one.
    sim.process(Mark(ct(d, 11), "ES", 5000.0 - (spec.mll - 100) / 50.0))
    assert sim.status == "active"


@pytest.mark.parametrize("size", ACCOUNT_SIZES)
def test_mll_trails_eod_and_locks_at_starting_balance(size):
    spec = RULES.account(size)
    sim = sim_nofee(size)
    gain = spec.mll * 0.6
    es_round_trip(sim, DAYS[0], gain)
    sim.process(Mark(ct(DAYS[1], 8), "ES", 5000))  # rolls the day
    assert sim.mll == pytest.approx(spec.starting_balance + gain - spec.mll)
    es_round_trip(sim, DAYS[1], -gain / 2)  # losing day: MLL never moves down
    sim.process(Mark(ct(DAYS[2], 8), "ES", 5000))
    assert sim.mll == pytest.approx(spec.starting_balance + gain - spec.mll)
    es_round_trip(sim, DAYS[2], spec.mll)  # balance well past start + MLL
    sim.process(Mark(ct(DAYS[3], 8), "ES", 5000))
    assert sim.mll == spec.starting_balance  # locked
    es_round_trip(sim, DAYS[3], spec.mll * 0.3)
    sim.process(Mark(ct(DAYS[4], 8), "ES", 5000))
    assert sim.mll == spec.starting_balance


# ------------------------------------------------------- pass and consistency
@pytest.mark.parametrize("size", ACCOUNT_SIZES)
def test_pass_after_two_days_within_consistency(size):
    spec = RULES.account(size)
    sim = sim_nofee(size)
    es_round_trip(sim, DAYS[0], spec.profit_target * 0.5)
    es_round_trip(sim, DAYS[1], spec.profit_target * 0.5)
    res = sim.finish()
    assert res.status == "passed"
    assert len(res.of(EventKind.PASS)) == 1


@pytest.mark.parametrize("size", ACCOUNT_SIZES)
def test_minimum_two_trading_days(size):
    spec = RULES.account(size)
    sim = sim_nofee(size)
    # Whole target in one day: blocked by both minimum days and consistency.
    es_round_trip(sim, DAYS[0], spec.profit_target)
    sim.process(Mark(ct(DAYS[1], 8), "ES", 5000))
    assert sim.status == "active"


@pytest.mark.parametrize("size", ACCOUNT_SIZES)
def test_consistency_raises_target(size):
    spec = RULES.account(size)
    sim = sim_nofee(size)
    big = spec.profit_target * 0.70  # 70% > 55%: target becomes big / 0.55
    es_round_trip(sim, DAYS[0], big)
    es_round_trip(sim, DAYS[1], spec.profit_target - big)  # reaches nominal target
    sim.process(Mark(ct(DAYS[2], 8), "ES", 5000))
    assert sim.status == "active"
    assert sim.effective_target() == pytest.approx(big / 0.55)
    needed = big / 0.55 - spec.profit_target
    es_round_trip(sim, DAYS[2], needed - 1)
    sim.process(Mark(ct(DAYS[3], 8), "ES", 5000))
    assert sim.status == "active"
    es_round_trip(sim, DAYS[3], 1)
    assert sim.finish().status == "passed"


def test_best_day_exactly_at_55_percent_passes():
    sim = sim_nofee("50K")
    es_round_trip(sim, DAYS[0], 1650)  # 1650 / 3000 = 55.0%
    es_round_trip(sim, DAYS[1], 1350)
    assert sim.finish().status == "passed"


# ------------------------------------------------------------ position limits
@pytest.mark.parametrize("size", ACCOUNT_SIZES)
def test_combine_position_limit_minis_and_micros(size):
    spec = RULES.account(size)
    sim = sim_nofee(size)
    d = DAYS[0]
    lots = int(spec.max_lots)
    assert not sim.process(Fill(ct(d, 9), "ES", lots - 1, 5000))
    # The last lot as 10 micros fits exactly; one more micro does not.
    assert not sim.process(Fill(ct(d, 9, 1), "MES", 10, 5000))
    ev = sim.process(Fill(ct(d, 9, 2), "MNQ", 1, 20000))
    assert ev[0].kind == EventKind.REJECTED and "position limit" in ev[0].data["reason"]
    # Reducing is always allowed.
    assert not sim.process(Fill(ct(d, 9, 3), "ES", -1, 5000))


# ---------------------------------------------------------- session timing
@pytest.mark.parametrize("size", ACCOUNT_SIZES)
def test_forced_flat_at_310pm(size):
    sim = sim_nofee(size)
    d = DAYS[0]
    sim.process(Fill(ct(d, 14), "ES", 1, 5000))
    ev = sim.process(Mark(ct(d, 15, 10), "ES", 5001))
    assert ev[0].kind == EventKind.FORCED_FLAT
    assert sim.open_lots() == 0
    ev = sim.process(Fill(ct(d, 15, 30), "ES", 1, 5001))
    assert ev[0].kind == EventKind.REJECTED and "session closed" in ev[0].data["reason"]
    # The new session at 5:00 PM is open again.
    ev = sim.process(Fill(ct(d, 17, 0), "ES", 1, 5001))
    assert [e.kind for e in ev] == [EventKind.DAY_CLOSE] and sim.open_lots() == 1


def test_late_entry_flagged_after_308pm():
    sim = sim_nofee("50K")
    d = DAYS[0]
    ev = sim.process(Fill(ct(d, 15, 8), "ES", 1, 5000))
    assert [e.kind for e in ev] == [EventKind.LATE_ENTRY]
    assert not sim.process(Fill(ct(d, 15, 9), "ES", -1, 5000))  # exits are fine


def test_position_open_at_day_rollover_is_flattened():
    sim = sim_nofee("50K")
    sim.process(Fill(ct(DAYS[0], 14), "ES", 1, 5000))
    ev = sim.process(Fill(ct(DAYS[0], 17, 5), "ES", 1, 5000))  # next session, no mark at 3:10
    assert EventKind.FORCED_FLAT in [e.kind for e in ev]


# --------------------------------------------------------- daily loss limit
@pytest.mark.parametrize("size", ACCOUNT_SIZES)
def test_optional_dll_locks_day_but_does_not_fail(size):
    spec = RULES.account(size)
    sim = sim_nofee(size, dll_enabled=True)
    d = DAYS[0]
    sim.process(Fill(ct(d, 9), "ES", 1, 5000))
    ev = sim.process(Mark(ct(d, 9, 5), "ES", 5000 - spec.daily_loss_limit / 50.0))
    assert ev[0].kind == EventKind.DLL_HIT
    assert sim.status == "active"
    assert sim.process(Fill(ct(d, 10), "ES", 1, 4980))[0].kind == EventKind.REJECTED
    ev = sim.process(Fill(ct(DAYS[1], 9), "ES", 1, 4980))  # next day is open
    assert [e.kind for e in ev] == [EventKind.DAY_CLOSE] and sim.open_lots() == 1


def test_dll_off_by_default():
    sim = sim_nofee("50K")
    sim.process(Fill(ct(DAYS[0], 9), "ES", 1, 5000))
    assert not sim.process(Mark(ct(DAYS[0], 9, 5), "ES", 5000 - 1500 / 50.0))


# ------------------------------------------------------------------ fees
def test_round_trip_fees_and_double_cost():
    for mult, expected in [(1.0, 3.78), (2.0, 7.56)]:
        sim = TopstepSim("50K", rules=RULES, commission_multiplier=mult)
        sim.process(Fill(ct(DAYS[0], 9), "ES", 1, 5000))
        sim.process(Fill(ct(DAYS[0], 10), "ES", -1, 5000))
        assert sim.balance == pytest.approx(50000 - expected)
    sim = TopstepSim("50K", rules=RULES)
    sim.process(Fill(ct(DAYS[0], 9), "MNQ", 10, 20000))
    sim.process(Fill(ct(DAYS[0], 10), "MNQ", -10, 20010))
    assert sim.balance == pytest.approx(50000 + 10 * 10 * 2.0 - 10 * 1.22)


def test_position_flip_pnl():
    sim = sim_nofee("50K")
    sim.process(Fill(ct(DAYS[0], 9), "ES", 2, 5000))
    sim.process(Fill(ct(DAYS[0], 9, 1), "ES", -3, 5010))  # close 2 (+$1,000), open 1 short
    assert sim.balance == pytest.approx(51000)
    assert sim.positions["ES"].qty == -1 and sim.positions["ES"].avg_price == 5010
    sim.process(Fill(ct(DAYS[0], 9, 2), "ES", 1, 5000))
    assert sim.balance == pytest.approx(51500)


# ------------------------------------------------------------------- XFA
@pytest.mark.parametrize("size", ACCOUNT_SIZES)
def test_xfa_starts_at_zero_and_locks_mll_at_zero(size):
    spec = RULES.account(size)
    sim = sim_nofee(size, mode="xfa", payout_policy=None)
    assert sim.balance == 0 and sim.mll == -spec.xfa_mll
    es_round_trip(sim, DAYS[0], 500)
    sim.process(Mark(ct(DAYS[1], 8), "ES", 5000))
    assert sim.mll == pytest.approx(500 - spec.xfa_mll)
    # Small days so the 1-lot limit never binds; grow balance past the MLL amount.
    day = 1
    while sim.balance < spec.xfa_mll + 100:
        es_round_trip(sim, DAYS[day], 400)
        day += 1
    sim.process(Mark(ct(DAYS[day], 8), "ES", 5000))
    assert sim.mll == 0.0


@pytest.mark.parametrize("size", ACCOUNT_SIZES)
def test_xfa_breach_closes_account(size):
    spec = RULES.account(size)
    sim = sim_nofee(size, mode="xfa")
    sim.process(Fill(ct(DAYS[0], 9), "ES", 1, 5000))
    ev = sim.process(Mark(ct(DAYS[0], 9, 5), "ES", 5000 - spec.xfa_mll / 50.0))
    assert ev[0].kind == EventKind.BREACH_MLL and sim.status == "breached"


@pytest.mark.parametrize("size", ACCOUNT_SIZES)
def test_xfa_scaling_plan_by_start_of_day_balance(size):
    spec = RULES.account(size)
    sim = sim_nofee(size, mode="xfa", payout_policy=None)
    first = spec.scaling_plan[0].max_lots
    d = DAYS[0]
    assert not sim.process(Fill(ct(d, 9), "MES", int(first * 10), 5000))
    ev = sim.process(Fill(ct(d, 9, 1), "MES", 1, 5000))
    assert ev[0].kind == EventKind.REJECTED
    # Bank +$2,000 intraday: the limit must not rise mid-session.
    sim.process(Fill(ct(d, 9, 2), "MES", -int(first * 10), 5000 + 2000 / (5.0 * first * 10)))
    assert sim.balance == pytest.approx(2000)
    sim.process(Fill(ct(d, 10), "MES", int(first * 10), 5000))
    assert sim.process(Fill(ct(d, 10, 1), "MES", 1, 5000))[0].kind == EventKind.REJECTED
    sim.process(Fill(ct(d, 10, 2), "MES", -int(first * 10), 5000))
    # Next session uses the $2,000 tier.
    nxt = sim.process(Mark(ct(DAYS[1], 8), "ES", 5000))
    assert sim.max_lots_today == 5
    assert nxt[0].kind == EventKind.DAY_CLOSE


@pytest.mark.parametrize("size", ACCOUNT_SIZES)
def test_xfa_standard_payout(size):
    spec = RULES.account(size)
    sim = sim_nofee(size, mode="xfa", payout_path="standard")
    # Four winning days, one small one, then the fifth winner.
    for i, pnl in enumerate([400, 400, 400, 400, 100]):
        es_round_trip(sim, DAYS[i], pnl)
    sim.process(Mark(ct(DAYS[5], 8), "ES", 5000))
    assert not sim.payouts_gross
    es_round_trip(sim, DAYS[5], 150)  # exactly $150 counts
    sim.process(Mark(ct(DAYS[6], 8), "ES", 5000))
    payout = [e for e in sim.events if e.kind == EventKind.PAYOUT]
    assert len(payout) == 1
    balance_before = 400 * 4 + 100 + 150
    expected = min(spec.payout_cap_standard, 0.5 * balance_before)
    assert payout[0].data["amount"] == pytest.approx(expected)
    assert payout[0].data["to_trader"] == pytest.approx(0.9 * expected)
    assert sim.balance == pytest.approx(balance_before - expected)
    assert sim.mll == 0.0
    # After a payout the MLL is $0: the remaining balance is the whole cushion.
    sim.process(Fill(ct(DAYS[6], 9), "ES", 1, 5000))
    ev = sim.process(Mark(ct(DAYS[6], 9, 5), "ES", 5000 - sim.balance / 50.0))
    assert ev[0].kind == EventKind.BREACH_MLL


def test_xfa_standard_payout_is_capped():
    spec = RULES.account("50K")
    sim = sim_nofee("50K", mode="xfa")
    for i in range(5):
        es_round_trip(sim, DAYS[i], 1000)  # balance $5,000; 50% = $2,500
    res = sim.finish()
    assert res.payouts_gross == pytest.approx(spec.payout_cap_standard)


@pytest.mark.parametrize("size", ACCOUNT_SIZES)
def test_xfa_consistency_payout(size):
    spec = RULES.account(size)
    sim = sim_nofee(size, mode="xfa", payout_path="consistency", payout_policy=None)
    es_round_trip(sim, DAYS[0], 500)
    es_round_trip(sim, DAYS[1], 300)
    sim.process(Mark(ct(DAYS[2], 8), "ES", 5000))
    assert sim.payout_allowed() is None  # only 2 days
    es_round_trip(sim, DAYS[2], 400)  # total 1200, largest 500 = 41.7% > 40%
    sim.process(Mark(ct(DAYS[3], 8), "ES", 5000))
    assert sim.payout_allowed() is None
    es_round_trip(sim, DAYS[3], 50)  # total 1250, largest = 40% exactly
    sim.process(Mark(ct(DAYS[4], 8), "ES", 5000))
    assert sim.payout_allowed() == pytest.approx(min(spec.payout_cap_consistency, 625))


def test_xfa_payout_below_minimum_not_paid():
    sim = sim_nofee("50K", mode="xfa", payout_path="consistency")
    for i in range(3):
        es_round_trip(sim, DAYS[i], 80)  # 50% of $240 = $120 < $125
    assert sim.finish().payouts_gross == 0
