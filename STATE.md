# STATE

_Last updated: 22 Nov 2026_

## Where we are

- **Phase:** loop iteration 1 done (stage 1 and 2 signal tests). Next: robustness and stage 3 strategy test for IMOM-04 on NQ.
- **Last verdict:** REVISE (reports/iter_01.md). IMOM-04 NQ: high-volatility-day late momentum, IC +0.114, t 4.10, 4.3x NQ cost. Trials run: 14.
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

## Findings so far (from reading, not data)

- Order-flow and order-book papers (Cont-Kukanov-Stoikov, Xu-Gould-Howison) measure **same-interval** relationships, and deep-book forecasting lasts about two price changes (Kolm et al.). Level 2 is probably out of reach for a home bot; OFI-03 tests this cheaply.
- The opening-range breakout's published 33% was net of commissions only; a replication found about zero after spread and slippage on NQ.
- Micros cost about 3.2 times more in fees per dollar of exposure than minis (MNQ 4.4 ticks round trip all-in vs NQ 2.8, assumed).

## Next three actions

1. IMOM-04 robustness: volatility cut-off sweep, leave-one-year-out, one-bar entry delay, ES+NQ combined (each counted as a trial).
2. Stage 3: rule for IMOM-04, event-driven backtest with conservative fills, replay through TopstepSim for $50K/$100K/$150K, Monte Carlo on resampled days.
3. Apply the METHOD change proposed in iter_01 (report dollar t next to IC) and test TREND-01/02, MR-02, MR-04, RV-01.

## Open questions for Ben

1. None blocking. Data spend so far is about $49 estimated, expected to come from the $125 free credit; the $50 paid cap is untouched unless Databento billed it.
