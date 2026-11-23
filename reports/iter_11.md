# Iteration 11: re-examining the breakout trades under Ben's new goals

_22 Nov 2026. Development period (June 2010 to October 2024) for all analysis and choices. One pre-committed check on the walk-forward year. The holdout year was not loaded. No data spend._

## 1. Verdict

**REVISE, and the new goals make the picture harder, not easier.**

- The rule only works in New York hours. It loses in Asia and London hours.
- A 30-day limit forces a position size at which the outcome is mostly luck: about **27-29% pass on development data and 12% on the walk-forward year** (simulated, $50K, 8 MNQ), against 15% for the same trades with random direction.
- The machine-learning filter predicted winners on development data and **failed on the walk-forward year**. Not adopted.
- Skipping news days makes this rule worse. Payrolls days are among its best days.
- To pass more than half the time within 30 days, a strategy needs roughly **three times this edge** (an annualised Sharpe ratio near 2.4, against about 0.8 here).

## 2. What was tested

New goals from Ben, and how each was applied:

| Goal | How it was applied |
|---|---|
| 1. Test each session separately; compare high and low volatility | The rule was rebuilt to run in any session, anchored to that session's open: New York 8:30-15:00 CT, Asia 18:00-01:00 CT, London 02:00-08:30 CT. Each is its own test, each split by volatility tercile. |
| 2. No more than 30 days | Plans whose median time to pass exceeds 30 trading days are marked low priority. (If you meant 30 calendar days, about 21 trading days, the conclusions below get stricter, not looser.) |
| 3. Profitability = payout ÷ (cost of an evaluation account × accounts needed × days required) | Implemented in `sniper/propscore.py`: payout is the expected dollars paid from one funded account; cost is the Combine subscription plus API fee for the months one attempt lasts; accounts needed is 1 ÷ pass rate; days is the median trading days to pass. Shown ×1000. Expected dollars per attempt is shown beside it. |
| 4. Avoid high-risk news days | CPI, payrolls and FOMC days skipped, tested against trading every day. Calendar extended to October 2026 from BLS and Federal Reserve pages. |

New code: `sniper/session_rule.py` (any-session engine with a trade log, entry-time features and optional risk limits), `sniper/propscore.py`, three trade logs in `reports/trades_noise_NQ_<SESSION>_dev.csv`. The new engine reproduces the frozen rule exactly on the New York session except on 3 of 3,502 days around market halts, where its handling of the prior close differs.

Trials: 18 this iteration (14 risk variants, 2 models, 1 walk-forward check, 1 post hoc sizing look), **105 in total**. Asia and London runs are in the same count as session variants of the trade-log run.

## 3. Sessions (measured, NQ, per contract, costs from the measured spread)

Spread measured on our tick data at each session's fill times: New York 2.0 ticks, Asia 2.2, London 1.9 (median; the 90th percentile is 5.0, 6.6 and 6.0).

| Session | Trades | Net per traded day | t (dollars) | t (daily-move units) | Years positive | Low / mid / high volatility, net per day |
|---|---|---|---|---|---|---|
| **New York** | 2,974 | **+$85** | +3.42 | +2.24 | 80% | +$31 / +$81 / +$146 |
| Asia | 3,623 | −$7 | −0.47 | −1.47 | 33% | −$21 / −$2 / +$3 |
| London | 5,153 | −$48 | −3.49 | −6.17 | 0% | −$46 / −$20 / −$77 |

- Breakouts continue only when US cash-market volume is present. In London hours they reverse, in every year, but the reversal is about the size of the cost, so fading it is not tradable either.
- Within New York the rule earns more when volatility is high, in dollars and in daily-move units (t 0.76, 1.12, 2.37 by tercile). Low-volatility periods contribute almost nothing.

## 4. Winners and losers (New York trade log, 2,974 trades)

**Shape of the results.** Hit rate 38% per trade. Trades held to the 3:00 PM close win 80% of the time and average +$738; trades stopped out win 15% and average −$302. The best 5% of trades make 2.6 times the total profit, so everything else is a net loss. Without the 20 best trades in 14 years, the total falls from $178,000 to $63,000 per NQ contract.

**Biggest gainers** (top 20): all held to the close, average 305 minutes, 15 of 20 are shorts opened at the first checks on large down days (3 Sep 2020 +$8,191; 7 Mar 2022 +$6,951; 3 Sep 2024 +$6,536). 16 of 20 are from 2022 or 2024.

**Biggest losers** (bottom 20): 16 were stopped at the very next half-hour check after entry, 12 are longs, 14 from 2022 or 2024 (7 Feb 2023 −$4,934 in 30 minutes; 27 Apr 2022 −$4,299). They look like the winners at entry: similar breakout size, volatility and volume. **The largest winners and losers cannot be told apart at the moment of entry**; the difference appears afterwards.

**Entry-time features against the trade result** (rank correlation with the result in daily-move units, in-sample):

| Feature | IC | t | Reading |
|---|---|---|---|
| Direction (long) | +0.110 | +6.0 | Longs: t 2.53. Shorts: t 0.89, but shorts hold the biggest winners. |
| Daily volatility (20-day) | +0.091 | +5.0 | Better in volatile periods. |
| Band width | +0.088 | +4.8 | Same information as volatility. |
| Overnight gap in the trade's direction | +0.084 | +4.6 | Gap-and-go days do better. |
| Move in the last 30 minutes | −0.076 | −4.2 | Chasing a fast move does slightly worse in rank terms. |
| Relative volume | −0.072 | −3.9 | Higher opening volume, slightly worse. |
| Entry number in the day | +0.018 | +1.0 | First entry: t 2.74. Second: t −0.62. |

By time: the 9:00 AM CT check has 859 trades at +$89 (t 2.52); checks from 9:30 to 1:30 are indistinguishable from zero; 2:00 PM is +$193 (t 1.24). By event: payrolls days +$264 a day (t 2.61, 108 days), CPI days +$48, FOMC days −$45.

These correlations are found on the same data they are measured on. Section 7 tests whether they hold up as a filter.

## 5. Risk: entries, exits and sizing (simulated on MNQ, $50K, development period)

MNQ costs 1.11 points a round trip (fees plus 2 ticks) against 0.69 for NQ, and that matters: on MNQ the development-period edge is $7.35 per contract per traded day with a daily standard deviation of $114.

**Sizing, frozen rule** (the central trade-off):

| Size | Pass rate | Median days to pass | Accounts needed | Payout per funded account | Ben's measure ×1000 | Expected $ per attempt | Within 30 days |
|---|---|---|---|---|---|---|---|
| 2 MNQ | 56.5% | 158 | 1.8 | $1,489 | 8 | +$56 | no |
| 3 MNQ | 46.7% | 86 | 2.1 | $1,649 | 23 | +$311 | no |
| 5 MNQ | 36.4% | 48 | 2.7 | $1,506 | 49 | +$260 | no |
| **8 MNQ** | **28.9%** | **29** | 3.5 | $1,832 | 117 | **+$330** | yes |
| 10 MNQ | 26.1% | 24 | 3.8 | $1,962 | 137 | +$318 | yes |
| 15 MNQ | 21.0% | 19 | 4.8 | $1,856 | 263 | +$280 | yes |
| 30 MNQ | 14.2% | 14 | 7.0 | $1,501 | 196 | +$114 | yes |
| Same trades, random direction, 8 MNQ | 15.0% | 24 | 6.7 | $666 | 38 | −$78 | yes |

- **Small size passes often but slowly; large size passes fast but rarely.** Inside the 30-day limit the best expected value is at 8 to 10 MNQ.
- **A caution about the measure.** Dividing by days rewards speed, so it peaks at 15 MNQ, where the pass rate (21%) is close to what random trades achieve at that size (13%). It also jumps when an attempt drops under one month of fees. I recommend reading it together with expected dollars per attempt and the pass rate, and not maximising it alone.

**Entry and exit limits** (each compared with the frozen rule at its own best size within 30 days):

| Variant | Net per MNQ per day | Worst day (daily moves) | Best size | Pass | Days | Expected $ |
|---|---|---|---|---|---|---|
| Frozen rule | $7.35 | −2.9 | 8 MNQ | 28.9% | 29 | +$330 |
| Skip CPI, payrolls, FOMC days | $6.82 | −2.9 | 8 MNQ | 28.0% | 30 | +$241 |
| Skip FOMC days only | $7.73 | −2.9 | 15 MNQ | 21.6% | 20 | +$294 |
| One entry a day | $5.57 | −2.0 | 15 MNQ | 20.5% | 27 | +$148 |
| No entries after 11:00 | $4.93 | −2.0 | 15 MNQ | 20.2% | 27 | +$90 |
| Per-trade stop, 0.25 / 0.40 daily moves | $7.56 / $7.47 | −2.0 | 15 MNQ | 21% | 19-21 | about +$300 |
| Session loss stop, 0.30 daily moves | $6.66 | −0.8 | 15 MNQ | 23.1% | 25 | +$285 |
| Long only | $7.70 | −2.0 | none within 30 days | 26.9% | 37 | +$272 |

- **No limit improves the outcome.** Stops cut the worst day from −2.9 to −0.8 daily moves, which sounds valuable, but they also cut the rare large winners that pay for everything, and they slow the pass.
- **Volatility-scaled sizing** (fewer contracts when the expected daily move is larger) was worse on development data: it trades tiny size in exactly the volatile periods where the rule earns. On the walk-forward year, looked at afterwards and not pre-committed, it did the opposite and helped (40-48% pass at about 1 MNQ, but 88-131 days). Unresolved, and outside the 30-day limit either way.

## 6. News days

Skipping CPI, payrolls and FOMC days lowers the expected value from +$330 to +$241 per attempt on development data and does not improve the worst day. On the walk-forward year the 21 news-day trades averaged +$1,042 per NQ contract and the rest +$101.

**I disagree with applying goal 4 to this particular rule.** A trend-following breakout wants large directional days, and releases supply them. The earlier finding that release windows are 2 to 3.6 times as volatile (iteration 7) is a reason to size carefully, and a reason for other kinds of strategy to stand aside, but here the filter removes profit. Skipping FOMC days only is roughly neutral. The filter stays available as a switch (`skip_days`), and I have left the decision to you.

## 7. Machine-learning filter (META-01)

Design: each trade's entry-time features feed a model that scores it; the worst-looking 30% are skipped. Validation is walk-forward by year (the model for 2019 sees only 2010-2018 trades, and so on), so all 2,047 scored trades from 2015-2024 are out of sample.

| Model | Rank IC of score with result | Years with positive IC | Net per trade: all / kept / skipped | t of the daily improvement |
|---|---|---|---|---|
| Logistic regression | +0.120 (t 5.45) | 100% | $88 / $130 / −$32 | **1.32** |
| Gradient-boosted trees | +0.045 (t 2.03) | 80% | $88 / $103 / +$46 | −0.70 |

The logistic model does predict which trades are more likely to win. But what it predicts is the hit rate, and this rule's profit comes from a few very large trades that the model cannot see coming. The improvement in money is not significant (t 1.32), and dropping any one of several features removes it.

**Pre-committed check on the walk-forward year** (model trained on all development trades, rule written before the run): kept trades averaged +0.016 daily moves and skipped trades +0.067. **The filter skipped the better trades. Not adopted.** The simple model beat the flexible one, and neither survives new data, which is the usual outcome for filters fitted to a few thousand trades with fat-tailed results.

## 8. Walk-forward year at the 30-day sizes (simulated, pre-committed)

| Plan | Pass rate | Days to pass | Expected $ per attempt |
|---|---|---|---|
| Frozen rule, 8 MNQ | 12.5% (11.3-13.7) | 14 | +$31 |
| Frozen rule, 10 MNQ | 11.0% | 13 | +$8 |
| Skip news, 8 MNQ | 9.4% | 14 | −$45 |
| Skip news + ML filter, 8 MNQ | 7.8% | 17 | −$73 |

In that year NQ's expected daily move was about $550 per MNQ, so 8 MNQ swings about $4,400 a day against a $2,000 loss limit. The size that fits a 30-day pass in a calm market is a coin flip with bad odds in a volatile one. Iteration 8's 27% pass on this same year was at 2 MNQ and took 38 days.

## 9. How much edge the 30-day goal needs (simulated)

Scaling this rule's average daily profit while keeping its day-to-day swings:

| Edge | Annualised Sharpe | Best pass rate within 30 days | Expected $ per attempt |
|---|---|---|---|
| None | 0.0 | 15% | −$78 |
| This rule | 0.8 | 27% | +$248 |
| 2× | 1.6 | 40% | +$1,544 |
| 3× | 2.4 | 59% | +$4,808 |
| 5× | 4.0 | 85% | +$15,857 |

A Sharpe ratio above 2 on a single intraday futures rule is rare and usually a sign of an error. The realistic routes are several unrelated modest edges traded together, or accepting a slower pass at a small size.

## 10. Mistakes

- Iterations 8 to 10 quoted NQ-contract profits while the plan trades MNQ, whose costs are 60% higher per point. On MNQ the development-period t in daily-move units is 1.15, not 2.2. Reports from now on state results in the contract that would be traded.
- The walk-forward check fixed 8 and 10 MNQ in advance and did not include volatility-scaled sizing. The later look at it is labelled post hoc.
- The walk-forward year has now been used three times for this rule (iterations 8, 11, and the post hoc look). It is no longer a clean test for it.

## 11. Critique of the result

1. **The rule's edge is real enough to beat random trades, and too small for the goals.** *Test:* none needed; section 9 quantifies it.
2. **The trade-level analysis is in-sample.** The one pattern tested out of sample (the ML filter) failed. *Test:* treat "long only", "first entry only" and "9:00 check only" as hypotheses for paper trading, not as improvements.
3. **Ben's measure can be gamed by size.** *Suggestion:* add a floor, for example only rank plans whose pass rate is at least 1.5 times the random-direction pass rate at the same size.
4. **MNQ slippage is assumed equal to NQ's.** *Test:* needs MNQ tick data (a purchase) or paper trading.

## 12. Suggestions

**Finding features:** look for edges that are unrelated to this one and work in different conditions (low-volatility days, mean reversion in London hours net of costs was close to zero but consistent in sign). Several modest unrelated edges are the only realistic way to the Sharpe that a 30-day pass needs.

**Testing features:** every future rule should be run through the session engine for all three sessions, in MNQ or MES costs, and scored with `propscore` from the start, with the random-direction control beside it.

## 13. Next iteration plan (Ben to choose)

1. Search for a second, unrelated edge to combine with this one, using the session engine and the new scoring from the first test.
2. Or relax the 30-day goal for this rule (2 to 3 MNQ, 3 to 8 months, 47-57% pass on development data) and build the paper-trading bot.
3. Or stop here on this rule.

Research, not financial advice. Simulated results are not forecasts.
