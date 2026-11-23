# LITERATURE

One note per source. Each record gives the claimed effect, market and period, data frequency, whether costs were included, replication, likely decay, and what changes for NQ/ES intraday under Topstep's rules.

**Verification status** (checked 22 Nov 2026):
- **read**: the abstract or paper page was read and the claim below matches it.
- **exists**: the paper was found at the link with the stated title, authors and venue, but the effect described is from the published abstract as commonly cited and was not re-read this session. Re-read before relying on a number.

---

## Intraday momentum

### GHLZ2018. Gao, Han, Li and Zhou, "Market intraday momentum", *Journal of Financial Economics* 129(2), 2018, 394-414. **read**
Link: https://econpapers.repec.org/RePEc:eee:jfinec:v:129:y:2018:i:2:p:394-414
- **Claim:** the first half-hour return of the S&P 500 ETF (SPY) predicts the last half-hour return. Stronger on volatile days, high-volume days, recessions and major macro news days. An earlier working version (1999-2012) reports an R² of about 2% and a timing strategy earning about 6% a year (via Alpha Architect's summary, not the published table).
- **Market, period, frequency:** SPY 1993-2013, plus ten other ETFs; half-hour returns.
- **Costs:** not in the abstract.
- **Replication and decay:** confirmed in futures by BDLM2021 (below). Widely known since 2014, so some decay is likely.
- **Translation to NQ/ES:** the cash session is 8:30-15:00 CT. First half hour = 8:30-9:00 CT, last half hour = 14:30-15:00 CT, which finishes before the 3:10 PM CT flat rule. One trade a day, 30-minute hold. A 2% R² is large for returns but means most days are noise; the question is whether the conditional move exceeds about 1.3 ticks in ES (METHOD §4). → IMOM-01, IMOM-03.

### BDLM2021. Baltussen, Da, Lammers and Martens, "Hedging demand and market intraday momentum", *Journal of Financial Economics* 142(1), 2021, 377-403. **read**
Link: https://www3.nd.edu/~zda/intramom.pdf
- **Claim:** the return from the previous close to 30 minutes before the close (rROD) predicts the last 30 minutes, in 17 developed-market equity index futures and in bond, commodity and currency futures. Mechanism: option market makers who are short gamma must trade in the direction of the move. For the S&P 500, momentum appears when a net-gamma proxy is negative and is absent when it is positive.
- **Market, period, frequency:** 1-minute bars, December 1974 to May 2020.
- **Costs:** main results are gross (per the paper summary; not confirmed in the text).
- **Replication and decay:** the paper reports significance in both 1974-1999 and 2000-2020 with a smaller coefficient later (from a summary, unverified). The 0DTE options boom since 2022 changes dealer gamma intraday; the sign of that change is unknown, so the effect could be stronger or weaker now.
- **Translation:** directly on ES and NQ futures. Without option open-interest data we cannot compute net gamma; we proxy it by realized volatility and the day's direction (IMOM-04). → IMOM-02, IMOM-04, VOL-01.

### ZA2023. Zarattini and Aziz, "Can Day Trading Really Be Profitable? Evidence of Sustainable Long-term Profits from Opening Range Breakout (ORB) Day Trading Strategy vs. Benchmark in the US Stock Market", SSRN 4416622, 2023. **read**
Link: https://papers.ssrn.com/abstract=4416622
- **Claim:** a 5-minute opening-range breakout on QQQ, traded via TQQQ, earned an annualized alpha of 33% net of commissions, 2016-2023.
- **Costs:** commissions only, no spread or slippage (per KRUEGER2026).
- **Replication:** see KRUEGER2026. The gross edge reproduces; net of realistic costs it is about zero.
- **Translation:** NQ is the futures equivalent of QQQ. The rule trades the direction of the first 5-minute bar with a stop at its far side and holds to the close, so win rate is low (about 23%) with rare large winners. That profile suits Topstep badly: few $150 days and long losing streaks against a trailing MLL. → IMOM-05, IMOM-06.

### KRUEGER2026. Krueger Algorithms, "The opening-range breakout paper, replicated on five indices: gross reproduced, net zero", MQL5 blog, 2026. **read**
Link: https://www.mql5.com/en/blogs/post/776235
- **Claim:** on NQ, S&P 500, Dow, DAX and FTSE CFDs, January 2015 to June 2026, the rule earns +0.131 R gross on NQ with a 23.2% hit rate, but +0.002 R (t ≈ 0) after spread and slippage; four of five markets are negative net. Against a random-direction benchmark the first bar shows a small edge of about 0.1 R in NQ, DAX and FTSE.
- **Caveat:** a vendor blog, not peer reviewed, and the author sells trading systems. We use it only as a warning that sets IMOM-05's kill criterion.

## Trend

### MOP2012. Moskowitz, Ooi and Pedersen, "Time series momentum", *Journal of Financial Economics* 104(2), 2012, 228-250. **read**
Link: https://www.aqr.com/library/journal-articles/time-series-momentum
- **Claim:** the past 12-month excess return of each of 58 futures and forwards predicts its next-month return; the effect persists about a year, then partly reverses.
- **Frequency:** monthly. **Costs:** not on the abstract page.
- **Translation:** the horizon is months, not minutes, so this is not evidence for intraday trend. We use simple trend rules (TREND-01 to 03) to calibrate the pipeline: they are expected to show little or nothing after costs, and a strong result would point to a bug.

## Lead-lag and price discovery

### HAS2003. Hasbrouck, "Intraday price formation in U.S. equity index markets", *Journal of Finance* 58(6), 2003, 2375-2400. **read**
Link: https://ideas.repec.org/a/bla/jfinan/v58y2003i6p2375-2400.html
- **Claim:** for the S&P 500 and Nasdaq-100, most price discovery happens in the E-mini futures, not in the floor-traded futures or the ETFs.
- **Translation:** we trade the venue that leads. Cash-index or ETF signals are therefore unlikely to lead ES/NQ (LEADLAG-02 is expected to fail). Whether NQ leads ES or the reverse is open (LEADLAG-01).

### HY2005. Hayashi and Yoshida, "On covariance estimation of non-synchronously observed diffusion processes", *Bernoulli* 11(2), 2005. **exists**
Link: https://projecteuclid.org/euclid.bj/1116340299
- **Claim:** a covariance estimator for two asynchronously traded prices that avoids the bias of sampling both on a common grid.
- **Use:** the tool for measuring NQ/ES lead-lag at tick level without the artificial lag from bar sampling.

### HA2014. Huth and Abergel, "High frequency lead/lag relationships: empirical facts", arXiv 1111.7103 (later in *Journal of Empirical Finance*). **read**
Link: https://www.arxiv.org/abs/1111.7103v1
- **Claim:** lead-lag cross-correlations are strongly asymmetric, especially futures leading stocks. Using the leader's past moves, the next mid-quote move of the lagger is forecast with about 60% accuracy, but a naive market-order strategy makes no profit after the spread.
- **Translation:** the effect lives at tick level. If NQ/ES lead-lag only exists at sub-second lags it is out of reach for a home bot and Topstep's HFT ban. LEADLAG-01 therefore has an extra kill rule: peak IC below 1 minute = not tradable.

## Relative value

### GGR2006. Gatev, Goetzmann and Rouwenhorst, "Pairs trading: performance of a relative-value arbitrage rule", *Review of Financial Studies* 19(3), 2006, 797-827. **exists**
Link: https://econpapers.repec.org/RePEc:oup:rfinst:v:19:y:2006:i:3:p:797-827
- **Claim (abstract):** pairs of US stocks matched on historical co-movement, traded when their spread diverges, earned excess returns of up to about 11% a year (1962-2002), with returns declining in later years.
- **Translation:** NQ and ES are a natural pair, but a two-leg trade pays two sets of costs. Spread trading within one account is a normal strategy; hedging across two Topstep accounts is prohibited. → RV-01, RV-02.

### AL2010. Avellaneda and Lee, "Statistical arbitrage in the US equities market", *Quantitative Finance* 10(7), 2010, 761-782. **exists**
Link: https://econpapers.repec.org/RePEc:taf:quantf:v:10:y:2010:i:7:p:761-782
- **Claim (abstract):** mean-reversion of residuals from factor (PCA or ETF) models gives profitable stat-arb signals, with performance falling after 2002; volume-adjusted signals help.
- **Translation:** model NQ against ES (and RTY, YM) as a residual and test its reversion (RV-01, RV-03).

## Mean reversion and price impact

### BBDG2018. Bouchaud, Bonart, Donier and Gould, *Trades, Quotes and Prices: Financial Markets Under the Microscope*, Cambridge University Press, 2018. **exists**
Link: https://doi.org/10.1017/9781316659335
- **Claim:** order flow is long-memory (metaorders are split into many child orders), and the price impact of each trade is partly transient and decays over time (propagator model). Prices stay close to a random walk because liquidity providers lean against persistent flow.
- **Translation:** gives the mechanism for two competing families: continuation from persistent flow (OFI-01, OFI-04) and reversion of transient impact (MR-01, MR-04). Which one wins at 5 to 60 minutes is an empirical question.

## Order flow and book depth (Level 1 and Level 2)

### CKS2014. Cont, Kukanov and Stoikov, "The price impact of order book events", *Journal of Financial Econometrics* 12(1), 2014, 47-88. **read**
Link: https://arxiv.org/abs/1011.6402
- **Claim:** over short intervals, mid-price changes are mainly driven by order-flow imbalance (OFI) at the best bid and ask, linearly, with slope inversely proportional to depth.
- **Frequency:** NYSE TAQ, 50 US stocks, short intervals. The relation is **contemporaneous** (same interval), not predictive.
- **Translation:** a contemporaneous fit says nothing about forecasting. OFI-02 tests whether OFI over the last minute predicts the next, which relies on OFI's own persistence.

### S2018. Stoikov, "The micro-price: a high-frequency estimator of future prices", *Quantitative Finance* 18(12), 2018, 1959-1966. **read**
Link: https://ideas.repec.org/a/taf/quantf/v18y2018i12p1959-1966.html
- **Claim:** the micro-price (built from bid-ask imbalance and spread) predicts short-term prices better than the mid or the size-weighted mid.
- **Translation:** a seconds-scale effect. OFI-03 exists to measure how fast Level 1 information decays, which decides whether Level 2 data is worth buying.

### XGH2019. Xu, Gould and Howison, "Multi-level order-flow imbalance in a limit order book", arXiv 1907.06230, 2019. **read**
Link: https://arxiv.org/abs/1907.06230
- **Claim:** adding OFI from deeper levels improves the out-of-sample fit of **contemporaneous** mid-price changes, for six liquid Nasdaq stocks.
- **Translation:** DEPTH-01 is gated behind a Level 1 pass, per the brief's Level 1 then Level 2 order.

### KTW2023. Kolm, Turiel and Westray, "Deep order flow imbalance: extracting alpha at multiple horizons from the limit order book", *Mathematical Finance* 33(4), 2023, 1044-1081. **read**
Link: https://papers.ssrn.com/abstract=3900141
- **Claim:** for 115 Nasdaq stocks, deep-learning models trained on order flow significantly outperform models trained on raw order-book states; predictability lasts roughly two average price changes.
- **Translation:** "two price changes" is seconds in NQ/ES. Strong evidence that deep-book alpha sits at horizons we cannot trade from home. DEPTH-02 tests it once, cheaply, if Level 2 data is earned.

## Flow toxicity

### ELO2012. Easley, López de Prado and O'Hara, "Flow toxicity and liquidity in a high-frequency world", *Review of Financial Studies* 25(5), 2012, 1457-1493. **read**
Link: https://papers.ssrn.com/abstract=1695596
- **Claim:** VPIN, an order imbalance measured in volume time with bulk volume classification, is "a useful indicator of short-term, toxicity-induced volatility", and it rose before the 6 May 2010 flash crash.

### AB2014. Andersen and Bondarenko, "VPIN and the Flash Crash", *Journal of Financial Markets* 17, 2014. **exists**
Link: https://www.kellogg.northwestern.edu/academics-research/research/detail/2014/vpin-and-the-flash-crash/
- **Claim (as described by the original authors' rebuttal, SSRN 2062450):** VPIN "essentially doesn't work": its predictive power for volatility disappears once trading volume and realized volatility are controlled for, and its flash-crash reading depends on construction choices.
- **Translation:** TOX-01's kill criterion is exactly this test: VPIN must add to trailing realized volatility.

## Volatility state

### AB1997. Andersen and Bollerslev, "Intraday periodicity and volatility persistence in financial markets", *Journal of Empirical Finance* 4(2-3), 1997, 115-158. **exists**
Link: https://ideas.repec.org/a/eee/empfin/v4y1997i2-3p115-158.html
- **Claim (abstract):** intraday volatility has a strong, regular time-of-day pattern (high at open and close, low at midday), and filtering it out is needed to measure volatility persistence correctly.
- **Translation:** every threshold and stop in this project is set in units of time-of-day-adjusted volatility (VOL-03).

### GK1980. Garman and Klass, "On the estimation of security price volatilities from historical data", *Journal of Business* 53(1), 1980, 67-78. **exists**
Link: https://arxiv.org/abs/0807.3492 (a later paper revisiting the estimator, which restates it; original is in J. Business)
- **Claim:** volatility estimated from open, high, low and close is several times more efficient than close-to-close.
- **Translation:** range-based volatility per bar for regime filters and stop sizing (VOL-02, VOL-04).

## Calendar and events

### LM2015. Lucca and Moench, "The pre-FOMC announcement drift", *Journal of Finance* 70(1), 2015, 329-371. **read** (via NY Fed Staff Report 512)
Link: https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr512.html
- **Claim:** the S&P 500 rose on average 49 basis points in the 24 hours before scheduled FOMC announcements (1994-2011), a large share of the period's equity premium.
- **Frequency:** intraday 2 PM to 2 PM windows. **Costs:** not discussed.
- **Decay:** the sample ends in 2011. The drift has been widely reported to have weakened since publication (not verified here). With about 8 meetings a year, even a real effect cannot reach t = 3 in a decade, so CAL-01 is reported as a descriptive statistic, not a strategy.
- **Translation:** the announcement is at 1:00 PM CT. Long ES from the morning of FOMC day to 12:55 PM CT fits Topstep's intraday rule.

---

## Method references

### AFML2018. López de Prado, *Advances in Financial Machine Learning*, Wiley, 2018. **exists**
Link: https://www.oreilly.com/library/view/advances-in-financial/9781119482086/
Triple-barrier labelling and meta-labelling (ch. 3), purged and embargoed k-fold cross-validation (ch. 7), combinatorial purged cross-validation (ch. 12). Used in METHOD §6.1 to §6.3.

### BL2014. Bailey and López de Prado, "The deflated Sharpe ratio: correcting for selection bias, backtest overfitting and non-normality", *Journal of Portfolio Management* 40(5), 2014, 94-107. **read**
Link: https://papers.ssrn.com/abstract=2460551
METHOD §6.4; validity bar DSR ≥ 0.95.

### BBLZ. Bailey, Borwein, López de Prado and Zhu, "The probability of backtest overfitting", *Journal of Computational Finance*. **read**
Link: https://papers.ssrn.com/abstract=2326253
Introduces combinatorially symmetric cross-validation (CSCV) to estimate PBO. METHOD §6.5.

### W2000. White, "A reality check for data snooping", *Econometrica* 68(5), 2000, 1097-1126. **exists**
Link: https://econometricsociety.org/publications/econometrica/browse/2000/09/01/reality-check-data-snooping
Bootstrap test of whether the best of many rules beats a benchmark, accounting for the search. METHOD §6.6.

### H2005. Hansen, "A test for superior predictive ability", *Journal of Business and Economic Statistics* 23(4), 2005. **exists**
Link: https://scilit.com/publications/3acb201045eb64ffec5aeeb2043454cc
Studentized, recentred refinement of the Reality Check that is less affected by poor rules in the tested set. METHOD §6.6.

### HLZ2016. Harvey, Liu and Zhu, "...and the cross-section of expected returns", *Review of Financial Studies* 29(1), 2016, 5-68. **read**
Link: https://nber.org/papers/w20592
"A newly discovered factor needs to clear a much higher hurdle, with a t-ratio greater than 3.0." METHOD §3.4.

---

## Corrections to the brief's starting references

- The ORB paper is by **Zarattini and Aziz** (SSRN 4416622), as the brief says. Its 33% figure is net of commissions only; an independent-ish replication finds the edge vanishes after spread and slippage.
- Xu, Gould and Howison and Cont, Kukanov and Stoikov both measure **contemporaneous** relationships. They show order flow explains price moves in the same interval, not that it forecasts the next one.
- The Andersen and Bondarenko critique is in *Journal of Financial Markets* 17 (2014); SSRN 2062450 is the original authors' reply, not the critique.

---

## Second literature pass: 2024 onward, niche features (22 Nov 2026)

Requested by Ben after 60 trials found nothing. Each source below was fetched on 22 Nov 2026; long PDFs were read verbatim for roughly the first 40,000 characters and the rest through a machine summary. Numbers from the summarised part are marked **(S)** and are unverified.

### BDS2023. Baltussen, Da and Soebhag, "End-of-Day Reversal", working paper dated October 2023 (EFMA 2024 Lisbon). **read in part**
- **Claim:** the return from the prior close to 15:00 ET predicts the last half hour (15:30-16:00 ET) with a **negative** sign in the cross-section of US stocks, 1993-2019; panel t −5.70, stronger for negative returns (t −6.28). Long-short 3.45 bp a day, t 10.49.
- **Costs:** the authors say it "might not be exploitable" after costs.
- **Mechanism:** transitory price pressure, short-seller end-of-day risk management, partly gamma hedging.
- **For us:** the paper is about single stocks. Whether the index shows it is an open question, and it points the opposite way to the late-day momentum idea (IMOM-04) that failed. Feature EOD-01.

### ZAB2025. Zarattini, Aziz and Barbon, "Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)", first version May 2024, this version February 2025. **read in part**
- **Claim:** go with the move when SPY leaves a "noise area" around the open, defined by the 14-day average absolute move from the open to that time of day. Checked on the hour and half hour, trailing stop at the band or VWAP, flat at the close. SPY 2007-2024, Sharpe 1.33 net of $0.0035 a share commission and $0.001 slippage.
- **Caveats:** no formal out-of-sample test; no t-statistic in the text read; assumed slippage is about a tenth of a cent a share, far below our assumed futures cost in relative terms; published by practitioners with a commercial interest.
- **For us:** fully computable from bars. Feature NOISE-01.

### GTBR2024. "Where does gamma hedge drive the intraday market move?", working paper dated 2 June 2024 (AFA submission; authors not shown in the text read). **read in part**
- **Claim:** the first half hour predicts the last half hour mainly on days when the move has crossed the option market makers' gamma-theta breakeven, roughly ± implied volatility ÷ √365. Interaction coefficient 0.96 to 1.18 (t 5.00 to 6.07, **(S)**), single stocks.
- **For us:** the short-gamma condition needs option data. The breakeven threshold can be approximated from bars with trailing realized volatility (**assumed** proxy). Feature IMOM-07. Close to the killed IMOM-04, so the prior is low.

### BLW2022. Boyarchenko, Larsen and Whelan, "The Overnight Drift", NY Fed Staff Report 917, February 2020, revised August 2022. **read in part**
- **Not from 2024**, included because it is niche, specific to E-mini futures, and falls inside Topstep's permitted hours.
- **Claim:** E-mini S&P 500 returns between 2:00 and 3:00 AM ET average 1.48 bp a day (t 7.1), 1998-2020, positive in 20 of 23 years, larger after a sell-off into the prior close.
- **Costs:** Sharpe 1.1 before costs and **−0.5 after bid-ask spreads**; a conditional version is reported at 1.1 after costs **(S)**.
- **Mechanism:** dealers absorb end-of-day order imbalance and unload it when European liquidity arrives.
- **For us:** the conditioning variable is signed volume, which needs quotes; the sign of the 15:15-16:15 ET price change is used as a bars-only proxy (**assumed**). Feature OD-01.

### MES2026. Mesfin, "A Validated Volatility-Volume-Gap Classifier for Regime Identification in MNQ Intraday Data", arXiv 2605.11423 v3, September 2026. **abstract only**
- **Claim:** on MNQ days where the overnight gap, the first 30-minute move and opening volume are all elevated (about 40 of 947 days, 2021-2025), 77.6% reverse from the intraday peak. The author's own directional tests did not pass (best t 1.46).
- **For us:** thresholds are not in the abstract, so ours are **assumed** (each above its trailing 20-day 67th percentile). Feature REG-01. Single-author preprint, small sample, low prior.

### ADEFOV2026. Adams, Dim, Eraker, Fontaine, Ornthanalai and Vilkov, "Do S&P 500 Options Increase Market Volatility? Evidence from 0DTEs", draft July 2026. **read in part**
- **Claim:** higher market-maker net gamma lowers next-10-minute E-mini volatility and weakens intraday momentum (top minus bottom gamma quartile −1.78 bp at 1 hour, t −3.93, **(S)**), 2018-2024.
- **For us:** needs Cboe Open-Close data (market-maker positions). Registered as GEX-02, **not testable without a purchase**.

### ABS2025. Aleti, Bollerslev and Siggaard, "Intraday Market Return Predictability Culled from the Factor Zoo", *Management Science* 71(9), 2025. **read in part**
- **Claim:** lagged 15-minute returns on 272 factor portfolios predict the next 15-minute market return; out-of-sample R² 0.21%, SPY Sharpe 1.37 after costs, 2004-2020.
- **For us:** needs intraday returns on hundreds of stock portfolios. Registered as LEADLAG-05, **not testable with our data**.

### Read and set aside
- Zhao, "Preying on Leveraged ETFs" (arXiv 2608.03703, 2026): Korean single stocks; the paper says the effect is one to two orders of magnitude smaller for US index products.
- Lou, Polk and Skouras, "The Day Destroys the Night, Night Extends the Day" (LSE FMG DP 961, 2026): predicts the next quarter's return, not a session.
- Zhang and Hua, "Market Predictability Before the Closing Bell Rings" (*Risks* 12(11), 2024): SPY and QQQ last-half-hour predictors, which the authors report have diminished; overlaps IMOM-01 to 03, already failed here.
- Da, Filippou and co-authors, "Intraday Option Return Predictability" (2026): about single-stock option returns.
- Not retrieved (site refused): "Cross-Market Intraday Time-Series Momentum" (SSRN 4651331); Bahcivan, "Day and Night Expected Returns Under Overnight Information Shocks" (SSRN 5240716).

## Third literature pass (23 Nov 2026)

Sources, read status and claims for iterations 13 to 19 are tabled inside `reports/SECOND_EDGE_LOG.md` under each iteration: Heston-Korajczyk-Sadka (JF 2010), Browne (AAP 1999), Golez-Jackwerth (JFE 2012), Rosa (JFM 2022), Huang et al. (JBF 2023), Cieslak-Morse-Vissing-Jorgensen (JF 2019), Ariel (JF 1990), Ko-Yang (CFR 2024), and three working papers marked as not peer reviewed.
