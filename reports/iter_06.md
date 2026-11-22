# Iteration 06: zero-edge baseline

_22 Nov 2026. Simulated on real NQ 1-minute day-session paths from the development period. No signal is involved._

## 1. Verdict

**Baseline set, nothing to promote.** A strategy with no edge passes the $50K Combine about **21-23%** of the time and is worth roughly **$0 per attempt** after fees (simulated; the best case across 5 policies was +$37 and the worst −$8 on $50K, within simulation noise).

## 2. What was tested

One MNQ trade a day at 9:00 CT in a direction that carries no information, with a stop, a target and a 15:00 CT time exit. Every development day (3,592 full sessions) is used twice, long and short, so the edge before costs is exactly zero. Fills are conservative: 1 tick of slippage on entry and stop, targets fill only on a trade through, and the stop wins a tie. Fees come from the rule spec. 4,000 Monte Carlo paths per cell.

Policies: stop/target of 20/20, 20/40, 40/20, 40/80 and 60/30 NQ points; sizes from 5 to 150 MNQ. Trials: 5 (50 in total).

## 3. Results at the size with the best expected value (simulated)

| Policy (stop/target, pts) | Account | Size | Combine pass | Median days to an outcome | XFA payout chance (Standard / Consistency) | Expected $ per attempt |
|---|---|---|---|---|---|---|
| 20 / 20 | $50K | 30 MNQ | 20.6% | 4 | 31% / 25% | −$8 |
| 20 / 40 | $50K | 20 MNQ | 21.5% | 5 | 21% / 16% | +$4 |
| 40 / 20 | $50K | 30 MNQ | 22.3% | 3 | 22% / 25% | +$10 |
| 40 / 80 | $50K | 10 MNQ | 22.9% | 7 | 29% / 17% | +$35 |
| 60 / 30 | $50K | 20 MNQ | 23.0% | 3 | 20% / 23% | +$37 |
| 40 / 80 | $100K | 20 MNQ | 18.4% | 5 | 23% / 14% | +$30 |
| 40 / 80 | $150K | 30 MNQ | 18.4% | 5 | 23% / 14% | +$38 |
| 20 / 20 | $150K | 75 MNQ | 15.0% | 4 | 45% / 18% | −$107 |

Expected dollars = pass rate × (trader's share of all payouts from the funded account − $149 activation) − Combine months × (subscription + $29 API).

## 4. What it means

- **The rules alone are close to a fair bet.** With no edge, a simple random walk between +$3,000 and −$2,000 would pass 40% of the time. The consistency rule, the 2-day minimum, the trailing loss limit and costs cut that to about 22% on $50K and 15-18% on the larger accounts.
- **$50K is the most forgiving size for a no-edge trader**, and the larger accounts are slightly worse. Their targets are twice the loss limit instead of 1.5 times.
- **The positive numbers are not an edge.** They are the best of several noisy estimates, each with a standard error of roughly $15-25. Read them as "about zero".
- **This is the bar.** A real strategy must clearly beat a 22% pass rate and $0 per attempt. Iteration 2's late-day idea showed 35-43% in-sample, which looked like progress, and then lost money out of sample.
- **Why it is not negative:** the trader's loss per attempt is capped at the fees (about $78 a month on $50K), while payouts are real money. Topstep earns on the many who fail, and the structure does not need the average attempt to lose much.

## 5. Critique

1. **Gambling a Combine is not a plan.** Topstep's prohibited-conduct rules let it deny payouts for trading it judges not to reflect real market behaviour, and large size held for a few days with random direction is close to that. The simulation ignores this risk entirely.
2. **The funded-account side is optimistic.** It assumes every payout is requested the moment it is allowed and approved without question, and it runs the account until it breaches.
3. **Costs are assumed, not measured.** One extra tick of slippage on 30 MNQ is $15 a trade, which is the same size as the whole expected value.

## 6. Next

Waiting on Ben's choice of direction (iteration 5 report, section 10).
