# STATE

_Last updated: 22 Nov 2026_

## Where we are

- **Phase:** loop iteration 5 done. All tested families have failed; waiting on Ben's direction for iteration 6.
- **Last verdict:** KILL (reports/iter_05.md). Order-flow imbalance has no forecast power at 1-15 minutes (best IC +0.007, t 0.5); limit-order reversal loses after fees. Trials run: 45.
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
- Iteration 5: Aug-Oct 2024 ES and NQ trades bought ($64.08, approved by Ben). OFI-01, OFI-04 fail; limit-order MR-04 loses to adverse selection.
- Iteration 3: TREND-01/02, MR-02 fail; MR-04 (5-minute reversal) and RV-01 (NQ/ES spread) are real but not tradable.

## Findings so far (from reading, not data)

- Order-flow and order-book papers (Cont-Kukanov-Stoikov, Xu-Gould-Howison) measure **same-interval** relationships, and deep-book forecasting lasts about two price changes (Kolm et al.). Level 2 is probably out of reach for a home bot; OFI-03 tests this cheaply.
- The opening-range breakout's published 33% was net of commissions only; a replication found about zero after spread and slippage on NQ.
- Micros cost about 3.2 times more in fees per dollar of exposure than minis (MNQ 4.4 ticks round trip all-in vs NQ 2.8, assumed).

## Next three actions (Ben to choose direction)

1. Event and calendar conditioning on existing data: CAL-01, CAL-02.
2. Price a dealer-gamma / options-positioning data source for a direct test of IMOM-04's mechanism.
3. Zero-edge baseline: what pass rate and expected dollars Topstep's rules give a no-edge strategy under different sizing and stop policies.

## Open questions for Ben

1. Which of the three directions above to take next (reports/iter_05.md, section 10).
2. Confirm on Databento's billing page that the free credit covered the spend so far (estimated $113.57 in total).
