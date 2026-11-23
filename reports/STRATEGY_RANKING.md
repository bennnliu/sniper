# Strategy ranking

_23 Nov 2026. Every strategy that has a daily result stream, scored the same way on development data (June 2010 to October 2024). All figures are **simulated** from measured daily results with assumed micro-contract costs, news days skipped unless stated. $50K Combine. Each strategy is scaled to the same daily dollar risk as the breakout rule at 8 MNQ (about $700 a day) unless a size is named, capped at 50 micros. Ranked by pass rate, then payout rate, then profit, then profit per account, as Ben asked. Research, not financial advice._

- **Pass rate:** share of Combine attempts that pass, with no time limit. **Within 30 days:** the same with a hard stop at 30 trading days.
- **Payout rate:** share of funded accounts that receive at least one payout (better of the two payout paths).
- **Profit:** expected payout from one funded account, minus the activation fee, minus the Combine fees spent to get that one pass.
- **Profit per account:** expected profit per Combine account bought.

| Rank | Strategy | Micros | Pass rate | Within 30 days | Median days to pass | Payout rate | Profit | Profit per account |
|---|---|---|---|---|---|---|---|---|
| 1 | Breakout NQ, New York, news days skipped, 2 MNQ | 2 | 52.7% | 0.6% | 164 | 82.7% | $-202 | $-107 |
| 2 | Breakout NQ, ensemble of nine settings | 8 | 29.4% | 13.8% | 34 | 44.4% | $+1,034 | $+304 |
| 3 | Breakout NQ, New York, news days traded, 8 MNQ | 8 | 27.9% | 14.7% | 29 | 41.9% | $+864 | $+241 |
| 4 | Breakout NQ, New York, news days skipped, 8 MNQ | 8 | 27.9% | 14.5% | 30 | 42.1% | $+770 | $+215 |
| 5 | Breakout NQ, quiet nights skipped | 9 | 25.5% | 10.4% | 38 | 39.2% | $+767 | $+196 |
| 6 | Breakout ES, New York (MES) | 12 | 23.2% | 14.2% | 27 | 39.8% | $+299 | $+69 |
| 7 | Long every Asia session (MNQ) | 8 | 22.8% | 15.2% | 24 | 45.4% | $+222 | $+51 |
| 8 | Long every New York session (MNQ) | 4 | 22.5% | 16.9% | 19 | 41.5% | $+201 | $+45 |
| 9 | FOMC-cycle even weeks long, New York (MNQ) | 5 | 21.6% | 12.0% | 28 | 36.3% | $-139 | $-30 |
| 10 | Long every night (MNQ) | 6 | 20.5% | 16.7% | 20 | 40.2% | $+203 | $+42 |
| 11 | Long overnight after a down day (MNQ) | 7 | 20.5% | 10.6% | 32 | 34.4% | $-15 | $-3 |
| 12 | New York fades the overnight move (MNQ) | 4 | 19.9% | 13.8% | 18 | 38.4% | $+111 | $+22 |
| 13 | Breakout NQ, New York, news skipped, 16 MNQ | 16 | 19.6% | 14.1% | 19 | 27.5% | $+1,060 | $+207 |
| 14 | Pre-holiday long, New York (MES) | 46 | 17.2% | 0.4% | 158 | 17.5% | $-2,038 | $-351 |
| 15 | Turn of month, New York (MNQ) | 8 | 16.3% | 5.4% | 47 | 22.7% | $-951 | $-155 |
| 16 | Random direction, same trades as the breakout, 8 MNQ | 8 | 15.0% | 9.1% | 24 | 29.3% | $-621 | $-79 |
| 17 | Breakout NQ, Asia session | 11 | 13.3% | 8.2% | 24 | 32.2% | $-737 | $-98 |
| 18 | Fade London breakouts (MNQ) | 12 | 10.0% | 8.6% | 18 | 25.4% | $-600 | $-60 |
| 19 | Breakout NQ, London session | 11 | 8.7% | 5.6% | 18 | 24.2% | $-1,629 | $-141 |

## How to read it

- **The random-direction row is the reference.** It takes the breakout rule's trades with the direction decided by a coin. It passes 15.0% (9.1% within 30 days) and loses $79 per account. Anything near it has no edge.
- **Only the breakout rows passed a signal test.** The rows between the breakout and the random row (long every session, FOMC weeks, fades) all failed their signal tests (t between -2.6 and +1.2). They rank above random only because the index rose over the sample, which a long position collects in dollars; in volatility units none is different from zero. They are not candidates.
- **Rank 1 is a trap for a 30-day goal.** At 2 MNQ the breakout passes 52.7% of attempts but takes a median of 164 trading days, so it pays about eight months of fees and loses money per account, and passes within 30 days 0.6% of the time.
- **The best profit per account is the breakout at 8 MNQ:** about +$215 to +$304 per account, with a 28 to 29% pass rate and 14 to 15% inside 30 trading days. The ensemble's lead over the single setting is inside simulation noise and failed its own test (iteration 20).
- **These are in-sample figures.** Out of sample the breakout did worse at this size: 12.5% pass at 8 MNQ in the walk-forward year (November 2024 to October 2025), and 35% at 2 MNQ in the holdout year (iteration 10). It is not promoted (deflated Sharpe 0.81 against a bar of 0.95).

## Tested earlier through the Combine simulator, numbers from the original reports

| Strategy | Result | Status |
|---|---|---|
| IMOM-04, last half hour follows the day on volatile down-trending days (iteration 2) | Best in-sample pass 35 to 43% on all three account sizes, about +$300 per attempt; then −$38 per MNQ trade (t −2.3) in the walk-forward year | Killed |
| Zero-edge baseline (iteration 6) | About 22% pass with no time limit at its best size, about $0 per attempt | Reference |
| Breakout with ML trade filter (iteration 11) | Failed its walk-forward check | Rejected |
| Breakout with stops, entry limits, news skip, expiration skip, ES confirmation, volatile-regime starts (iterations 11 to 16) | None raised pass rate or profit | Rejected |
| Breakout with goal-based, optimal (DP) and constant-risk sizing (iterations 13, 21, 22) | Best +2 to +5 points of 30-day pass rate, matched by the random control | Rejected |

## Failed the signal or cost test, never run through the Combine simulator

| Group | Strategies | Why |
|---|---|---|
| Real but smaller than the cost | 5-minute reversal (MR-04); NQ/ES spread reversion (RV-01); NQ-over-ES continuation intraday (RV-02) and overnight (PAIR-01, t 4.5); 1 to 2 AM drift (OD-01); one-minute lead-lag (LEADLAG-01) | Gross move 0.02x to 0.9x the micro cost |
| No signal | Moving-average and range-break trend (TREND-01/02/03); first-half-hour momentum (IMOM-01/02/03/07); opening-range breakouts (IMOM-05/06); VWAP, overnight-extreme, gap and prior-day-level reversion (MR-01/02/03/05); order-flow imbalance from trades and from bars (OFI-01/04, TOX-02); FOMC drift and release continuation (CAL-01/05); end-of-day reversal (EOD-01, ROSA-01); volume-gap regime (REG-01); same-half-hour periodicity (PERIOD-01); weekend and weekday effects (WKND-01, DOW-01); overnight compression (VOL-02) | t below 3, usually below 2 |
| Near miss | Pre-holiday long in New York hours (HOL-01): MES t 2.67, 93% of years, about 7 days a year | Below t 3; ranks low above because it almost never trades |
| Not testable with our data | Dealer gamma (GEX-02), factor-portfolio lead-lag (LEADLAG-05), order book (OFI-02/03, DEPTH-01/02), VIX and bond lead-lag (LEADLAG-03/04), breadth (RV-03) | Needs data we do not have |
