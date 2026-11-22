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

## Status: search paused (22 Nov 2026, Ben's decision)

Ben declined the options-positioning data purchase and paused the search. Overall summary: `reports/SUMMARY.md`. Nothing is promoted.

## If the search resumes

1. NQ options open interest from Databento for a dealer-gamma test ($47.63, priced in DATA.md, needs approval).
2. Remaining free bar tests: CAL-03, VOL filters.
3. Re-verify `topstep_rules.yaml` if after 22 Dec 2026.

## Open questions for Ben

1. Confirm on Databento's billing page that the free credit covered the spend so far (estimated $113.57 in total).
