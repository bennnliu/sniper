# Iteration 07: event and calendar tests (FOMC, CPI, payrolls)

_22 Nov 2026. Development period only (to 31 Oct 2024). Holdout and walk-forward untouched. No data spend._

## 1. Verdict

**KILL** for CAL-01 and CAL-05 as trading ideas. **CAL-02 is kept as a risk filter, not an edge:** release windows are 2 to 3.6 times as volatile as the same window on other days, which matters for the Maximum Loss Limit, but no direction is predictable around them.

## 2. What was tested

- **CAL-01:** on scheduled FOMC days, ES and NQ drift up from 8:30 CT to 12:55 CT, before the 1:00 PM CT statement (Lucca and Moench).
- **CAL-02:** CPI, payrolls and FOMC days differ in volatility, and the 5-minute reversal (MR-04) behaves differently on them.
- **CAL-05** (registered in this iteration, before the run): the first reaction continues. The 7:30-8:30 CT move on CPI and payrolls days predicts 8:30-15:00 CT, and the 13:00-13:30 CT move on FOMC days predicts 13:30-15:00 CT.

Trials: 10 this iteration, **60 in total**.

**Dates.** `calendar_data/events.csv`. CPI and payrolls dates come from the BLS release schedules (verified, 171 and 172 days). FOMC dates come from the Federal Reserve's per-year pages for 2010-2020 and its calendar page for January-July 2024 (verified). FOMC dates for 2021-2023 and September 2024 could only be read from a truncated page and are marked **unverified**; headline FOMC numbers use verified dates only, and the all-dates figure is shown beside them. The 1:00 PM CT statement time is **assumed** from March 2013 onward; earlier meetings had varying times and are shown separately.

## 3. Signal evidence (measured)

### CAL-01: pre-FOMC drift, 8:30 to 12:55 CT, March 2013 to October 2024

| Symbol | FOMC days (verified) | Mean | t | Share up | 2015 onward mean (t) | All dates incl. unverified, mean (t) | Other days mean (t) |
|---|---|---|---|---|---|---|---|
| ES | 67 | −1.4 bp | −0.35 | 36% | +0.3 bp (0.06) | −0.5 bp (−0.16), n 91 | +1.4 bp (1.20) |
| NQ | 67 | −7.5 bp | −1.62 | 34% | −6.0 bp (−1.14) | −3.4 bp (−0.77), n 91 | +1.7 bp (1.04) |

The drift is not there. The mean is zero on ES and negative on NQ, and only about a third of FOMC mornings rose. For 2010-2012 (22 meetings, 8:30 to 11:25 CT) the mean was −1.8 bp on ES (t −0.17). The registered kill rule was "mean return in 2015-2024 not positive": ES is +0.3 bp with t 0.06, which is not distinguishable from zero, and NQ is negative. A naive long loses $21 per ES contract and $51 per NQ contract after assumed costs.

This agrees with the note in LITERATURE.md that the effect weakened after publication. Lucca and Moench also measured the 24 hours before the statement, most of which is overnight; this test only covers the part a Topstep day trade could hold.

### CAL-02: volatility and the reversal signal on release days

| Event | Symbol | Day-session volatility vs other days (median ratio) | Release window | Absolute move in window, event vs other days (median) | MR-04 mean capture on event days (× cost) | MR-04 on other days (× cost) |
|---|---|---|---|---|---|---|
| CPI | ES | 1.10× (p 0.03) | 7:30-8:00 CT | 13.9 bp vs 6.4 bp (2.2×) | −0.17 | 0.23 |
| CPI | NQ | 1.08× (p 0.07) | 7:30-8:00 CT | 15.2 bp vs 7.4 bp (2.0×) | −0.07 | 0.24 |
| Payrolls | ES | 1.10× (p 0.04) | 7:30-8:00 CT | 22.9 bp vs 6.4 bp (3.6×) | 0.11 | 0.23 |
| Payrolls | NQ | 1.04× (p 0.21) | 7:30-8:00 CT | 25.9 bp vs 7.4 bp (3.5×) | 0.32 | 0.24 |
| FOMC | ES | 1.27× (p < 0.001) | 13:00-13:30 CT | 22.1 bp vs 8.2 bp (2.7×) | −0.10 | 0.23 |
| FOMC | NQ | 1.25× (p < 0.001) | 13:00-13:30 CT | 25.1 bp vs 10.1 bp (2.5×) | 0.08 | 0.24 |

- The release windows themselves are 2 to 3.6 times as volatile. CPI and payrolls come out an hour before the day session, so the 8:30-15:00 CT session is only about 5-10% more volatile on those days. FOMC days are about 26% more volatile in the day session because the statement lands inside it.
- MR-04 looks weaker on event days, but none of the differences is significant (t between −1.1 and +0.1), so this is not evidence. MR-04 is not tradable on any kind of day.
- FOMC rows in this table use all 91 dates including the unverified ones.

### CAL-05: continuation of the first reaction

| Event | Symbol | n | IC | t | Years with right sign | Mean move ÷ cost | Net per contract | Dollar t | Stage 1 |
|---|---|---|---|---|---|---|---|---|---|
| CPI | ES | 171 | +0.060 | 0.78 | 53% | −0.7 | −$27 | −0.28 | fail |
| CPI | NQ | 171 | +0.020 | 0.25 | 67% | −4.5 | −$76 | −0.47 | fail |
| Payrolls | ES | 167 | −0.061 | −0.78 | 47% | −6.0 | −$114 | −1.26 | fail |
| Payrolls | NQ | 167 | −0.088 | −1.14 | 33% | −16.4 | −$241 | −1.60 | fail |
| FOMC | ES | 67 | +0.157 | 1.28 | 50% | −0.6 | −$26 | −0.28 | fail |
| FOMC | NQ | 67 | +0.103 | 0.83 | 50% | +0.9 | −$2 | −0.02 | fail |

No continuation. If anything, payrolls days lean toward reversal (following the first move lost $114 per ES contract), but at t −1.3 to −1.6 that is noise, and re-registering the opposite sign on the same data would be snooping.

## 4-6. Trading, prop-firm and overfitting evidence

Not applicable: nothing passed stage 1.

## 7. Mistakes

- The first collection of dates returned only June-December for each year, and FOMC dates for 2021-2023 could not be read verbatim from the Fed's site. The gap was caught before any test ran. Unverified dates are flagged in the events file and excluded from headline numbers.
- CAL-05 was not in the registry at the start of the iteration. It was registered and committed before its test was run.

## 8. Critique of the result

1. **The FOMC sample is small** (67 verified meetings). A drift of +10 bp would have shown up as t of about 2.5; one of +3 bp could not be detected. *Test:* none worth running. An effect that small does not pay for a once-a-month trade.
2. **The unverified FOMC years (2021-2023) were high-volatility years** and could matter. With them included, the ES mean is −0.5 bp (t −0.16), so the conclusion does not change. *Test:* verify the dates from another source when convenient.
3. **Lucca and Moench's drift is mostly overnight.** *Test:* not testable inside Topstep's rules in a useful way, since holding through the 3:10 PM CT flat time is not allowed, though the 5:00 PM CT reopen to next-day window could be held. That is a different hypothesis with overnight gap risk against the Maximum Loss Limit, and it is not registered.

## 9. Suggestions

**Finding features:** every bar-based family registered so far has now been tested, 60 trials, and nothing predicts direction after costs. Remaining untested ideas need new data (dealer gamma and options positioning for IMOM-04's mechanism and CAL-04, Level 2 for OFI-03) or are low-prior (CAL-03 turn of month, VOL filters).

**Testing features:** use CAL-02 as a design rule for any future strategy: no entries in the 30 minutes after CPI, payrolls or FOMC releases, and treat FOMC afternoons as roughly 2.5× normal risk when sizing against the Maximum Loss Limit.

## 10. Next iteration plan

Ben to choose (details in STATE.md):

1. Price and, if approved, buy options-positioning data to test the dealer-gamma mechanism directly.
2. Accept the null result for directional signals on this data and stop the search, keeping the infrastructure (rule simulator, baseline, pipeline) for any idea Ben brings.
3. Run the remaining low-prior bar tests (CAL-03, VOL filters) for completeness, no spend.
