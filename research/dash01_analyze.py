"""Dashboard run 1, part 2: every statistic for ENS-01 (nine-setting NQ breakout ensemble), written as CSV files
in reports/dash01/. Reads data/cache/dash01.pkl (research/dash01_run.py).

Size: one SET = one MNQ per setting = at most 9 MNQ. Dollars are for one set unless a size is named.
Costs: 1.11 NQ points per round trip per MNQ (assumed), and the same run at double cost.
Periods: dev = development, to 31 Oct 2024 (in-sample: the rule and its settings were chosen on it);
         wf = walk-forward year, 1 Nov 2024 to 31 Oct 2025 (out-of-sample, but looked at before).
All trade and day figures are MEASURED on historical bars with ASSUMED costs; Monte Carlo figures are SIMULATED.
"""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.iter13_tests import news  # noqa: E402
from sniper.montecarlo import DayRecords, block_bootstrap, simulate_xfa  # noqa: E402
from sniper.rules import load_rules  # noqa: E402

OUT = ROOT / "reports" / "dash01"
PV = 2.0  # dollars per NQ point for one MNQ
NSET = 9
DEV_END = pd.Timestamp("2024-11-01")
TRIALS = 191
RULES = load_rules()
BASE_N = {"50K": 9, "100K": 18, "150K": 27}


def per(idx):
    return np.where(pd.DatetimeIndex(idx) < DEV_END, "dev", "wf")


def tstat(x):
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std() * np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else np.nan


def pf(x):
    x = np.asarray(x, float)
    loss = -x[x < 0].sum()
    return float(x[x > 0].sum() / loss) if loss > 0 else np.nan


def streak(mask):
    best = cur = 0
    for m in mask:
        cur = cur + 1 if m else 0
        best = max(best, cur)
    return best


def drawdown(usd):
    eq = usd.cumsum()
    dd = eq - eq.cummax()
    end = dd.idxmin()
    start = eq.loc[:end].idxmax()
    under = (dd < 0).to_numpy()
    return dd, float(dd.min()), start, end, streak(under)


def regime(days):
    """Volatility regime known before the day: expected daily move over its trailing 250-day median."""
    r = days["dvol_pts"] / days["dvol_pts"].rolling(250, min_periods=60).median().shift(1)
    dev = r[r.index < DEV_END].dropna()
    lo, hi = dev.quantile([1 / 3, 2 / 3])
    return pd.Series(np.where(r.isna(), "unknown", np.where(r <= lo, "low", np.where(r <= hi, "mid", "high"))), index=days.index)


def kpis(days, trades, label):
    usd = days["net_pts"] * PV
    tr = usd[days["round_trips"] > 0]
    t = trades["net_pts"] * PV
    dd, mdd, s, e, ddlen = drawdown(usd)
    vu = (days["net_pts"] / days["dvol_pts"])[days["round_trips"] > 0]
    top = tr.sort_values(ascending=False)
    k = max(1, int(round(0.05 * len(tr))))
    gross_t = trades["gross_pts"] * PV
    cost_t = (trades["gross_pts"] - trades["net_pts"]).mean() * PV
    rows = [
        ("Sample", "Trading days in sample", len(days), "n"),
        ("Sample", "Days with at least one trade", len(tr), "n"),
        ("Sample", "Trades (one MNQ each)", len(t), "n"),
        ("Sample", "Trades per traded day", len(t) / max(len(tr), 1), "x"),
        ("Sample", "Most contracts held at once (average day)", days["max_pos"][days["round_trips"] > 0].mean(), "x"),
        ("Profit", "Total net profit", usd.sum(), "$"),
        ("Profit", "Net profit per day, all days", usd.mean(), "$"),
        ("Profit", "Net profit per traded day", tr.mean(), "$"),
        ("Profit", "Median traded day", tr.median(), "$"),
        ("Profit", "Net profit per trade", t.mean(), "$"),
        ("Profit", "Gross profit per trade, before costs", gross_t.mean(), "$"),
        ("Profit", "Cost per trade", cost_t, "$"),
        ("Profit", "Gross profit per trade over cost", gross_t.mean() / cost_t, "x"),
        ("Profit", "Total costs paid", cost_t * len(t), "$"),
        ("Risk-adjusted", "Sharpe ratio, annualised, all days", usd.mean() / usd.std() * np.sqrt(252), "x"),
        ("Risk-adjusted", "Sortino ratio, annualised", usd.mean() / np.sqrt((np.minimum(usd, 0) ** 2).mean()) * np.sqrt(252), "x"),
        ("Risk-adjusted", "t-statistic of daily dollars", tstat(tr), "x"),
        ("Risk-adjusted", "t-statistic in volatility units", tstat(vu), "x"),
        ("Risk-adjusted", "Net profit over worst drawdown", usd.sum() / -mdd if mdd < 0 else np.nan, "x"),
        ("Hit rate", "Winning days, share of traded days", (tr > 0).mean(), "%"),
        ("Hit rate", "Winning trades", (t > 0).mean(), "%"),
        ("Hit rate", "Average winning trade", t[t > 0].mean(), "$"),
        ("Hit rate", "Average losing trade", t[t <= 0].mean(), "$"),
        ("Hit rate", "Average win over average loss", t[t > 0].mean() / -t[t <= 0].mean(), "x"),
        ("Hit rate", "Profit factor, trades", pf(t), "x"),
        ("Hit rate", "Profit factor, days", pf(tr), "x"),
        ("Hit rate", "Average winning day", tr[tr > 0].mean(), "$"),
        ("Hit rate", "Average losing day", tr[tr <= 0].mean(), "$"),
        ("Hit rate", "Days at $150 or more, share of all days", (usd >= 150).mean(), "%"),
        ("Hit rate", "Days at $150 or more, share of traded days", (tr >= 150).mean(), "%"),
        ("Risk", "Standard deviation of a day, all days", usd.std(), "$"),
        ("Risk", "Best day", usd.max(), "$"),
        ("Risk", "Worst day", usd.min(), "$"),
        ("Risk", "Worst open loss inside a day", days["mae_pts"].min() * PV, "$"),
        ("Risk", "Average worst open loss on traded days", days["mae_pts"][days["round_trips"] > 0].mean() * PV, "$"),
        ("Risk", "Days losing $500 or more, share of all days", (usd <= -500).mean(), "%"),
        ("Risk", "Worst drawdown", mdd, "$"),
        ("Risk", "Longest time under a previous high, trading days", ddlen, "n"),
        ("Risk", "Longest run of losing traded days", streak((tr <= 0).to_numpy()), "n"),
        ("Risk", "Longest run of winning traded days", streak((tr > 0).to_numpy()), "n"),
        ("Shape", "Skew of daily result", float(st.skew(usd)), "x"),
        ("Shape", "Excess kurtosis of daily result", float(st.kurtosis(usd)), "x"),
        ("Shape", "Share of gross winnings from the best 5% of traded days", top.iloc[:k].sum() / tr[tr > 0].sum(), "%"),
        ("Shape", "Net profit without the best 5% of traded days", usd.sum() - top.iloc[:k].sum(), "$"),
        ("Trade", "Average minutes held", trades["minutes_held"].mean(), "n"),
        ("Trade", "Median minutes held", trades["minutes_held"].median(), "n"),
        ("Trade", "Average worst open loss per trade", trades["mae_pts"].mean() * PV, "$"),
        ("Trade", "Average best open gain per trade", trades["mfe_pts"].mean() * PV, "$"),
        ("Trade", "Share of the best open gain kept at exit, winners", (trades["gross_pts"] / trades["mfe_pts"])[(trades["net_pts"] > 0) & (trades["mfe_pts"] > 0)].mean(), "%"),
        ("Trade", "Long trades, share", (trades["dir"] > 0).mean(), "%"),
    ]
    out = pd.DataFrame(rows, columns=["group", "metric", label, "unit"])
    return out, (s, e)


def dsr(usd, trials):
    """Deflated Sharpe ratio (Bailey and Lopez de Prado 2014) on daily results; trial Sharpes assumed to have the
    variance of a worthless rule, 1/T."""
    T = len(usd)
    sr = usd.mean() / usd.std()
    g = 0.5772156649
    emax = (1 - g) * st.norm.ppf(1 - 1 / trials) + g * st.norm.ppf(1 - 1 / (trials * np.e))
    sr0 = np.sqrt(1 / T) * emax
    sk, ku = st.skew(usd), st.kurtosis(usd, fisher=False)
    z = (sr - sr0) * np.sqrt(T - 1) / np.sqrt(1 - sk * sr + (ku - 1) / 4 * sr ** 2)
    return float(st.norm.cdf(z)), float(sr0 * np.sqrt(252)), float(sr * np.sqrt(252))


def bucket_stats(x, keys, dim, order=None, period=None):
    df = pd.DataFrame({"x": np.asarray(x, float), "k": np.asarray(keys), "p": np.asarray(period)})
    rows = []
    for (p, k), g in df.groupby(["p", "k"], observed=True):
        v = g["x"]
        rows.append({"dimension": dim, "bucket": str(k), "period": p, "n": len(v), "win_rate": float((v > 0).mean()),
                     "avg_usd": float(v.mean()), "total_usd": float(v.sum()), "profit_factor": pf(v), "t": tstat(v)})
    out = pd.DataFrame(rows)
    if order is not None and len(out):
        out["order"] = out["bucket"].map({str(k): i for i, k in enumerate(order)})
    else:
        out["order"] = out.groupby("period").cumcount()
    return out


# ------------------------------------------------------------------ Monte Carlo
def combine_sim(pnl, mae, mfe, cost, traded, idx, spec, flip=None, keep_paths=0, keep_days=60):
    """Combine under the rule spec. Dollars for the whole position, net of all costs. Returns passed, breached,
    days, and (optionally) the balance path relative to the start for the first ``keep_paths`` paths."""
    n_paths, length = idx.shape
    b = np.zeros(n_paths); m = np.full(n_paths, -spec.mll)
    best = np.zeros(n_paths); tdays = np.zeros(n_paths, int)
    alive = np.ones(n_paths, bool); passed = np.zeros(n_paths, bool); breached = np.zeros(n_paths, bool)
    days = np.full(n_paths, length)
    hist = np.full((keep_paths, keep_days + 1), np.nan); hist[:, 0] = 0.0
    for t in range(length):
        d = idx[:, t]
        p, a = pnl[d], mae[d]
        if flip is not None:
            f = flip[:, t]
            p = np.where(f, -(pnl[d] + cost[d]) - cost[d], p)
            a = np.where(f, np.minimum(-mfe[d] - cost[d], 0), a)
        tr = traded[d] & alive
        hit = tr & (b + a <= m + 1e-9)
        b = np.where(hit, m, b)
        ok = tr & ~hit
        b = np.where(ok, b + p, b)
        best = np.where(ok, np.maximum(best, p), best)
        tdays += ok
        m = np.where(alive & ~hit, np.minimum(np.maximum(m, b - spec.mll), 0.0), m)
        target = np.maximum(spec.profit_target, best / spec.consistency_fraction)
        win = alive & ~hit & (tdays >= spec.min_trading_days) & (b >= target - 1e-9)
        passed |= win; breached |= hit
        done = hit | win
        days = np.where(done & alive, t + 1, days)
        alive &= ~done
        if t < keep_days and keep_paths:
            hist[:, t + 1] = b[:keep_paths]
        if not alive.any() and t >= keep_days:
            break
    return passed, breached, days, hist


def mc_row(dd, n, size, source, seed=0, n_paths=6000, horizon=400):
    """dd: per-set days frame (points). n: MNQ-equivalent contracts (9 = one whole set)."""
    spec = RULES.account(size)
    k = n / NSET * PV
    pnl, mae, mfe = dd["net_pts"].to_numpy() * k, dd["mae_pts"].to_numpy() * k, dd["mfe_pts"].to_numpy() * k
    cost = (dd["gross_pts"] - dd["net_pts"]).to_numpy() * k
    traded = (dd["round_trips"] > 0).to_numpy()
    rng = np.random.default_rng(seed)
    idx = block_bootstrap(len(dd), n_paths, horizon, 5, rng)
    flip = rng.random(idx.shape) < 0.5
    passed, breached, days, _ = combine_sim(pnl, mae, mfe, cost, traded, idx, spec)
    cp, _, cd, _ = combine_sim(pnl, mae, mfe, cost, traded, idx, spec, flip=flip)
    p = float(passed.mean()); se = np.sqrt(p * (1 - p) / n_paths)
    p30 = float((passed & (days <= 30)).mean()); se30 = np.sqrt(p30 * (1 - p30) / n_paths)
    # XFA: the day engine charges its own commission per contract; add it back so costs are not counted twice
    fee = RULES.commission_per_side["MNQ"] * 2
    per1 = PV / NSET
    rec = DayRecords(traded, dd["net_pts"].to_numpy() * per1 + fee, dd["mae_pts"].to_numpy() * per1 + fee / 2, "MNQ")
    xs = simulate_xfa(rec, idx[:3000], n, size, "standard", RULES).summary()
    xc = simulate_xfa(rec, idx[:3000], n, size, "consistency", RULES).summary()
    payout = max(xs["mean_to_trader"], xc["mean_to_trader"])
    dpass = float(np.median(days[passed])) if passed.any() else np.nan
    month = spec.combine_monthly_standard + RULES.api_monthly
    cost_acct = float(np.ceil(days / 21).mean() * month)  # billed every 30 calendar days = about 21 trading days
    ev = p * (payout - spec.activation_fee_standard) - cost_acct
    d30 = np.minimum(days, 30)
    cost30 = float(np.ceil(d30 / 21).mean() * month)
    ev30 = p30 * (payout - spec.activation_fee_standard) - cost30
    dp30 = float(np.median(days[passed & (days <= 30)])) if p30 > 0 else np.nan
    return {"account": size, "contracts": n, "days_from": source, "pass": p, "pass_lo": max(0, p - 1.96 * se), "pass_hi": p + 1.96 * se,
            "breach": float(breached.mean()), "median_days_to_pass": dpass,
            "pass_30d": p30, "pass_30d_lo": max(0, p30 - 1.96 * se30), "pass_30d_hi": p30 + 1.96 * se30,
            "control_pass": float(cp.mean()), "control_pass_30d": float((cp & (cd <= 30)).mean()),
            "payout_rate_standard": xs["p_payout"], "payout_rate_consistency": xc["p_payout"],
            "payout_usd_standard": xs["mean_to_trader"], "payout_usd_consistency": xc["mean_to_trader"],
            "xfa_days_to_first_payout": xs["median_days_to_first"] if xs["mean_to_trader"] >= xc["mean_to_trader"] else xc["median_days_to_first"],
            "fees_per_account": cost_acct, "profit_per_account": float(ev),
            "profit_per_funded": float(payout - spec.activation_fee_standard - cost_acct / p) if p > 0 else np.nan,
            "ben_score": float(payout / (cost_acct / p * dpass)) if p > 0 and dpass > 0 else 0.0,
            "fees_per_account_30d": cost30, "profit_per_account_30d": float(ev30),
            "ben_score_30d": float(payout / (cost30 / p30 * dp30)) if p30 > 0 and dp30 > 0 else 0.0}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    o = pickle.load(open(ROOT / "data/cache/dash01.pkl", "rb"))
    trades, days = o["NY", "skip", 1]
    trades2, days2 = o["NY", "skip", 2]
    trades = trades.assign(period=per(trades["day"])); trades2 = trades2.assign(period=per(trades2["day"]))
    days = days.assign(period=per(days.index), regime=regime(days))
    days2 = days2.assign(period=per(days2.index))
    usd = days["net_pts"] * PV

    # ---------------- KPI table
    cols, ddspan = [], {}
    for lab, d, t in (("dev", days[days.period == "dev"], trades[trades.period == "dev"]),
                      ("dev_2x", days2[days2.period == "dev"], trades2[trades2.period == "dev"]),
                      ("wf", days[days.period == "wf"], trades[trades.period == "wf"]),
                      ("wf_2x", days2[days2.period == "wf"], trades2[trades2.period == "wf"])):
        k, ddspan[lab] = kpis(d, t, lab)
        cols.append(k)
    kp = cols[0]
    for c in cols[1:]:
        kp = kp.merge(c.drop(columns=["group", "unit"]), on="metric")
    kp = kp[["group", "metric", "unit", "dev", "dev_2x", "wf", "wf_2x"]]
    kp.to_csv(OUT / "kpis.csv", index=False)

    # ---------------- overfitting checks
    dv = usd[days.period == "dev"]
    d18 = dv[dv.index >= "2018-01-01"]; d17 = dv[dv.index < "2018-01-01"]
    D, sr0, sr = dsr(dv, TRIALS)
    wfu = usd[days.period == "wf"]
    chk = pd.DataFrame([
        ("Deflated Sharpe ratio, development", D, "x", "Bar is 0.95. Chance the Sharpe is real after 191 trials."),
        ("Sharpe a worthless rule would show as best of 191", sr0, "x", "Annualised."),
        ("Sharpe, development", sr, "x", "Annualised, all days, in-sample."),
        ("Sharpe, 2010 to 2017", d17.mean() / d17.std() * np.sqrt(252), "x", "First half of development."),
        ("Sharpe, 2018 to Oct 2024", d18.mean() / d18.std() * np.sqrt(252), "x", "Second half of development."),
        ("Sharpe, walk-forward year", wfu.mean() / wfu.std() * np.sqrt(252), "x", "Out-of-sample, looked at before."),
        ("t-statistic, walk-forward year", tstat(wfu[days.loc[wfu.index, "round_trips"] > 0]), "x", "Needs about 2 to stand alone."),
        ("Trials counted so far", TRIALS, "n", "This rerun adds none."),
    ], columns=["check", "value", "unit", "note"])
    chk.to_csv(OUT / "checks.csv", index=False)

    # ---------------- daily series
    eq = usd.cumsum(); dd = eq - eq.cummax()
    roll = usd.rolling(250, min_periods=250)
    daily = pd.DataFrame({"date": days.index.strftime("%Y-%m-%d"), "period": days.period, "pnl": usd.round(2), "pnl_2x": (days2["net_pts"] * PV).round(2),
                          "gross": (days["gross_pts"] * PV).round(2), "trades": days["round_trips"].astype(int), "worst_open": (days["mae_pts"] * PV).round(2),
                          "best_open": (days["mfe_pts"] * PV).round(2), "max_contracts": days["max_pos"].astype(int),
                          "expected_move_usd": (days["dvol_pts"] * PV * NSET).round(0), "regime": days.regime,
                          "equity": eq.round(2), "equity_2x": (days2["net_pts"] * PV).cumsum().round(2), "equity_gross": (days["gross_pts"] * PV).cumsum().round(2),
                          "drawdown": dd.round(2), "sharpe_250d": (roll.mean() / roll.std() * np.sqrt(252)).round(3),
                          "std_60d": usd.rolling(60, min_periods=40).std().round(1)})
    lp = trades.assign(u=trades["net_pts"] * PV).pivot_table(index="day", columns=np.where(trades["dir"] > 0, "long", "short"), values="u", aggfunc="sum").reindex(days.index).fillna(0)
    daily["equity_long"] = lp["long"].cumsum().round(2).to_numpy(); daily["equity_short"] = lp["short"].cumsum().round(2).to_numpy()
    daily.to_csv(OUT / "daily.csv", index=False)

    # ---------------- yearly and monthly
    yr = []
    for (y), g in days.groupby(days.index.year):
        u = g["net_pts"] * PV; t = trades[trades["day"].dt.year == y]
        e = u.cumsum()
        yr.append({"year": y, "period": "dev" if y < 2024 else ("dev + wf" if y == 2024 else "wf"), "days": len(g), "trades": len(t), "pnl": u.sum(), "pnl_2x": (days2.loc[g.index, "net_pts"] * PV).sum(),
                   "per_day": u.mean(), "std_day": u.std(), "sharpe": u.mean() / u.std() * np.sqrt(252), "win_days": (u[g.round_trips > 0] > 0).mean(),
                   "worst_day": u.min(), "best_day": u.max(), "worst_drawdown": (e - e.cummax()).min(), "avg_nq_price": float(t["entry_px"].mean()) if len(t) else np.nan,
                   "days_150": (u >= 150).mean()})
    pd.DataFrame(yr).to_csv(OUT / "yearly.csv", index=False)
    mo = usd.groupby([usd.index.year.rename("y"), usd.index.month.rename("m")]).agg(["sum", "size"]).reset_index()
    mo.columns = ["year", "month", "pnl", "days"]
    mo["period"] = np.where((mo.year < 2024) | ((mo.year == 2024) & (mo.month <= 10)), "dev", "wf")
    mo.to_csv(OUT / "monthly.csv", index=False)

    # ---------------- breakdowns (trade level)
    t = trades.copy(); t["u"] = t["net_pts"] * PV
    et = (t["ct_minute"] + 60)
    t["entry_time"] = (et // 60).astype(str) + ":" + (et % 60).astype(str).str.zfill(2)
    t["hold"] = pd.cut(t["minutes_held"], [0, 30, 60, 120, 240, 400], labels=["up to 30 min", "31 to 60 min", "1 to 2 h", "2 to 4 h", "over 4 h"])
    t["reg"] = days.regime.reindex(t["day"]).to_numpy()
    t["setting"] = "lookback " + t["lookback"].astype(str) + ", width " + t["vm"].astype(str)
    dname = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    mname = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    B = [
        bucket_stats(t.u, np.where(t["dir"] > 0, "Long", "Short"), "Direction", ["Long", "Short"], t.period),
        bucket_stats(t.u, t.entry_time, "Entry time (New York time)", sorted(t.entry_time.unique(), key=lambda s: int(s.split(":")[0]) * 60 + int(s.split(":")[1])), t.period),
        bucket_stats(t.u, t["f_dow"].map(lambda i: dname[i]), "Weekday", dname, t.period),
        bucket_stats(t.u, t["exit_reason"].map({"stop": "Back inside the band", "flip": "Reversed to the other side", "session_end": "Held to the close"}), "How the trade ended", ["Held to the close", "Back inside the band", "Reversed to the other side"], t.period),
        bucket_stats(t.u, np.minimum(t["entry_no"], 4).map({1: "1st", 2: "2nd", 3: "3rd", 4: "4th or later"}), "Entry number that day (per setting)", ["1st", "2nd", "3rd", "4th or later"], t.period),
        bucket_stats(t.u, t["hold"].astype(str), "Time held", ["up to 30 min", "31 to 60 min", "1 to 2 h", "2 to 4 h", "over 4 h"], t.period),
        bucket_stats(t.u, t["reg"], "Volatility regime (trades)", ["low", "mid", "high", "unknown"], t.period),
        bucket_stats(t.u, t["setting"], "Setting", [f"lookback {lb}, width {vm}" for lb in (7, 14, 28) for vm in (0.8, 1.0, 1.2)], t.period),
        bucket_stats(t.u, t["day"].dt.month.map(lambda i: mname[i - 1]), "Month of year (trades)", mname, t.period),
    ]
    feats = {"f_excess": "Distance past the band at entry", "f_dist_vwap": "Distance from VWAP at entry", "f_efficiency": "Straightness of the move since the open",
             "f_relvol": "Volume so far against normal", "f_rv20": "20-day volatility", "f_gap": "Overnight gap in the trade's direction",
             "f_last30": "Move in the last 30 minutes", "f_move_open": "Move from the open", "f_prior_pnl": "Result so far that day"}
    devt = t[t.period == "dev"]
    for f, lab in feats.items():
        try:
            edges = np.unique(devt[f].dropna().quantile([0, .2, .4, .6, .8, 1]).to_numpy())
            if len(edges) < 4:
                continue
            edges[0], edges[-1] = -np.inf, np.inf
            q = pd.cut(t[f], edges, labels=[f"Q{i + 1}" for i in range(len(edges) - 1)])
            m = q.notna()
            B.append(bucket_stats(t.u[m], q[m].astype(str), "Feature: " + lab, [f"Q{i + 1}" for i in range(5)], t.period[m]))
        except Exception as ex:  # noqa: BLE001
            print("feature skipped", f, ex)
    # day level
    trd = days[days["round_trips"] > 0]; du = trd["net_pts"] * PV
    prev = np.sign(usd.shift(1)).reindex(trd.index).map({1.0: "After a winning day", -1.0: "After a losing day", 0.0: "After a day with no trade"}).fillna("n/a")
    B += [
        bucket_stats(du, trd.index.dayofweek.map(lambda i: dname[i]), "Weekday (days)", dname, trd.period),
        bucket_stats(du, trd.regime, "Volatility regime (days)", ["low", "mid", "high", "unknown"], trd.period),
        bucket_stats(du, pd.cut(trd["round_trips"], [0, 3, 9, 18, 27, 200], labels=["1 to 3", "4 to 9", "10 to 18", "19 to 27", "28 or more"]).astype(str), "Trades that day, all settings (days)", ["1 to 3", "4 to 9", "10 to 18", "19 to 27", "28 or more"], trd.period),
        bucket_stats(du, pd.cut(trd["max_pos"], [0, 3, 6, 8, 9], labels=["1 to 3", "4 to 6", "7 to 8", "all 9"]).astype(str), "Settings in the market at the peak (days)", ["1 to 3", "4 to 6", "7 to 8", "all 9"], trd.period),
        bucket_stats(du, prev, "Previous day (days)", ["After a winning day", "After a losing day", "After a day with no trade"], trd.period),
        bucket_stats(du, trd.index.month.map(lambda i: mname[i - 1]), "Month of year (days)", mname, trd.period),
    ]
    # news days: from the run that trades every day
    _, alld = o["NY", "all", 1]
    ev = pd.read_csv(ROOT / "calendar_data/events.csv", parse_dates=["date"]).groupby("date")["event"].agg(lambda s: "+".join(sorted(set(s))))
    ad = alld[alld["round_trips"] > 0]
    lab = ev.reindex(ad.index).fillna("No scheduled release").map(lambda s: s if s in ("CPI", "NFP", "FOMC", "No scheduled release") else "Two on one day")
    lab = lab.map({"CPI": "CPI day (skipped by default)", "NFP": "Payrolls day (skipped by default)", "FOMC": "FOMC day (skipped by default)", "Two on one day": "Two releases (skipped by default)", "No scheduled release": "No scheduled release (traded)"})
    B.append(bucket_stats(ad["net_pts"] * PV, lab, "News days (days)", ["No scheduled release (traded)", "CPI day (skipped by default)", "Payrolls day (skipped by default)", "FOMC day (skipped by default)", "Two releases (skipped by default)"], per(ad.index)))
    br = pd.concat(B, ignore_index=True)
    br["id"] = br["dimension"] + "|" + br["bucket"] + "|" + br["period"]
    br.to_csv(OUT / "breakdowns.csv", index=False)

    # ---------------- sessions x regime
    rows, curves = [], []
    for sess in ("NY", "ASIA", "LONDON"):
        _, sdays = o[sess, "skip", 1]
        sdays = sdays.assign(period=per(sdays.index), regime=regime(sdays))
        su = sdays["net_pts"] * PV
        w = su.resample("W").sum().cumsum()
        curves.append(pd.DataFrame({"session": sess, "week": w.index.strftime("%Y-%m-%d"), "equity": w.round(0).to_numpy()}))
        for p in ("dev", "wf"):
            for rg in ("all", "low", "mid", "high"):
                g = sdays[(sdays.period == p) & ((sdays.regime == rg) | (rg == "all"))]
                u = g["net_pts"] * PV; a = g["round_trips"] > 0
                rows.append({"id": f"{sess}|{rg}|{p}", "session": {"NY": "New York", "ASIA": "Asia", "LONDON": "London"}[sess], "regime": rg, "period": p, "days": len(g), "traded_days": int(a.sum()),
                             "per_day": u.mean(), "total": u.sum(), "std_day": u.std(), "sharpe": u.mean() / u.std() * np.sqrt(252) if u.std() > 0 else np.nan,
                             "t_vol_units": tstat((g["net_pts"] / g["dvol_pts"])[a]), "win_days": float((u[a] > 0).mean()), "worst_day": u.min()})
    pd.DataFrame(rows).to_csv(OUT / "sessions.csv", index=False)
    pd.concat(curves).to_csv(OUT / "session_curves.csv", index=False)

    # ---------------- intraday profile (New York)
    px = o["px"]; pos_of = {d: i for i, d in enumerate(px["days"])}
    nb = 13
    prof = {p: {"pnl": np.zeros(nb), "pos": np.zeros(nb), "entries": np.zeros(nb), "days": 0} for p in ("dev", "wf")}
    for day, g in trades.groupby("day"):
        c = px["px"][pos_of[day]]; p = "dev" if day < DEV_END else "wf"
        step = np.zeros(390); pos = np.zeros(390)
        for dr, a, b, ck in zip(g["dir"], g["fill"], g["exit_min"], g["check_min"]):
            step[a:b] += dr * np.diff(c[a:b + 1]); pos[a:b] += dr
            prof[p]["entries"][min(ck // 30, nb - 1)] += 1
        prof[p]["pnl"] += step.reshape(nb, 30).sum(axis=1) * PV
        prof[p]["pos"] += np.abs(pos).reshape(nb, 30).mean(axis=1)
    rows = []
    for p in ("dev", "wf"):
        nd = int((days.period == p).sum())
        for i in range(nb):
            m = 9 * 60 + 30 + 30 * i
            rows.append({"id": f"{i}|{p}", "period": p, "slot": i, "from_et": f"{m // 60}:{m % 60:02d}", "gross_per_day": prof[p]["pnl"][i] / nd,
                         "avg_contracts": prof[p]["pos"][i] / nd, "entries_per_day": prof[p]["entries"][i] / nd})
    pd.DataFrame(rows).to_csv(OUT / "intraday.csv", index=False)

    # ---------------- histograms
    H = []
    def hist(x, name, edges, p):
        x = np.clip(np.asarray(x, float), edges[0], edges[-1] - 1e-9)
        c, _ = np.histogram(x, edges)
        for i, n in enumerate(c):
            H.append({"what": name, "period": p, "lo": edges[i], "hi": edges[i + 1], "count": int(n), "share": n / max(len(x), 1)})
    for p in ("dev", "wf"):
        tp = trades[trades.period == p]; dp = days[(days.period == p) & (days.round_trips > 0)]
        hist(dp["net_pts"] * PV, "Daily result, traded days ($, one set)", np.arange(-1500, 1501, 100.0), p)
        hist(tp["net_pts"] * PV, "Trade result ($, one MNQ)", np.arange(-300, 301, 20.0), p)
        hist(tp["mae_pts"] * PV, "Worst open loss per trade ($, one MNQ)", np.arange(-300, 1, 15.0), p)
        hist(tp["mfe_pts"] * PV, "Best open gain per trade ($, one MNQ)", np.arange(0, 451, 15.0), p)
        hist(tp["minutes_held"], "Minutes held", np.arange(0, 391, 30.0), p)
        hist(dp["mae_pts"] * PV, "Worst open loss per day ($, one set)", np.arange(-2000, 1, 100.0), p)
    pd.DataFrame(H).to_csv(OUT / "histograms.csv", index=False)

    # ---------------- trade sample for scatter, best and worst days
    rs = np.random.default_rng(7)
    samp = trades.iloc[np.sort(rs.choice(len(trades), 1800, replace=False))]
    pd.DataFrame({"date": samp["day"].dt.strftime("%Y-%m-%d"), "period": samp.period, "side": np.where(samp["dir"] > 0, "Long", "Short"),
                  "net": (samp["net_pts"] * PV).round(2), "worst_open": (samp["mae_pts"] * PV).round(2), "best_open": (samp["mfe_pts"] * PV).round(2),
                  "minutes": samp["minutes_held"]}).to_csv(OUT / "trade_sample.csv", index=False)
    ex = pd.concat([usd.nlargest(12), usd.nsmallest(12)])
    pd.DataFrame({"date": ex.index.strftime("%Y-%m-%d"), "period": days.period.reindex(ex.index), "pnl": ex.round(2), "trades": days["round_trips"].reindex(ex.index).astype(int),
                  "worst_open": (days["mae_pts"].reindex(ex.index) * PV).round(2), "regime": days.regime.reindex(ex.index),
                  "kind": ["Best"] * 12 + ["Worst"] * 12}).to_csv(OUT / "extreme_days.csv", index=False)

    # full trade log for Ben (one MNQ per trade)
    tl = trades.drop(columns=["session"]).copy()
    tl.insert(0, "net_usd", (tl["net_pts"] * PV).round(2))
    tl["day"] = tl["day"].dt.strftime("%Y-%m-%d")
    tl.round(4).to_csv(OUT / "trades_full.csv", index=False)

    # ---------------- Monte Carlo
    dev = days[days.period == "dev"]; wf = days[days.period == "wf"]
    src = {"Development, all years (in-sample)": dev, "Development at double cost": days2[days2.period == "dev"],
           "2022 to Oct 2024 only (in-sample, today's price level)": dev[dev.index >= "2022-01-01"],
           "Walk-forward year (out-of-sample, seen before)": wf}
    grid = {"50K": [3, 6, 9, 12, 18, 27, 36, 45], "100K": [6, 9, 18, 27, 36, 54, 72, 90], "150K": [9, 18, 27, 36, 54, 81, 108, 135]}
    rows = []
    for size, ns in grid.items():
        for sname, sd in src.items():
            for n in ns:
                r = mc_row(sd, n, size, sname)
                r["id"] = f"{size}|{n}|{sname}"; r["base"] = int(n == BASE_N[size])
                rows.append(r)
        print("mc", size, "done")
    mc = pd.DataFrame(rows)
    mc.to_csv(OUT / "montecarlo.csv", index=False)

    # paths and days-to-outcome at the base size
    P, DH = [], []
    for size, n in BASE_N.items():
        spec = RULES.account(size)
        for sname in ("Development, all years (in-sample)", "2022 to Oct 2024 only (in-sample, today's price level)"):
            sd = src[sname]; k = n / NSET * PV
            idx = block_bootstrap(len(sd), 6000, 400, 5, np.random.default_rng(3))
            a = lambda c: sd[c].to_numpy() * k  # noqa: E731
            passed, breached, dys, hist_ = combine_sim(a("net_pts"), a("mae_pts"), a("mfe_pts"), (sd["gross_pts"] - sd["net_pts"]).to_numpy() * k, (sd["round_trips"] > 0).to_numpy(), idx, spec, keep_paths=6000, keep_days=60)
            q = np.nanpercentile(hist_, [5, 25, 50, 75, 95], axis=0)
            for d in range(61):
                P.append({"account": size, "days_from": sname, "kind": "band", "path": "", "day": d, "p5": q[0, d], "p25": q[1, d], "p50": q[2, d], "p75": q[3, d], "p95": q[4, d], "balance": np.nan, "outcome": ""})
            for j in range(30):
                oc = "pass" if passed[j] and dys[j] <= 60 else ("breach" if breached[j] and dys[j] <= 60 else "open")
                last = min(dys[j], 60)
                for d in range(last + 1):
                    P.append({"account": size, "days_from": sname, "kind": "path", "path": j, "day": d, "p5": np.nan, "p25": np.nan, "p50": np.nan, "p75": np.nan, "p95": np.nan, "balance": hist_[j, d], "outcome": oc})
            edges = list(range(0, 121, 5)) + [401]
            for lab, m in (("Passed", passed), ("Breached", breached)):
                c, _ = np.histogram(dys[m], edges)
                for i, v in enumerate(c):
                    DH.append({"account": size, "days_from": sname, "outcome": lab, "from_day": edges[i] + 1, "to_day": edges[i + 1] if i < len(c) - 1 else 400, "share": v / len(dys)})
    pd.DataFrame(P).round(1).to_csv(OUT / "mc_paths.csv", index=False)
    pd.DataFrame(DH).to_csv(OUT / "mc_days.csv", index=False)

    # reproduction of the ranking row (8 MNQ-equivalent, development, 50K)
    r8 = mc_row(dev, 8, "50K", "repro")
    print("repro 8 MNQ-eq 50K dev: pass %.3f pass30 %.3f control30 %.3f payout rate %.3f profit/acct %.0f" % (r8["pass"], r8["pass_30d"], r8["control_pass_30d"], max(r8["payout_rate_standard"], r8["payout_rate_consistency"]), r8["profit_per_account"]))
    print(kp.to_string()); print(chk.to_string())
    print(mc[mc.base == 1][["account", "contracts", "days_from", "pass", "pass_30d", "control_pass_30d", "breach", "median_days_to_pass", "payout_rate_standard", "payout_rate_consistency", "profit_per_account", "profit_per_account_30d"]].to_string())


if __name__ == "__main__":
    main()
