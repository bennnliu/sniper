# New strategy log

_Started 23 Nov 2026 at Ben's request ("start from scratch again"). One running log for the new search; iterations continue the project numbering (the last was 31 in `reports/SECOND_EDGE_LOG.md`) and the trial count continues from 232. Every figure is labelled measured, simulated or assumed. Research, not financial advice._

**Target (Ben, 23 Nov 2026):** pass a Trading Combine consistently inside 30 trading days and produce consistent payouts; minimising loss and consistent winning days come first. Unchanged: default validity bar, his profitability measure (`sniper/propscore.py`), New York and Asia tested separately, high and low volatility reported separately, high-risk news days skipped by default.

**What the first 232 trials established (not repeated here):**
1. ES/NQ bar-only ideas are exhausted; order flow on Aug-Oct 2024 trades failed.
2. The one rule with a signal, the NQ noise-area breakout, has a Sharpe near 0.85 in-sample and about zero after October 2024. Filters, stops, sizing and timing changes did not fix that.
3. Its losses come from choppy days and its gains from trend days; skipping days slows the 30-day clock as much as it saves.
4. A 30-day pass rate above 50% needs a daily Sharpe near 2.4, about three times that rule's.

**Consequence for this search:** one market cannot supply a Sharpe of 2.4 from this family. The untested lever is breadth: several unrelated markets traded every day, so that a choppy day in one is offset by a trend day in another. That raises Sharpe without skipping days, which is the one route the past findings leave open.

## Data purchases (new Databento key, approved budget $150)

| Date | What | Quoted cost | Running total |
|---|---|---|---|
| 23 Nov 2026 | One-minute bars, CL GC NG RTY YM ZN 6E 6J 6B (front contract by volume), 1 Jan 2018 to 31 Oct 2025, nine batch jobs | $87.31 | $87.31 |
| 23 Nov 2026 | Aborted first attempt by streaming (about 2 MB of crude bars before I switched to batch jobs) | about $0.30 (estimate) | $87.61 |

## Topstep rules for other markets (read 23 Nov 2026)

Sources: help.topstep.com articles 8284206 (products), 10296582 (prohibited conduct), 9221977 (micros), 8284213 (fees, dated 30 Sep 2026), 13613539 (risk adjustments, "updated this week").
- Permitted: equity (ES, NQ, RTY, YM, NKD and micros), FX (6A, 6B, 6C, 6E, 6J, 6S, 6M, 6N, E7, M6E, M6A, M6B), energy (CL, MCL, QM, NG, QG, MNG, RB, HO), metals (GC, MGC, SI, SIL, HG, MHG, PL), rates (ZT, ZF, ZN, TN, ZB, UB), ags (ZC, ZW, ZS, ZM, ZL, HE, LE). Flat by 3:10 PM CT, or the product's own earlier close.
- **Current temporary caps ($50K / $100K / $150K, Combine and funded):** CL 3/6/9, MCL 30/60/90, GC 3/6/9, MGC 30/60/90, **SI 0, HG 0, PL 0**, SIL and MHG 2/5/7. So silver, copper and platinum are not usable; crude and gold are, at reduced size.
- Micros count 10 to 1 against the position limit (Micro Silver 5 to 1).
- **Tier 1 news (CPI, FOMC, NFP, PPI), 5 minutes either side:** no new positions in minis of equity indices and metals; micros limited to 3/6/9 contracts. Rates, FX and energy are unaffected. Existing positions may be held. Our default of skipping these days makes this moot.
- Prohibited conduct has no rule against trading several products in one account. Hedging across accounts is prohibited; we use one account.
- Round-turn fees (assumed from the fee page): CL $4.02, MCL $1.72, NG $4.22, MNG $1.92, GC $4.32, MGC $1.92, RTY/YM $3.78, M2K/MYM $1.22, ZN $2.62, ZB $2.76, 6E/6J/6B $4.22, M6E/M6B $1.00.

## Iteration 32 (23 Nov 2026): XM-01, the frozen breakout rule on nine other markets (written before buying or running)

**Source.** Baltussen, Da, Lammers and Martens (JFE 2021, already in LITERATURE.md, read) find intraday momentum in more than 60 futures across equities, bonds, commodities and currencies, and tie it to hedging by option sellers and leveraged funds. Zarattini, Aziz and Barbon (2024) give the trading rule we already built. If the mechanism is hedging demand, it should not be confined to the Nasdaq.

**Hypothesis.** The noise-area breakout, with nothing re-tuned, earns a positive result after costs on other liquid futures in New York hours, and its daily results are weakly correlated across asset classes, so an equal-risk portfolio has a much higher Sharpe than any one leg.

**Markets (fixed now):** CL, GC, NG, RTY, YM, ZN, 6E, 6J, 6B. Chosen for liquidity in New York hours, Topstep permission and asset-class spread. Silver and copper are excluded because Topstep caps them at zero.

**Rule (frozen, `run_session` defaults):** New York session 8:30 to 15:00 CT for every market, bands from the 14-day average move, width 1.0, anchored on the open and the prior 15:00 close, checks every 30 minutes, VWAP condition, fill one minute after the decision, flat at 15:00. News days (CPI, payrolls, FOMC in `calendar_data/events.csv`) skipped.

**Costs (assumed):** round-turn fee above plus one tick of slippage per side, on the contract we would actually trade: MCL, MGC, MNG, M2K, MYM, M6E for the six with micros (priced off the full-size bars), and full-size ZN, 6J, 6B. Shown again at double cost.

**Data split for the new markets:** development 1 Jan 2018 to 31 Oct 2024; walk-forward 1 Nov 2024 to 31 Oct 2025; holdout 1 Nov 2025 on, **not bought**, untouched for every new market. 2018 is the start because the NQ rule only worked from 2018 and it halves the data cost.

**Measure.** Each market's daily net result divided by its expected daily move (prior close x 20-day volatility), so markets and years are comparable. Portfolio = the plain average of the nine.

**Pass rule, all on development data:**
1. Portfolio daily t at least 3.0.
2. Portfolio still positive with t at least 2.0 at double cost.
3. Portfolio positive in at least 5 of the 7 calendar years.
4. At least 6 of the 9 markets positive on their own.
If all four hold, one run on the walk-forward year (mean must be positive), then the Combine simulation with NQ added, against a random-direction control. If they fail, the per-market table decides whether anything is worth a narrower, separately registered test.

**Trials:** 9 markets + 1 portfolio = 10. Total after this iteration: 242.

### Iteration 32 result: FAIL on all four criteria. The breakout does not travel.

Development data, 1 Jan 2018 to 31 Oct 2024, news days skipped, costs on. Measured. Files: `reports/xm01/`. Code: `research/xm01.py`.

| Market (contract) | Days | Net t | Gross t (no costs) | Win rate | Cost as share of the daily move | Years positive |
|---|---|---|---|---|---|---|
| Crude (MCL) | 1,390 | -2.22 | 0.39 | 39% | 2.4% | 1 of 7 |
| Gold (MGC) | 1,417 | -1.68 | 1.32 | 38% | 2.5% | 2 of 7 |
| Natural gas (MNG) | 1,387 | -6.70 | -1.29 | 35% | 3.3% | 0 of 7 |
| Russell (M2K) | 1,446 | -1.51 | 0.21 | 37% | 1.8% | 2 of 7 |
| Dow (MYM) | 1,448 | -0.02 | 1.38 | 38% | 1.5% | 4 of 7 |
| 10-year note (ZN) | 1,443 | -8.10 | 0.69 | 33% | 8.3% | 0 of 7 |
| Euro (M6E) | 1,465 | -6.05 | 0.72 | 38% | 5.8% | 0 of 7 |
| Yen (6J) | 1,444 | -2.80 | 1.36 | 37% | 3.3% | 2 of 7 |
| Pound (6B) | 1,430 | -5.36 | -0.99 | 36% | 3.9% | 0 of 7 |
| **Equal-risk portfolio** | 1,494 | **-8.78** | | | | **0 of 7** |

- Before costs no market has a t above 1.4, and two are negative. There is nothing to rescue with cheaper execution or a different contract.
- After costs every market loses. Rates and currencies lose most because their daily move is small against a one-tick spread: one round trip costs 4 to 8% of a day's expected move, against 1.5% for the Dow.
- The diversification half of the hypothesis was right: daily results are nearly uncorrelated across asset classes (0.00 to 0.17; Russell and Dow 0.44). Breadth would work if there were an edge to spread. There is not.
- It is not a mirror-image fade either: gross results sit at zero, not below it.
- Reading: the NQ result of 2018 to 2024 looks more like one market's good run than a general hedging-demand effect. That fits its failure after October 2024.

**Verdict: KILL XM-01.** The walk-forward year for these markets was not opened. Trials: 10, total 242.

## Options positioning data: priced, not bought (23 Nov 2026)

Dealer gamma is the mechanism every paper names for trend days versus choppy days, so I priced the open-interest data to compute it. A two-day sample ($0.03) showed the "ES options" product holds only the quarterly options; the weekly and daily expiries, where most short-dated gamma now sits, are sixteen separate products. Open interest for all of them from 2018 costs about $201, and the quarterlies alone $27.65. The full set is over the remaining budget and the quarterlies alone would be a poor proxy after 2020, so nothing was bought. Running total: $87.64. This stays an open option for Ben.

Free alternative found: Yahoo (already allowed in this environment) serves daily history for the VIX, its 9-day and 3-month versions, the VVIX and the Nasdaq VXN back to 2009-2011. Implied volatility and its term structure are the cheapest window onto the same mechanism, and the old loop was paused waiting for exactly this data.

## Iteration 33 (23 Nov 2026): IV-01 to IV-04, implied volatility as a regime and direction signal (written before running)

**Sources.** Baltussen et al. 2021 (momentum stronger when dealer gamma is negative; read). Cheng, "The VIX Premium", Review of Financial Studies 2019 (exists; abstract only: the premium embedded in VIX futures falls or turns negative when risk rises, and predicts returns). Both name states that the VIX term structure reveals: when the VIX is above its 3-month version the market is stressed and dealers are typically short gamma.

**Data.** Yahoo daily closes of ^VIX, ^VIX3M, ^VVIX. Every signal uses the close of the day before the session it predicts. ES and NQ bars, development period June 2011 to October 2024, news days skipped, micro costs, results in volatility units.

**Tests (10 trials, total 252).** Each is a regression of a daily result on the signal's percentile within its own trailing 250 days; pass needs t at least 3.0 with the stated sign, the same sign in at least 70% of years, and for a pass the difference between the top and bottom thirds must exceed twice the cost.
- IV-01 (2 trials: ES, NQ): the breakout rule's daily result rises with the term-structure slope VIX / VIX3M. Sign +.
- IV-02 (2 trials): the breakout rule's daily result rises with the VVIX. Sign +.
- IV-03 (2 trials): a long position through the New York session earns more after a high slope (stress premium). Sign +.
- IV-04 (4 trials: ES and NQ, New York session and Asia session): after a day when the VIX rose by more than the index return explains (residual of a trailing 250-day regression of VIX change on index return), the next session rises. Sign +.

A filter alone cannot help a 30-day Combine (iterations 13 to 19), so IV-01 and IV-02 matter only if strong enough to switch between two rules; IV-03 and IV-04 trade every day.

## Iteration 34 (23 Nov 2026): XA-01, do bonds, yen, crude and gold lead the index by minutes? (written before running)

**Source.** Registered since Phase 3 as LEADLAG-04 (rates react first to macro news) and never testable; the new bars make it so. Hasbrouck 2003 on price discovery across index products (in LITERATURE.md).

**Hypothesis.** The move in ZN, 6J, CL or GC over the last k minutes, multiplied by that market's trailing 20-day beta to the index at the same horizon (so the sign is set by past data, not by me), predicts the index's next k minutes. k = 1, 5, 15. Targets ES and NQ, New York session, 2018 to October 2024.

**Pass:** rank correlation t at least 3.0 with a positive sign (the smaller of the overlapping and non-overlapping t), same sign in 70% of years, and the average next-k move in the top and bottom tenths of the signal at least twice the micro cost (MES 0.5 points, MNQ 1.11 points).

**Trials:** 4 predictors x 2 targets x 3 horizons = 24. Total 276.

### Iteration 33 result: all ten FAIL (best t 2.58)

ES and NQ, June 2011 to October 2024, news days skipped, micro costs, volatility units. Measured. `reports/iv01/results.csv`, `research/iv01.py`. Raw VIX history saved to `/mnt/project-files/data/raw/yfinance/iv_daily.csv`.

| Test | Market | Slope t | Years same sign | Top third mean (t) | Bottom third mean (t) |
|---|---|---|---|---|---|
| IV-01 breakout vs VIX/VIX3M | ES | 1.87 | 64% | +0.010 (0.56) | -0.027 (-2.03) |
| IV-01 breakout vs VIX/VIX3M | NQ | 2.58 | 79% | +0.045 (2.98) | -0.005 (-0.36) |
| IV-02 breakout vs VVIX | ES / NQ | 0.62 / 1.01 | 50% / 57% | | |
| IV-03 long New York vs slope | ES / NQ | -0.48 / -0.70 | wrong sign | | |
| IV-04 long after a VIX overshoot, New York | ES / NQ | -0.16 / -1.30 | wrong sign | | |
| IV-04 long after a VIX overshoot, Asia | ES / NQ | -0.84 / -1.10 | wrong sign | | |

- IV-01 has the sign the theory predicts in both markets: the breakout earns in the third of days when short-dated implied volatility is high against 3-month, and nothing or less in the calm third. At t 2.58 and 1.87 it is below the bar, and as a filter it would remove two thirds of trading days, which the 30-day clock cannot afford. Recorded as a near miss that supports the dealer-gamma reading, not as a rule.
- The directional ideas (IV-03, IV-04) have no signal; a long position in New York hours loses its costs in every regime.
**Verdict: KILL all four.** Trials 10, total 252.

### Iteration 34 result: all 24 FAIL (wrong sign, and under a quarter of the cost)

ES and NQ against ZN, 6J, CL, GC, New York session, 2018 to October 2024. Measured. `reports/xa01/results.csv`, `research/xa01.py`.

- Not one of the 24 has a significant positive rank correlation. Twelve are significantly negative (t -2.4 to -4.8), meaning the index slightly reverses the move the other market implied. That is the index's own short-term reversal seen through a correlated market (MR-04 found the same in iteration 3), not information arriving from bonds or yen.
- Size: trading the top and bottom tenths of the signal earns between -0.46 and +0.27 points per trade before costs, against a cost of 0.74 points (MES) or 1.11 (MNQ). The largest is a quarter of the cost.
**Verdict: KILL XA-01 and close LEADLAG-04.** Trials 24, total 276.

## Iteration 35 (23 Nov 2026): FXS-01 and GCS-01, session drifts in currencies and gold (written before running)

**Source.** Breedon and Ranaldo, "Intraday Patterns in FX Returns and Order Flow", Journal of Money, Credit and Banking 45(5), 2013 (exists; recalled from the abstract, not re-read today): a currency tends to fall during its own country's working hours and rise during the other country's, because local firms and investors are net buyers of foreign currency in their own day. The effect was reported as large against spot spreads. Gold's rise in Asian hours and fall in London and New York hours is a practitioner observation with no peer-reviewed source I can confirm, so it is low priority.

**Why now.** Iteration 32 showed daily results in currencies, gold and the index are nearly uncorrelated. A one-trade-a-day drift in each would be the every-day, uncorrelated stream the 30-day goal needs. The bars are already paid for.

**Tests (8 trials, total 284).** One position per session, entered at the session start and closed at its end, 2018 to October 2024, news days skipped, costs on, volatility units. Sessions as before: Asia 18:00 to 01:00 CT, London 02:00 to 08:30, New York 08:30 to 15:00.
- FXS-01a: long 6E, long 6B, long 6J through New York hours (the dollar falls in US hours). 3 trials.
- FXS-01b: short 6E and short 6B through London hours; short 6J through Asia hours. 3 trials.
- GCS-01: long gold through Asia hours; short gold through New York hours. 2 trials.

**Pass:** net t at least 3.0 with the stated sign, positive in at least 5 of 7 years, still positive at double cost.
