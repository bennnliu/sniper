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
