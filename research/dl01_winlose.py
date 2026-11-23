"""META-02, step 2: winners against losers on New York high-volatility days, development data (in-sample, descriptive).
For each entry-time feature: mean among winners and losers, standardised difference, and the AUC of the feature
alone (0.5 = no separation) with a 95% interval from resampling whole days. Writes reports/dash02/winlose.csv."""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.dl01_model import FEATS, LABELS  # noqa: E402

POST = {"minutes_held": "Minutes held", "mae_dv": "Worst open loss, share of expected daily move", "mfe_dv": "Best open gain, share of expected daily move",
        "to_close": "Held to the close (1 = yes)"}


def auc_ci(y, x, day, n=300, seed=0):
    m = np.isfinite(x)
    y, x, day = y[m], x[m], day[m]
    a = roc_auc_score(y, x)
    rng = np.random.default_rng(seed)
    ud, inv = np.unique(day, return_inverse=True)
    idx_by = [np.where(inv == k)[0] for k in range(len(ud))]
    bs = []
    for _ in range(n):
        pick = np.concatenate([idx_by[k] for k in rng.integers(0, len(ud), len(ud))])
        if 0 < y[pick].mean() < 1:
            bs.append(roc_auc_score(y[pick], x[pick]))
    return a, np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def main():
    d = pickle.load(open(ROOT / "data/cache/dl01.pkl", "rb"))
    t = d["trades"]; t = t[(t.regime == "high") & (t.period == "dev")].copy()
    t["mae_dv"] = t["mae_pts"] / t["dvol_pts"]; t["mfe_dv"] = t["mfe_pts"] / t["dvol_pts"]; t["to_close"] = (t["exit_reason"] == "session_end").astype(float)
    y = t["win"].to_numpy(); day = t["day"].to_numpy()
    rows = []
    for kind, cols in (("Known at entry", {f: LABELS[f] for f in FEATS}), ("Known only after entry", POST)):
        for f, lab in cols.items():
            x = t[f].to_numpy(float)
            w, l = x[(y == 1) & np.isfinite(x)], x[(y == 0) & np.isfinite(x)]
            sd = np.sqrt((w.var() + l.var()) / 2)
            a, lo, hi = auc_ci(y, x, day)
            rows.append({"feature": lab, "kind": kind, "winners_mean": w.mean(), "losers_mean": l.mean(), "std_diff": (w.mean() - l.mean()) / sd if sd > 0 else 0.0,
                         "auc": a, "auc_lo": lo, "auc_hi": hi, "separates": int(lo > 0.5 or hi < 0.5)})
    out = pd.DataFrame(rows)
    out["strength"] = (out["auc"] - 0.5).abs()
    out = out.sort_values(["kind", "strength"], ascending=[True, False])
    (ROOT / "reports/dash02").mkdir(parents=True, exist_ok=True)
    out.to_csv(ROOT / "reports/dash02/winlose.csv", index=False)
    pd.set_option("display.width", 220)
    print(len(t), "trades", t["day"].nunique(), "days, win rate", y.mean())
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
