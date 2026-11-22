# sniper

Research lab for an intraday NQ/ES (and MNQ/MES) strategy aimed at passing Topstep Trading Combines and earning Express Funded Account payouts through the TopstepX API. This is research, not financial advice, and no backtest here predicts live results.

## Layout

| Path | What it is |
|---|---|
| `STATE.md` | Current phase, next actions, open questions. Read first. |
| `topstep_rules.yaml` | Machine-readable Topstep rules, each with source URL and verification date |
| `sniper/rules.py` | Loads the YAML into typed specs |
| `sniper/sim.py` | **TopstepSim**: replays fills and marks under Combine or XFA rules |
| `sniper/economics.py` | Cost per attempt and break-even pass rate; `python -m sniper.economics` |
| `ECONOMICS.md` | The economics write-up |
| `METHOD.md` | How a feature is tested: signal test, cost test, overfitting guards, data split |
| `LITERATURE.md` | One verified note per source |
| `feature_registry.csv` | Every hypothesis with mechanism, sign, horizon and kill criterion |
| `DATA.md` | Databento plan, budget, roll rule, Level 1 vs Level 2 |
| `sniper/signal.py` | Stage 1 signal-test harness: IC, overlap-corrected t, Holm, decay, look-ahead guard |
| `tests/` | One hand-built test per rule, for all three account sizes |

## Setup

```bash
pip install -e '.[dev]'
pytest
```

## TopstepSim in one example

```python
from datetime import datetime
from zoneinfo import ZoneInfo
from sniper import TopstepSim, Fill, Mark

ct = ZoneInfo("America/Chicago")
sim = TopstepSim("50K", mode="combine")          # or mode="xfa", payout_path="standard"
sim.process(Fill(datetime(2026, 11, 23, 9, 0, tzinfo=ct), "MNQ", 10, 20000.0))
sim.process(Mark(datetime(2026, 11, 23, 9, 5, tzinfo=ct), "MNQ", 19990.0))
result = sim.finish()
print(result.status, result.balance, [e.kind for e in result.events])
```

Feed it every fill and enough marks to see the worst open loss. With bar data, mark the adverse extreme of each bar (low for longs, high for shorts) before the close, because the Maximum Loss Limit is enforced on open losses in real time.

What it enforces: trailing end-of-day MLL with intraday breach on unrealized P&L and the lock at the starting balance (Combine) or $0 (XFA); MLL at $0 after the first payout; optional Daily Loss Limit; 55% consistency rule raising the target; 2 minimum trading days; contract limits at 10 micros per mini; XFA Scaling Plan from start-of-day balance; flat by 3:10 PM CT; late-entry flag after 3:08 PM CT; Standard and Consistency payout paths with caps, the 50% balance rule, the $125 minimum and the 90% split; TopstepX commissions with a multiplier for the double-cost check.

What it does not do: fill simulation and slippage (that belongs to the backtester), holiday calendars, news-time position-limit cuts, and multiple simultaneous accounts.
