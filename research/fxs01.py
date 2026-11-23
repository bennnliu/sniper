"""Iteration 35: session drifts in currencies and gold (FXS-01, GCS-01). Pre-registered in reports/NEW_STRATEGY_LOG.md."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.xm_common import DEV_END, DEV_START, bars, cost_pts, news, tstat  # noqa: E402
from sniper.session_rule import build_session, hold  # noqa: E402

TESTS = [("FXS-01a", "6E", "NY", 1), ("FXS-01a", "6B", "NY", 1), ("FXS-01a", "6J", "NY", 1),
         ("FXS-01b", "6E", "LONDON", -1), ("FXS-01b", "6B", "LONDON", -1), ("FXS-01b", "6J", "ASIA", -1),
         ("GCS-01", "GC", "ASIA", 1), ("GCS-01", "GC", "NY", -1)]


def main():
    skip = news(); rows = []; cache = {}
    for name, sym, ses, sign in TESTS:
        if sym not in cache:
            cache[sym] = bars(sym, end=DEV_END, start=DEV_START)
        sd = build_session(cache[sym], ses)
        r = {}
        for m in (0, 1, 2):
            h = hold(sd, sign * np.ones(len(sd.days)), cost_pts(sym, m), skip_days=skip)
            h = h[np.isfinite(h["dvol_pts"]) & (h["dvol_pts"] > 0) & (h["pos"] != 0)]
            r[m] = h["net_pts"] / h["dvol_pts"]
        yr = r[1].groupby(r[1].index.year).sum()
        rows.append({"test": name, "market": sym, "session": ses, "side": "long" if sign > 0 else "short", "days": len(r[1]),
                     "gross_t": tstat(r[0]), "net_t": tstat(r[1]), "net_t_2x": tstat(r[2]), "gross_mean": r[0].mean(),
                     "cost_r": (r[0] - r[1]).mean(), "years_pos": int((yr > 0).sum()), "years": len(yr)})
    out = pd.DataFrame(rows); out.to_csv(ROOT / "reports/fxs01/results.csv", index=False)
    pd.set_option("display.width", 220); print(out.round(3).to_string())


if __name__ == "__main__":
    main()
