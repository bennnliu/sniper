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
