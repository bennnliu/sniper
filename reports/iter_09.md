# Iteration 09: stress tests on the NQ noise-area breakout (NOISE-01B)

_22 Nov 2026. Development period only. No parameters changed. No data spend. Holdout untouched._

## 1. Verdict

**REVISE, and weaker than it looked.** Once results are measured in units of each day's expected move instead of dollars, the development-period t-statistic falls from 3.30 to **2.21**, below the bar of 3. The rule did nothing from 2010 to 2017 (t −0.36) and worked from 2018 to 2024 (t 3.94). Either something changed in the market around 2018, or this is luck found after 86 trials. Development data cannot tell these apart; only untouched data can.

## 2. What was tested

1. Does the edge depend on the volatility regime?
2. Does it survive when the growth of the index level is removed (volatility units)?
3. Is the assumed slippage realistic at the times the rule trades?

Trials: 1 new (the volatility-unit restatement), **86 in total**.

## 3. Evidence (measured)

**By volatility tercile (lagged 20-day daily volatility):**

| Tercile | Traded days | Net per traded day per NQ | t (dollars) | Mean in volatility units | t (volatility units) |
|---|---|---|---|---|---|
| Low | 729 | +$31 | 1.36 | +0.016 | 0.64 |
| Mid | 685 | +$85 | 2.15 | +0.028 | 1.33 |
| High | 679 | +$137 | 2.22 | +0.041 | 2.23 |

Positive in all three and rising with volatility. It is not purely a high-volatility bet, but most of the money comes from volatile periods.

**In volatility units** (net points ÷ prior close × 20-day daily volatility): mean +0.028 of a daily move per traded day, **t 2.21**. By year: 2010 −0.25, 2011 +0.02, 2012 +0.04, 2013 −0.02, 2014 +0.02, 2015 +0.05, 2016 −0.06, 2017 +0.02, 2018 +0.17, 2019 −0.01, 2020 +0.05, 2021 +0.05, 2022 +0.05, 2023 +0.08, 2024 +0.06. Positive in 73% of years.

**Early versus late** (split chosen after seeing the yearly table, so descriptive only): 2010-2017 mean −0.007, t −0.36; 2018-2024 mean +0.067, t 3.94.

**Measured spread on the NQ trade tape, Aug-Oct 2024**, in the 10 seconds after each fill time (398 windows): the gap between buyer-initiated and seller-initiated trade prices has a median of **2.0 ticks**, mean 2.3, 90th percentile 5.0. A round trip that crosses the spread twice therefore costs about 2 ticks in a typical window, which matches the assumed slippage. The assumption is fair, not conservative, and one window in ten is more than twice as expensive. This estimate includes price movement inside the 10 seconds, so it is an upper bound on the quoted spread. MNQ, which is what would be traded, was not measured and may be wider.

## 7. Mistakes

- Iteration 8 reported the dollar t of 3.30 as the headline without first removing the index-level effect. The method should require volatility-unit results for any rule tested over many years.

## 8. Critique of the result

1. **A plausible reason for a 2018 break exists** (the growth of short-dated index options and hedging flows, which the source paper also cites), but a story found after the fact is cheap. *Test:* the holdout year.
2. **The walk-forward year agrees with the late period** (+$296 per traded day, t 0.93), which is mild support and nothing more.
3. **Tuning exits and sizing now would add trials to an unconfirmed edge.** *Suggestion:* run the single holdout test on the frozen paper rule first. The NQ bars for Nov 2025 to Oct 2026 cost **$1.29** (Databento quote, 22 Nov 2026).

## 10. Next iteration plan

Ask Ben whether to buy the holdout year ($1.29) and run the one-time test on the frozen rule, with the pass condition written down before the data is loaded:
- mean net result per traded day positive at 1× and 2× costs, and
- Combine pass rate on the holdout days above the 22% zero-edge baseline on $50K (simulated).

A holdout pass would justify the exits and sizing work and a paper-trading period. A fail ends the candidate. Either way the holdout is then spent for this rule.
