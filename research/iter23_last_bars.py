"""Iteration 23: ROSA-01, WKND-01, DOW-01. Hypotheses in reports/SECOND_EDGE_LOG.md. Development data only."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import f_oneway

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.iter12_second_edge import MICRO, news, tstat  # noqa: E402
from research.iter13_tests import bars, stream  # noqa: E402
from sniper.data import DEV_END  # noqa: E402
from sniper.session_rule import build_session  # noqa: E402


def main():
    skip = news()
    out = {}
    for s in ("ES", "NQ"):
        name, pv, cost = MICRO[s]
        df = bars(s, DEV_END)
        ny, on = build_session(df, "NY"), build_session(df, "OVERNIGHT")
        keep = ~ny.days.isin(list(skip)) & np.isfinite(ny.prev_close) & np.isfinite(ny.rv20)
        dvol = ny.prev_close * ny.rv20
        gap = (ny.px[:, 0] - ny.prev_close) / dvol
        last = ny.px[:, -1] - ny.px[:, -31]
        m = keep & (np.abs(gap) > 0.5)
        pnl = pd.Series(np.sign(gap[m]) * last[m] - cost, index=ny.days[m]) / dvol[m]
        g = float(np.mean(np.sign(gap[m]) * last[m]))
        yr = pnl.groupby(pnl.index.year).mean()
        out[f"ROSA-01 {name}"] = {"n": int(m.sum()), "gross_pts": g, "gross_x_cost": g / cost, "t_net": tstat(pnl), "t_2018_on": tstat(pnl[pnl.index >= "2018-01-01"]), "years_pos": float((yr > 0).mean())}
        print(f"ROSA-01 {name}", json.dumps(out[f"ROSA-01 {name}"]))
        for w, sd, dow, lab in (("OVERNIGHT", on, 0, "Sunday night"), ("NY", ny, 4, "Friday New York")):
            k = ~sd.days.isin(list(skip)) & np.isfinite(sd.rv20) & (sd.rv20 > 0)
            r = pd.Series((sd.px[:, -1] - sd.px[:, 0]) / (np.where(np.isfinite(sd.prev_close), sd.prev_close, sd.px[:, 0]) * sd.rv20), index=sd.days)[k]
            a, b = r[r.index.dayofweek == dow], r[r.index.dayofweek != dow]
            td = (a.mean() - b.mean()) / np.sqrt(a.var() / len(a) + b.var() / len(b))
            pts = pd.Series(sd.px[:, -1] - sd.px[:, 0], index=sd.days)[k]
            out[f"WKND-01 {lab} {name}"] = {"n": int(len(a)), "mean": float(a.mean()), "t": tstat(a), "mean_other": float(b.mean()), "t_diff": float(td),
                                            "mean_pts": float(pts[pts.index.dayofweek == dow].mean()), "x_cost": float(abs(pts[pts.index.dayofweek == dow].mean()) / cost)}
            print(f"WKND-01 {lab} {name}", json.dumps(out[f"WKND-01 {lab} {name}"]))
    st = stream(DEV_END, skip)
    st = st[st["round_trips"] > 0]
    vu = st["net_pts"] / st["dvol_pts"]
    groups = [vu[vu.index.dayofweek == d] for d in range(5)]
    F, p = f_oneway(*groups)
    out["DOW-01"] = {"F": float(F), "p": float(p), "mean_by_day": [float(g.mean()) for g in groups], "t_by_day": [tstat(g) for g in groups],
                     "mean_by_day_2018_on": [float(g[g.index >= "2018-01-01"].mean()) for g in groups], "mean_by_day_to_2017": [float(g[g.index < "2018-01-01"].mean()) for g in groups]}
    print("DOW-01", json.dumps(out["DOW-01"]))
    (ROOT / "reports/iter_23.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
