# Final summary: strategy search stopped (23 Nov 2026)

Ben chose to stop the search on 23 Nov 2026 after 290 trials. This is research, not financial advice. All results are measured on historical data unless marked otherwise.

## Outcome

No strategy was found that passes a Topstep Combine consistently within 30 trading days. Nothing was promoted and nothing should be traded live on the basis of this work.

## Why

A 30-day pass at a useful rate needs a daily Sharpe ratio near 2.4. A strategy with no edge passes about 10 to 15% of the time within 30 trading days (simulated). The best real signal found sits far below that.

## What was tested

| Family | Trials | Result |
|---|---|---|
| ES and NQ bar signals: opening range, momentum, VWAP, gaps, reversal, trend, calendar, news | 1 to 191 | One real edge: the NQ noise-area breakout. It passed its one-time holdout weakly (t 1.05) and was not promoted. |
| Filters, sizing, stops, ensembles on that edge | to 232 | Looked good in development, flat on the walk-forward year (30-day pass 8.8% against 15.1% for the control) and lost on a live check week. |
| Order-flow imbalance on trades data | 10 | No forecast power at 1 to 15 minutes. |
| Breakout rule on nine other markets | 10 | Loses after costs in all nine. |
| VIX term structure, VVIX | 10 | Best t 2.58, below the bar. |
| Cross-market lead-lag | 24 | Edge at most a quarter of cost. |
| Currency and gold session drift | 8 | Negative after costs. |
| Dealer gamma from ES option open interest | 6 | Forecasts range (t -6.7, every year), not direction. |

## What is true and reusable

- The NQ and ES intraday breakout edge is real but small, and specific to equity index futures.
- Overnight continuation in NQ and ES is real but below trading cost.
- Dealer gamma and the VIX term structure forecast how far the market moves in the New York session.
- Skipping days with filters lowers the 30-day pass rate, because the clock keeps running.
- News windows are 2 to 3.6 times as volatile as normal.

## Data and spend

- First Databento credit: about $125, used.
- Second key: $116.92 of $150 spent; about $33 unspent. Log in `data_spend.csv`.
- Untouched: the walk-forward year (Nov 2024 to Oct 2025) for the nine new markets, and all holdout data from Nov 2025 for them. The NQ holdout year is spent.
- Raw files are in project files under `data/raw/`.

## If the search is ever reopened

The ideas not tested are slower strategies (60 or more trading days to pass), full option positioning data (about $201, judged unlikely to help), and long-history order-book data (far over budget). Every new trial adds to the 290 already counted, so the bar for believing a result is higher than it was at the start.

Full records: `reports/NEW_STRATEGY_LOG.md`, `reports/SECOND_EDGE_LOG.md`, `experiments.csv`, `feature_registry.csv`.
