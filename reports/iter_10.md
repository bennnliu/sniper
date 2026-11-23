# Iteration 10: one-time holdout test of the NQ noise-area breakout (NOISE-01B)

_22 Nov 2026. Approved by Ben. Protocol committed (9e1b3c6) before the holdout bars were downloaded. The script ran once, unchanged._

## 1. Verdict

**The holdout test is a PASS on all three pre-written conditions. The strategy is still not promoted:** the deflated Sharpe ratio from the development period (0.81) is below the validity bar (0.95), one year is a small sample (t 1.05), and the holdout year contains a two-month losing streak that would have failed a Combine started at the wrong time. Promotion is Ben's decision.

## 2. What was tested

The frozen rule from iteration 8 (14-day lookback, band multiplier 1.0, band-or-VWAP stop, fills one minute after each half-hour check, flat at 3:00 PM CT) on NQ, trading days 1 Nov 2025 to 30 Oct 2026. Bars from Aug-Oct 2025 were used only to warm up the lookback.

Data: 352,701 one-minute bars, 257 trading days, 9 half days excluded, no duplicates, no bad bars, no gaps over 5 minutes in the day session. Cost $1.29 (quote), logged in `data_spend.csv`.

Trials: 1, **87 in total**. The holdout is now spent for this rule.

## 3. Pre-written conditions and results

| Condition | Result | Met |
|---|---|---|
| Mean net result per traded day above 0 at 1× cost | **+$287** per NQ contract (measured, costs assumed) | yes |
| Same at 2× cost | **+$267** | yes |
| Simulated $50K Combine pass rate at 2 MNQ above the 22% zero-edge baseline (lower end of the simulation interval) | **35.2%** (33.8-36.7) | yes |

## 4. Trading evidence (measured, per NQ contract, 1× cost)

- 244 full days, 136 traded, hit rate 46%, **t 1.05**. Total +$39,053 for the year.
- Best day +$15,351, worst day −$7,018. One tenth of these for MNQ.
- By month: Nov +$1,634, **Dec −$7,853, Jan −$18,485**, Feb +$4,460, Mar +$13,586, Apr −$937, May +$1,975, Jun +$10,288, Jul −$856, Aug +$11,286, Sep +$10,478, Oct +$13,477.
- The three out-of-development periods now agree in sign: development 2018-2024 (+), walk-forward year (+$296 per traded day, t 0.93), holdout year (+$287, t 1.05). The two clean years together are about 272 traded days at roughly +$291, t about 1.4.

## 5. Prop-firm evidence (simulated from holdout days, 4,000 paths, 5-day blocks)

| Account | Size | Combine pass (95% CI) | Median days | Funded payout chance (Standard / Consistency) | Expected $ per attempt |
|---|---|---|---|---|---|
| $50K | 2 MNQ | 35.2% (33.8-36.7) | 24 | 54% / 35% | +$479 |
| $50K | 3 MNQ | 29.0% (27.6-30.4) | 13 | 39% / 25% | +$412 |
| $50K | 5 MNQ | 23.2% (21.9-24.5) | 8 | 25% / 18% | +$389 |
| $100K | 2 MNQ | 40.5% (38.9-42.0) | 53 | 73% / 48% | +$881 |
| $100K | 3 MNQ | 31.7% (30.2-33.1) | 27 | 57% / 35% | +$559 |
| $150K | 2 MNQ | 54.3% (52.7-55.8) | 122 | 88% / 66% | +$1,365 |
| $150K | 3 MNQ | 40.5% (38.9-42.0) | 53 | 75% / 48% | +$1,244 |

- **Account size matters here, unlike in earlier iterations.** With a small fixed position, a larger account gives more room under the Maximum Loss Limit, so the pass rate rises (35% → 41% → 54% at 2 MNQ), at the price of a much slower pass (24 → 53 → 122 trading days) and higher monthly fees. The expected-value column includes those fees.
- The intervals are simulation error only. They assume future days look like the holdout year, which is the real uncertainty.
- **The real path would have hurt.** December and January lost about $2,630 per MNQ in total. Two MNQ would have lost about $5,270, more than the $2,000 loss limit on a $50K account. A Combine started in November 2025 would have failed. The 35% is an average over many possible starting points and orderings.

## 6. Overfitting evidence

- Parameters were fixed before the walk-forward year and never changed. The holdout conditions were written and committed before the data was bought.
- Development-period deflated Sharpe ratio remains 0.81 (bar 0.95), and the volatility-unit t is 2.21 (bar 3). **The validity bar is not met on development data.** The two out-of-sample years are supporting evidence, not a substitute.
- 87 trials in total. This candidate is the best of them.

## 7. Mistakes

- The third condition used a Combine size (2 MNQ) picked on the walk-forward year. That was fixed in advance, but 3 and 5 MNQ would also have cleared 22% only marginally (5 MNQ: 21.9-24.5), so the pass is not sensitive to that choice at small sizes and is at large ones.
- The Monte Carlo charges assumed slippage of 2 ticks per round trip on MNQ. MNQ spreads were never measured.

## 8. Critique of the result

1. **t of 1.05 on one year is weak.** A coin-flip strategy with this daily volatility would show a year this good about 15% of the time. *Test:* only more out-of-sample time helps: paper trading forward.
2. **Three positive periods are not independent of the regime.** All sit in the post-2018 high-volume, option-heavy market. If that regime ends, so may the edge. *Test:* a monthly monitor of the rule's volatility-unit result with a stop rule.
3. **Low hit rate and long losing streaks fit Topstep badly.** *Test:* sizing and daily-loss rules evaluated on development data only. Any such change can no longer be checked on the holdout, so it must be simple and justified in advance.
4. **Execution is untested.** Fills one minute after the half hour with 2 ticks are assumed. *Test:* a paper-trading bot on the TopstepX API from Ben's own computer.

## 9. Suggestions

**Finding features:** unchanged from iteration 8. Index- and futures-specific sources replicated; single-stock results did not.

**Testing features:** a second candidate should not reuse this holdout year casually. Each extra use weakens it. Keep a log of holdout uses (this is use number 1).

## 10. Next iteration plan (Ben to choose)

1. Build the bot for this exact rule and run it in paper or practice mode for several weeks, comparing live fills with the backtest. No Combine fee is at risk during that time.
2. Or first study sizing and a daily loss rule on development data.
3. Or keep searching for a second, unrelated candidate.

Research, not financial advice. Simulated results are not a forecast.
