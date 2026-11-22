# METHOD

How a feature becomes a strategy, or dies trying. This file is fixed **before** any candidate is tested so that the method cannot bend to fit a result. Changes go through the change log at the bottom, with a reason, and never in the same iteration as the result that prompted them.

Every number in a report is labelled **measured** (computed from market data), **simulated** (from TopstepSim or the Monte Carlo) or **assumed** (an input we chose).

---

## 1. Data split (set once, before looking)

| Period | Use | Rule |
|---|---|---|
| Development: first available bar (CME Globex on Databento starts June 2010) to 31 Oct 2024 | Signal tests, cost tests, purged cross-validation, parameter choice | Free to use, but every look is a counted trial |
| Walk-forward: 1 Nov 2024 to 31 Oct 2025 | Out-of-sample check of anything that survives development | Each strategy is run forward with parameters frozen from data before each step |
| Final holdout: 1 Nov 2025 to the last full month of data | Run **once** per strategy candidate, at promotion | Never loaded by research code. The loader raises an error for any date in this range unless called with `holdout=True`, which only the promotion script does |

The holdout is the most recent 12 months on purpose: it is the regime the bot will actually trade in. If the data vendor's history turns out shorter or the regime break is obvious (for example, the 2020 crash), the dates are changed here with a reason before any test is run.

## 2. A feature is a hypothesis

No code touches a feature before its row in `feature_registry.csv` is complete:

| Column | Meaning |
|---|---|
| `id` | `FAMILY-NN`, never reused |
| `family` | One of the families in LITERATURE.md |
| `hypothesis` | One sentence: what predicts what |
| `mechanism` | Who is on the other side and why the effect should persist. Blank mechanism → bottom of the queue |
| `sign` | Expected sign of the relationship with forward return (+, −, or "filter" for conditioning variables) |
| `horizon` | Prediction horizon(s) to test |
| `data` | bars-1m, bars-1s, L1 (trades + top of book), L2 (depth), calendar |
| `kill` | The result that kills it (default: see §3.4) |
| `hold_profile` | Expected holding time and win-rate profile (Topstep fit) |
| `refs` | LITERATURE.md keys |
| `priority` | 1 (test first) to 3 |
| `status` | registered → signal_pass / signal_fail → cost_pass / not_tradable → strategy_* |
| `trials` | Number of variants tested so far |
| `result` | Headline measured numbers, filled automatically by the harness |

## 3. Stage 1: signal test (no trading rules)

**Goal:** does the feature carry information about future returns, before any choice of entry, exit or size?

1. **Forward returns.** Log mid-price return from the bar close at time *t* to *t + h*, for h ∈ {1, 5, 15, 30, 60 minutes, to 3:00 PM CT}. A horizon never crosses the 3:10 PM CT flat time or a session gap.
2. **Information coefficient (IC).** Spearman rank correlation between the feature at *t* and the forward return. Rank correlation is used because returns have fat tails and a few crash days would dominate a Pearson correlation.
3. **Overlap correction.** Consecutive 1-minute samples with a 30-minute horizon share 29 minutes of the same return, so they are not independent. The t-statistic uses Newey-West standard errors with *h* − 1 lags, and is cross-checked by computing the IC on non-overlapping samples (one every *h* minutes). We report the smaller of the two t-statistics.
4. **Stability.** IC by calendar year, by time-of-day bucket (overnight, 8:30 to 10:00, 10:00 to 14:00, 14:00 to 15:10 CT), and by volatility regime (terciles of trailing 20-day realized volatility). A real effect should keep its sign in most slices.
5. **Decay.** Plot IC against horizon. The peak sets where to look, and the horizon where IC falls to half its peak (the **half-life**) sets the natural holding time used in Phase 5.

### 3.4 Pass rule (default kill criterion)

A feature passes stage 1 only if **all** of these hold on the development period:

- |t| ≥ 3.0 at its best pre-registered horizon. The Harvey, Liu and Zhu hurdle: with hundreds of factors tried by the profession, t = 2 is no longer evidence.
- The IC has the pre-registered sign. A significant IC of the wrong sign is a fail, not a discovery (it can be re-registered as a new hypothesis with its own mechanism, and counts as a new trial).
- Same sign in at least 70% of calendar years and in at least 2 of 3 volatility terciles.
- Holm-adjusted p-value below 0.05 across all horizons tested for that feature.

A feature that fails is recorded as `signal_fail` with its numbers. That is a successful experiment.

## 4. Stage 2: cost test

**Goal:** can the effect pay for the trade?

All-in round-trip cost per contract, **assumed** until calibrated from tick data:

| Contract | Tick value | Fees per round trip (TopstepX) | Fees in ticks | Slippage assumed (round trip) | Total, ticks |
|---|---|---|---|---|---|
| ES | $12.50 | $3.78 | 0.30 | 1 tick | 1.30 |
| MES | $1.25 | $1.22 | 0.98 | 1 tick | 1.98 |
| NQ | $5.00 | $3.78 | 0.76 | 2 ticks | 2.76 |
| MNQ | $0.50 | $1.22 | 2.44 | 2 ticks | 4.44 |

**Micros cost far more per dollar of exposure.** One MNQ trade costs $1.22 for $2 a point; one NQ trade costs $3.78 for $20 a point, so the micro pays about 3.2 times as much in fees for the same exposure. Micros give sizing granularity (Phase 6), but a signal that only clears costs on minis cannot be traded in micros.

Pass rule: the mean forward move in the signal's direction must exceed **2 × total cost** at the chosen horizon, the gross expectancy of a naive "trade every signal" rule must stay positive at **double** cost, and the **t-statistic of that rule's dollar P&L must be at least 3** in the development period. Rank IC ignores the size of moves; dollars do not. A real effect that fails is recorded as `not_tradable`.

Before any Monte Carlo work, the frozen naive rule is run once on the walk-forward year. A negative mean there ends the candidate.

## 5. Stage 3: strategy test

Only features that pass stages 1 and 2. In order:

1. **Single-feature baseline:** a threshold rule (enter when the feature is beyond its development-period 80th or 20th percentile), fixed-time exit at the half-life, no stop. This is the benchmark everything later must beat.
2. **Labels that match real exits:** triple-barrier labels (§6.2).
3. **Combination:** only if two or more features survive, and only if a model beats the best single-feature rule after costs in purged cross-validation.
4. **Backtest:** event-driven, conservative fills (limit fills only when price trades through; market orders pay the spread plus slippage; home-connection latency), every equity path replayed through TopstepSim for all three account sizes.
5. **Walk-forward**, then (once) **holdout**.

## 6. Guards against overfitting

Each is explained the first time it is used in a report.

### 6.1 Purged and embargoed cross-validation (López de Prado, AFML ch. 7)
Ordinary k-fold cross-validation leaks when labels overlap in time: a training sample whose 30-minute label window overlaps the test fold has seen part of the test answer. **Purging** drops training samples whose label window overlaps any test sample. **Embargo** also drops training samples right after each test fold (we use the longest horizon plus one session), because features built from rolling windows carry test-period information forward. Folds are contiguous blocks of whole trading days, never shuffled.

### 6.2 Triple-barrier labels and meta-labelling (AFML ch. 3)
A trade ends at whichever comes first: profit target, stop, or time limit. The label is which barrier was hit. This matches how the bot exits, unlike a fixed-horizon return. **Meta-labelling** splits the problem: a primary rule picks direction, and a second model decides only whether to take each trade and at what size. It is used only once a primary rule has survived on its own.

### 6.3 Combinatorial purged cross-validation (CPCV, AFML ch. 12)
Split the development period into N groups, and test on every combination of k groups, training on the rest with purging and embargo. This gives many out-of-sample paths instead of one, so we see a distribution of results rather than a single lucky walk-forward. Default N = 10, k = 2 (45 splits, 9 paths).

### 6.4 Deflated Sharpe ratio (Bailey and López de Prado, 2014)
The best Sharpe ratio out of many trials is biased upward even if nothing works. The DSR computes the probability that the true Sharpe exceeds the expected maximum Sharpe of N worthless strategies, adjusting for skewness, fat tails and sample length. N is the trial count from `experiments.csv`. Validity bar: DSR ≥ 0.95.

### 6.5 Probability of backtest overfitting (Bailey, Borwein, López de Prado and Zhu)
Combinatorially symmetric cross-validation (CSCV): split the performance matrix of all variants into halves in every balanced way, pick the best variant in-sample, and record where it ranks out-of-sample. PBO is the share of splits where the in-sample winner falls below the out-of-sample median. PBO above 0.5 means the selection process is worse than a coin flip. We report it for every parameter sweep.

### 6.6 Multiple-testing corrections
- **White's Reality Check** and **Hansen's SPA test**: bootstrap tests (stationary bootstrap over whole days) of whether the best of all tested rules beats a benchmark (flat, zero return) after accounting for the whole set tried. SPA is less sensitive to poor, irrelevant rules in the set, so it is the one we act on; RC is reported alongside.
- **Harvey, Liu and Zhu:** the t ≥ 3.0 hurdle in stage 1, and Holm adjustment across horizons.

### 6.7 Parameter sensitivity
Every parameter is moved ±20% (and ±1 step for integers). A result that loses more than half its edge, or changes sign, under such a move is reported as fragile and is not promoted.

### 6.8 Counting trials
Every run that produces a number we look at is a row in `experiments.csv`: config hash, git commit, seed, feature ids, the number of variants in the run, and the cumulative total. Failed and abandoned runs count. The DSR and the Reality Check use the cumulative count, not the count for the winning feature alone.

## 7. Judging features together

- Correlation matrix of surviving features on the development period. When two have |ρ| > 0.7, keep the one with the stronger mechanism and simpler construction.
- Incremental value: regress forward returns on the incumbent features plus the candidate (with Newey-West errors). A candidate that adds no significant coefficient adds nothing.
- Prefer monotonic relationships (IC by feature decile should rise or fall steadily) and few parameters.

## 8. Prop-firm scoring

Sharpe is a diagnostic, not the objective. The headline for every surviving strategy is from the Monte Carlo over resampled days (blocks of whole days, so that intraday paths and day-to-day clustering are kept), for each of $50K, $100K and $150K:

- Combine pass probability with 95% confidence interval, median days to pass, breach probability.
- XFA probability of at least one payout before breach, on each payout path.
- Expected dollars per attempt net of all fees (ECONOMICS.md).
- Share of days at $150 or more.

## 9. Engineering rules

One config file per experiment; fixed random seed; git commit hash stored with every result; feature functions take only data up to time *t*, enforced by a test that shifts future data and checks the feature does not change; research and live code import the same feature functions.

---

## Change log

| Date | Change | Reason |
|---|---|---|
| 2026-11-22 | First version | Written before any feature was tested |
| 2026-11-22 | Stage 2 requires dollar P&L t ≥ 3; walk-forward check moved before the Monte Carlo | Iterations 1-2: IMOM-05 and IMOM-04 passed on rank IC with dollar t of 0.9 and 2.7, and IMOM-04 lost money in the walk-forward year |
