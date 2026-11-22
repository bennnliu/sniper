# STATE

_Last updated: 22 Nov 2026_

## Where we are

- **Phase:** loop iteration 2 done. Next: iteration 3 on new hypotheses (Phase 2 signal tests).
- **Last verdict:** KILL (reports/iter_02.md). IMOM-04 lost $38 per MNQ trade (t −2.32) in the walk-forward year; in-sample Combine pass rate peaked at 43%. Trials run: 22.
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

## Findings so far (from reading, not data)

- Order-flow and order-book papers (Cont-Kukanov-Stoikov, Xu-Gould-Howison) measure **same-interval** relationships, and deep-book forecasting lasts about two price changes (Kolm et al.). Level 2 is probably out of reach for a home bot; OFI-03 tests this cheaply.
- The opening-range breakout's published 33% was net of commissions only; a replication found about zero after spread and slippage on NQ.
- Micros cost about 3.2 times more in fees per dollar of exposure than minis (MNQ 4.4 ticks round trip all-in vs NQ 2.8, assumed).

## Next three actions

1. Stage 1 and 2 (with the new dollar-t gate) on TREND-01, TREND-02, MR-02, MR-04, RV-01 using the existing bars.
2. Register IMOM-07 (late-day reversal since 2023) as a new, flagged hypothesis suggested by iteration 2.
3. Price ES and NQ 1-second bars for 2022-2024 (LEADLAG-01) against the remaining budget.

## Open questions for Ben

1. None blocking. Data spend so far is about $49 estimated, expected to come from the $125 free credit; the $50 paid cap is untouched unless Databento billed it.
