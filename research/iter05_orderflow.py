"""Iteration 5: order flow on Level 1 trades (Aug-Oct 2024, development period).

OFI-01  aggressor-signed volume imbalance over the last 1 or 5 minutes -> next 1/5/15 min return (+)
OFI-04  signed volume of large prints (>= 99th percentile size) over the last 5 minutes -> next 5/15 min (+)
MR-04L  limit-order version of the 5-minute reversal: after a 5-minute return beyond 2 sd, rest a limit
        order 1 tick through the last price in the reversal direction for up to 2 minutes. It fills only if
        a later trade prints THROUGH the limit (strictly better than it). Exit at market 5 minutes after the
        fill, paying 1 tick. Fees from the rule spec.

Day session (8:30-15:00 CT) only; the month is used as the stability slice.
Run: python research/iter05_orderflow.py [--log]
"""
import csv
import glob
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from sniper import load_rules  # noqa: E402
from sniper.data import add_session_columns  # noqa: E402
from sniper.signal import forward_returns, passes_stage1, signal_test  # noqa: E402

TICK = 0.25
PV = {"ES": 50.0, "NQ": 20.0}
MKT_COST_PTS = {"ES": 1.30 * TICK, "NQ": 2.76 * TICK}


JOB = {"ES": "GLBX-20261122-5C3CTGW3JK", "NQ": "GLBX-20261122-SJ3NGWQPBV"}


def load_trades(sym):
    """Compact trade tape: only the columns needed, to stay within memory."""
    import databento as db
    parts = []
    for f in sorted(glob.glob(str(ROOT / f"data/raw/trades/{JOB[sym]}/*.dbn.zst"))):
        a = db.DBNStore.from_file(f).to_ndarray()
        parts.append(pd.DataFrame({
            "ts": a["ts_event"].astype("int64"), "instrument_id": a["instrument_id"].astype("int32"),
            "price": (a["price"] / 1e9).astype("float64"), "size": a["size"].astype("int32"),
            "side": a["side"].astype("S1"),
        }))
        del a
    t = pd.concat(parts, ignore_index=True).sort_values("ts", kind="stable").reset_index(drop=True)
    return t


def minute_bars(t):
    buy = np.where(t["side"] == b"B", t["size"], 0)
    sell = np.where(t["side"] == b"A", t["size"], 0)
    big = (t["size"] >= t["size"].quantile(0.99)).to_numpy()
    g = pd.DataFrame({"minute": t["ts"] // 60_000_000_000, "instrument_id": t["instrument_id"],
                      "price": t["price"], "buy": buy, "sell": sell, "big": np.where(big, buy - sell, 0)})
    m = g.groupby(["minute", "instrument_id"], sort=True).agg(
        close=("price", "last"), buy=("buy", "sum"), sell=("sell", "sum"), big=("big", "sum"), n=("price", "size")
    ).reset_index()
    m.index = pd.to_datetime(m.pop("minute") * 60_000_000_000, utc=True)
    m = add_session_columns(m)
    vol = m.groupby(["trading_day", "instrument_id"])["n"].sum().reset_index()
    front = vol.sort_values("n").groupby("trading_day").tail(1).set_index("trading_day")["instrument_id"]
    m = m[m["instrument_id"] == m["trading_day"].map(front)]
    m["segment"] = m["instrument_id"].astype(str) + "|" + m["trading_day"].astype(str)
    return m


def ofi_tests(sym, m):
    rth = m["rth"]
    seg = m["segment"]
    # reindex to a full minute grid within each segment so shifts are in minutes
    fwd = forward_returns(m["close"], [1, 5, 15], seg)
    for h in fwd.columns:
        fwd.loc[m["minute_ct"] + h > 900, h] = np.nan
    tot = (m["buy"] + m["sell"]).replace(0, np.nan)
    imb1 = (m["buy"] - m["sell"]) / tot
    b5 = m.groupby(seg)["buy"].transform(lambda x: x.rolling(5, min_periods=5).sum())
    s5 = m.groupby(seg)["sell"].transform(lambda x: x.rolling(5, min_periods=5).sum())
    imb5 = (b5 - s5) / (b5 + s5)
    big5 = m.groupby(seg)["big"].transform(lambda x: x.rolling(5, min_periods=5).sum())
    month = pd.Series(m.index.tz_convert("America/Chicago").month, index=m.index)
    out = []
    for fid, f, hs in (("OFI-01/1m", imb1, [1, 5, 15]), ("OFI-01/5m", imb5, [1, 5, 15]), ("OFI-04", big5, [5, 15])):
        k = rth & f.notna()
        rep = signal_test(f[k], fwd.loc[k, hs], horizon_bars={h: h for h in hs}, slices={"year": month[k]}, name=fid)
        ok, why = passes_stage1(rep, +1)
        best = rep.best(+1)
        pts = (m["close"].groupby(seg).shift(-best.horizon) - m["close"])[k]
        ff = f[k]
        hi, lo = ff.quantile(0.9), ff.quantile(0.1)
        pos = pd.Series(np.where(ff >= hi, 1, np.where(ff <= lo, -1, 0)), index=ff.index)
        pnl = (pos * pts)[pos != 0].dropna()
        nonover = pnl.iloc[:: max(best.horizon, 1)]
        tdol = nonover.mean() / nonover.std() * np.sqrt(len(nonover))
        out.append({"feature": fid, "symbol": sym, "h": best.horizon, "ic": best.ic, "t": best.t, "stage1": ok,
                    "why": why, "months": {str(k_): v[best.horizon] for k_, v in rep.slices["year"].items()},
                    "rule_mean_pts": float(pnl.mean()), "x_cost": float(pnl.mean() / MKT_COST_PTS[sym]),
                    "t_dollar": float(tdol), "n_rule": int(len(pnl))})
    return out


def limit_reversal(sym, t, m, fee_rt):
    """MR-04 with a resting limit order and trade-through fills on the actual trade tape."""
    rth = m[m["rth"]]
    r5 = np.log(rth["close"]).groupby(rth["segment"]).diff(5)
    sd = r5.groupby(rth["minute_ct"]).transform(lambda x: x.rolling(20, min_periods=15).std().shift(1))
    z = r5 / sd
    sig = rth[(z.abs() >= 2) & (rth["minute_ct"] <= 890)]
    front = t["instrument_id"].isin(m["instrument_id"].unique())
    times = t["ts"].to_numpy()[front.to_numpy()]
    prices = t["price"].to_numpy()[front.to_numpy()]
    one, two, five = (pd.Timedelta(minutes=k).value for k in (1, 2, 5))
    res = []
    last_exit = None
    for ts, zz in zip(sig.index.asi8, z.loc[sig.index].to_numpy()):
        if last_exit is not None and ts < last_exit:
            continue
        direction = -np.sign(zz)  # fade the move
        t0 = ts + one  # bar timestamp is the open; the signal is known at its close
        i0 = np.searchsorted(times, t0, "left")
        last_px = prices[i0 - 1]
        limit = last_px - direction * TICK
        i1 = np.searchsorted(times, t0 + two, "right")
        w = prices[i0:i1]
        hit = np.nonzero((w < limit) if direction > 0 else (w > limit))[0]
        if hit.size == 0:
            res.append({"filled": False})
            continue
        tf = times[i0 + hit[0]]
        j = np.searchsorted(times, tf + five, "right")
        if j >= len(prices):
            continue
        exit_px = prices[j] - direction * TICK
        pts = direction * (exit_px - limit)
        res.append({"filled": True, "pts": pts, "usd": pts * PV[sym] - fee_rt})
        last_exit = tf + five
    r = pd.DataFrame(res)
    f = r[r["filled"]] if len(r) else r
    usd = f["usd"] if len(f) else pd.Series(dtype=float)
    return {"feature": "MR-04L", "symbol": sym, "signals": int(len(r)), "fills": int(len(f)),
            "fill_rate": float(len(f) / max(len(r), 1)), "mean_pts": float(f["pts"].mean()) if len(f) else float("nan"),
            "mean_usd_net": float(usd.mean()) if len(usd) else float("nan"),
            "t_dollar": float(usd.mean() / usd.std() * np.sqrt(len(usd))) if len(usd) > 2 else float("nan"),
            "hit": float((usd > 0).mean()) if len(usd) else float("nan")}


def main():
    rules = load_rules()
    results = []
    for sym in ("ES", "NQ"):
        t = load_trades(sym)
        m = minute_bars(t)
        results += ofi_tests(sym, m)
        fee = rules.commission_per_side[sym] * 2
        results.append(limit_reversal(sym, t, m, fee))
        del t, m
    for r in results:
        print(json.dumps(r, default=float))
    if "--log" in sys.argv:
        (ROOT / "reports" / "iter_05_orderflow.json").write_text(json.dumps(results, indent=1, default=float))
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
        rows = list(csv.DictReader((ROOT / "experiments.csv").open()))
        total = int(rows[-1]["trials_total"])
        with (ROOT / "experiments.csv").open("a", newline="") as fh:
            w = csv.writer(fh)
            for r in results:
                total += 1
                head = (f"IC {r['ic']:+.4f} t {r['t']:+.2f} -> {'PASS' if r['stage1'] else 'FAIL'}; {r['x_cost']:.2f}x cost"
                        if "ic" in r else f"fill {r['fill_rate']:.0%}, net ${r['mean_usd_net']:.2f}/trade, t$ {r['t_dollar']:.2f}")
                w.writerow([f"it05-{r['feature']}-{r['symbol']}", date.today().isoformat(), commit, "iter05", 1, total, head])
        print("trials total", total)


if __name__ == "__main__":
    main()
