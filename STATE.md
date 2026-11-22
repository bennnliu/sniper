# STATE

_Last updated: 22 Nov 2026_

## Where we are

- **Phase:** loop iteration 3 done. Next: Level 1 data (needs Ben's approval) or the remaining low-priority bar hypotheses.
- **Last verdict:** KILL (reports/iter_03.md). Trend, overnight-level reversal, 5-minute reversal and NQ/ES spread all fail costs; three are real but at most 0.22x cost. Trials run: 31.
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
- Iteration 3: TREND-01/02, MR-02 fail; MR-04 (5-minute reversal) and RV-01 (NQ/ES spread) are real but not tradable.

## Findings so far (from reading, not data)

- Order-flow and order-book papers (Cont-Kukanov-Stoikov, Xu-Gould-Howison) measure **same-interval** relationships, and deep-book forecasting lasts about two price changes (Kolm et al.). Level 2 is probably out of reach for a home bot; OFI-03 tests this cheaply.
- The opening-range breakout's published 33% was net of commissions only; a replication found about zero after spread and slippage on NQ.
- Micros cost about 3.2 times more in fees per dollar of exposure than minis (MNQ 4.4 ticks round trip all-in vs NQ 2.8, assumed).

## Next three actions

1. If Ben approves: buy about 3 months of ES and NQ `trades` (~$62) and test OFI-01 and a limit-order MR-04, with a limit-order fill simulator.
2. With no spend: IMOM-06, CAL-02, TREND-03 on bars.
3. Register IMOM-07 (late-day reversal since 2023), flagged as suggested by iteration 2.

## Open questions for Ben

1. Approve Level 1 (tick) data spend? About 3 months of ES and NQ trades is roughly $62; a full year is about $205.
