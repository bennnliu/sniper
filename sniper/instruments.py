"""Contract specifications for the CME equity-index futures we trade.

Values are exchange contract specs (CME Group), not Topstep rules.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Instrument:
    symbol: str
    point_value: float  # dollars per 1.0 index point per contract
    tick_size: float  # minimum price increment in index points
    is_micro: bool
    mini_equivalent: float  # contracts of the mini this contract counts as

    @property
    def tick_value(self) -> float:
        return self.point_value * self.tick_size


INSTRUMENTS: dict[str, Instrument] = {
    "ES": Instrument("ES", 50.0, 0.25, False, 1.0),
    "NQ": Instrument("NQ", 20.0, 0.25, False, 1.0),
    "MES": Instrument("MES", 5.0, 0.25, True, 0.1),
    "MNQ": Instrument("MNQ", 2.0, 0.25, True, 0.1),
}


def get(symbol: str) -> Instrument:
    try:
        return INSTRUMENTS[symbol.upper()]
    except KeyError as exc:
        raise KeyError(f"unknown instrument {symbol!r}; known: {sorted(INSTRUMENTS)}") from exc
