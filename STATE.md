# STATE

_Last updated: 22 Nov 2026_

## Where we are

- **Phase:** 1 (Topstep rule spec), finishing. Iteration 0, before the first research loop.
- **Last verdict:** none yet. No strategy has been tested. Trials run: 0.
- **Account sizes:** test all three ($50K, $100K, $150K) and compare outcomes (Ben, 22 Nov 2026).
- **Validity bar:** the defaults in the project brief, confirmed by Ben on 22 Nov 2026.

## Done in Phase 1

- `topstep_rules.yaml`: every figure re-read on Topstep's help center on 22 Nov 2026, with source and status per value.
- `TopstepSim` (`sniper/sim.py`) with 59 hand-built tests covering every rule on all three sizes, including an intraday breach on unrealized loss.
- `ECONOMICS.md`: cost per attempt and break-even pass rate (assumed figures).

## Findings that differ from the brief

- XFA payouts are also limited by the Scaling Plan, which starts at 2 lots (50K) or 3 lots (100K, 150K) and grows with balance. This is from secondary sources because Topstep shows the table only as an image.
- A minimum of 2 trading days applies to the Combine.
- The no-activation-fee Combine path ($95/$149/$229 a month, $0 activation) exists alongside the standard path ($49/$99/$199 a month, $149 activation).
- The API costs $29 a month, or $14.50 with Topstep's code, billed by Sim2Funded Solutions. Live Funded Accounts cannot trade through the API.
- Topstep gives no numeric definition of high-frequency trading. Its examples describe hundreds of trades a day held for seconds.

## Next three actions

1. Phase 2: research current practice and write `METHOD.md` (signal test, cost test, purged cross-validation, deflated Sharpe, trial counting).
2. Phase 3: literature review into `LITERATURE.md` and at least 30 hypotheses in `feature_registry.csv`, each with mechanism, sign, horizon and kill criterion.
3. Phase 4 groundwork: compare data vendors in `DATA.md` (Databento first) and build the bar loader and signal-test harness.

## Open questions for Ben

1. Confirm the XFA Scaling Plan numbers against the image on Topstep's Scaling Plan page (`topstep_rules.yaml` → `open_items`).
2. Data budget: Phase 3 needs years of 1-minute NQ/ES bars. Is a paid vendor such as Databento acceptable, and at what monthly limit?
