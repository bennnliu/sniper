# Account economics

All numbers here are **assumed**: they come from Topstep's published prices in `topstep_rules.yaml` (read 22 Nov 2026), not from any trading result. Regenerate the table with `python -m sniper.economics`.

## What one attempt costs

A Combine has no time limit, but each 30 days costs a subscription month, and a reset after a breach costs the same as a month. So the cost of an attempt is the number of months it runs times (subscription + $29 API). The API fee is per person, not per account, so it is shared when several Combines run at once.

On the standard path the Express Funded Account (XFA) then costs a $149 activation fee. On the no-activation-fee path the activation is $0 but each Combine month costs more.

## Break-even

Let **p** be the pass probability per attempt and **V** the trader's share of all payouts one XFA produces before it breaches.

- Expected profit per attempt = p × (V − activation) − months × (subscription + API)
- Break-even pass rate p* = months × (subscription + API) / (V − activation)
- Break-even XFA value V* = activation + months × (subscription + API) / p

The table uses V = one maximum Standard payout at the 90% split, and 1-month attempts.

| Size | Combine path | Monthly | Activation | Cost per 1-month attempt (with API) | Trader share of one max Standard payout (V) | XFA balance needed for it | Break-even pass rate at V | Break-even V at 20% pass rate |
|---|---|---|---|---|---|---|---|---|
| 50K | standard | $49 | $149 | $78 | $1,800 | $4,000 | 4.7% | $539 |
| 50K | no_activation | $95 | $0 | $124 | $1,800 | $4,000 | 6.9% | $620 |
| 100K | standard | $99 | $149 | $128 | $2,700 | $6,000 | 5.0% | $789 |
| 100K | no_activation | $149 | $0 | $178 | $2,700 | $6,000 | 6.6% | $890 |
| 150K | standard | $199 | $149 | $228 | $4,500 | $10,000 | 5.2% | $1,289 |
| 150K | no_activation | $229 | $0 | $258 | $4,500 | $10,000 | 5.7% | $1,290 |

## What the table says

1. **The fees are small next to the payout.** A strategy that passes 1 attempt in 20 and then takes one maximum payout already breaks even on every size. The hard part is entirely V, not the fees.
2. **V is the bottleneck, and it is harder than it looks.** A payout is capped at 50% of the XFA balance, so the maximum $2,000 payout on a 50K XFA needs a $4,000 balance, built from $0 while a $2,000 trailing MLL follows it. After the first payout the MLL sits at $0, so whatever is left in the account is the entire cushion. This is why Phase 6 treats the XFA as its own sizing problem.
3. **Which Combine path is cheaper depends on the pass rate.** Standard costs $149 × p per attempt in activation; no-activation costs an extra $46, $50 or $30 per month (50K, 100K, 150K). For 1-month attempts, standard is cheaper when p is below about 31% (50K), 34% (100K) or 20% (150K). Until we have a measured pass rate, assume the standard path.
4. **Account size only scales the fees and the payout caps.** The ratio of target to MLL is 1.5 on 50K, 2.0 on 100K and 2.0 on 150K, so the 50K Combine is the hardest race relative to its cushion. Whether that changes the outcome for a given strategy is a TopstepSim question that we will answer with Monte Carlo once we have a strategy, for all three sizes.

## Not modelled yet

- The limited-time promotion that doubles payout caps when the DLL is added at purchase.
- Multiple payouts per XFA, the Live Funded Account, and Back2Funded reactivation ($599/$699/$829).
- Taxes and payment-method fees (ACH and wire cost $30; Prop-to-Brokerage and Aeropay are free).
