# Iteration 02: stress test and strategy test of IMOM-04

_22 Nov 2026. Development period June 2010 to 31 Oct 2024; walk-forward year 1 Nov 2024 to 31 Oct 2025 used once. Holdout untouched._

## 1. Verdict

**KILL.** IMOM-04 as a strategy lost money in the walk-forward year: **−$38.26 per MNQ trade, t = −2.32** (measured, after assumed costs). Even in-sample, its best simulated Combine pass rate was 43%, below the 50% validity bar.

## 2. What was tested

- **Signal:** IMOM-04 on NQ, which uses the return from the prior 15:00 CT close to 14:30 CT, on high-volatility days only, to predict 14:30-15:00. ES was used for a combined check.
- **Rule (frozen before the Monte Carlo):** on a high-volatility day, buy MNQ at 14:30 CT if the day is up so far and sell if it is down. Exit at 15:00 CT. Each fill is 1 tick worse than the bar close, plus TopstepX fees of $1.22 per MNQ round trip. Variant B adds a 40-point stop.
- **Trials:** 8 this iteration (4 volatility cut-offs, 1 delayed entry, 1 ES+NQ, 2 strategy variants), **22 in total**.

## 3. Signal evidence (development, measured)

| Check | Result |
|---|---|
| Volatility cut-off at the 50th, 60th, 67th, 75th, 80th percentile | IC t = 3.25, 3.47, 4.10, 4.41, 3.52 |
| Leave one year out (67th percentile) | IC t between 3.24 (without 2022) and 4.22 |
| Entry delayed one minute (14:31 to 14:59) | IC +0.110, t = 3.96 |
| ES + NQ, one mini each | $92 a day, t = 2.79 |

The signal looked robust in-sample. The dollar t-statistics were always weaker, between 2.2 and 2.8, because a few large days dominate the dollars.

## 4. Trading evidence (per 1 MNQ, after assumed costs)

| | Dev: no stop | Dev: 40-pt stop | **Walk-forward: no stop** | **Walk-forward: 40-pt stop** |
|---|---|---|---|---|
| Trades | 1,269 | 1,269 | 95 | 95 |
| Mean net per trade | $3.75 | $4.18 | **−$38.26** | **−$16.52** |
| Win rate | 52.4% | 49.8% | 37.9% | 29.5% |
| Avg win / avg loss | $50 / −$48 | $49 / −$41 | $111 / −$130 | $113 / −$71 |
| Profit factor | 1.17 | 1.20 | 0.52 | 0.67 |
| Worst trade | −$573 | −$82 | −$551 | −$82 |
| t of mean | 1.68 | 2.30 | −2.32 | −1.71 |
| Mean at double cost | $1.53 | $1.96 | −$40.48 | −$18.74 |

The walk-forward losses were spread across the year (January, March and May 2025 each lost over $900 per MNQ), not concentrated in one event.

## 5. Prop-firm evidence (in-sample only, simulated)

The Monte Carlo used 2,000 paths of up to 750 days, drawn from development days in blocks of about 10 days. As a check, the fast simulation was replayed event by event through TopstepSim on 30 paths and gave the same pass or breach result on all 30.

| Account | Best pass rate (size) | Pass at a practical size | Median days to pass | XFA payout probability (Standard) |
|---|---|---|---|---|
| $50K | 43% (2 MNQ, but 465 days) | 35% at 10 MNQ | 52 | 53% |
| $100K | 42% (5 MNQ, 352 days) | 28% at 20 MNQ | 44 | 46% |
| $150K | 38% (10 MNQ, 221 days) | 31% at 20 MNQ | 76 | 62% |

(The table shows variant B, with the stop.)

**Does account size matter?** Not much for the pass rate. A larger account mostly lets the same strategy run at a larger size before it breaches. The pass rate peaks at roughly 35-43% on every size, and falls steadily as size grows past the peak. The expected value per attempt was at most about +$300 in-sample, before the walk-forward result removed it.

## 6. Overfitting checks

- The in-sample to walk-forward gap is the whole story. The expected profit went from +$4 to −$17/−$38 per trade.
- Deflated Sharpe and PBO were not computed. With a negative walk-forward result they cannot change the verdict.
- Researcher degrees of freedom: the volatility proxy was chosen after IMOM-02 showed strength in the high-volatility tercile (iteration 1 critique). The walk-forward result is consistent with that snooping.

## 7. Mistakes

- None found in the code. The fast simulation matched TopstepSim on 30 of 30 paths.
- A process lesson: stage 1 (rank IC) passed easily while the dollar t was never above 3. The METHOD change proposed in iteration 1 (fail stage 2 when the dollar t is below 2) would have kept the strategy, so it is not enough. Proposal: also require the dollar t ≥ 3 in-sample before stage 3.

## 8. Critique of the KILL

1. **One year is a small sample.** It has 95 trades, and 2025 was an unusual year (tariff shock, record 0DTE volumes). A one-year loss of t = −2.3 is unlikely if the in-sample edge were real, but not impossible. *Test:* re-run once the holdout year is opened for a future promoted candidate. Do not reopen this one to rescue it.
2. **Dealer positioning may have flipped.** Since 2022, 0DTE options may leave dealers net long gamma intraday, which would turn late-day momentum into reversal. *Test:* register "late-day reversal since 2023" as a new hypothesis with its own mechanism. Count it as a new trial, and treat it with suspicion because it was suggested by this result.
3. **The volatility proxy is not gamma.** A direct gamma-exposure series might separate the regimes properly. *Test:* price a dealer-gamma dataset.

## 9. Suggestions

**Finding features:** move to features whose mechanism does not depend on the options market regime: RV-01 (NQ/ES spread reversion), MR-02, MR-04, TREND-01/02 as calibration, LEADLAG-01 at 1-second bars. Register IMOM-07 (late-day reversal, post-2022) with an explicit warning that it was suggested by this result.

**Testing features:** add the in-sample dollar t ≥ 3 gate before stage 3. Run the walk-forward check as soon as the signal passes, before building the Monte Carlo, to save effort.

## 10. Next iteration plan

1. Apply the two METHOD changes (dollar t reported and gated).
2. Stage 1 and 2 on TREND-01, TREND-02, MR-02, MR-04, RV-01 using the existing bars.
3. Price 1-second bars for ES and NQ for 2022-2024 (LEADLAG-01) against the remaining budget.

## Independent review

Not required: nothing is being promoted.
