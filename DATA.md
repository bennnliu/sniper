# DATA

Where the research data comes from, what it costs, and how it is cleaned. Prices below were read on 22 Nov 2026.

## Budget (Ben, 22 Nov 2026)

- Vendor: **Databento**.
- Bars come out of Databento's free signup credit first.
- Hard cap of **$50 of paid spend in total** before any tick (Level 1) data. Ask Ben before going over it.
- Every pull is priced first with Databento's cost-estimate call (`metadata.get_cost`), and the estimate and actual cost are logged in `data_spend.csv` with the date, dataset, schema, symbols and date range.

## Databento facts (read 22 Nov 2026)

| Item | Value | Source |
|---|---|---|
| Free credit | $125 for new users, one set per team, **expires after 6 months** | https://databento.com/docs/faqs/usage-pricing-and-data-credits |
| Historical pricing | Usage-based, per GB of uncompressed binary data; no monthly fee for historical data | same |
| Cost estimate before buying | `Historical.metadata.get_cost` and `get_billable_size` | https://databento.com/docs/api-historical/basics/metered-pricing |
| Re-download | Batch downloads can be re-downloaded for 30 days at no charge | same |
| CME dataset | `GLBX.MDP3` (CME Globex MDP 3.0): ES, NQ, MES, MNQ, RTY, YM, ZN and others | https://databento.com/datasets/GLBX.MDP3 |
| Continuous symbols | `ES.v.0` = front contract by volume, `.v.1` = second; prices are **not** back-adjusted | https://databento.com/docs/examples/symbology/continuous |

Not yet confirmed: the per-GB rate for each schema, the first date of GLBX.MDP3 history (believed to be mid-2010), and the licence terms for personal research use. All three are checked with the API before the first pull.

## Order of purchase

1. **1-minute bars (`ohlcv-1m`)** for ES and NQ, full history. Enough for trend, intraday momentum, relative value, mean reversion, volatility and calendar features: 23 of the 37 registered hypotheses. Small (roughly 5-6 million bars per symbol over 16 years), expected to fit in the free credit with room to spare.
2. **1-minute bars for RTY, YM and ZN**, for RV-03 and LEADLAG-04. Also small.
3. **1-second bars (`ohlcv-1s`)** for ES and NQ, recent 2-3 years only, for LEADLAG-01. Larger; priced first.
4. **Level 1 (`trades`, `tbbo`)**, 1-2 recent years, only after a bar-based feature has passed signal and cost tests, or to calibrate slippage for a strategy that has. Counts against the $50 cap.
5. **Level 2 (`mbp-10`)**, only if a Level 1 order-flow feature shows signal at 10 seconds or longer (METHOD and the brief's Level 1 then Level 2 rule). Needs Ben's approval for budget.

## Level 1 vs Level 2: working position

What the literature says (LITERATURE.md): order-flow imbalance at the best bid and ask explains price changes in the same interval (CKS2014), deeper levels add to that contemporaneous fit (XGH2019), and the forecasting power of deep order flow lasts about two price changes (KTW2023), which is seconds in NQ and ES. Lead-lag between futures and other instruments is strongest at tick level and is not profitable with market orders after the spread (HA2014).

Topstep bans high-frequency trading and requires orders from a home device with no VPS, so seconds-scale alpha is out of reach whatever the data says. The working position is therefore: **bars first, Level 1 only for order-flow features at 1 minute or longer and for fill calibration, Level 2 probably never.** OFI-03 (micro-price) is the one cheap experiment that measures how fast Level 1 information decays; if its IC is gone by 10 seconds, Level 2 is ruled out on evidence, not assumption.

## Cleaning rules

- **Timestamps:** stored as UTC nanoseconds (`ts_event`, exchange time from CME). A derived column holds Chicago time and the Topstep trading day (5:00 PM CT to 3:10 PM CT, labelled by the date it ends), computed by the same function the simulator uses.
- **Roll rule:** use `.v.0` (front contract by volume). Never compute a return across a change of `instrument_id`: the bar after a roll starts a new series, and any feature window spanning a roll is recomputed on the new contract or marked missing. Prices are kept unadjusted, which is what the bot will trade.
- **Alignment:** NQ and ES are joined on bar timestamps from the same exchange clock. A minute with no trade in one contract is left missing, not forward-filled, for lead-lag work.
- **Sessions:** flag the daily 4:00-5:00 PM CT maintenance halt, weekends, CME holidays and half days (for example, the day after Thanksgiving, early closes before Christmas and Independence Day). Half days are excluded from intraday-momentum tests because "last half hour" moves.
- **Quality checks:** duplicate timestamps, bars with high < low, zero-volume bars during the day session, and gaps over 5 minutes in the day session are counted and reported per month.
- **Storage:** partitioned Parquet by symbol and year under `data/` (git-ignored), with a manifest recording the request, cost and file hash.

## TopstepX feed

The live bot will trade on TopstepX's feed, not Databento's. Once a strategy reaches forward testing, we record the TopstepX feed alongside Databento for the same days and compare bar values and timestamps. Whether the ProjectX API serves useful history is still to be checked against its current documentation.

## Access from this cloud environment

The Databento API host is blocked by this project's cloud network policy today. To pull data from here, Ben needs to (1) allow `hist.databento.com` in the environment's network settings and (2) store the Databento API key as an environment secret named `DATABENTO_API_KEY`. The key must never be pasted into chat or committed.
