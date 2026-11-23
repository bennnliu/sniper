# Summary at pause: 60 tests, no tradable strategy

_22 Nov 2026. Search paused at Ben's decision. Research, not financial advice._

## 1. Verdict

**No strategy is promoted, and none is close.** Of 38 registered hypotheses, 19 were tested in 60 counted trials. None predicts ES or NQ direction strongly enough to pay trading costs out of sample. The honest position is that there is no evidence of an edge, and a Topstep Combine traded without one is worth about **$0 per attempt** (simulated).

The walk-forward year (Nov 2024 to Oct 2025) was used once, for one candidate. The holdout (from Nov 2025) was never bought or loaded.

## 2. What was tested

| Family | Ideas tested | Result |
|---|---|---|
| Intraday momentum (IMOM-01 to 06) | First half hour predicts last half hour, opening-range breakout, late-day momentum on high-volatility days | Published effects do not replicate on 2010-2024 data. IMOM-04 on NQ passed in-sample (IC +0.114, t 4.10), then lost $38 per MNQ trade in the walk-forward year. **Killed.** |
| Trend (TREND-01 to 03) | Moving-average spread, breakouts | No signal, as expected. |
| Mean reversion (MR-01 to 04) | VWAP, overnight gap, overnight extremes, sharp 5-minute moves | MR-04 is real (t −16 on ES) but earns about a fifth of its cost. With limit orders on real trade data it loses to adverse selection. **Real, not tradable.** |
| Relative value (RV-01) | NQ/ES spread reversion | Real (t −4.8), about a twentieth of cost. |
| Order flow (OFI-01, OFI-04) | Aggressor imbalance and large prints, on 3 months of tick trades | No forecast power beyond the same minute. |
| Calendar (CAL-01, 02, 05) | Pre-FOMC drift, release windows, post-release continuation | No direction. Release windows are 2 to 3.6 times as volatile, which is a risk rule, not an edge. |

Not tested (19): lead-lag, depth and toxicity ideas that need Level 2 data, volatility filters, turn of month, options-expiry pinning, dealer gamma. Options-positioning data was priced at $48 to $104 (DATA.md) and not bought.

## 3. What the numbers say about Topstep itself (simulated)

- With zero edge, the $50K Combine passes about **22%** of the time, and the $100K and $150K about 15-18%. A naive random walk would suggest 40%; the consistency rule, the trailing loss limit and costs take the rest.
- After subscription, activation and API fees, the expected value of an attempt is roughly **$0** (between −$8 and +$37 across five policies on $50K, inside simulation noise).
- Break-even pass rate from fees alone is 4.7-6.9% (ECONOMICS.md), but a pass only pays if the funded account then reaches a payout, and without an edge it mostly does not.
- Account size changes the best position size, not the pass rate.

## 4. What exists and still works

| Piece | Where | Use |
|---|---|---|
| Rule spec | `topstep_rules.yaml` | Every Topstep rule with source and date. **Re-verify after 22 Dec 2026.** |
| Rule simulator | `sniper/sim.py` | Replays fills through Combine and XFA rules for all three sizes. 89 tests pass. |
| Monte Carlo | `sniper/montecarlo.py` | Pass, breach and payout odds from daily results; checked 30/30 against the simulator. |
| Signal harness | `sniper/signal.py` | Rank IC with overlap-corrected t, stability slices, look-ahead check. |
| Data | `sniper/data.py`, project files | ES and NQ 1-minute bars Jun 2010 to Oct 2025; 3 months of tick trades. Holdout guarded. |
| Method and log | `METHOD.md`, `feature_registry.csv`, `experiments.csv` | The rules of evidence and every trial counted. |

Any new idea can be tested in an hour or two: add a registry row, compute the feature, run it through the harness. A full strategy test through the Topstep simulator takes a few hours more.

## 5. Mistakes made along the way

- IMOM-04 looked good on rank IC while its dollar t was only 2.7. The method now requires dollar t ≥ 3 and a walk-forward check before any Monte Carlo work.
- A truncated NQ download and incomplete event-date lists were both caught by checks before any result depended on them.
- Estimated data spend is $113.57 of a $125 free credit. This is an estimate from cost quotes; the billing page is the truth.

## 6. Critique of this conclusion

1. **"Nothing works" is only shown for simple, public, bar-based ideas.** A home setup with 1-minute bars competes worst exactly where these ideas live. The untested families need costlier data and faster execution, where a home bot is at a larger disadvantage.
2. **Costs were assumed, not measured** (1 tick round-trip slippage on ES, 2 on NQ). Lower real costs would not rescue anything: the best real effects earn 0.05 to 0.22 times cost.
3. **A 12-month walk-forward can kill a real but weak strategy by bad luck.** IMOM-04's loss there (t −2.3) was large enough that this is unlikely, though not impossible.

## 7. If the search resumes

In order of expected value per dollar: (1) NQ options open interest for a dealer-gamma test, $48; (2) remaining free bar tests, CAL-03 and volatility filters, low odds; (3) Level 2 data, expensive and unlikely to suit a home connection. A different goal is also worth considering: using this infrastructure to evaluate a discretionary or third-party approach before paying for Combines, since the simulator answers "what pass rate does this trade record imply?" for any trade log.
