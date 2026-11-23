# STATE

_Last updated: 23 Nov 2026_

## Where we are

- **New strategy loop (23 Nov 2026, iterations 32 to 36):** log in reports/NEW_STRATEGY_LOG.md. Nine other markets, VIX measures, cross-market lead-lag, currency and gold session drift, dealer gamma: all fail. 290 trials. New Databento key: $116.92 of $150 spent. Dealer gamma and VIX term structure forecast range, not direction. Walk-forward year for the nine new markets is unopened; holdout not bought.

- **Latest (23 Nov 2026):** iteration 31. Final rule (ENS-01 + LOSS-01 C3) is roll-robust but flat on the walk-forward year ($468) and lost $5,904 on Yahoo 16-20 Nov. 232 trials. See reports/SECOND_EDGE_LOG.md.
- **Phase:** loop iteration 5 done. All tested families have failed; waiting on Ben's direction for iteration 6.
- **Last verdict:** KILL (reports/iter_05.md). Order-flow imbalance has no forecast power at 1-15 minutes (best IC +0.007, t 0.5); limit-order reversal loses after fees. Trials run: 50.
- **Account sizes:** test all three ($50K, $100K, $150K) and compare outcomes (Ben, 22 Nov 2026).
- **Validity bar:** the defaults in the project brief, confirmed by Ben on 22 Nov 2026.
- **Data budget:** Databento; bars from the $125 free credit (expires 6 months after signup); hard cap of $50 paid before any tick data (Ben, 22 Nov 2026).

## Done

- Phase 1: `topstep_rules.yaml` (verified 22 Nov 2026; XFA Scaling Plan confirmed against Topstep's chart), `TopstepSim` with tests, `ECONOMICS.md`.
- Phase 2: `METHOD.md`, fixed before any test. Data split: development to 31 Oct 2024, walk-forward 1 Nov 2024 to 31 Oct 2025, holdout from 1 Nov 2025.
- Phase 3: `LITERATURE.md` (26 sources, each marked read or exists), `feature_registry.csv` (37 hypotheses in 10 families).
- Phase 4 groundwork: `DATA.md`; `sniper/signal.py` signal-test harness; `sniper/data.py` loader with holdout guard.
- Data: ES and NQ 1-minute bars, June 2010 to 31 Oct 2025 (holdout not bought). Estimated spend $49.49 (log in `data_spend.csv`), expected from the free credit. Raw files also in project files under `data/raw/`.
- Iteration 1: 7 hypotheses on ES and NQ. Gao et al.'s first-half-hour effect does not replicate; VWAP and gap reversion show nothing.
- Iteration 2: IMOM-04 robust in-sample, built into a strategy, replayed through TopstepSim (fast engine validated 30/30 against it) for all three sizes, then killed by the walk-forward year. Account size changed the best size, not the best pass rate (35-43% on all three).
- `sniper/montecarlo.py`: block-bootstrap Monte Carlo for Combine and XFA outcomes.
- Iteration 7: FOMC drift (CAL-01) and post-release continuation (CAL-05) fail on ES and NQ. Release windows are 2 to 3.6 times as volatile (CAL-02), kept as a no-trade and sizing rule. 60 trials in total. Event dates in `calendar_data/events.csv` (FOMC 2021-2023 unverified).
- Iteration 6: zero-edge baseline. No-edge trading passes the $50K Combine about 22% of the time and is worth about $0 per attempt after fees (simulated). This is the bar a strategy must beat.
- Iteration 5: Aug-Oct 2024 ES and NQ trades bought ($64.08, approved by Ben). OFI-01, OFI-04 fail; limit-order MR-04 loses to adverse selection.
- Iteration 3: TREND-01/02, MR-02 fail; MR-04 (5-minute reversal) and RV-01 (NQ/ES spread) are real but not tradable.

## Findings so far (from reading, not data)

- Order-flow and order-book papers (Cont-Kukanov-Stoikov, Xu-Gould-Howison) measure **same-interval** relationships, and deep-book forecasting lasts about two price changes (Kolm et al.). Level 2 is probably out of reach for a home bot; OFI-03 tests this cheaply.
- The opening-range breakout's published 33% was net of commissions only; a replication found about zero after spread and slippage on NQ.
- Micros cost about 3.2 times more in fees per dollar of exposure than minis (MNQ 4.4 ticks round trip all-in vs NQ 2.8, assumed).

## Status: search resumed (22 Nov 2026, Ben's request); one candidate under revision

Iteration 8 (reports/iter_08.md): second literature pass (2024 onward) and five niche features. **NOISE-01B on NQ** (noise-area breakout with a VWAP stop) passes the dollar test (t 3.30), parameter sensitivity and the walk-forward check (+$296 per traded day per NQ, t 0.93). Simulated on MNQ: $50K Combine pass 47% (development) and 27% (walk-forward year) against a 22% zero-edge baseline. **Not promotable:** deflated Sharpe 0.81 (bar 0.95), edge concentrated in 2018 and later. The walk-forward year has now been used for this rule; do not tune on it. 85 trials in total.

Also in iteration 8: overnight drift (OD-01) replicates but is below cost; EOD-01, IMOM-07, REG-01 fail. Features live in `sniper/features.py` and `sniper/noise.py`.

Iteration 9 (reports/iter_09.md): in volatility units the development t falls to 2.21 (below 3); the edge is absent in 2010-2017 and present in 2018-2024. Measured spread at fill times is about 2 ticks, matching the assumption. 86 trials.

Iteration 10 (reports/iter_10.md): **holdout test PASSED** on the three pre-written conditions (NQ, Nov 2025 to Oct 2026: +$287 per traded day per contract, t 1.05; +$267 at 2x cost; simulated $50K Combine pass 35% at 2 MNQ against a 22% baseline). Not promoted: development deflated Sharpe 0.81 is below the 0.95 bar, and Dec 2025 to Jan 2026 would have breached a $50K account. **The NQ holdout year is now spent (use number 1).** 87 trials.

Iteration 11 (reports/iter_11.md): Ben's new goals applied (sessions tested separately, 30-day limit, payout/(cost x accounts x days) measure in `sniper/propscore.py`, news filter). The rule works only in New York hours. Within 30 days the best plan is 8 MNQ on $50K: 28.9% pass on development data, 12.5% on the walk-forward year, random-direction control 15%. News skipping, entry/exit limits and the ML filter do not help (ML filter failed its walk-forward check). A 30-day pass above 50% needs about 3x this edge. 105 trials. Walk-forward year used three times for this rule.

Iteration 12 (reports/iter_12.md): search for a second unrelated edge on ES/NQ bars. Overnight and session drift, day/night reversal, turn of month, London fade and NQ-over-ES continuation all fail (25 tests, news days skipped, micro costs). 130 trials. Conclusion: ES/NQ bars are exhausted; an unrelated edge needs another market.

Iterations 13-19 (reports/SECOND_EDGE_LOG.md, one running log; 23 Nov 2026): research loop for a second edge that complements the breakout rule. 45 tests, none succeeded, 175 trials in total. Real but below cost: overnight NQ/ES continuation (t 4.5), one-minute lead-lag. Near miss: pre-holiday long in New York hours (MES t 2.67, 7 days a year). Correction: with a hard stop at 30 trading days, fixed 8 MNQ passes about 15% against 10% for random direction (iteration 11's 28.9% counted passes after day 30). No filter on the first edge helps a 30-day Combine. The walk-forward year was not used again (no check was triggered); it stays at three uses for this rule.

Iterations 20-22 (same log): parameter ensemble, ES+NQ, dynamic-programming sizing and constant-risk sizing all fail. 184 trials. Sizing is closed: the edge adds 3 to 7 points of 30-day pass rate at any size; larger size lifts the random control equally.

Iteration 23 (same log): thresholded overnight-to-close, weekend and weekday effects all fail. 191 trials. **The research loop is paused, waiting on data**: every idea family testable on ES/NQ bars has been tested; further rounds would be data mining.

## Next actions

1. Resume the loop when any of these arrives: free VIX/FRED data (hosts cdn.cboe.com and fred.stlouisfed.org are blocked by the environment network policy; Ben can allow them or upload CSVs), other-markets bars (decision card of 22 Nov, unapproved), or options positioning data (priced earlier).
2. Before any other-markets test: read Topstep's "Prohibited Conduct" page for micro-contract restrictions.

## Open questions for Ben

1. Which of the three data routes to open.
2. Confirm on Databento's billing page that the free credit covered the spend so far (estimated $114.86 in total).
