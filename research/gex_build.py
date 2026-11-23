"""Build the daily dealer-gamma measure from quarterly ES option statistics (iteration 36, GEX-03).
Input: data/raw/opt/<job>/*.statistics.dbn.zst  Output: data/cache/gex_daily.csv (also reports/gex03/gex_daily.csv)
For day D uses open interest and settlement prices whose reference date is D; both are published before the
8:30 CT open of the next session (checked on a sample: OI at about 20:20 CT and 08:00 CT, settlements by 17:00 CT).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parent.parent
MONTHS = {"H": 3, "M": 6, "U": 9, "Z": 12}


def extract(path):
    import databento as db
    df = db.DBNStore.from_file(str(path)).to_df()
    df = df[df["stat_type"].isin([3, 9]) & df["ts_ref"].notna() & df["symbol"].str.match(r"^ES[HMUZ]\d [CP]\d+$", na=False)]
    df = df.reset_index().sort_values("ts_recv")
    df["ref"] = df["ts_ref"].dt.tz_localize(None).dt.normalize()
    oi = df[df["stat_type"] == 9].groupby(["ref", "symbol"])["quantity"].last().rename("oi")
    px = df[df["stat_type"] == 3].groupby(["ref", "symbol"])["price"].last().rename("settle")
    return pd.concat([oi, px], axis=1).reset_index()


def third_friday(y, m):
    d = pd.Timestamp(y, m, 15)
    return d + pd.Timedelta(days=(4 - d.dayofweek) % 7)


def expiry(code, ref):
    m, yd = MONTHS[code[2]], int(code[3])
    y = ref.year - ref.year % 10 + yd
    if y < ref.year - 1:
        y += 10
    return third_friday(y, m)


def b76_price(F, K, T, s, cp):
    d1 = (np.log(F / K) + 0.5 * s * s * T) / (s * np.sqrt(T)); d2 = d1 - s * np.sqrt(T)
    return np.where(cp == 1, F * norm.cdf(d1) - K * norm.cdf(d2), K * norm.cdf(-d2) - F * norm.cdf(-d1))


def implied_vol(price, F, K, T, cp):
    lo, hi = np.full(len(price), 0.01), np.full(len(price), 3.0)
    for _ in range(40):
        mid = (lo + hi) / 2
        up = b76_price(F, K, T, mid, cp) < price
        lo, hi = np.where(up, mid, lo), np.where(up, hi, mid)
    return (lo + hi) / 2


def day_gex(g, ref):
    g = g.copy()
    g["cp"] = np.where(g["symbol"].str[5] == "C", 1, -1)
    g["K"] = g["symbol"].str[6:].astype(float)
    g["code"] = g["symbol"].str[:4]
    out = {"net": 0.0, "tot": 0.0, "call_oi": 0.0, "put_oi": 0.0, "F": np.nan}
    for code, e in g.groupby("code"):
        T = (expiry(code, ref) - ref).days
        if T < 1 or T > 100:
            continue
        w = e.pivot_table(index="K", columns="cp", values="settle")
        if 1 not in w or -1 not in w:
            continue
        w = w.dropna()
        if len(w) < 5:
            continue
        k0 = (w[1] - w[-1]).abs().idxmin()
        F = k0 + w.loc[k0, 1] - w.loc[k0, -1]
        e = e[e["oi"].fillna(0) > 0].dropna(subset=["settle"])
        # out-of-the-money side only for the vol (in-the-money settlements are mostly intrinsic)
        t = T / 365.0
        intrinsic = np.maximum(e["cp"] * (F - e["K"]), 0)
        e = e[(e["settle"] - intrinsic > 0.1) & (e["K"] > 0.5 * F) & (e["K"] < 1.5 * F)]
        if e.empty:
            continue
        iv = implied_vol(e["settle"].to_numpy(), F, e["K"].to_numpy(), t, e["cp"].to_numpy())
        d1 = (np.log(F / e["K"].to_numpy()) + 0.5 * iv * iv * t) / (iv * np.sqrt(t))
        gamma = norm.pdf(d1) / (F * iv * np.sqrt(t))
        dollar = gamma * e["oi"].to_numpy() * 50 * F * F * 0.01  # dollars of delta per 1% move
        out["net"] += float((dollar * e["cp"].to_numpy()).sum()); out["tot"] += float(dollar.sum())
        out["call_oi"] += float(e["oi"][e["cp"] == 1].sum()); out["put_oi"] += float(e["oi"][e["cp"] == -1].sum())
        if not np.isfinite(out["F"]):
            out["F"] = F
    return out


def main(files=None):
    files = files or sorted((ROOT / "data/raw/opt").glob("GLBX-*/*.statistics.dbn.zst"))
    parts = []
    for f in files:
        parts.append(extract(f)); print(Path(f).name, len(parts[-1]), flush=True)
    raw = pd.concat(parts).groupby(["ref", "symbol"]).last().reset_index()
    rows = []
    for ref, g in raw.groupby("ref"):
        r = day_gex(g, ref); r["day"] = ref; rows.append(r)
    out = pd.DataFrame(rows).set_index("day").sort_index()
    out = out[out["tot"] > 0]
    out["ratio"] = out["net"] / out["tot"]
    (ROOT / "data/cache").mkdir(parents=True, exist_ok=True); (ROOT / "reports/gex03").mkdir(parents=True, exist_ok=True)
    out.to_csv(ROOT / "data/cache/gex_daily.csv"); out.to_csv(ROOT / "reports/gex03/gex_daily.csv")
    return out


if __name__ == "__main__":
    o = main([sys.argv[1]] if len(sys.argv) > 1 else None)
    print(o.tail(10)); print(o.describe())
