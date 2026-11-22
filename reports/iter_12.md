# Iteration 12: search for a second, unrelated edge

_22 Nov 2026. Development period only. News days (CPI, payrolls, FOMC) skipped throughout, per Ben's constraint. No data spend. Walk-forward and holdout untouched._

## 1. Verdict

**KILL for all five ideas (25 tests). No second edge exists in our ES and NQ data.** After 130 trials, the honest reading is that one-minute bars on two highly correlated index futures have been searched thoroughly. A second edge that is truly unrelated most likely has to come from a different market, which needs a data purchase.

## 2. What was tested

The first edge trades breakouts in New York hours and earns most on volatile trend days. An unrelated edge should hold a different kind of position, at a different time, or in a different market. Earlier short-horizon ideas all died on costs, so these tests hold for hours, where costs are small against the move.

| ID | Idea | Sessions |
|---|---|---|
| ON-01 | Being long earns a premium outside cash hours | Asia, London, whole night, New York (each its own test) |
| ON-02 | The night reverses the previous New York session; long after down days | Overnight |
| ON-03 | New York reverses the overnight move | New York |
| CAL-03 | Turn-of-month days drift up | New York, overnight |
| FADE-01 | London-hours breakouts reverse | London |
| RV-02 | NQ's morning lead over ES continues into the afternoon | New York |

Each on ES and NQ, in micro-contract costs (MES 0.495 points, MNQ 1.11 points a round trip, assumed). Pass rule: t ≥ 3 in daily-move units, positive in 70% of years, gross move at least twice the cost.

Trials: 25 this iteration (two are controls), **130 in total**.

## 3. Evidence (measured; costs assumed)

| Test | MES: mean per trade, t | MNQ: mean per trade, t | Years positive (MES / MNQ) |
|---|---|---|---|
| Long, Asia session | −$0.65, −2.54 | +$1.35, −0.47 | 13% / 33% |
| Long, London session | −$1.53, −2.54 | −$2.19, −2.59 | 13% / 20% |
| Long, whole night | +$1.03, −0.40 | +$2.30, +0.37 | 47% / 47% |
| Long, New York session | +$0.10, −0.53 | +$0.37, −0.27 | 47% / 47% |
| Night fades prior New York move | −$2.13, −1.64 | −$1.63, −1.50 | 40% / 53% |
| Long overnight after a down day | +$1.85, +0.68 | +$3.21, +0.64 | 53% / 60% |
| New York fades the overnight move | −$1.68, −2.23 | −$2.36, −2.01 | 27% / 27% |
| Turn of month, New York | −$0.56, −0.92 | +$1.51, −0.52 | 40% / 47% |
| Turn of month, overnight | −$1.73, +0.36 | −$3.55, +0.45 | 47% / 60% |
| London breakout fade | −$3.05, −6.59 | −$2.38, −6.33 | 7% / 13% |
| NQ-over-ES continuation (pair) | IC +0.039, t 2.17; net −3.5 bp after 4.5 bp of costs on two legs | | 20% |

The t-statistics are in daily-move units, so a dollar mean can be slightly positive while t is negative: the dollars come from recent years when the index is higher.

- **There is no overnight premium to harvest in micros.** The gross overnight drift is 1.4 to 2 times the cost on average and not statistically different from zero once news nights are removed (t −0.4 to +0.4). The drift after down days points the right way (as Boyarchenko, Larsen and Whelan report) and is far from significant.
- **Volatility split, as requested.** The overnight long is negative in calm regimes and positive in volatile ones (MES t −2.86 low, +2.32 high; MNQ −1.84 and +2.17). That is the usual "risk premium is paid when risk is high" pattern. It was not a registered hypothesis, so it is noted, not claimed. A filter chosen after seeing this table would be snooping.
- **Day and night do not reverse each other here.** Before 2018 the New York session tended to continue the overnight move (t +2.8 to +3.3 for continuation); since 2018 there is nothing (t 0.1).
- **London breakouts lose and so does fading them.** Both sides lose roughly the cost: there is no directional information in those hours at this horizon. This corrects the hint in iteration 11 that London reversals were close to tradable.
- **NQ's lead over ES does continue a little** (t 2.2), by about 1 basis point, against 4.5 basis points of costs for a two-legged micro trade.

## 4-6. Trading, prop-firm and overfitting evidence

Not applicable: nothing passed the signal test, so nothing was scored under Topstep rules. No combination with the breakout rule was possible.

## 7. Mistakes

- The control "overnight on non-turn-of-month days" was first computed with a sign bug (positions of −1 and −2 from negating a non-boolean column) and showed t −4.6. It was fixed before any conclusion. The corrected control is t −0.5 and +0.1. The logged trial row for it still carries the first number and is corrected in the report here.

## 8. Critique of the result

1. **Skipping news nights removes some of the documented overnight drift**, since part of it is tied to macro days. *Test:* not run, because trading those nights conflicts with constraint 4.
2. **ES and NQ are about 0.9 correlated.** Any edge found on one is nearly the same bet on the other, so two instruments are really one. *Test:* other markets.
3. **Bars cannot see order flow or positioning.** The two paid routes already priced (options positioning, $48 to $104) remain untested.

## 9. Suggestions

**Finding features:** the cheapest route to an unrelated edge is the **same breakout rule in unrelated markets**. Intraday momentum from hedging flows is documented across more than 60 futures markets (Baltussen and co-authors, in LITERATURE.md), and a rule that works in gold or crude oil on different days from NQ would add up to a much steadier combined result. If each of four unrelated markets had this rule's Sharpe ratio of about 0.8, the combination would be near 1.6, where the 30-day pass rate rises to about 40% (iteration 11, section 9). If the rule fails elsewhere, that is also strong evidence that the NQ result is luck.

**Testing features:** nothing new. The session engine, micro costs, news filter and Topstep scoring were used from the first test, as planned.

## 10. Next iteration plan

Needs Ben's approval because it costs money.

- Topstep's help page lists CL, GC, RTY, ZN and 6E and their micros (MCL, MGC, M2K, M6E) as permitted products (read 22 Nov 2026). The micros carry a note pointing to restrictions under "Prohibited Conduct", which I have not yet read and will verify before any test relies on them. TopstepX round-turn fees listed: MCL $1.04, MGC $1.24, M2K $0.74, M6E $0.52, ZN $1.60.
- Databento quotes for 1-minute bars (22 Nov 2026): 2018 to October 2024 costs $8.27 to $8.76 per market; June 2010 to October 2024 costs $16.85 to $18.21 (RTY $8.74). Five markets (crude oil, gold, Russell 2000, 10-year note, euro): **$42.76** from 2018, **$80.02** for full history. About $10 of free credit remains (estimate).
- The test would be fixed in advance: the frozen rule, unchanged parameters, each market in its own most active session, micro costs, news days skipped, t ≥ 3 in daily-move units per market, then the combined Topstep score within 30 trading days.
