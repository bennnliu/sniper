"""TopstepSim: replay timestamped fills and price marks under Topstep's rules.

Every backtest equity path must pass through this module. It returns the
events Topstep itself would generate: a Maximum Loss Limit breach (including
intraday on open positions), a Daily Loss Limit stop, a forced flatten at
3:10 PM CT, a rejected order, a Combine pass, or an XFA payout.

Conventions
-----------
* Timestamps are timezone-aware datetimes. Naive datetimes are rejected.
* ``Fill.qty`` is signed: +2 buys two contracts, -2 sells two.
* ``balance`` is realized P&L net of fees plus the starting balance, which is
  what Topstep calls the account balance. ``equity`` adds open P&L.
* The MLL is checked on every fill and every mark. The simulator can only see
  the prices you give it, so for bar data feed the adverse extreme of each bar
  (the low for a long, the high for a short) as a mark before the close.
* The trading day runs 5:00 PM CT to 3:10 PM CT and is labelled by the
  calendar date on which it ends.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Callable, Iterable
from zoneinfo import ZoneInfo

from . import instruments
from .rules import AccountSpec, RuleSpec, load_rules

# Shifting Chicago time forward by 7 hours maps the 5:00 PM CT open to midnight,
# so the trading day is simply the shifted calendar date.
_SHIFT = timedelta(hours=7)


@dataclass(frozen=True)
class Fill:
    ts: datetime
    symbol: str
    qty: int
    price: float


@dataclass(frozen=True)
class Mark:
    ts: datetime
    symbol: str
    price: float


class EventKind(str, Enum):
    DAY_CLOSE = "day_close"
    BREACH_MLL = "breach_mll"
    DLL_HIT = "dll_hit"
    FORCED_FLAT = "forced_flat"
    LATE_ENTRY = "late_entry"
    REJECTED = "rejected"
    PASS = "pass"
    PAYOUT = "payout"


@dataclass(frozen=True)
class Event:
    ts: datetime
    kind: EventKind
    data: dict = field(default_factory=dict)


@dataclass
class DayRecord:
    day: date
    pnl: float
    balance: float
    mll_after: float
    trades: int


@dataclass
class SimResult:
    mode: str
    size: str
    status: str  # "active", "breached", "passed"
    balance: float
    events: list[Event]
    days: list[DayRecord]
    payouts_gross: float
    payouts_to_trader: float

    def of(self, kind: EventKind) -> list[Event]:
        return [e for e in self.events if e.kind == kind]


PayoutPolicy = Callable[["TopstepSim", float], float | None]


def request_max(sim: "TopstepSim", allowed: float) -> float | None:
    """Default payout policy: request the largest amount allowed."""
    return allowed


@dataclass
class _Position:
    qty: int = 0
    avg_price: float = 0.0


class TopstepSim:
    """Simulate one Topstep account (a Combine or an Express Funded Account).

    Parameters
    ----------
    size: "50K", "100K" or "150K".
    mode: "combine" or "xfa".
    dll_enabled: whether the optional Daily Loss Limit was bought.
    payout_path: XFA only, "standard" or "consistency".
    payout_policy: XFA only. Called when a payout is allowed, with the maximum
        allowed amount; returns the amount to request or None to skip.
    commission_multiplier: scales commissions and fees, e.g. 2.0 for the
        double-cost check.
    """

    def __init__(
        self,
        size: str,
        mode: str = "combine",
        rules: RuleSpec | None = None,
        dll_enabled: bool = False,
        payout_path: str = "standard",
        payout_policy: PayoutPolicy | None = request_max,
        commission_multiplier: float = 1.0,
    ) -> None:
        if mode not in ("combine", "xfa"):
            raise ValueError("mode must be 'combine' or 'xfa'")
        if payout_path not in ("standard", "consistency"):
            raise ValueError("payout_path must be 'standard' or 'consistency'")
        self.rules = rules or load_rules()
        self.spec: AccountSpec = self.rules.account(size)
        self.mode = mode
        self.dll_enabled = dll_enabled
        self.payout_path = payout_path
        self.payout_policy = payout_policy
        self.commission_multiplier = commission_multiplier
        self.tz = ZoneInfo(self.rules.session.timezone)
        self._flat_by = _shifted(self.rules.session.flat_by_ct)
        self._late = _shifted(self.rules.session.no_new_positions_after_ct)

        if mode == "combine":
            self.start = self.spec.starting_balance
            self.mll_amount = self.spec.mll
            self.mll_ceiling = self.start  # trail locks at the starting balance
        else:
            self.start = 0.0
            self.mll_amount = self.spec.xfa_mll
            self.mll_ceiling = 0.0  # trail locks at $0
        self.balance = self.start
        self.mll = self.start - self.mll_amount
        self.status = "active"
        self.positions: dict[str, _Position] = {}
        self.last_price: dict[str, float] = {}
        self.events: list[Event] = []
        self.days: list[DayRecord] = []
        self.fees_paid = 0.0

        self.day: date | None = None
        self.day_start_balance = self.balance
        self.day_trades = 0
        self.day_locked = False
        self.last_ts: datetime | None = None

        # Combine objectives
        self.trading_days = 0
        self.best_day = 0.0
        # XFA payout window (resets after each payout)
        self.payout_taken = False
        self.window_days: list[float] = []
        self.window_winning_days = 0
        self.window_start_balance = self.balance
        self.max_lots_today = self._max_lots()
        self.payouts_gross = 0.0
        self.payouts_to_trader = 0.0

    # ------------------------------------------------------------------ public
    @property
    def equity(self) -> float:
        return self.balance + self.open_pnl()

    def open_pnl(self) -> float:
        total = 0.0
        for sym, pos in self.positions.items():
            if pos.qty:
                px = self.last_price[sym]
                total += (px - pos.avg_price) * pos.qty * instruments.get(sym).point_value
        return total

    def open_lots(self) -> float:
        return sum(abs(p.qty) * instruments.get(s).mini_equivalent for s, p in self.positions.items())

    def process(self, item: Fill | Mark) -> list[Event]:
        """Feed one fill or mark. Returns the events it produced."""
        n_before = len(self.events)
        ts = item.ts
        if ts.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")
        if self.last_ts is not None and ts < self.last_ts:
            raise ValueError(f"out-of-order event at {ts} (last {self.last_ts})")
        self.last_ts = ts
        day, shifted = self._session_clock(ts)
        if self.day is None:
            self.day = day
        elif day != self.day:
            self._close_day(ts)
            self.day = day
            self._open_day()

        if isinstance(item, Fill):
            self._on_fill(item, shifted)
        else:
            self._on_mark(item, shifted)
        return self.events[n_before:]

    def finish(self, ts: datetime | None = None) -> SimResult:
        """Close the final trading day and return the result."""
        if self.day is not None:
            self._close_day(ts or self.last_ts)
            self.day = None
        return SimResult(
            mode=self.mode,
            size=self.spec.size,
            status=self.status,
            balance=self.balance,
            events=list(self.events),
            days=list(self.days),
            payouts_gross=self.payouts_gross,
            payouts_to_trader=self.payouts_to_trader,
        )

    def run(self, stream: Iterable[Fill | Mark]) -> SimResult:
        for item in stream:
            self.process(item)
        return self.finish()

    # ---------------------------------------------------------------- internals
    def _session_clock(self, ts: datetime) -> tuple[date, time]:
        shifted = ts.astimezone(self.tz) + _SHIFT
        return shifted.date(), shifted.time()

    def _emit(self, ts: datetime, kind: EventKind, **data) -> None:
        self.events.append(Event(ts, kind, data))

    def _fee(self, symbol: str, qty: int) -> float:
        return self.rules.commission_per_side[symbol.upper()] * abs(qty) * self.commission_multiplier

    def _max_lots(self) -> float:
        if self.mode == "combine":
            return self.spec.max_lots
        allowed = self.spec.scaling_plan[0].max_lots
        for tier in self.spec.scaling_plan:
            if self.balance >= tier.min_balance - 1e-6:
                allowed = tier.max_lots
        return min(allowed, self.spec.max_lots)

    def _on_fill(self, f: Fill, shifted: time) -> None:
        sym = f.symbol.upper()
        inst = instruments.get(sym)
        if f.qty == 0:
            return
        reason = None
        if self.status != "active":
            reason = f"account {self.status}"
        elif self.day_locked:
            reason = "daily loss limit hit; locked until next trading day"
        elif shifted >= self._flat_by:
            reason = "session closed (3:10 PM to 5:00 PM CT)"
        pos = self.positions.setdefault(sym, _Position())
        new_qty = pos.qty + f.qty
        if reason is None:
            lots_after = self.open_lots() + (abs(new_qty) - abs(pos.qty)) * inst.mini_equivalent
            if abs(new_qty) > abs(pos.qty) and lots_after > self.max_lots_today + 1e-9:
                reason = f"position limit: {lots_after:g} lots > {self.max_lots_today:g} allowed"
        if reason is not None:
            self._emit(f.ts, EventKind.REJECTED, symbol=sym, qty=f.qty, reason=reason)
            return
        if abs(new_qty) > abs(pos.qty) and shifted >= self._late:
            self._emit(f.ts, EventKind.LATE_ENTRY, symbol=sym, qty=f.qty)
        self._apply_fill(sym, f.qty, f.price)
        self.day_trades += 1
        self._check_risk(f.ts)

    def _apply_fill(self, sym: str, qty: int, price: float) -> None:
        inst = instruments.get(sym)
        pos = self.positions.setdefault(sym, _Position())
        fee = self._fee(sym, qty)
        self.balance -= fee
        self.fees_paid += fee
        if pos.qty == 0 or (pos.qty > 0) == (qty > 0):
            total = pos.qty + qty
            pos.avg_price = (pos.avg_price * pos.qty + price * qty) / total
            pos.qty = total
        else:
            closing = min(abs(qty), abs(pos.qty))
            sign = 1 if pos.qty > 0 else -1
            self.balance += (price - pos.avg_price) * closing * sign * inst.point_value
            remaining = pos.qty + qty
            if remaining == 0:
                pos.qty, pos.avg_price = 0, 0.0
            elif (remaining > 0) == (pos.qty > 0):
                pos.qty = remaining
            else:  # flipped through zero
                pos.qty, pos.avg_price = remaining, price
        self.last_price[sym] = price

    def _on_mark(self, m: Mark, shifted: time) -> None:
        self.last_price[m.symbol.upper()] = m.price
        if self.status != "active":
            return
        if shifted >= self._flat_by and self.open_lots() > 0:
            self._flatten(m.ts, EventKind.FORCED_FLAT, reason="open position at 3:10 PM CT")
            return
        self._check_risk(m.ts)

    def _flatten(self, ts: datetime, kind: EventKind, **data) -> None:
        closed = {}
        for sym, pos in self.positions.items():
            if pos.qty:
                closed[sym] = pos.qty
                self._apply_fill(sym, -pos.qty, self.last_price[sym])
        self._emit(ts, kind, closed=closed, balance=self.balance, **data)

    def _check_risk(self, ts: datetime) -> None:
        if self.status != "active":
            return
        eq = self.equity
        if eq <= self.mll + 1e-9:
            self._flatten(ts, EventKind.BREACH_MLL, equity=eq, mll=self.mll)
            self.status = "breached"
            return
        if self.dll_enabled and not self.day_locked:
            if eq - self.day_start_balance <= -self.spec.daily_loss_limit + 1e-9:
                self._flatten(ts, EventKind.DLL_HIT, day_pnl=eq - self.day_start_balance)
                self.day_locked = True

    def _open_day(self) -> None:
        self.day_start_balance = self.balance
        self.day_trades = 0
        self.day_locked = False
        self.max_lots_today = self._max_lots()

    def _close_day(self, ts: datetime) -> None:
        if self.open_lots() > 0 and self.status == "active":
            self._flatten(ts, EventKind.FORCED_FLAT, reason="position still open at day close")
        pnl = self.balance - self.day_start_balance
        traded = self.day_trades > 0
        if self.status == "active":
            if self.mode == "combine":
                self._combine_eod(ts, pnl, traded)
            else:
                self._xfa_eod(ts, pnl, traded)
        self.days.append(DayRecord(self.day, pnl, self.balance, self.mll, self.day_trades))
        self._emit(ts, EventKind.DAY_CLOSE, day=self.day, pnl=pnl, balance=self.balance, mll=self.mll)

    def _trail_mll(self) -> None:
        if self.payout_taken:
            self.mll = 0.0
            return
        self.mll = min(max(self.mll, self.balance - self.mll_amount), self.mll_ceiling)

    def _combine_eod(self, ts: datetime, pnl: float, traded: bool) -> None:
        if traded:
            self.trading_days += 1
            self.best_day = max(self.best_day, pnl)
        self._trail_mll()
        profit = self.balance - self.start
        target = self.effective_target()
        if self.trading_days >= self.spec.min_trading_days and profit >= target - 1e-9:
            self.status = "passed"
            self._emit(ts, EventKind.PASS, profit=profit, target=target, best_day=self.best_day,
                       trading_days=self.trading_days)

    def effective_target(self) -> float:
        """Profit target after the consistency rule: max(target, best day / 0.55)."""
        return max(self.spec.profit_target, self.best_day / self.spec.consistency_fraction)

    def _xfa_eod(self, ts: datetime, pnl: float, traded: bool) -> None:
        p = self.rules.payout
        if traded:
            self.window_days.append(pnl)
            if pnl >= p.standard_winning_day_min - 1e-9:
                self.window_winning_days += 1
        self._trail_mll()
        allowed = self.payout_allowed()
        if allowed is not None and self.payout_policy is not None:
            amount = self.payout_policy(self, allowed)
            if amount is not None and amount >= p.minimum - 1e-9:
                amount = min(amount, allowed)
                self.balance -= amount
                self.payouts_gross += amount
                self.payouts_to_trader += amount * p.trader_split
                self.payout_taken = True
                self.mll = 0.0
                self._emit(ts, EventKind.PAYOUT, amount=amount, to_trader=amount * p.trader_split,
                           path=self.payout_path, balance=self.balance)
                self.window_days = []
                self.window_winning_days = 0
                self.window_start_balance = self.balance
                if self.balance <= self.mll + 1e-9:
                    self.status = "breached"
                    self._emit(ts, EventKind.BREACH_MLL, equity=self.balance, mll=self.mll,
                               reason="balance at $0 after payout")

    def payout_allowed(self) -> float | None:
        """Largest payout allowed right now on this account's path, or None."""
        p = self.rules.payout
        net = self.balance - self.window_start_balance
        if self.payout_path == "standard":
            ok = self.window_winning_days >= p.standard_winning_days and (not self.payout_taken or net > 0)
            cap = self.spec.payout_cap_standard
        else:
            ok = (
                len(self.window_days) >= p.consistency_min_days
                and net > 0
                and max(self.window_days) <= p.consistency_max_fraction * net + 1e-9
            )
            cap = self.spec.payout_cap_consistency
        if not ok:
            return None
        amount = min(cap, p.max_fraction_of_balance * self.balance)
        return amount if amount >= p.minimum - 1e-9 else None


def _shifted(t: time) -> time:
    return (datetime.combine(date(2000, 1, 1), t) + _SHIFT).time()
