# Iteration 01: first signal tests on 1-minute bars

_22 Nov 2026. Development period only (June 2010 to 31 Oct 2024). No walk-forward or holdout data was used._

## 1. Verdict

**REVISE.** One candidate is worth a strategy test: **IMOM-04 on NQ** (late-day momentum on high-volatility days), with rank IC **+0.114, t = 4.10** (measured) and an average move 4.3 times the assumed NQ round-trip cost. Everything else failed or is marginal.

## 2. What was tested

- **Data:** ES and NQ front-month 1-minute bars from Databento (`.v.0`, volume roll), 3,585 full day sessions (8:30-15:00 CT) after removing half days, holidays and roll days (measured).
- **Hypotheses:** IMOM-01, IMOM-02, IMOM-03, IMOM-04, IMOM-05, MR-01, MR-03, each on ES and NQ.
- **Trials:** 14 this iteration, 14 in total (`experiments.csv`). Each feature-symbol pair counts as one trial; horizons within a feature are covered by the Holm adjustment.

## 3. Signal evidence (stage 1, measured)

| Feature | What it is | ES IC (t) | NQ IC (t) | Stage 1 |
|---|---|---|---|---|
| IMOM-01 | First half hour → last half hour | −0.006 (−0.32) | −0.009 (−0.48) | fail both |
| IMOM-02 | Prior close to 14:30 → last half hour | +0.044 (+2.36) | +0.025 (+1.34) | fail both |
| IMOM-03 | Overnight + first half hour → last half hour | −0.002 (−0.11) | −0.001 (−0.06) | fail both |
| IMOM-04 | IMOM-02 on high-volatility days only | +0.104 (+3.43) | **+0.114 (+4.10)** | **NQ pass**; ES fails year stability (69% < 70%) |
| IMOM-05 | First 5-minute bar → rest of day | +0.048 (+2.59) | **+0.071 (+3.90)** | NQ pass; ES fail |
| MR-01 | Distance from VWAP → next 15-60 min | −0.004 (−0.90) | +0.000 (+0.08) | fail both |
| MR-03 | Opening gap → first 30-90 min | +0.002 (+0.08) | −0.031 (−1.69) | fail both |

**IMOM-04 detail.** "High volatility" means the trailing 20-day volatility is above its own expanding two-thirds quantile, using only data before the day. On those days (1,269 for NQ) the IC is +0.114; on the other days it is −0.063. The difference has z = 5.08 (NQ) and 3.01 (ES), so the registered kill criterion (no difference) is not met. This matches Baltussen et al.'s mechanism: dealers who are short gamma, more likely in volatile markets, hedge in the direction of the day's move into the close.

**The Gao et al. result does not replicate here.** The first half hour does not predict the last half hour in ES or NQ futures in 2010-2024 (t below 0.5 on both).

## 4. Trading evidence (stage 2 cost test, measured gross, costs assumed)

| Rule | Trades | Mean gross per trade | Hit rate | t of mean | × cost (mini) | × cost (micro) |
|---|---|---|---|---|---|---|
| IMOM-04 NQ: trade 14:30-15:00 in the direction of the day, high-vol days only | 1,269 | 2.99 NQ points ($59.80 per NQ, $5.98 per MNQ) | 55.1% | 2.68 | 4.3 | 2.7 |
| IMOM-04 ES: same | 1,082 | 0.89 ES points ($44.50 per ES) | 53.2% | 2.42 | 2.7 | 1.8 (fails 2× at double cost) |
| IMOM-05 NQ: trade 8:35-15:00 in the direction of the first 5-minute bar | 3,527 | 1.50 NQ points | 52.1% | 0.91 | 2.2 | 1.4 (fail) |

Assumed costs: NQ 2.76 ticks, MNQ 4.44 ticks, ES 1.30 ticks, MES 1.98 ticks per round trip (METHOD.md §4). The cost test passes IMOM-04 on NQ and MNQ, IMOM-04 on ES minis only, and IMOM-05 on NQ minis only.

Year by year, IMOM-04 NQ had a negative mean in 5 of 14 years (2012, 2016, 2017, 2019, 2024). IMOM-05 NQ was negative every year from 2021 to 2024.

## 5. Prop-firm evidence

Not run yet. No strategy has passed stage 2 cleanly enough to replay through TopstepSim.

## 6. Overfitting checks

- The 14 trials are logged. With 14 trials, the expected maximum |t| under no effect is roughly 2.4. IMOM-04 NQ's t = 4.10 clears that and the t ≥ 3.0 hurdle (assumed approximation).
- **IMOM-04 was registered before the test** ("stronger on high-volatility, down-trending days"). The test used only the volatility half of that proxy. The "down-trending" half was not tested, and the choice of the two-thirds quantile cut-off is one researcher degree of freedom: count it.
- No parameter sweep, deflated Sharpe, PBO or walk-forward yet. Those start at stage 3.

## 7. Mistakes

- The first NQ download was cut off at 29 May 2017 without an error. Caught by the quality report (only 1,783 trading days), re-pulled for an estimated $10.83, and merged. Lesson: check row counts and the date range after every pull.
- Stage 1 for IMOM-05 passed on rank IC but the dollar P&L has t = 0.91. Rank IC ignores the size of moves. A day-session move is dominated by a few large days, so ranks can agree while dollars do not. METHOD.md should require the stage 2 dollar t-statistic to be reported next to the IC (change proposed below).

## 8. Critique: why IMOM-04 might be false

1. **It is a regime artefact.** A few volatile years (2015, 2021, 2022) may carry the result. *Test:* drop each year in turn and see whether t stays above 3; run the walk-forward year (Nov 2024 to Oct 2025) once the strategy is frozen.
2. **The volatility cut-off was chosen after seeing that IMOM-02 was strong in the high-vol tercile.** That is a form of data snooping, even though IMOM-04 was registered. *Test:* vary the cut-off (median, 60th, 75th, 80th percentile) and require the result to hold across all of them; count each as a trial.
3. **The fill is unrealistic.** Entering exactly at the 14:30 bar close and exiting at the 15:00 close ignores slippage around the close and the cash-close auction. *Test:* enter one bar later, exit at 14:59, and double the slippage.

## 9. Suggestions

**Finding features (Phases 2 and 3)**
- Add a direct dealer-gamma measure. CBOE or third-party gamma-exposure data would let us test Baltussen's mechanism instead of a volatility proxy. Price it first.
- Register a combined NQ and ES version of IMOM-04 (trade both) as a new hypothesis rather than tuning one symbol.

**Testing features (Phases 4 to 6)**
- METHOD change: report the stage 2 dollar t-statistic next to the IC, and fail stage 2 when the gross P&L t is below 2 (it would kill IMOM-05 NQ).
- Add a leave-one-year-out check to stage 1.

## 10. Next iteration plan

1. IMOM-04 NQ: robustness (cut-off sweep, leave-one-year-out, entry delay, ES and NQ together), then stage 3: build the rule, replay it through TopstepSim for $50K, $100K and $150K, and run the Monte Carlo on resampled days.
2. Remaining priority-1 filters: VOL-03 (time-of-day normalisation) and CAL-02 (macro-release windows), applied to IMOM-04.
3. Next priority-2 hypotheses on bars: TREND-01/02 (pipeline calibration), MR-02, MR-04, RV-01.

## Independent review

Not required: nothing is being promoted.
