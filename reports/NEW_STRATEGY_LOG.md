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
