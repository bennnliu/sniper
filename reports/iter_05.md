# Iteration 05: order flow on tick data (and iteration 4 bar checks)

_22 Nov 2026. Level 1 trades for ES and NQ, 1 Aug to 31 Oct 2024 (inside the development period). Holdout untouched._

## 1. Verdict

**KILL.** Order-flow imbalance has no forecasting power at 1 to 15 minutes: the best rank IC is **+0.007 with t = 0.5** (measured). The limit-order reversal loses money after fees.

## 2. What was tested

- **OFI-01:** buy-minus-sell aggressor volume over the last 1 and 5 minutes, predicting the next 1, 5 and 15 minutes.
- **OFI-04:** signed volume of the largest 1% of prints over the last 5 minutes.
- **MR-04L:** the 5-minute reversal from iteration 3, traded with a resting limit order. The order sits one tick through the last price for up to 2 minutes and fills only when a later trade prints through it. Exit is at market 5 minutes later.
- **Iteration 4 bar checks (no spend):** IMOM-06 (30-minute opening-range breakout) and TREND-03 (prior-day return).
- **Data:** 28.0 million ES trades and 23.2 million NQ trades, day session only.
- **Trials:** 10 in iteration 5 (including 2 void runs, see Mistakes) and 4 in iteration 4. **45 in total.**

## 3. Signal evidence (measured)

| Feature | Symbol | Best horizon | IC | t | Stage 1 |
|---|---|---|---|---|---|
| OFI-01, 1-minute window | ES | 15 min | +0.004 | 0.55 | fail |
| OFI-01, 5-minute window | ES | 15 min | +0.007 | 0.52 | fail |
| OFI-04 | ES | 5 min | −0.007 | −0.28 | fail |
| OFI-01, 1-minute window | NQ | 5 min | −0.003 | −0.09 | fail |
| OFI-01, 5-minute window | NQ | 5 min | −0.001 | −0.10 | fail |
| OFI-04 | NQ | 15 min | +0.024 | −0.17 | fail |
| IMOM-06 | ES / NQ | to close | −0.005 / −0.014 | −0.31 / −0.82 | fail |
| TREND-03 | ES / NQ | day session | −0.008 / −0.015 | −0.45 / −0.85 | fail |

**Sanity check.** Imbalance and the return in the *same* minute have a rank correlation of 0.66 (ES) and 0.72 (NQ). So the trade signing is correct and order flow does move price, exactly as Cont, Kukanov and Stoikov describe. It just tells us nothing about the *next* minute. By the time a 1-minute bar closes, the information is already in the price.

## 4. Trading evidence: limit-order reversal (measured fills, fees from the rule spec)

| | ES | NQ |
|---|---|---|
| Signals | 465 | 460 |
| Fill rate | 89% | 98% |
| Mean per trade, points | −0.46 | +0.10 |
| Mean per trade after fees | **−$26.82** | **−$1.83** |
| t of mean | −2.01 | −0.08 |
| Win rate | 43% | 49% |

The limit order saves the spread but gets filled mostly when price keeps going against it. This is adverse selection, as the brief predicted.

## 5-6. Prop-firm and overfitting evidence

Not applicable: nothing passed stage 1 or 2.

## 7. Mistakes

- The first run of MR-04L produced zero signals. Its volatility window needed 200 days of history and the sample has 64. It was fixed to the 20-day window used in iteration 3 and re-run. Both void runs stay in `experiments.csv` and are counted.
- Three months is a short sample for stability checks (the "year" slice is really a month here). That weakens a pass, not these fails: t-statistics near zero on 25,000 minutes would not become 3 with more data unless the effect were tiny.

## 8. Critique of the result

1. **The horizon may be too long.** Order-flow predictability probably lives below one minute (Kolm et al.: about two price changes). *Test:* 10-second windows on the same data, at no extra cost. But a signal that only exists for seconds cannot be traded from home under Topstep's rules, so it would only confirm the Level 2 decision.
2. **Aug-Oct 2024 may be unrepresentative.** *Test:* another quarter, about $64. Not worth it given t near zero.
3. **The limit-order test used one rule.** Other queue placements or exits might work. *Test:* a real queue-position simulator needs order-book data (MBO), which is far outside the budget.

## 9. Suggestions

**Finding features.** After 45 trials, every family that fits this setup has been tested at least once: trend, intraday momentum, mean reversion, relative value and order flow. None survives costs. The evidence now says something about the whole project, not only about single features: **simple, published, bar-level and trade-level effects in ES and NQ are either gone or smaller than a retail round trip.** Remaining untested ideas are conditional ones (macro-release windows, FOMC days, dealer gamma with real options data) and cross-market ones (Treasuries, VIX futures).

**Testing features.** No change. The pipeline caught every failure cheaply, which is its job.

## 10. Next iteration plan (needs Ben's direction)

Three ways forward, in the order I would take them:

1. **Event and calendar conditioning (no spend):** CAL-01 (FOMC-day drift), CAL-02 (behaviour around CPI and payrolls releases), and whether any failed signal works only inside those windows. Few events a year means weak statistics, so expectations should be low.
2. **Dealer-gamma data (new spend):** test Baltussen's mechanism directly instead of the volatility proxy that failed out of sample. Needs an options-positioning data source to be priced.
3. **Change the question:** the Combine is passable with a zero-edge strategy some fraction of the time (iteration 2 saw 35-43% in-sample with a tiny edge). A study of pure risk-shaping (size, daily stops, payout timing) on a no-edge random walk would show what pass rate and expected dollars the rules alone give, net of fees. That is an honest baseline every future strategy has to beat, and it may be negative.
