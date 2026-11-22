# Iteration 08: niche features from papers dated 2024 onward

_22 Nov 2026. Requested by Ben. No data spend. Holdout untouched. The walk-forward year was used once, for one frozen rule._

## 1. Verdict

**REVISE.** One of five new ideas is the first candidate in this project to pass the signal, cost and walk-forward checks: the **noise-area breakout on NQ** (NOISE-01, from Zarattini, Aziz and Barbon). It is **not** ready to promote: its deflated Sharpe ratio is 0.81 against a bar of 0.95, its edge sits almost entirely in 2018 and later, and the walk-forward year is positive but not significant on its own (t 0.93). The other four ideas fail or are real but not tradable.

## 2. What was tested

A second literature pass (LITERATURE.md, "Second literature pass") read 12 sources dated 2023 to 2026 and registered 7 hypotheses before any test. Five can be tested on our bars:

| ID | Idea | Source |
|---|---|---|
| EOD-01 | The day's move up to 2:00 PM CT reverses in the last half hour | Baltussen, Da, Soebhag (2023/24) |
| IMOM-07 | First half hour predicts last half hour only after a move larger than one daily standard deviation | "Where does gamma hedge drive the intraday market move?" (2024) |
| OD-01 | Futures drift up between 1:00 and 2:00 AM CT, more after a weak close | Boyarchenko, Larsen, Whelan (2022; not from 2024, included as niche) |
| REG-01 | Days with a large gap, large opening move and heavy opening volume reverse | Mesfin (2026 preprint, MNQ) |
| NOISE-01 | A move outside the usual range for that time of day continues; exit at the band or VWAP | Zarattini, Aziz, Barbon (2024/25) |

Two more need data we do not own (GEX-02: Cboe market-maker positions; LEADLAG-05: intraday stock-portfolio returns).

The features are in the pipeline as `sniper/features.py` and `sniper/noise.py`, with tests that fail if a feature uses later data.

Trials: 25 this iteration (12 first tests, 12 follow-up variants, 1 walk-forward run), **85 in total**.

## 3. Signal and cost evidence (measured; costs assumed)

Development period, June 2010 to October 2024. Net figures are per mini contract after the assumed all-in cost.

| Feature | Symbol | n | Signal | Net per trade | Dollar t | Verdict |
|---|---|---|---|---|---|---|
| EOD-01 | ES | 3,513 | IC +0.038, t +2.03 (wrong sign) | −$25 | −3.71 | fail |
| EOD-01 | NQ | 3,514 | IC +0.020, t +1.07 (wrong sign) | −$19 | −2.04 | fail |
| IMOM-07 | ES | 1,018 | IC −0.029, t −0.86 | −$41 | −2.65 | fail |
| IMOM-07 | NQ | 1,030 | IC −0.017, t −0.51 | −$36 | −1.85 | fail |
| OD-01 | ES | 3,556 | mean +1.04 bp, t +4.02 | −$7 | −1.97 | real, not tradable (0.56× cost) |
| OD-01 | NQ | 3,353 | mean +1.20 bp, t +4.01 | −$1 | −0.24 | real, not tradable (0.90× cost) |
| REG-01 | ES | 309 | rule only | +$49 | +0.58 | fail |
| REG-01 | NQ | 315 | rule only | −$170 | −1.38 | fail |
| NOISE-01A (hold to close) | ES / NQ | 2,128 / 2,103 | rule only | +$5 / +$62 | +0.20 / +1.73 | fail |
| NOISE-01B (paper's stop) | ES | 2,126 | rule only | +$43 | +2.60 | fail (below 3) |
| **NOISE-01B (paper's stop)** | **NQ** | **2,096** | rule only | **+$83** | **+3.30** | **pass** |

Notes:
- **The end-of-day reversal found in single stocks does not exist in the index.** If anything the index leans the other way, as in the earlier late-day momentum tests.
- **The overnight drift replicates** (t 4.0 on both contracts, 87% of years positive on NQ) and is larger after a falling close (+1.9 bp, t 3.8 to 4.4), as the paper says. It earns less than one round trip of cost, and since 2019 it is +0.3 to +0.6 bp with t near 1. The authors also report a negative Sharpe after spreads.
- NOISE-01B figures use fills **one minute after** each half-hour check. Filling at the check price itself, as a backtest naturally would, inflates NQ to $98 and t 3.89.

### NOISE-01B on NQ: robustness (development period)

| Variant | Net per traded day | t | Years positive |
|---|---|---|---|
| Frozen rule (14-day lookback, multiplier 1.0, VWAP stop) | $83 | 3.30 | 80% |
| Costs doubled | $63 | 2.52 | 53% |
| Lookback 11 / 17 | $82 / $95 | 3.21 / 3.71 | 67% / 80% |
| Multiplier 0.8 / 1.2 | $80 / $83 | 3.30 / 3.08 | 60% / 73% |
| No VWAP stop | $78 | 3.05 | 73% |

Not fragile to its parameters. **But the money is made late in the sample.** Average net per day per NQ contract by year: 2010 −$50, 2011 +$4, 2012 +$12, 2013 −$7, 2014 +$8, 2015 +$14, 2016 −$26, 2017 +$7, 2018 +$168, 2019 +$4, 2020 +$76, 2021 +$112, 2022 +$167, 2023 +$150, 2024 +$55. Part of that is simply that NQ's price is several times higher than in 2012, so a point move is the same but there are more points; part may be a real change (more option hedging flows), and part may be luck.

## 4. Trading evidence

- About 60% of days trade, 1.4 round trips on those days, hit rate 42%: many small losses and fewer larger wins. This is the opposite of what the Topstep consistency rule and the $150 winning-day rule favour.
- **Walk-forward year (Nov 2024 to Oct 2025), run once with the frozen rule:** 136 traded days, **+$296 per traded day per NQ contract, t 0.93**; +$275 at doubled costs. Positive, so the candidate survives the check, but one year cannot confirm it. The worst day lost $5,091 per NQ contract, and the median worst intraday drawdown on a traded day was about $990 per NQ, so it must be traded in micros.

## 5. Prop-firm evidence (simulated, MNQ, 4,000 resampled paths in 5-day blocks)

Best-EV position size for each account. Zero-edge baseline for comparison: 22% pass and about $0 per attempt on $50K.

| Day sample | Account | Size | Combine pass (95% CI) | Pass at 2× fees | Median days | Funded payout chance (Standard / Consistency) | Expected $ per attempt |
|---|---|---|---|---|---|---|---|
| Development, all years | $50K | 3 MNQ | 46.6% (45.0-48.1) | 41.7% | 75 | 73% / 49% | +$441 |
| Development, all years | $100K | 15 MNQ | 23.2% (21.9-24.5) | 21.2% | 18 | 40% / 21% | +$450 |
| Development, all years | $150K | 30 MNQ | 20.4% (19.2-21.7) | 18.6% | 13 | 34% / 18% | +$614 |
| Walk-forward year | $50K | 2 MNQ | 27.2% (25.8-28.6) | 26.2% | 38 | 53% / 27% | +$268 |
| Walk-forward year | $100K | 3 MNQ | 26.3% (24.9-27.7) | 25.4% | 39 | 56% / 27% | +$347 |
| Walk-forward year | $150K | 15 MNQ | 13.5% (12.4-14.5) | 13.1% | 7 | 19% / 10% | +$145 |
| Development from 2018 (optimistic, chosen after seeing the yearly table) | $50K | 2 MNQ | 62.9% | 60.0% | 78 | 86% / 69% | +$1,707 |

- Expected value is positive in every sample, where the zero-edge baseline was about $0. The confidence intervals shown are simulation error only; they do not include the much larger uncertainty about whether the edge is real.
- **Account size:** on $50K the best plan is small and slow (2-3 MNQ, 2 to 4 months of subscription). The larger accounts do not help: at small size they behave like the $50K, and at large size they turn into a quick gamble.
- Share of traded days at $150 or more with 10 MNQ: 31% (development), 40% (walk-forward).
- The walk-forward year was far more volatile than the development average (daily standard deviation $370 per MNQ against $115), which is why its pass rate is lower despite a higher mean.

## 6. Overfitting evidence

- **Deflated Sharpe ratio: 0.81** (annualised Sharpe 0.89 on all development days, 85 trials, skew 1.7, kurtosis 19). The bar is 0.95. **Not met.** With 85 trials, the best of 85 worthless rules would be expected to show a Sharpe of about 0.66.
- The 85 trials are not independent (many are variants), so the correction is conservative, but the bar is the bar.
- Probability of backtest overfitting and SPA were not computed: there was no parameter sweep to select from, and the frozen rule is the paper's own.
- The paper reports a Sharpe of 1.33 on SPY with far lower assumed slippage. We get 0.89 on NQ futures with ours, and ES fails.

## 7. Mistakes

- The first NOISE-01B run filled orders at the same price that triggered them, which is a small look-ahead. It was caught before any conclusion and the headline uses delayed fills. The first run's numbers are logged as trials.
- "Development from 2018" was chosen after looking at the yearly results. It is labelled optimistic and is not a headline.
- OD-01's source is from 2022, outside the "2024 onward" request. It is included and labelled.

## 8. Critique of the result

1. **The edge may just be the 2018-2024 trend-day regime.** *Test:* the holdout year (Nov 2025 on) is the clean check, used once at promotion, and it costs a data purchase. Before that, a free test: does the yearly edge track realised volatility? If the rule only pays in high-volatility years, it is a volatility bet.
2. **Dollar results grow with the index level.** *Test:* restate everything in units of daily volatility rather than dollars, and size positions by volatility.
3. **Half-hour fills in a fast market may be worse than 2 ticks.** *Test:* measure slippage on the 3 months of tick data we own at the exact fill times.
4. **A 42% hit rate fights the Topstep rules.** *Test:* Phase 5 and 6 work on exits and sizing (a daily stop, a daily profit lock, volatility-scaled size) evaluated on pass rate, in purged cross-validation so the choice is not overfit.
5. **Selection:** this is the best of 85 tries. The deflated Sharpe says there is roughly a 1 in 5 chance that it is nothing.

## 9. Suggestions

**Finding features:** the two that replicated in this pass (overnight drift, noise-area breakout) both come from papers with a specific mechanism and futures-relevant data. The single-stock results (end-of-day reversal, gamma breakeven) did not carry over to the index. Future reading should favour index- or futures-specific papers.

**Testing features:** rule-based ideas from practitioner papers do not fit the rank-IC test. This iteration tested them directly on dollars with the same t ≥ 3 bar, which should be written into METHOD.md as the standard path for such rules.

## 10. Next iteration plan

1. The three free critique tests above (volatility dependence, volatility units, slippage on tick data).
2. Exits and sizing for NOISE-01B under Topstep rules, in purged cross-validation, development period only.
3. If it still stands, ask Ben whether to buy the holdout year of NQ bars for the one final test. No promotion without that and without Ben's decision.
