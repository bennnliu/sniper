# STATE

_Last updated: 22 Nov 2026_

## Where we are

- **Phase:** 3 done on paper (method, literature, registry). Next is Phase 4 groundwork: get data and run the first signal tests. Iteration 0, before the first research loop.
- **Last verdict:** none yet. No feature has touched data. Trials run: 0.
- **Account sizes:** test all three ($50K, $100K, $150K) and compare outcomes (Ben, 22 Nov 2026).
- **Validity bar:** the defaults in the project brief, confirmed by Ben on 22 Nov 2026.
- **Data budget:** Databento; bars from the $125 free credit (expires 6 months after signup); hard cap of $50 paid before any tick data (Ben, 22 Nov 2026).

## Done

- Phase 1: `topstep_rules.yaml` (verified 22 Nov 2026; XFA Scaling Plan confirmed against Topstep's chart), `TopstepSim` with tests, `ECONOMICS.md`.
- Phase 2: `METHOD.md`, fixed before any test. Data split: development to 31 Oct 2024, walk-forward 1 Nov 2024 to 31 Oct 2025, holdout from 1 Nov 2025.
- Phase 3: `LITERATURE.md` (26 sources, each marked read or exists), `feature_registry.csv` (37 hypotheses in 10 families).
- Phase 4 groundwork: `DATA.md`; `sniper/signal.py` signal-test harness with tests.

## Findings so far (from reading, not data)

- Order-flow and order-book papers (Cont-Kukanov-Stoikov, Xu-Gould-Howison) measure **same-interval** relationships, and deep-book forecasting lasts about two price changes (Kolm et al.). Level 2 is probably out of reach for a home bot; OFI-03 tests this cheaply.
- The opening-range breakout's published 33% was net of commissions only; a replication found about zero after spread and slippage on NQ.
- Micros cost about 3.2 times more in fees per dollar of exposure than minis (MNQ 4.4 ticks round trip all-in vs NQ 2.8, assumed).

## Next three actions

1. Ben: allow `hist.databento.com` in the cloud environment's network settings and store the API key as the secret `DATABENTO_API_KEY` (DATA.md).
2. Price and pull ES and NQ 1-minute bars (development period only; the loader refuses holdout dates), build the cleaner and session calendar.
3. Run stage 1 on the priority-1 hypotheses: IMOM-01, IMOM-02, IMOM-05, MR-01, MR-03, with VOL-01, VOL-03 and CAL-02 as filters. Write `reports/iter_01.md`.

## Open questions for Ben

1. The two Databento setup steps above.
