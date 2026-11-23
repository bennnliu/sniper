# Second-edge research log

_One running document for the research loop Ben asked for on 22 Nov 2026 (evening): research, hypothesis, test, repeat. Every iteration is logged here with its number and the running trial count. Hypotheses are written and committed before their tests run. Development data only (to 31 Oct 2024) unless a line says otherwise. Costs always on, in micro contracts (MNQ 1.11 points, MES 0.495 points a round trip, assumed). News days (CPI, payrolls, FOMC) skipped. No money spent._

**First edge (for reference):** NOISE-01B, the noise-area breakout on NQ in New York hours. It is a trend rule: it earns on days that move far in one direction, mostly when volatility is high, and bleeds on choppy days. Sharpe about 0.8, not promoted (deflated Sharpe 0.81 against a bar of 0.95). Within 30 trading days it passes a $50K Combine about 29% of the time at 8 MNQ on development data, against 15% for random direction.

**What a second edge must do:** either earn on the days the first edge loses (choppy, low-volatility, pinned days), or raise the pass rate of the first edge without needing new forecasting power.

| Iteration | Trials in iteration | Trials in total | Verdict |
|---|---|---|---|
| 1 to 12 (earlier reports) | 130 | 130 | One unpromoted candidate, everything else failed |

---

## Iteration 13

### Sources read for this iteration (third literature sweep)

| Source | Status | Read | Claim |
|---|---|---|---|
| Heston, Korajczyk and Sadka, "Intraday Patterns in the Cross-Section of Stock Returns", *Journal of Finance* 65(4), 2010 | Peer reviewed | Abstract and summary pages | A stock's return in a given half hour predicts its return in the same half hour on later days, for up to 40 days. Cross-section of stocks, not index futures. |
| Haendler, Heston, Korajczyk and Sadka, "The Intra-Day Stock Return Periodicity Puzzle", 2025 | Working paper | Abstract | The periodicity persists out of sample and is tied to institutional VWAP and closing-auction trading. |
| Browne, "Reaching Goals by a Deadline", *Advances in Applied Probability* 31(2), 1999 | Peer reviewed | Abstract | The policy that maximises the chance of reaching a wealth goal by a fixed date is a digital option: bet more as the deadline nears and the goal is still far. Theory, no data. |
| Golez and Jackwerth, "Pinning in the S&P 500 Futures", *Journal of Financial Economics* 106(3), 2012 | Peer reviewed | Abstract | On option expiration days S&P 500 futures are pulled toward the at-the-money strike by market makers' hedging. |
| Rosa, "Understanding Intraday Momentum Strategies", *Journal of Futures Markets* 42(12), 2022 | Peer reviewed | Abstract | The overnight return predicts the last half hour, but "the predictability disappears in the out-of-sample period". Matches our failed IMOM-03. Not retested. |
| Huang, Tsai, Weng and Yang, "Intraday Momentum in the VIX Futures Market", *Journal of Banking & Finance* 148, 2023 | Peer reviewed | Abstract | Intraday momentum in VIX futures only when option dealers' net gamma is negative. VIX futures are not in our data. Not testable. |
| Harvey, Mazzoleni and Melone, "The Unintended Consequences of Rebalancing", NBER WP 33554, 2025 | Working paper | Abstract | When stocks are overweight in institutional portfolios, equity returns fall 17 basis points the next day. Not peer reviewed, and the signal needs bond returns we do not have. Parked. |
| Safari and Schmidhuber, "Trends and Reversion in Financial Markets on Time Scales from Minutes to Decades", arXiv 2501.16772, 2025 | Preprint | Abstract and summary | Futures trend at horizons of hours to years and revert at minutes. Consistent with our results (minute reversal real but below cost, hours-long breakout positive). Not peer reviewed. |

I also tried to fetch free daily VIX history from Cboe for volatility-conditioned tests. The download was blocked by this environment's network policy, so every test below uses our bars only.

### Hypotheses (written before testing)

**PERIOD-01. Same-half-hour continuation.** *Claim:* the average return of a given half hour over the previous 20 days predicts the return of that half hour today, in index futures. *Why it could work:* institutions that split orders with VWAP schedules trade at the same times each day (Heston and co-authors). *Why it fits the first edge:* each trade lasts 30 minutes and is tied to the clock, not to the size of the day's move, so it should earn on quiet days when the breakout rule does not trade or bleeds. *Why it probably fails:* the published effect is across stocks, where the market's own move cancels out; in a single index the effect per half hour is likely far smaller than the 1.11-point cost. *Test:* NQ and ES, each of New York, Asia and London as its own test (6 trials). Signal test by rank IC, then a rule: long the half hour if its 20-day mean is positive, short if negative. *Pass:* t at least 3 in daily-move units after micro costs, positive in 70% of years, gross at least twice the cost.

**CAL-04. Option-expiration pinning hurts the breakout rule.** *Claim:* on monthly expiration Fridays (third Friday) price is pulled toward a strike, so breakouts fail more often and the frozen rule earns less than on other days. *Why it fits:* it is a filter that removes days on which the first edge should not exist. *Test:* frozen rule on NQ, New York, mean result in daily-move units on third Fridays against other days (1 trial). *Adopt as a skip rule only if* the expiration-day mean is lower with t at or below −2 and the sign holds in both halves of the data. About 170 such days, so power is low.

**GOAL-01. State-dependent sizing raises the 30-day pass rate.** *Claim:* with a fixed target, a trailing loss limit and a 30-day limit, the size that maximises the chance of passing is not constant. Browne's result says to bet according to the distance to the goal and the time left. *Why it fits:* it adds no forecast. It reshapes the same breakout results to the Topstep objective, which is the stated objective of this project. *Caution:* bold sizing raises the pass rate of a zero-edge strategy too, so every policy is also run on a random-direction control, and the claim is only that the policy converts the existing edge more efficiently. *Policies fixed in advance (4 trials, against the fixed 8 MNQ baseline):*
- C0.75 and C1.25: contracts = k × (balance − loss-limit level) ÷ (expected daily move per MNQ), so risk shrinks as the cushion shrinks and grows as it grows.
- B: Browne-style. Contracts = profit still needed ÷ (√days left × typical daily result per MNQ), capped at the C1.5 size.
- CL: C1.0, and once three quarters of the target is banked, never more contracts than needed to finish in one typical day.
All capped at 50 MNQ (Topstep's limit on $50K) and at least 1. *Measure:* share of attempts that pass within 30 trading days (block bootstrap of development days, simulated), and expected dollars per attempt. *Adopt only if* the 30-day pass rate beats fixed 8 MNQ by at least 5 points on development data, the gain over the random control is not smaller than for fixed 8 MNQ, and one check on the walk-forward year (its fourth use for this rule) is not worse than fixed 8 MNQ.

### Results (measured on development data; costs assumed; pass rates simulated)

**PERIOD-01: FAIL in all six tests.** The same-half-hour pattern does not exist in ES or NQ.

| Session | MES rank IC (t) | MNQ rank IC (t) | Gross per trade against cost |
|---|---|---|---|
| New York | −0.006 (−1.1) | −0.010 (−1.9) | −0.06x / −0.27x |
| Asia | +0.003 (+0.5) | 0.000 (0.0) | −0.01x / −0.05x |
| London | −0.003 (−0.5) | 0.000 (0.1) | −0.03x / −0.07x |

The gross result is slightly negative before any cost. The stock-level pattern does not carry over to the index.

**CAL-04: FAIL.** On 84 monthly expiration Fridays the breakout rule earned +0.044 daily-move units a day against +0.017 on other days (difference t +0.4, the wrong sign for the hypothesis; first half +0.10, second half −0.03). No evidence that pinning hurts the rule. No filter adopted.

**GOAL-01: FAIL.** No sizing policy beat fixed 8 MNQ by the required 5 points.

| Policy | Pass within 30 trading days | Random-direction control | Gain from the edge | Dollars per attempt |
|---|---|---|---|---|
| Fixed 8 MNQ | 14.7% | 9.7% | +5.0 | +$53 |
| Cushion 0.75 | 13.6% | 10.0% | +3.5 | +$37 |
| Cushion 1.25 | 15.1% | 12.7% | +2.4 | +$58 |
| Browne-style | 11.1% | 5.8% | +5.3 | +$1 |
| Cushion 1.0 with lock-in | 16.7% | 13.0% | +3.7 | +$81 |

The best policy adds 2 points. The walk-forward check was not run because no policy qualified.

**A correction this test exposed.** Iteration 11 reported 28.9% for fixed 8 MNQ with a median of 29 to 30 days to pass. That figure counted attempts that passed after day 30. With a hard stop at 30 trading days the pass rate is **14.7%**, against 9.7% for random direction (simulated, 20,000 paths). The earlier number was not wrong for what it measured, but it overstated what a strict 30-day rule delivers. The first edge adds about 5 points of pass rate inside 30 days.

### Mistakes and critique
- Browne's policy was taken from the abstract only; my version is an approximation with a cushion cap, so "Browne-style fails" is a statement about my approximation.
- The sizing family is small. A full dynamic-programming solution could do better than these four, but the random control shows most of any gain would be bold play that works without an edge, so the ceiling is low.

**Iteration 13: 11 trials. Running total 141. Verdict: KILL all three.**

---

## Iteration 14

### Sources
| Source | Status | Read | Claim |
|---|---|---|---|
| Cieslak, Morse and Vissing-Jorgensen, "Stock Returns over the FOMC Cycle", *Journal of Finance* 74(5), 2019 | Peer reviewed (I read the 2015 working-paper draft) | Main text in part | Since 1994 the equity premium is earned in even weeks counted from scheduled FOMC meetings. Day 0 is the meeting day, weekends excluded. Week 0 is days −1 to 3, week 2 days 9 to 13, week 4 days 19 to 23, week 6 days 29 to 33. Days in week 0 earn 13.6 bp more and days in weeks 2, 4, 6 earn 10 bp more than odd-week days (both significant at 1%), 1994-2013. Nothing shown after 2013. |
| Ariel, "High Stock Returns before Holidays", *Journal of Finance* 45(5), 1990 | Peer reviewed | Citation only | Pre-holiday days earn 9 to 14 times the ordinary daily return. |
| Ko and Yang, "The Pre-Holiday Premium of Ariel (1990) Has Largely Become a Small-Firm Effect Out of Sample", *Critical Finance Review* 13(3-4), 2024 | Peer reviewed | Abstract | 1983-2019: for large firms the pre-holiday difference is "insignificant, and especially after 1990". |

### Hypotheses (written before testing)

**CYCLE-01. FOMC-cycle even weeks.** *Claim:* a long position in ES or NQ earns more on days in even FOMC-cycle weeks (0, 2, 4, 6) than in odd weeks, and enough to cover micro costs. *Why it fits the first edge:* it is a long-only calendar position, set days ahead, with no link to whether the day trends. The breakout rule is long and short about equally and earns on big moves, so the two should be nearly uncorrelated, which is what raises a combined Sharpe ratio. *Why it may fail:* published 2019 on data to 2016; widely known; our sample starts 2010. *Test:* long from session open to close on even-week days, FOMC day itself and other news days skipped. New York session and the overnight session each as its own test, MES and MNQ (4 trials), plus odd weeks as a control (4 trials). *Pass:* t at least 3 in daily-move units after costs, 70% of years positive, gross at least twice the cost, and even minus odd difference positive with t at least 2. FOMC dates for 2021-2023 in our calendar are marked unverified; a result that depends on those years will be flagged.

**HOL-01. Pre-holiday days.** *Claim:* a long position on the trading day before a US market holiday earns a positive mean after costs. *Prior:* low, because Ko and Yang report it gone for large firms. Tested because it is cheap and peer reviewed in both directions. *Test:* New York and overnight sessions, MES and MNQ (4 trials). About 9 days a year, so the t-test has little power; same pass rule.

### Results (measured on development data; costs assumed)

| Test | MES: mean per trade, t, years positive | MNQ: mean per trade, t, years positive |
|---|---|---|
| Even weeks, New York | −$0.46, t −0.50, 33% | +$0.41, t −0.26, 33% |
| Odd weeks, New York (control) | −$0.32, t −0.39, 53% | −$0.99, t −0.29, 47% |
| Even weeks, overnight | −$0.95, t −1.13, 40% | −$0.49, t −0.57, 47% |
| Odd weeks, overnight (control) | +$2.87, t +0.59, 53% | +$4.51, t +1.16, 60% |
| Pre-holiday, New York | **+$25.09, t +2.67, 93%** (97 days) | +$26.08, t +2.18, 80% (97 days) |
| Pre-holiday, overnight | −$0.39, t −0.53, 47% | +$9.64, t +0.64, 60% |

- **CYCLE-01: FAIL.** Even weeks are no better than odd weeks in 2010-2024 (difference t between −1.2 and 0.0). The published pattern is not in our sample. As predicted, the position was nearly uncorrelated with the breakout rule (−0.13 and −0.03), which would have been useful had it earned anything.
- **HOL-01: FAIL on the rule, and the closest miss of the loop.** A long position through the New York session on the day before a market holiday earned about $25 per micro, 11 to 13 times the cost, positive in 93% of years on MES. But t is 2.67 and 2.18, below the bar of 3, with only 97 days, and after 153 trials a t of 2.7 is what luck alone is expected to produce at least once. It also cannot matter to a 30-day Combine: it trades about 7 days a year. Not adopted. Noted as a harmless bias: there is no reason to avoid being long on those days.

### Mistakes and critique
- I read the 2015 draft of the FOMC-cycle paper, not the 2019 journal version; the week definitions could differ slightly.
- FOMC dates for 2021-2023 remain unverified. The result does not depend on them: 2018 onward and before 2018 both fail.
- Holiday list is built from standard rules (New Year, King, Presidents, Good Friday, Memorial, Juneteenth from 2022, Independence, Labor, Thanksgiving, Christmas) and not checked against the exchange calendar.

**Iteration 14: 12 trials. Running total 153. Verdict: KILL both.**

---

## Iteration 15

### Sources
| Source | Status | Read | Claim |
|---|---|---|---|
| Gao, Han, Li and Zhou, "Market Intraday Momentum", *Journal of Financial Economics* 129(2), 2018 | Peer reviewed | Read in the first literature pass | Intraday momentum is stronger on high-volatility, high-volume and news days. |
| Baltussen, Da, Lammers and Martens, "Hedging Demand and Market Intraday Momentum", *Journal of Financial Economics* 142(1), 2021 | Peer reviewed | Read in the first pass | Intraday momentum comes from option dealers hedging when they are short gamma, which happens in volatile, falling markets. Holds across 60+ futures. |

Our own data agree: the breakout rule's t-statistic by volatility tercile is 0.76, 1.12, 2.37 (iteration 11). That split was seen after the fact, so development data cannot confirm it again.

### Hypothesis (written before testing)

**VOL-01 (as a start rule). Begin Combine attempts only when volatility is high.** *Claim:* an attempt started on a day when the trailing 20-day volatility is above its trailing 250-day median passes within 30 trading days more often than one started when it is below, by at least 10 points, with the size scaled so that every attempt risks the same share of the loss limit. *Why it fits the first edge:* it adds no new signal. The trader chooses when to pay for an attempt, and the mechanism behind the first edge (dealer hedging) is only active in volatile markets, so attempts should be bought only then. This changes "accounts needed" in Ben's measure without changing the rule. *Why it may fail:* volatility regimes end; a start in a volatile month can run into a calm one. And volatile periods have fatter tails against a fixed loss limit.
*Test:* every development day is a possible start. Run the actual following 30 trading days (real history, not shuffled) through the Combine rules. Two sizings fixed in advance: 8 MNQ, and volatility-scaled contracts = 8 × (median expected daily move ÷ today's expected daily move), set each day. Compare starts in the high regime with starts in the low regime, each against a random-direction control (average of 20 random draws). 2 trials. Windows overlap heavily, so the standard error is estimated from non-overlapping windows.
*Adopt only if* high-regime starts pass at least 10 points more often than low-regime starts and at least 10 points above their own random control, on development data, and the same direction shows on the walk-forward year (fifth use of that year for this rule, stated plainly).

### Results (simulated on real 30-day windows of development data)

| Sizing | Start in high volatility | Start in low volatility | All starts |
|---|---|---|---|
| Fixed 8 MNQ: pass within 30 days (random control) | 13.1% (8.4%) | 16.5% (8.6%) | 14.5% (8.5%) |
| Volatility-scaled: pass within 30 days (random control) | 3.7% (2.7%) | 8.8% (3.8%) | 5.8% (3.2%) |

Standard errors are 4 to 6 points because 30-day windows overlap.

**VOL-01 as a start rule: FAIL.** Starting in a volatile regime does not raise the pass rate; it is slightly lower (13.1% against 16.5%, not a significant difference). The edge per day is larger in volatile markets, but so are the swings against a fixed $2,000 loss limit, and the two cancel. The walk-forward check was not run. Volatility-scaled sizing keyed to the long-run median trades too small to reach the target in 30 days.

This run on real history also confirms the corrected figure from iteration 13: fixed 8 MNQ passes within 30 trading days about 14.5% of the time, against 8.5% for random direction.

**Iteration 15: 2 trials. Running total 155. Verdict: KILL.**

---

## Iteration 16

### Sources
| Source | Status | Read | Claim |
|---|---|---|---|
| Our own RV-01 result (iteration 3) | Measured | — | The NQ/ES spread reverts within the session (IC −0.018, t −4.8, 80% of years). Too small to trade by itself. |
| Pitkäjärvi, Suominen and Vaittinen, "Cross-Asset Signals and Time Series Momentum", *Journal of Financial Economics* 136(1), 2020 | Peer reviewed | Citation only, not read this session | Trend signals confirmed by a related market predict better than a market's own trend alone (monthly, bonds and equities). |
| Hasbrouck, "Intraday Price Formation in U.S. Equity Index Markets", *Journal of Finance* 58(6), 2003 | Peer reviewed | Citation only | Index price discovery happens mostly in the E-mini futures. |

### Hypothesis (written before testing)

**CONF-01. Breakouts confirmed by ES continue; NQ-only breakouts fade.** *Claim:* an NQ breakout entry is better when ES is also outside its own noise area in the same direction at that check. When only NQ has broken out, the move is a tech-specific move against the broad market, and the measured tendency of the NQ/ES spread to revert works against the trade. *Why it fits the first edge:* it uses information the rule does not have (a second market) to remove the entries that our own data say should fail. It is the first filter in this project built from a relationship already measured as real (t −4.8) and not from the trade log. It was not among the features of the failed ML filter, which saw NQ only. *Why it may fail:* ES and NQ are 0.9 correlated, so nearly every NQ breakout may be confirmed and the filter would remove almost nothing.
*Test:* for each trade of the frozen rule (NQ, New York, MNQ costs, news days skipped), compute the ES confirmation score = ES's signed move from its open at the entry check ÷ ES's 14-day noise width at that time. Confirmed means the score is at least 1. Compare the mean result in daily-move units of confirmed and unconfirmed trades (1 trial), then the daily results of the rule taking confirmed trades only (1 trial).
*Adopt only if* confirmed minus unconfirmed has t at least 2 with the same sign before and after 2018, the filtered rule's 30-day pass rate at 8 MNQ rises by at least 3 points, and on the walk-forward year the kept trades do better than the skipped ones and the kept total is at least the unfiltered total (fifth use of that year for this rule).

### Results (measured on development data; costs assumed)

| Group | Trades | Mean per trade (daily-move units) | t | Dollars per MNQ |
|---|---|---|---|---|
| Confirmed by ES (score at least 1) | 1,779 | +0.017 | 1.40 | +$6.11 |
| Not confirmed | 816 | +0.003 | 0.17 | +$2.17 |
| Difference | | +0.015 | **0.76** | |

**CONF-01: FAIL.** The sign is as predicted in both halves (+0.006 before 2018, +0.027 after), and unconfirmed breakouts earn nothing, but the difference is far from significant (t 0.76, needed 2). Trading confirmed entries only lifts the daily t from 1.30 to 1.40 and lowers the 30-day pass rate at 8 MNQ from 15.0% to 10.1%, because fewer trades means fewer chances to reach the target in time. Not adopted; walk-forward check not run.

A fact worth keeping: 31% of NQ breakouts happen without ES. The filter is not empty, it is just weak.

**Iteration 16: 2 trials. Running total 157. Verdict: KILL.**

---

## Iteration 17

### Sources
| Source | Status | Read | Claim |
|---|---|---|---|
| Gatev, Goetzmann and Rouwenhorst, "Pairs Trading: Performance of a Relative-Value Arbitrage Rule", *Review of Financial Studies* 19(3), 2006 | Peer reviewed | Citation only, from memory | Pairs of close substitutes that diverge tend to converge over the following days to months. |
| Moskowitz and Grinblatt, "Do Industries Explain Momentum?", *Journal of Finance* 54(4), 1999 | Peer reviewed | Citation only, from memory | Industry relative returns continue at the one-month horizon. This predicts the opposite sign for tech against the broad market. |
| Our RV-01 and RV-02 | Measured | — | Within a session the NQ/ES spread reverts at 15 minutes (t −4.8) and continues weakly from morning to afternoon (t +2.2). Both are below cost at intraday size. |

I have not re-read the two papers this session, so their claims above are from memory and carry that label.

### Hypothesis (written before testing)

**PAIR-01. The NQ-against-ES spread is predictable over days, not minutes.** *Claim:* the beta-hedged relative return of NQ over ES in the last 1, 5 or 20 days predicts the relative return in the next session. The literature gives both signs (convergence of substitutes, or continuation of sector trends), so this is a two-sided test at the t ≥ 3 hurdle. *Why it fits the first edge:* a long-one, short-the-other position has almost no exposure to the market's direction, which is what the breakout rule bets on, so the two results should be uncorrelated. And unlike the intraday spread trades that died on costs, a position held for a whole session faces a two-leg cost of about 4.5 basis points against a daily spread move of roughly 50, so costs are no longer the binding problem. *Why it may fail:* it is the same two instruments again, and index-level relative value is among the most watched trades there is.
*Test:* spread return = NQ return − beta × ES return, beta from the trailing 60 days. Signal = sum of the last 1, 5 and 20 daily (15:00 to 15:00 CT) spread returns. Target = next session's spread return, overnight (18:00-08:30 CT) and New York (08:30-15:00 CT) as separate tests. 6 trials. *Pass:* rank IC with t at least 3 (either sign, with the Bonferroni caveat that six two-sided tests are being run), then a sign rule net of 4.5 basis points with t at least 3 and 70% of years positive.

### Results (measured on development data; costs assumed)

| Session | Lookback | Rank IC (t) | Years with that sign | Gross per day | Net of 4.5 bp |
|---|---|---|---|---|---|
| Overnight | 1 day | **+0.089 (t +4.54)** | 80% | +1.46 bp | −3.03 bp |
| Overnight | 5 days | +0.070 (t +3.55) | 87% | +1.41 bp | −3.08 bp |
| Overnight | 20 days | +0.057 (t +2.88) | 47% | +0.64 bp | −3.85 bp |
| New York | 1 day | −0.023 (t −1.28) | 67% | +1.06 bp | −3.43 bp |
| New York | 5 days | −0.021 (t −1.13) | 67% | +0.75 bp | −3.74 bp |
| New York | 20 days | −0.001 (t −0.03) | 67% | −0.32 bp | −4.81 bp |

**PAIR-01: real overnight, NOT TRADABLE.** When NQ beat ES during the day, it keeps beating ES overnight (t 4.5 at one day, the same sign in 80% of years, and it survives a Bonferroni correction for six tests). This is a new measured fact. But the move is 1.5 basis points against a two-leg micro cost of 4.5, and commissions alone are about 1.2. In New York hours there is nothing.

**I was wrong in the hypothesis** about the size of the spread's daily move: I wrote roughly 50 basis points; measured, it is 22 overnight and 39 in New York. Costs are still the binding problem.

This is the fourth signal in this project that is statistically real and smaller than the cost of trading it (with the 5-minute reversal, the intraday NQ/ES spread, and the 1-2 AM drift). The pattern is consistent: what can be found in these bars is real and priced to within the cost of a retail micro trade.

**Iteration 17: 6 trials. Running total 163. Verdict: KILL (not tradable).**

---

## Iteration 18: clearing the untested backlog

Four hypotheses have sat in the registry since the first literature pass and can be tested with bars. They are tested now so that no idea is left unexamined.

### Sources
| Source | Status | Claim used |
|---|---|---|
| Easley, López de Prado and O'Hara, "Flow Toxicity and Liquidity in a High-Frequency World", *Review of Financial Studies* 25(5), 2012 | Peer reviewed (read in the first pass) | Order imbalance can be estimated from bars by bulk volume classification. |
| Hasbrouck (2003), cited above | Peer reviewed | Index futures lead each other by seconds, not minutes. |
| Prior-day high and low as reversal levels | Trader lore, no peer-reviewed source found | Listed as such. |
| Volatility clustering (Andersen and Bollerslev, *Journal of Empirical Finance* 4, 1997) | Peer reviewed (from memory) | Quiet periods follow quiet periods; the "compression then expansion" idea predicts the opposite. |

### Hypotheses (written before testing)
- **LEADLAG-01.** NQ's return over the last 1 or 5 minutes predicts ES's next 1 or 5 minutes, and the reverse. New York session. 4 trials. *Fit with the first edge:* none needed if it worked; it is a separate fast trade. *Prior:* very low after costs.
- **TOX-02.** Bulk-volume-classified imbalance over the last 30 minutes predicts the next 30-minute return. ES and NQ, New York. 2 trials. *Fit:* the breakout rule decides at the same half-hour checks, so a real flow signal could confirm or veto its entries.
- **MR-05.** The first touch of the prior day's New York high or low reverses over the next 30 minutes. ES and NQ. 2 trials. *Fit:* a fade trade that earns on range days, the days the breakout rule loses.
- **VOL-02.** A compressed overnight range (bottom third against the expected daily move) is followed by a larger New York range, and the breakout rule does better on those days. 2 trials (range relation, rule filter). *Fit:* a filter for the first edge.
Pass rules as before: t at least 3 after micro costs for trades; t at least 2 on the difference for a filter, then the walk-forward check.

### Results (measured on development data; costs assumed)

| Test | Result | Verdict |
|---|---|---|
| LEADLAG-01, NQ leads ES, 1 minute | Controlling for ES's own last minute, IC +0.062 (t +48). Trading it: gross −0.03 bp against a cost of 1.81 bp | Real, not tradable |
| LEADLAG-01, ES leads NQ, 1 minute | Partial IC +0.019 (t +18); gross −0.01 bp against 1.45 bp | Real, not tradable |
| LEADLAG-01, 5 minutes, both ways | Partial IC +0.014 and +0.016 (t 6 to 7); gross −0.13 bp | Real, not tradable |
| TOX-02, bar-based flow imbalance, MES and MNQ | Gross −0.01x and +0.18x the cost. It carries the same information as the plain past return | Fail |
| MR-05, fade first touch of prior day's high or low | MES gross −0.70x cost (t net −7.5); MNQ +0.17x cost (t net −4.4) | Fail |
| VOL-02, compressed overnight range then a bigger day | Opposite: after a quiet night the New York range is 0.94 expected daily moves against 1.37 otherwise (t −18.5). Quiet follows quiet | Fail (wrong sign) |
| VOL-02 as a filter for the breakout rule | Opposite to the hypothesis: the rule earns −0.012 a day after quiet nights (456 days) and +0.052 otherwise, difference t −2.27 | Hypothesis fails; the reverse is carried to iteration 19 |

- NQ does lead ES by a minute, strongly in statistical terms, and the effect is one sixtieth of the cost.
- The raw rank ICs for TOX-02 (−0.085) are an artifact: a rank correlation computed inside each day over 12 intervals is biased by about −1/12. The gross result in points is the honest number, and it is zero.

**Mistake:** I registered VOL-02 years of folklore the wrong way round. The peer-reviewed fact (volatility clusters) predicted what the data show.

**Iteration 18: 10 trials. Running total 173. Verdict: KILL all four as written.**

---

## Iteration 19

### Hypothesis (written before the tests below; its motivating number came from iteration 18)

**VOL-05. Skip the breakout rule after a quiet overnight session.** *Claim:* when the overnight range (18:00 to 08:30 CT) divided by the expected daily move is in the bottom third of its trailing 250 days, the New York session will be quiet too, the dealer-hedging mechanism behind intraday momentum is not active (Gao et al. 2018; Baltussen et al. 2021), and the rule's breakouts are noise. Standing aside on those days improves the first edge. *Why it fits:* it is a same-morning filter known at 08:30 CT that removes the days on which the first edge has no reason to work. It differs from the regime filter that failed in iteration 15, which used a 20-day average; this uses the night just ended.
*Honest status of the evidence:* the −2.27 was found while testing the opposite idea, after 170 trials, so by itself it is worth little. The test that counts is out of sample.
*Tests (3 trials):* (1) development data: the difference must have the same sign before and after 2018, and the filtered rule must have a higher daily t-statistic; (2) 30-day pass rate at 8 MNQ, filtered against unfiltered, with random-direction controls; (3) one check on the walk-forward year, fixed in advance: days kept must average more than days skipped, and the kept total must be at least the unfiltered total. This is the walk-forward year's fifth use for this rule. *Adopt only if all three hold.*

### Results (measured on development data; pass rates simulated)

| Measure | All days | Quiet nights skipped |
|---|---|---|
| Mean result on quiet-night days / other days (daily-move units) | −0.008 / +0.050 | difference t 2.05 |
| Difference before 2018 / from 2018 | +0.123 / **+0.008** | |
| Daily t-statistic of the rule | 2.19 | 2.57 |
| Dollars per MNQ over the period | $13,115 | $10,560 |
| Pass within 30 days, 8 MNQ (random control) | 17.7% (11.7%) | 11.9% (9.3%) |
| Pass within 30 days, 12 MNQ (random control) | 17.5% (12.4%) | 12.8% (10.4%) |

**VOL-05: FAIL.** Test 1 passes only on paper: the whole difference comes from 2011-2017, when the rule did not work anyway. Since 2018, the period in which the first edge exists, quiet nights are no worse (+0.008, negative in four of seven years). Test 2 fails outright: skipping a third of the trading days cuts the 30-day pass rate from 17.7% to 11.9%, because the filter removes chances to reach the target and, in dollars, removes profit. The walk-forward check was not run, so that year was not used again.

(The all-days pass rate here is 17.7%, against 14.7% in iteration 13, because this sample starts later: the filter needs 250 days of history.)

**Iteration 19: 2 trials. Running total 175. Verdict: KILL.**

---

## Where the loop stands after iteration 19

| Iteration | Idea | Trials | Total | Verdict |
|---|---|---|---|---|
| 13 | Same-half-hour pattern; expiration-day filter; goal-based sizing | 11 | 141 | All fail |
| 14 | FOMC-cycle weeks; pre-holiday days | 12 | 153 | Fail (pre-holiday t 2.67, near miss, 7 days a year) |
| 15 | Start attempts only in volatile regimes | 2 | 155 | Fail |
| 16 | NQ breakouts confirmed by ES | 2 | 157 | Fail (right sign, t 0.76) |
| 17 | NQ against ES over days | 6 | 163 | Real overnight (t 4.5), below cost |
| 18 | Backlog: lead-lag, flow imbalance, prior-day levels, overnight compression | 10 | 173 | Fail or below cost |
| 19 | Skip days after a quiet night | 2 | 175 | Fail |

**No test has succeeded.** Three things are now established with some confidence:

1. **Everything real in these bars is smaller than a micro contract's cost.** Five separate effects pass t ≥ 3 before costs (5-minute reversal, intraday NQ/ES reversion, 1-2 AM drift, overnight NQ/ES continuation, one-minute lead-lag) and none comes within a factor of three of the cost.
2. **Filters on the first edge do not help a 30-day Combine.** Every filter tried (news, expiration, volatility regime, ES confirmation, quiet nights, the ML model) either had no effect or reduced the pass rate by removing trading days. With a deadline, fewer trades is a cost in itself.
3. **The first edge inside a strict 30 trading days is worth about 5 points of pass rate** (roughly 15% against 10% for random direction at 8 MNQ, simulated). Iteration 11's 28.9% included attempts that passed after day 30.

**Where I disagree with the instruction to loop until success.** With 175 trials on the same two correlated instruments, a "success" at t ≥ 3 is now more likely to be luck than not, unless it also survives data it has never seen. Only one unseen year remains for ES (the unbought holdout) and none for NQ. Continuing to mine the same bars will eventually produce a pass, and that pass would be the least trustworthy result of the project. The loop continues as instructed, but from here each new idea needs either a mechanism that predicts something the data have not already shown, or data the loop has not seen.

**What would open new ground (none costs money except the first):**
- Other markets (the open decision: $25.74 to $80.02).
- Free daily data that this environment's network policy blocks: Cboe VIX history and FRED rates. Every peer-reviewed explanation of intraday momentum runs through option dealers' hedging, and implied volatility is the cheapest window onto it. Allowing `cdn.cboe.com` and `fred.stlouisfed.org` in the environment's network settings, or uploading the CSV files, would make those tests possible.

---

## Iteration 20

_Second round, 23 Nov 2026. The Cboe and FRED hosts are still blocked and no new data has been approved, so this round stays on our bars._

### Sources
| Source | Status | Read | Claim |
|---|---|---|---|
| Rapach, Strauss and Zhou, "Out-of-Sample Equity Premium Prediction: Combination Forecasts and Links to the Real Economy", *Review of Financial Studies* 23(2), 2010 | Peer reviewed | From memory, not re-read | Averaging many weak forecasts beats any single one out of sample because it cancels estimation noise. |
| Search for academic work on passing prop-firm evaluations | — | Searched | Nothing peer reviewed found; only blogs and vendor pages. Browne (1999) remains the closest theory. |

### Hypotheses (written before testing)

**ENS-01. An ensemble of breakout settings is steadier than one setting.** *Claim:* averaging the rule over lookbacks of 7, 14 and 28 days and band widths of 0.8, 1.0 and 1.2 (nine versions, equal weight) gives a higher daily t-statistic than the single frozen setting, and a higher 30-day pass rate at the same total size. *Why it fits:* it is the first edge itself with the luck of one parameter choice averaged out, and entries spread over more checks, which smooths the daily result against the loss limit. *Why it may fail:* the nine versions are highly correlated, so there is little noise to cancel. 1 trial.

**ENS-02. Trade the rule on ES and NQ together.** *Claim:* splitting the same dollar risk between MNQ and MES (4 MNQ plus 6 MES against 8 MNQ) raises the daily t-statistic and the pass rate. *Why it may fail:* the rule was weaker on ES, and the two are 0.9 correlated. 1 trial.

*Adopt either only if* the daily t-statistic rises and the 30-day pass rate rises by at least 3 points with the gain over the random control not smaller.

## Iteration 21

**DP-01. The best possible sizing policy, by dynamic programming, tested out of sample.** *Claim:* the sizing policy that maximises the probability of passing within 30 trading days, solved exactly by backward induction over (profit so far, high-water mark, days left) from the rule's daily results before 2021, beats fixed 8 MNQ by at least 5 points on the unseen 2021 to October 2024 results. Sizes are in risk units (contracts × expected daily move) so that the policy carries across price levels. *Why it fits:* it is the upper limit of what sizing alone can add to the first edge, so it settles the question GOAL-01 left open. *Why it may fail:* the edge is small, so the optimum is mostly bold play that works equally for random direction. 1 trial, with fixed 8 MNQ and the random-direction control alongside. The consistency rule and minimum days are left out of the optimisation and enforced in the evaluation.

### Results for iterations 20 and 21 (development data; pass rates simulated, 20,000 paths)

| Version (8-contract equivalent) | Daily t, all years | Daily t, 2018 on | Pass within 30 days | Random control |
|---|---|---|---|---|
| Frozen single setting, 8 MNQ | 1.30 | 3.31 | 14.7% | 9.7% |
| ENS-01, nine settings | 1.31 | 3.69 | 13.8% | 9.0% |
| ENS-02, 4 MNQ + 6 MES | 0.33 | 3.28 | 13.4% | 9.3% |

**ENS-01 and ENS-02: FAIL.** The nine settings are 0.88 correlated with each other, so averaging them cancels almost nothing; the pass rate does not rise. Adding ES lowers the result (the rule is weaker on ES, and the two versions are 0.67 correlated).

| DP-01 | Fixed 8 MNQ | DP policy | Constant risk, 2,000 units |
|---|---|---|---|
| Train, to 2020: pass (control) | 7.2% (4.2%) | 13.9% (11.8%) | 14.6% (11.1%) |
| **Test, 2021 to Oct 2024: pass (control)** | 24.7% (17.3%) | **29.6% (18.9%)** | **29.8% (18.7%)** |

**DP-01: FAIL on the rule I set, by a hair, and it points somewhere useful.** Out of sample the optimal policy beats fixed 8 MNQ by 4.9 points; I required 5. More telling, the full optimisation is matched by the simplest policy there is: hold the number of contracts that makes the expected daily move equal to a fixed dollar amount ("constant risk"; 2,000 units means contracts = $2,000 ÷ today's expected daily move per MNQ). The DP learned nothing beyond that. Two honest caveats: the constant-risk line was a benchmark I added, not a registered hypothesis, and most of every pass rate here is bold play (the random-direction control passes 19%).

The DP's own model promised 30% on the training data and delivered 14%. The model assumes independent days and ignores the consistency rule; real results come in streaks. That gap is a warning against trusting any pass rate computed from shuffled independent days.

**Iterations 20 and 21: 3 trials. Running total 178. Verdict: KILL as written; constant-risk sizing carried to iteration 22.**

---

## Iteration 22

### Hypothesis (written before testing)

**RISK-01. Constant-risk sizing is the right way to trade the first edge in a Combine.** *Claim:* sizing each day at contracts = R ÷ (expected daily move per MNQ), with one risk level R chosen on data before 2021, passes a $50K Combine within 30 trading days more often than fixed 8 MNQ, and by more than it helps a random-direction trader. *Why it fits the first edge:* the loss limit is a fixed $2,000 while NQ's daily move has ranged from $75 to over $500 per MNQ. A fixed contract count is far too small in calm years and a coin flip against the loss limit in volatile ones, which is exactly how the walk-forward year failed in iteration 11 (12.5% at 8 MNQ). Constant risk keeps every day the same size relative to the limit. It resolves SIZE-01, which was left "unresolved" in iteration 11 because the version tested there was scaled far too small. *Why it may fail:* the improvement may be only bold play; the control will show it.
*Procedure fixed in advance:* (1) choose R from {1000, 1500, 2000, 3000, 4000} on data before 2021 by the largest pass-rate gain over the random control; (2) evaluate that single R on 2021 to October 2024; (3) one check on the walk-forward year, November 2024 to October 2025, its fourth use for this rule. 5 trials for the grid plus 1.
*Success means:* in both the 2021-2024 test and the walk-forward year, the 30-day pass rate is at least 25%, beats fixed 8 MNQ, and exceeds the random control by at least 8 points. Results will also be given in Ben's measure and in dollars per attempt. Success here would be a sizing rule for the existing candidate, not a second source of profit, and would not change the candidate's promotion status (deflated Sharpe 0.81).

### Results (simulated; 20,000 shuffled paths, and real consecutive 30-day windows)

| Data before 2021 (step 1) | Pass within 30 days | Random control | Gain | Real windows |
|---|---|---|---|---|
| Fixed 8 MNQ | 6.7% | 4.1% | +2.6 | 8.3% |
| Risk 1,000 | 10.4% | 5.9% | **+4.5** | 11.9% |
| Risk 1,500 | 14.0% | 10.1% | +4.0 | 14.3% |
| Risk 2,000 | 14.2% | 11.1% | +3.1 | 14.5% |
| Risk 3,000 | 12.8% | 11.6% | +1.3 | 12.5% |
| Risk 4,000 | 11.9% | 11.1% | +0.9 | 11.6% |

The rule fixed in advance picks the level with the largest gain over the control: **risk 1,000**.

| 2021 to Oct 2024 (step 2) | Pass within 30 days | Random control | Gain | Real windows |
|---|---|---|---|---|
| Fixed 8 MNQ | 24.5% | 17.3% | +7.2 | 26.9% |
| Risk 1,000 (about 2 MNQ) | 10.8% | 5.1% | +5.6 | 10.6% |

**RISK-01: FAIL.** The level chosen by my own procedure passes 10.8% in the test period, below fixed 8 MNQ and far below the 25% required. The walk-forward check was not run.

What this says, read together with iteration 21:
- **The edge's contribution is flat at about 3 to 7 points of pass rate whatever the size.** Bigger size raises the pass rate, but it raises the random trader's pass rate by the same amount. Size buys variance, not edge.
- Had I chosen the risk level by raw pass rate, 2,000 would have been picked and would show 29.8% against fixed 8 MNQ's 24.7% in the test period (iteration 21). I did not register that criterion, and switching to it after seeing the answer would be exactly the kind of choice this project forbids. It is recorded here as an unregistered observation: at 2,000 risk units a random-direction trader passes 18.7%.
- The practical upshot for the first edge is modest and does not need a test to justify: contracts should be set from the day's expected move, not fixed, so that a volatile year is not traded at a calm year's size. That is risk hygiene. It is not a second edge.

**Iteration 22: 6 trials. Running total 184. Verdict: KILL.**

### Where the loop stands after iteration 22

| Iteration | Idea | Trials | Total | Verdict |
|---|---|---|---|---|
| 20 | Ensemble of nine breakout settings; ES with NQ | 2 | 177 | Fail |
| 21 | Optimal sizing by dynamic programming, out of sample | 1 | 178 | Fail by 0.1 point; equals simple constant risk |
| 22 | Constant-risk sizing, level chosen on early data | 6 | 184 | Fail |

Ten iterations and 54 tests since Ben asked for the loop; none has succeeded. The sizing question is now closed from three directions (goal-based policies, exact optimisation, constant risk): with this edge, no sizing rule adds more than a few points of pass rate over what a random trader gets from the same size.

---

## Iteration 23: the last ideas that need only our bars

_Third round, 23 Nov 2026. Cboe and FRED hosts still blocked; no new upload; no purchase approved._

### Sources
| Source | Status | Read | Claim |
|---|---|---|---|
| Rosa, *Journal of Futures Markets* 42(12), 2022 (cited in iteration 13) | Peer reviewed | Abstract | "A strategy with thresholds delivers higher returns than a strategy that is always active"; the overnight return predicts the last half hour only when the signal is strong; gone out of sample. |
| Singal and Tayal, "Risky Short Positions and Investor Sentiment: Evidence from the Weekend Effect in Futures Markets", *Journal of Futures Markets* 40(3), 2020 | Peer reviewed | Title and listing only | A weekend effect exists in futures and is tied to short sellers avoiding weekend risk. I have not read the size or sign, so the test is two-sided. |
| French, "Stock Returns and the Weekend Effect", *Journal of Financial Economics* 8(1), 1980 | Peer reviewed | From memory | Monday returns were negative on average in 1953-1977. |

### Hypotheses (written before testing)
- **ROSA-01.** When the overnight move (prior 15:00 CT close to 08:30 CT) is larger than half the expected daily move, the last half hour (14:30 to 15:00 CT) continues in its direction. ES and NQ, 2 trials. *Fit with the first edge:* a 30-minute trade at the end of the day on days that opened with a large gap; the breakout rule is usually already positioned by then, so this would add size when two signals agree. *Prior:* low; IMOM-03 (the always-on version) failed and the paper says the effect is gone.
- **WKND-01.** Returns around the weekend differ from other days: the Sunday-night session (18:00 Sunday to 08:30 Monday CT) and the Friday New York session, each against the same session on other days, ES and NQ. Two-sided, 4 trials. *Fit:* a calendar position unrelated to trend. *Prior:* low.
- **DOW-01.** The breakout rule's result differs by weekday. One F-test across five weekdays, 1 trial. *Fit:* a filter. *Prior:* very low; a filter that removes days has already been shown to cost pass rate, so only a large effect (F-test p below 0.01, same ordering before and after 2018) would matter.

### Results (measured on development data; costs assumed)

| Test | MES | MNQ | Verdict |
|---|---|---|---|
| ROSA-01, last half hour follows a large overnight move | Gross −0.30 points (−0.6x cost), t net −3.4, 13% of years | Gross −1.46 points (−1.3x cost), t net −3.0, 20% of years | Fail, wrong sign |
| WKND-01, Sunday night against other nights | Difference t +0.17 | Difference t +0.01 | Fail |
| WKND-01, Friday New York against other days | Difference t −0.70 | Difference t −1.60 | Fail |
| DOW-01, breakout rule by weekday | F-test p = 0.31; best days differ before and after 2018 | | Fail |

- After a large overnight move the last half hour leans the other way, not the same way, by about one cost on MNQ. This matches the wrong-sign result of EOD-01 in iteration 8. Fading it would gross 1.3 times the cost, short of the factor of 2 required, and it was not the registered direction.
- No weekend or weekday pattern.

**Iteration 23: 7 trials. Running total 191. Verdict: KILL all three.**

---

## Status after iteration 23: the loop is waiting on data

| Round | Iterations | Tests | Passed |
|---|---|---|---|
| First (evening of 22 Nov) | 13 to 19 | 45 | 0 |
| Second | 20 to 22 | 9 | 0 |
| Third | 23 | 7 | 0 |
| **Since the loop began** | **11 iterations** | **61** | **0** |
| Whole project | 23 iterations | 191 trials | 1 unpromoted candidate (NOISE-01B) |

I have stopped scheduling new rounds on the ES and NQ bars, and want to be plain about why, since the instruction was to continue until success. Every family of idea that these bars can test has now been tested: trend, intraday momentum, mean reversion, relative value at minutes and at days, lead-lag, bar-based order flow, volatility regimes, calendar (FOMC, FOMC cycle, releases, turn of month, expiration, holidays, weekdays, weekends), overnight and session effects, periodicity, filters on the first edge, an ML filter, ensembles, and sizing from three directions. What remains is variations of ideas already rejected. Running those would be data mining in the strict sense: with 191 trials behind us, the next "pass" on the same data would most likely be a false one, and I would have to advise against trading it.

The loop resumes the moment any of these arrives:
1. **Free volatility data** (Cboe VIX, VIX9D, VIX3M daily history; FRED rates). Opens: intraday momentum conditioned on implied volatility and its term structure, the gamma-theta breakeven with real implied volatility in place of our proxy, and the variance risk premium. These are the mechanisms the peer-reviewed papers actually name.
2. **Other markets** (decision card of 22 Nov, $25.74 to $80.02). Opens: the frozen rule on unrelated markets, the only route to real diversification.
3. **Options positioning data** (priced earlier at $48 to $104). Opens: the dealer-gamma hypothesis directly.

---

## Dashboard run 1 (23 Nov 2026): rerun of ENS-01, the nine-setting NQ breakout ensemble

Ben selected ENS-01 as the strategy to improve. This run adds no hypothesis and no trial (191 total). It reruns the ensemble with a full trade log and the true combined intraday equity (`sniper/ensemble.py`, `research/dash01_run.py`, `research/dash01_analyze.py`; outputs in `reports/dash01/`; dashboard source in `dashboard/`).

- **Reproduction:** $36.65 a day and $687 daily standard deviation at 8 MNQ-equivalent on development data, identical to iteration 20. Pass rate 30.2% (29.4% before; the difference is the more accurate worst-open-loss figure and simulation noise).
- **Size convention from here on:** one set = one MNQ per setting = at most 9 MNQ.
- **Development (in-sample), one set, measured with assumed costs:** +$126,711, Sharpe 0.85, 34.8% winning days, worst drawdown −$18,383. Sharpe −0.53 for 2010-2017 and +1.40 for 2018-Oct 2024. At double cost +$74,000, Sharpe 0.49.
- **Walk-forward year (out-of-sample, fourth look for this family):** +$7,197, Sharpe 0.23, t 0.21. One day (9 Apr 2025, +$24,927) exceeds the year's total.
- **Deflated Sharpe ratio 0.59** with 191 trials (bar 0.95).
- **Dollar risk has tripled:** daily standard deviation of one set $773 over development, $2,312 in the walk-forward year (NQ near 22,000). Monte Carlo from all development days understates today's risk at a fixed contract count. Drawn from walk-forward days, 9 MNQ on $50K passes 6.3% against 13.9% for the random control (simulated).
- **Structure of the edge:** trades held to the close win 79% and earn everything; trades that come back inside the band lose. Days on which all nine settings are in the market earn all the profit. The best 5% of traded days supply 55% of gross winnings. New York only; Asia and London lose in both samples.
- **News days:** payrolls days, skipped by default, averaged +$177 per set (t 2.3) in development.

---

## Iteration 24 (23 Nov 2026): META-02, a deep-learning filter for losing trades on New York high-volatility days

**Scope set by Ben (23 Nov 2026):** all testing is now on New York high-volatility days only. A day is high-volatility when its expected daily move (prior close times 20-day volatility), divided by its trailing 250-day median, is above 1.2828. That number is the upper-third cut on development data and is fixed from here on. It is known before the day starts.

**Winners against losers, development data, in-sample, descriptive (research/dl01_winlose.py; 7,680 trades on 752 days; 38.2% win).** The 33 entry-time features were fixed before this table was made.
- Nothing known at entry separates winners from losers well. The best single features have an AUC of 0.55 (0.50 is a coin): the noise width, minutes since the open, depth of the last hour's pullback, volume against normal, and direction (longs win more often).
- What separates them is known only after entry: winners are held 186 minutes on average and 72% of them reach the close; losers are held 66 minutes and 10% reach the close (AUC 0.79 to 0.88).
- Reading: with the same entry conditions, the outcome is decided by whether the day keeps trending after the entry. The filter has to forecast that from the entry-time state, and the single-feature evidence says the forecastable part is small.

**Prior evidence:** META-01 in iteration 11 (logistic and boosted trees, 15 features, all volatility regimes) failed its walk-forward check.

**META-02 hypothesis, written before any model was trained.** *Claim:* a neural network that reads the last 60 one-minute price changes before the entry (1-D convolutions) together with 33 entry-time features can score each New York high-volatility trade so that the lowest-scored third are net losers, and skipping them raises profit and the Combine pass rate. *Why it might work:* the shape of the path into the breakout (steady grind against spike, depth of pullbacks) is not captured by the summary features that failed in META-01, and losing breakouts are the ones that reverse quickly. *Why it may fail:* the edge is a few large trend days; a win/loss label treats a $20 win like a $600 win, so the filter can remove small losers and large winners together. 7,680 trades is small for a network. Trades of the nine settings on one day are near-copies, so the effective sample is about 750 days.

*Models (4 trials, total 195):* logistic regression and boosted trees on the table (baselines), a three-layer network on the table, and the convolutional network (primary). Fixed architecture, no tuning. *Protocol:* walk-forward by calendar year from 2016; train on earlier years only; last 15% of training days held back for early stopping and for the skip threshold (33rd percentile of held-back scores). The walk-forward year (November 2024 to October 2025) is scored once by a model trained on all development years; this is at least its fifth use for this rule family.

*Adopt only if all of these hold for the primary model on the out-of-fold development trades (2016 to October 2024):*
1. AUC at least 0.53, with the 95% interval from resampling whole days above 0.50.
2. Skipped trades lose money on average, and kept minus skipped has a day-clustered t of at least 2.
3. The filtered set earns at least as many dollars per day as the unfiltered set, has a higher Sharpe ratio, and its total beats the 95th percentile of random filters that skip the same share of trades.
4. Conditions 2 and 3 also hold at double cost.
5. The 30-day Combine pass rate ($50K, one set) is not lower than unfiltered (simulated).
6. In the walk-forward year the kept trades average more than the skipped ones.

**META-02 results (research/dl01_model.py, research/dl01_eval.py; out-of-fold test years 2016 to October 2024: 5,400 trades on 712 high-volatility days; walk-forward year: 602 trades on 87 days). Costs assumed 1.11 points per round trip; Monte Carlo simulated. Dashboard: https://claude.ai/artifact/Pigfz7om1vfyMiFjGjNf4a**

Unfiltered rule on New York high-volatility days: test years +$77,018 per set, Sharpe 1.51, t 2.55; walk-forward year +$13,311, Sharpe 0.80. $50K at 9 MNQ: 30-day pass 8.2% against 5.9% control, 34% with no time limit.

| Model | AUC (95% interval) | Kept / skipped per trade | t | Total filtered | Sharpe | 30-day pass | WF kept / skipped | Criteria |
|---|---|---|---|---|---|---|---|---|
| Convolutional network (primary) | 0.547 (0.508 to 0.583) | $16.83 / $9.98 | 0.69 | $56,811 | 1.52 | 7.4% | $44.23 / −$11.03 | 2 of 6 |
| Network on the table | 0.552 | $15.59 / $12.15 | 0.33 | $51,720 | n/a | n/a | −$36.77 / $111.54 | 1 of 6 |
| Boosted trees | 0.554 | $27.27 / −$5.91 | 3.42 | $89,537 | 2.17 | 7.8% | $67.82 / −$67.73 | 5 of 6 |
| Logistic regression | 0.553 (0.517 to 0.591) | $22.80 / −$0.12 | 2.18 | $77,263 | 2.00 | 9.3% | $76.91 / −$46.64 | 6 of 6 |

**Verdict: META-02 REJECTED.** The deep-learning filter (the model the hypothesis names) fails criteria 2, 3, 4 and 5. Its skipped trades were still profitable, so removing them cut total profit by a quarter. The predicted failure mode held: a win/loss label cannot tell a small loser from a missed large winner.

**Side finding, not adopted:** the two simple models rank trades slightly better than chance, and the logistic regression met all six criteria (worst drawdown −$6,659 against −$14,284; pass with no time limit 49% against 34%, simulated). It is not promoted because (a) it was a comparison model, not the pre-declared primary, so choosing it now is selection after the fact; (b) t 2.18 is before correction for 195 trials; (c) kept beat skipped in only 4 of 8 test years, with the gain concentrated in 2022 and 2024; (d) the same family failed walk-forward in iteration 11. Its largest weights: straightness of the move since the open (+), move in the last 30 minutes (−), distance past the band (+), overnight gap in the trade's direction (+), the set's closed result so far today (−).

**Trials: 195.** Next candidate if Ben wants it: pre-register the logistic filter as its own hypothesis (LOGIT-01) and judge it only on data it has not seen, which means paper tracking forward, since the holdout and walk-forward years are used.

---

## Iteration 25 (23 Nov 2026): SIZEVOL-01, volatility and contract size with the logistic filter, all New York hours

**Scope set by Ben (23 Nov 2026, 1:49 AM ET):** use the logistic regression as the filter; all New York trading hours and all volatility environments (not only high-volatility days); vary contract size and volatility; find out whether the two are related; compare the environments.

**Set-up, fixed before any result was seen.**
- *Filter (LOGIT-ALL, 1 trial):* the same logistic regression, 33 features, skip threshold and walk-forward protocol as iteration 24, but trained on all New York trades instead of high-volatility trades only. Test years 2016 to October 2024 out-of-fold; walk-forward year scored once (sixth use for this family). Note: the iteration 24 logistic was a side finding, not an adopted filter, and the all-days logistic in iteration 11 failed walk-forward. This iteration uses the filter because Ben asked for it; it does not promote it.
- *Environments:* low, middle and high volatility by the day's expected move over its 250-day median, with the cuts fixed in iteration 24 (thirds of development days; high is above 1.2828). Known before the open. A second, descriptive view sorts days by expected move in dollars.
- *Size grid:* MNQ held when every setting is in. $50K: 3, 6, 9, 12, 18, 27, 36, 50. $100K: 9, 18, 27, 36, 54, 72, 100. $150K: 9, 18, 27, 36, 54, 81, 108, 150. Capped at the Topstep position limit.

**Hypothesis.**
- *H1 (risk):* the dollar swing of one set rises in proportion to the expected daily move, so the contract count that maximises the Combine pass rate falls as volatility rises. *Test:* in a Monte Carlo that draws days from one environment only, the best size on high-volatility days is smaller than on low-volatility days for every account, and daily standard deviation per set rises across the three environments.
- *H2 (edge):* the edge per unit of risk is higher in high volatility (iteration 24 found Sharpe 1.5 there against 0.85 on all days), so at its own best size the high-volatility environment passes more often than the low one.
- *H3 (policy, the decision that matters):* over the full calendar, a size set each morning as a fixed dollar risk divided by the expected move (constant-risk sizing) passes the Combine within 30 trading days more often than the best fixed size. *Pass bar:* at least 2 percentage points better than the best fixed size on test years, larger than twice the Monte Carlo standard error, also better at double cost, and not worse on the walk-forward year. *Prior evidence against:* constant-risk sizing failed in iteration 22 on the unfiltered rule.
- *Policies tested (5 trials):* fixed size; constant-risk; fixed size on high-volatility days only; constant-risk on high-volatility days only; fixed size on middle and high days (skip low). Each over a grid of its one parameter, compared at its best value and with the full curve shown. Choosing the best grid point in-sample flatters every policy equally; the walk-forward year uses the parameter chosen on test years.
- *Why it may fail:* the 30-day limit rewards variance, so shrinking size on volatile days can remove the days that pass the Combine. The random-direction control at the same size is reported next to every pass rate.

**Trials:** 6 (1 filter, 5 policies), total 201.

**SIZEVOL-01 results (research/sv01.py; test years 2016 to October 2024 out-of-fold, 1,899 days; walk-forward year 212 days). Costs assumed 1.11 points per round trip; all pass rates simulated, 4,000 attempts. Dashboard: https://claude.ai/artifact/3HL4HUtN3Acp1qx1fdQyTd**

*Filter retrained on all New York trades (LOGIT-ALL):* AUC 0.564 (0.545 to 0.583); kept $13.90 against skipped $1.07 per trade, t 2.40; total $127,497 against $133,368 unfiltered; Sharpe 1.39 against 1.15. By environment the filter is inconsistent: middle volatility kept $18.14 against skipped −$14.30 (t 3.0); low $11.49 against $1.43 (t 1.4); **high $13.48 against $16.18 (t −0.2), so it removed profitable trades there**, the opposite of iteration 24's high-only model. Walk-forward year: kept $5.81 against skipped $0.44, t 0.14. Not adopted.

*Environments, one set, logistic filter, test years:*

| Environment | Days | Per day | Daily swing | Sharpe | t | MNQ for a $500 swing |
|---|---|---|---|---|---|---|
| Low | 676 | $53.73 | $575 | 1.48 | 2.43 | 7.8 |
| Middle | 511 | $77.42 | $718 | 1.71 | 2.44 | 6.3 |
| High | 712 | $72.50 | $942 | 1.22 | 2.05 | 4.8 |
| All | 1,899 | $67.14 | $767 | 1.39 | 3.81 | 5.9 |

Unfiltered: low Sharpe 1.23, middle 0.54, high 1.51. Daily swing grows with the expected dollar move with an elasticity of about 0.7 (a doubling of the expected move raises the swing 1.63 times).

- **H1 PARTLY SUPPORTED.** Daily swing rises low to high ($575, $718, $942). The pass-maximising size is smaller in high than in low volatility only on the $50K account (9 against 12 MNQ); the $100K and $150K grids tie (18 and 27). In every environment the best 30-day size is the one whose daily swing is about 40% to 70% of the loss limit.
- **H2 NOT SUPPORTED.** At each environment's own best size, $50K passes within 30 days 20.8% in high volatility against 21.2% in low. With the filter, high volatility has the lowest Sharpe of the three.
- **H3 FAIL.** $50K within 30 trading days, logistic filter: constant risk 18.8% against fixed 12 MNQ 20.9% (test years), 16.1% against 18.4% (double cost), 6.5% against 8.4% (walk-forward year). Same ordering on $100K and $150K. Trading only high-volatility days passes 7.6% within 30 days because the clock runs while waiting; skipping low-volatility days 12.9%. Constant-risk sizing confirms iteration 22.
- **Walk-forward year:** no size or sizing rule beat the random-direction control beyond simulation error (fixed 12 MNQ 8.4% against control 14.5%). The expected move of one set was $4,515 in that year against a $2,276 test-year median, so the test-year best size of 12 MNQ is about twice too large for today's index level; the best fixed size there was 6 MNQ.

**Verdict:** there is a relationship between volatility and contract size, and it is a risk relationship only: size should keep the daily dollar swing near half the loss limit, which means fewer contracts as the expected dollar move rises (today roughly half of what the 2016 to 2024 average suggests). Volatility does not identify days on which the edge justifies more risk, and varying size day by day did not raise the pass rate. No change adopted. **Trials: 201.**

---

## Iteration 26 (23 Nov 2026): STRAT-01, Ben's combined strategy

**Rule as given by Ben (23 Nov 2026, 2:09 AM ET), made exact before testing:**
- Trade the nine-setting ensemble in New York hours only on middle- and high-volatility days (expected move over its 250-day median above the lower-third cut fixed in iteration 24). No trading on low-volatility days.
- On middle-volatility days apply the logistic filter (the all-days model of iteration 25, unchanged, same scores). On high-volatility days take every trade.
- Baseline size N on middle-volatility days. On high-volatility days hold N x (1.2828 / ratio), where ratio is that morning's expected move over its 250-day median and 1.2828 is the high-volatility cut. The size therefore falls smoothly from N at the cut, in proportion to how far volatility is above it, and never rises above N. Known before the open. Whole-contract rounding is ignored in the test.
- Baseline grid: the iteration 25 size grid for each account.

**Comparisons (not new ideas):** the same rule without the size reduction; the same rule without the filter; iteration 25's fixed size on all days with the filter everywhere; the unfiltered rule on all days.

**Honest prior:** this rule was assembled after seeing iteration 25, which showed the filter helped in middle volatility and hurt in high. Choosing where to apply it from those same test years is selection after the fact, so test-year results are flattered. Iteration 25 also found that skipping low-volatility days and scaling size down in volatility each lowered the 30-day pass rate. The walk-forward year is the only check not used in that choice, and it has been viewed many times.

**Pass criteria for the strategy, $50K account:**
1. Test years: net profit positive with a daily t of at least 2.
2. Still positive with t of at least 2 at double cost.
3. Best-baseline 30-day pass rate at least 2 points above the iteration 25 benchmark (fixed size, all days, filter everywhere) at its best size.
4. That pass rate beats the random-direction control by more than twice the simulation error.
5. The size reduction earns its place: 30-day pass rate not lower than the same rule without it, each at its best baseline.
6. Walk-forward year, at the baseline chosen on test years: 30-day pass rate above the control.

**Trials:** 2 (the strategy, and the variant without the reduction; the no-filter variant is a decomposition), total 203.

**STRAT-01 results (research/strat01.py; test years 2016 to October 2024, 1,899 days; walk-forward year 212 days). Costs assumed 1.11 points per round trip; pass and payout rates simulated, 4,000 attempts. Dashboard page built in `dashboard4/` from `reports/dash04/`, not published at the time of writing.**

| Variant, test years, one baseline set | Traded days | Total | Sharpe | t | Worst drawdown |
|---|---|---|---|---|---|
| The strategy | 779 | $94,092 | 1.23 | 3.38 | −$12,784 |
| Same, no size reduction | 779 | $116,579 | 1.23 | 3.39 | −$14,614 |
| Same, no filter | 905 | $71,252 | 0.83 | 2.27 | −$24,490 |
| All days, filter everywhere, fixed size (iteration 25) | 1,011 | $127,497 | 1.39 | 3.81 | −$9,973 |
| All days, unfiltered, fixed size | 1,424 | $133,368 | 1.15 | 3.16 | −$13,895 |

Double cost: strategy $80,405, t 2.89. Walk-forward year: strategy $6,113, Sharpe 0.29, t 0.26 (unfiltered all days $7,197, Sharpe 0.23). In the walk-forward year the middle-volatility filtered trades lost (−$12.33 per trade, 351 trades); the high-volatility trades made $17.34.

Criteria, $50K: 1 PASS (t 3.38). 2 PASS (t 2.89). 3 FAIL (30-day pass 14.7% at 18 MNQ against 20.9% for the benchmark at 12 MNQ). 4 PASS (14.7% against control 9.0%). 5 PASS (14.7% with the reduction against 14.6% without, inside simulation error). 6 FAIL (walk-forward 4.4% against control 9.5%).

**Verdict: STRAT-01 not adopted, 4 of 6.** Profitable on test years but worse than trading every day with the filter, because skipping low-volatility days removes a third of the trading days and the 30-day clock keeps running. The size reduction lowers the drawdown and leaves the Sharpe ratio and pass rate unchanged. The filter on middle-volatility days did not hold in the walk-forward year. **Trials: 203.**

---

## Iteration 27 (23 Nov 2026): STRAT-02, STRAT-01 plus low-volatility days

**Change asked by Ben (23 Nov 2026, 2:19 AM ET):** include low-volatility days without the filter. Rule made exact before testing:
- Trade every New York day. Low-volatility days: every trade, baseline size N. Middle-volatility days: logistic filter (iteration 25 model, unchanged), baseline size N. High-volatility days: every trade, size N x (1.2828 / ratio).
- Days in the first year with no volatility ratio do not occur in the test years.

**Comparisons:** the same rule without the size reduction; STRAT-01; fixed size on all days with the filter everywhere (iteration 25 benchmark); the unfiltered rule on all days.

**Honest prior:** still assembled after seeing the test years (filter only where it helped there). In iteration 26 the middle-volatility filter lost money in the walk-forward year. Adding low-volatility days restores the trading days whose absence cost STRAT-01 its 30-day pass rate, so criterion 3 is the one to watch.

**Pass criteria, $50K account:** the same six as iteration 26 (profit with daily t of at least 2; the same at double cost; best-baseline 30-day pass rate at least 2 points above the iteration 25 benchmark; beats the coin control by more than twice the simulation error; the size reduction does not lower the 30-day pass rate; walk-forward year pass rate above the control at the baseline chosen on test years).

**Trials:** 2 (the rule, and the variant without the reduction), total 205.

**STRAT-02 results (research/strat01.py v2; data in reports/dash05/; page source dashboard5/). Costs assumed 1.11 points per round trip; pass and payout rates simulated, 4,000 attempts. Dashboard, published after Ben said to: https://claude.ai/artifact/V69E2CJQEtoiZaBuDvAX3J**

| Variant, test years, one baseline set | Traded days | Total | Sharpe | t | Worst drawdown |
|---|---|---|---|---|---|
| STRAT-02 (all days; filter on middle; reduced size on high) | 1,298 | $133,721 | 1.43 | 3.93 | −$11,634 |
| Same, no size reduction | 1,298 | $156,207 | 1.44 | 3.95 | −$12,264 |
| Same, no filter | 1,424 | $110,881 | 1.09 | 3.00 | −$13,890 |
| STRAT-01 (no low-volatility days) | 779 | $94,092 | 1.23 | 3.38 | −$12,784 |
| All days, filter everywhere, fixed size | 1,011 | $127,497 | 1.39 | 3.81 | −$9,973 |
| All days, unfiltered, fixed size | 1,424 | $133,368 | 1.15 | 3.16 | −$13,895 |

Double cost: $107,857, t 3.17. Walk-forward year: $6,009, Sharpe 0.24, t 0.22; by environment low −$104, middle (filtered) −$4,327, high (reduced) +$10,440.

Criteria, $50K: 1 PASS (t 3.93). 2 PASS (t 3.17). 3 FAIL (30-day pass 22.1% at 9 MNQ against 20.9% for the benchmark at 12 MNQ; 1.2 points, inside twice the simulation error, bar was 2). 4 PASS (22.1% against control 12.4%). 5 FAIL by a hair (22.1% with the reduction against 22.3% without, a tie within simulation error). 6 FAIL (walk-forward 7.8% against control 16.3%).

**Verdict: STRAT-02 not adopted, 3 of 6.** It is the best version on the test years so far (highest Sharpe, 30-day pass rate 22.1% against 14.7% for STRAT-01), which confirms that dropping low-volatility days was the cost in iteration 26. It is statistically level with the simpler benchmark, the size reduction is neutral, and the walk-forward year again shows no pass-rate edge over the control. **Trials: 205.**

---

## Iteration 28 (23 Nov 2026): TIMING-01, entry and exit timing

**Asked by Ben (23 Nov 2026, 2:56 AM ET):** research how entries and exits can be timed better, from the academic literature, and test varying methods. Goal: minimise loss while maximising gains.

**Base rule under test:** the unfiltered nine-setting ensemble, all New York days, news days skipped (ENS-01). Entry and exit are both decided at half-hour checks; exit when price is back inside the higher of band and VWAP; flat at the close. No filter and no size rule, so that a timing change is measured on its own.

**Literature and what each paper implies for this rule** (summaries from my reading of the abstracts and my memory of the papers; not re-derived here):
- Zarattini, Aziz and Barbon (2024), "Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)", Swiss Finance Institute paper 24-97. The source of the rule. Half-hour decisions, band plus VWAP as a trailing exit. https://ideas.repec.org/p/chf/rpseri/rp2497.html
- Maróy (2025), "Improvements to Intraday Momentum Strategies Using Parameter Optimization and Different Exit Strategies". Tests alternative exits on the same rule, including VWAP-based and ladder exits. Implies: test the exit level and how often it is checked.
- Kaminski and Lo (2014), "When Do Stop-Loss Rules Stop Losses?", Journal of Financial Markets 18. Stops add value only when returns have momentum (positive serial correlation); under a random walk they cost the risk premium. https://econpapers.repec.org/RePEc:eee:finmar:v:18:y:2014:i:c:p:234-254
- Lo and Remorov (2017), "Stop-loss strategies with serial correlation, regime switching, and transaction costs", Journal of Financial Markets. Tight stops are eaten by costs and whipsaw; benefit needs strong trend persistence. Implies: trailing stops should be wide and tested at double cost.
- Han, Zhou and Zhu (2016), "Taming Momentum Crashes: A Simple Stop-Loss Strategy". Stops cut the left tail of momentum. Implies: a stop may reduce the worst days even if it does not raise the mean.
- Gao, Han, Li and Zhou (2018), "Market intraday momentum", Journal of Financial Economics 129. The first half-hour return predicts the last half-hour return. Implies: take only trades in the direction of the first half hour. https://econpapers.repec.org/RePEc:eee:jfinec:v:129:y:2018:i:2:p:394-414
- Baltussen, Da, Lammers and Martens (2021), "Hedging demand and market intraday momentum", Journal of Financial Economics. Late-day continuation is driven by hedging flows into the close. Implies: holding to the close is where the edge is, so profit targets should hurt.
- Handa and Schwartz (1996), "Limit order trading", Journal of Finance. A limit order fills when price comes back to it, which is adverse selection for a momentum entry. Implies: a pullback entry improves price but misses the days that run.
- Prior project evidence: fixed stop at 0.25 daily moves, entry-count limits and entry-time cut-offs were rejected in iteration 11. Winners are trades held to the close (72%); losers are back inside within about an hour.

**Hypotheses (13 trials, total 218). Each changes one thing from the base rule.**
- *Decision frequency:* F1 exits checked every 5 minutes (entries stay half-hourly). F2 exits checked every minute. F3 entries and exits every 15 minutes. F4 entries and exits every 5 minutes. Claim: faster exits cut the loss on failed breakouts. Risk: whipsaw and cost (Lo and Remorov).
- *Exit level:* X1 exit on VWAP alone. X2 exit on the band alone. Claim: one of the two levels does the work.
- *Stops and targets, checked every minute, on top of the rule's exits:* S1 trailing stop 0.25 expected daily moves from the trade's best price. S2 trailing stop 0.5. S3 profit target at 1.0 expected daily move. S4 break-even stop once the trade has been 0.25 expected daily moves in profit. After a stop or target the setting may not re-enter in the same direction until a check finds price back inside the band. Claims: S1, S2, S4 reduce losses (Han et al.); S3 should hurt (Baltussen et al.).
- *Entry timing:* N1 confirmation: price must also have been beyond the band five minutes before the check. N2 pullback: after a signal, enter with a limit at the band level, valid until the next check; no fill, no trade. N3 only trades in the direction of the first half hour (Gao et al.).

**Adopt a method only if all hold on development data (all New York days to October 2024), then the walk-forward check:**
1. Net profit of one set not lower than the base rule.
2. Sharpe ratio higher than the base rule.
3. Worst drawdown not deeper.
4. Criteria 1 and 2 also hold at double cost.
5. Sharpe ratio higher in both halves of the development period (to 2017, from 2018).
6. The daily difference against the base rule has a t of at least 2.
7. Walk-forward year (seen many times): Sharpe not lower than the base rule.
Also reported for every method: average win, average loss, win rate, profit factor, worst day, worst open loss, and the same on high-volatility days. With 13 methods, one would be expected to clear a single t of 2 by chance about a third of the time, which is why all seven are required.

**TIMING-01 results (sniper/timing.py, research/timing01.py; tables in reports/timing01/). Development data, all New York days to October 2024, one set, costs assumed 1.11 points per round trip. The engine reproduces the frozen rule trade for trade (tests/test_timing.py).**

| Method | Trades | Total | Sharpe | Worst drawdown | Total at double cost | Avg win | Avg loss | Winners | t of daily difference | Criteria met (of 6) |
|---|---|---|---|---|---|---|---|---|---|---|
| B0 base rule | 23,744 | $126,711 | 0.85 | −$18,383 | $74,000 | $81.82 | −$38.99 | 37% | | |
| F1 exits every 5 min | 30,498 | $110,268 | 0.83 | −$21,570 | $42,563 | $74.30 | −$25.62 | 29% | −1.08 | 0 |
| F2 exits every minute | 34,073 | $96,746 | 0.75 | −$29,248 | $21,104 | $68.54 | −$21.53 | 27% | −1.72 | 0 |
| F3 15-minute decisions | 34,073 | $124,597 | 0.76 | −$18,063 | $48,955 | $75.40 | −$30.78 | 32% | −0.11 | 1 |
| F4 5-minute decisions | 60,627 | $65,482 | 0.39 | −$48,650 | −$69,110 | $59.43 | −$20.76 | 27% | −2.42 | 0 |
| X1 exit on VWAP alone | 20,250 | $153,834 | 0.93 | −$19,623 | $108,879 | $93.44 | −$52.27 | 41% | 1.81 | 4 |
| X2 exit on band alone | 22,963 | $128,587 | 0.85 | −$17,215 | $77,609 | $84.87 | −$40.96 | 37% | 0.25 | 3 |
| S1 trailing stop 0.25 | 23,009 | $65,513 | 0.64 | −$18,983 | $14,433 | $56.13 | −$29.42 | 38% | −2.04 | 0 |
| S2 trailing stop 0.5 | 23,226 | $124,467 | 0.94 | −$15,790 | $72,906 | $72.53 | −$35.79 | 38% | −0.12 | 3 |
| S3 profit target 1.0 | 23,645 | $134,262 | 0.93 | −$18,596 | $81,770 | $81.44 | −$39.17 | 37% | 0.56 | 3 |
| S4 break-even stop | 23,447 | $110,297 | 0.80 | −$17,416 | $58,244 | $77.57 | −$33.30 | 34% | −1.12 | 1 |
| N1 confirmed entry | 21,002 | $131,725 | 0.92 | −$16,831 | $85,101 | $85.18 | −$40.63 | 37% | 0.61 | 5 |
| N2 pullback entry | 16,222 | −$92,310 | −1.24 | −$93,304 | −$128,323 | $50.14 | −$28.24 | 29% | −6.76 | 0 |
| N3 first half hour's direction | 19,023 | $118,755 | 0.87 | −$13,942 | $76,524 | $82.63 | −$38.49 | 37% | −0.44 | 3 |

**Verdict: no method adopted; the walk-forward year was not opened for any of them.**
- Faster exits (F1, F2, F4) do cut the average loss (−$39 to about −$21) but cut winners more and multiply trades; at double cost they lose most or all of the profit. This is the whipsaw cost Lo and Remorov describe.
- A tight trailing stop (S1) halves the profit; a wide one (S2) lowers the worst day (−$4,064 against −$5,151) and drawdown at no gain in profit. The break-even stop hurts.
- The pullback entry (N2) loses heavily: the limit fills on the breakouts that fail and misses the ones that run, as Handa and Schwartz predict.
- The profit target (S3) did not hurt as predicted; it was roughly neutral (t 0.56).
- Near misses: exiting on VWAP alone (X1) raised profit by $27,123 and held at double cost, by letting more trades reach the close (50% against 35%), but with a larger average loss, a deeper drawdown and a t of 1.81. The confirmed entry (N1) met five of six and failed only on significance (t 0.61).
- Reading: losses in this rule are the price of staying in for the trend days. Methods that shrink the average loss shrink the gains by more; the one direction with support is the opposite, a looser exit. **Trials: 218.**

---

## Iteration 29 (23 Nov 2026): LOSS-01, minimising loss through entries and exits

**Direction from Ben (23 Nov 2026, 3:30 AM ET):** focus on minimising loss through optimal entries and exits. My reading, stated to him: loss reduction is now the primary objective and profit is a constraint, not the target. "Loss" is measured four ways: worst drawdown, the sum of all losing days, the worst single day, and how often a $50K Combine hits its loss limit.

**Starting point from iteration 28 (development data, one set):** base rule drawdown −$18,383, worst day −$5,151. Methods that lowered a loss measure without wrecking profit: wide trailing stop 0.5 daily moves (drawdown −$15,790, worst day −$4,064), entry confirmed five minutes earlier (drawdown −$16,831), first half hour's direction only (drawdown −$13,942). Methods that cut the average loss per trade by exiting faster made drawdown worse, because they multiplied the number of losing trades. So the target is the losing day, not the losing trade.

**Methods (8 trials, total 226). Each is the base rule plus:**
- C1 confirmed entry + trailing stop 0.5. C2 confirmed entry + first half hour's direction. C3 all three.
- T1 trailing stop 0.35. T2 trailing stop 0.75. (Brackets the 0.5 already tested; Lo and Remorov: width decides whether a stop pays.)
- D1 daily loss stop: once the whole set is down 0.5 expected daily moves (per contract, times nine) on the day, open positions included, flatten and stop for the day. D2 the same at 0.75. (Kaminski and Lo: a stop helps only if losses persist within the day; iteration 11 rejected a per-trade stop, this is a per-day stop on the combined position.)
- E1 no entries at the first check (10:00 AM ET); first entry at 10:30. (Iteration 24: later entries win more often.)

**Adopt only if all hold on development data, against the base rule:**
1. Worst drawdown at least 15% shallower.
2. Sum of losing days at least 10% smaller.
3. Worst day not worse.
4. Net profit at least 90% of the base rule, and Sharpe higher.
5. Criteria 1 and 4 also hold at double cost.
6. Drawdown shallower in both halves of the development period.
7. $50K Combine at 9 MNQ (simulated, days from 2016 to October 2024): loss limit hit less often and 30-day pass rate not lower.
8. Then the walk-forward year (seen many times): drawdown not deeper and Sharpe not lower.
The three single methods from iteration 28 are shown against the same criteria for reference; they were chosen for this list after their results were seen, so they are not fresh tests.
