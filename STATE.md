# STATE

_Last updated: 22 Nov 2026_

## Where we are

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

## Next actions

1. Waiting on Ben: build the bot and paper trade, study sizing first, or keep searching.

## Open questions for Ben

1. The direction above.
2. Confirm on Databento's billing page that the free credit covered the spend so far (estimated $114.86 in total).
