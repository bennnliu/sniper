# Iteration 03: trend, reversal and NQ/ES spread on 1-minute bars

_22 Nov 2026. Development period only. Holdout and walk-forward untouched._

## 1. Verdict

**KILL** for all five hypotheses as trading ideas. The best tradability ratio was **0.22× the assumed round-trip cost** (MR-04, NQ). Three effects are real (|t| from 4.8 to 16) but far too small to pay the spread: **real, not tradable.**

## 2. What was tested

- **TREND-01:** 60/240-minute EMA spread.
- **TREND-02:** 60-minute breakout.
- **MR-02:** first touch of the overnight high or low, 8:30-10:00 CT.
- **MR-04:** extreme 5-minute return reversal, scaled by time-of-day volatility.
- **RV-01:** z-score of the beta-hedged NQ/ES spread.

ES and NQ were tested separately except for RV-01. Samples were taken every 5 minutes in the day session from 9:00 CT. No horizon was allowed past 3:10 PM CT.

Trials: 9 this iteration, **31 in total**.

## 3. Signal and cost evidence (measured; costs assumed)

| Feature | Symbol | Best horizon | IC | t | Years with right sign | Stage 1 | Mean move ÷ cost | Verdict |
|---|---|---|---|---|---|---|---|---|
| TREND-01 | ES | 60 min | +0.011 | 0.98 | 60% | fail | 0.38 | fail |
| TREND-01 | NQ | 60 min | +0.017 | 1.86 | 73% | fail | 1.36 | fail |
| TREND-02 | ES | 60 min | −0.005 | −0.51 | 33% | fail | 0.03 | fail |
| TREND-02 | NQ | 60 min | −0.003 | −1.07 | 13% | fail | −0.13 | fail |
| MR-02 | ES | 15 min | −0.039 | −2.16 | 60% | fail | 0.50 | fail |
| MR-02 | NQ | 15 min | −0.014 | −0.80 | 47% | fail | 0.38 | fail |
| MR-04 | ES | 5 min | −0.033 | **−16.2** | 100% | pass | **0.20** | real, not tradable |
| MR-04 | NQ | 5 min | −0.019 | **−8.9** | 100% | pass | **0.22** | real, not tradable |
| RV-01 | NQ/ES | 15 min | −0.018 | **−4.8** | 80% | pass | **0.05** | real, not tradable |

**What "real, not tradable" means here.** Short-horizon reversal after a sharp 5-minute move exists in every year. But the average reversal is about a fifth of what a round trip costs, and part of it is probably bid-ask bounce: a bar that closes on the ask after buying tends to be followed by a close on the bid, which looks like reversal but cannot be captured. The NQ/ES spread does revert, but by about a twentieth of the cost of trading two legs.

**Trend rules were the pipeline calibration** (LITERATURE.md, MOP2012). They were expected to show nothing intraday after costs, and they show nothing, which is reassuring about the pipeline.

## 4-6. Trading, prop-firm and overfitting evidence

Not applicable: nothing passed stage 2.

## 7. Mistakes

- The first run of the iteration 3 script was killed for using too much memory (all features, both symbols and the joined NQ/ES frame in one process). The script now runs ES, NQ and the spread as separate processes. No results came from the failed run, and none were logged.
- The TREND rules show a positive mean per trade but a strongly negative mean per day. Their few winning days carry many signals with large moves, while most days lose. This is not a bug; it is how trend rules typically behave intraday.

## 8. Critique of the result

1. **MR-04 might be tradable with limit orders.** A limit order at the bar extreme could earn the spread instead of paying it. *Test:* needs Level 1 data to simulate queue position and adverse selection honestly (DATA.md step 4). This is the first feature that earns a Level 1 purchase.
2. **RV-01 might work at longer horizons or with a stricter threshold.** *Test:* not worth it. At 0.05× cost, even a tenfold improvement fails.
3. **MR-02 was close (t −2.16 on ES).** *Test:* not re-tested on the same data. Re-registering it with a tweak would be snooping.

## 9. Suggestions

**Finding features:** the bar-only families (trend, intraday momentum, mean reversion, relative value) have now mostly been tested, and nothing survives costs. The untested bar hypotheses left are low priority (TREND-03, IMOM-06, MR-05, RV-02, RV-03, VOL filters, CAL-01, CAL-03). The next information source should be **Level 1 data**, for OFI-01 (aggressor imbalance at 1-15 minutes) and a limit-order version of MR-04. Those are the most promising remaining families.

**Testing features:** a limit-order fill simulator (trade-through rule, queue position) is needed before any Level 1 strategy test.

## 10. Next iteration plan

1. Level 1 data for OFI-01 and a limit-order MR-04. Priced on 22 Nov 2026 (Databento `get_cost`, Jan-Oct 2024): `trades` about $103 per symbol, `tbbo` about $172 per symbol, `ohlcv-1s` $31-37 per symbol. About 3 months of ES and NQ `trades` costs roughly $62. **This needs Ben's approval** (tick data was outside the approved budget).
2. In parallel, with no spend: IMOM-06 (30-minute opening-range breakout), CAL-02 (macro-release windows), TREND-03.
