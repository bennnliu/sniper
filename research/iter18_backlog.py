"""Iteration 18: registry backlog testable with bars: LEADLAG-01, TOX-02, MR-05, VOL-02. Hypotheses in reports/SECOND_EDGE_LOG.md."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm, spearmanr

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.iter12_second_edge import MICRO, news, tstat  # noqa: E402
from research.iter13_tests import bars, stream  # noqa: E402
from sniper.data import DEV_END  # noqa: E402
from sniper.session_rule import build_session  # noqa: E402


def main():
    skip = news()
    out = {}
    S = {s: {w: build_session(bars(s, DEV_END), w) for w in ("NY", "OVERNIGHT")} for s in ("ES", "NQ")}
    # LEADLAG-01
    common = S["ES"]["NY"].days.intersection(S["NQ"]["NY"].days)
    common = common[~common.isin(list(skip))]
    L = {s: np.log(S[s]["NY"].px[S[s]["NY"].days.isin(common)]) for s in S}
    for k in (1, 5):
        r = {s: np.diff(L[s][:, ::k], axis=1) for s in S}
        for lead, lag in (("NQ", "ES"), ("ES", "NQ")):
            x, y = r[lead][:, :-1], r[lag][:, 1:]
            ics = [spearmanr(x[i], y[i])[0] for i in range(len(common))]
            # partial: control for the lagging market's own last return
            own = r[lag][:, :-1]
            resid = x - own
            ics_p = [spearmanr(resid[i], y[i])[0] for i in range(len(common))]
            gross = float(np.mean(np.sign(x) * y) * 1e4)
            cost = MICRO[lag][2] / float(np.exp(L[lag]).mean()) * 1e4
            row = {"k": k, "lead": lead, "lag": lag, "ic": float(np.nanmean(ics)), "t": tstat(ics), "ic_partial": float(np.nanmean(ics_p)), "t_partial": tstat(ics_p),
                   "gross_bp": gross, "cost_bp": cost}
            out[f"LEADLAG-01 {lead}->{lag} {k}m"] = row
            print(f"LEADLAG-01 {lead}->{lag} {k}m: IC {row['ic']:+.4f} (t {row['t']:+.1f}) partial IC {row['ic_partial']:+.4f} (t {row['t_partial']:+.1f}) gross {gross:+.3f} bp vs cost {cost:.2f} bp")
    for s in ("ES", "NQ"):
        name, pv, cost = MICRO[s]
        sd = S[s]["NY"]
        keep = ~sd.days.isin(list(skip))
        px, cv = sd.px[keep], sd.cumvol[keep]
        days = sd.days[keep]
        dvol = (np.where(np.isfinite(sd.prev_close), sd.prev_close, sd.px[:, 0]) * sd.rv20)[keep]
        # TOX-02
        dp = np.diff(px, axis=1)
        sig1 = pd.DataFrame(dp).rolling(20, min_periods=10).std().shift(1).mean(axis=1).to_numpy()[:, None]  # trailing 20-day 1-minute std
        v = np.diff(cv, axis=1)
        buy = norm.cdf(dp / sig1)
        imb_num, vol = np.cumsum(v * (2 * buy - 1), axis=1), np.cumsum(v, axis=1)
        checks = np.arange(30, sd.n, 30)
        I = np.stack([(imb_num[:, c - 1] - (imb_num[:, c - 31] if c > 30 else 0)) / np.maximum(vol[:, c - 1] - (vol[:, c - 31] if c > 30 else 0), 1) for c in checks], axis=1)
        nxt = np.stack([px[:, c + 30] - px[:, c] for c in checks], axis=1)
        prev = np.stack([px[:, c] - px[:, c - 30] for c in checks], axis=1)
        ok = np.isfinite(I).all(axis=1) & np.isfinite(sig1[:, 0])
        ics = [spearmanr(I[i], nxt[i])[0] for i in np.where(ok)[0]]
        ics_prev = [spearmanr(prev[i], nxt[i])[0] for i in np.where(ok)[0]]
        g = float(np.mean(np.sign(I[ok]) * nxt[ok]))
        out[f"TOX-02 {name}"] = {"ic": float(np.nanmean(ics)), "t": tstat(ics), "ic_plain_return": float(np.nanmean(ics_prev)), "t_plain": tstat(ics_prev), "gross_pts": g, "gross_x_cost": g / cost}
        print(f"TOX-02 {name}: IC {np.nanmean(ics):+.4f} (t {tstat(ics):+.2f}); plain past return IC {np.nanmean(ics_prev):+.4f} (t {tstat(ics_prev):+.2f}); gross {g:+.3f} pts = {g / cost:+.2f}x cost")
        # MR-05
        hi, lo = px.max(axis=1), px.min(axis=1)
        res = []
        for i in range(1, len(days)):
            if (days[i] - days[i - 1]).days > 4 or not np.isfinite(dvol[i]) or dvol[i] <= 0:
                continue
            c = px[i]
            for lvl, side in ((hi[i - 1], -1), (lo[i - 1], +1)):
                if side == -1 and c[0] < lvl:
                    hit = np.where(c[:-31] >= lvl)[0]
                elif side == 1 and c[0] > lvl:
                    hit = np.where(c[:-31] <= lvl)[0]
                else:
                    continue
                if len(hit):
                    t0 = hit[0] + 1  # fill one minute later
                    res.append((days[i], (side * (c[t0 + 30] - c[t0]) - cost) / dvol[i], side * (c[t0 + 30] - c[t0])))
        r = pd.DataFrame(res, columns=["day", "vu", "gross"]).set_index("day")
        yr = r["vu"].groupby(r.index.year).mean()
        out[f"MR-05 {name}"] = {"n": int(len(r)), "gross_pts": float(r["gross"].mean()), "gross_x_cost": float(r["gross"].mean() / cost), "t_net": tstat(r["vu"]), "years_pos": float((yr > 0).mean())}
        print(f"MR-05 {name}: n {len(r)} gross {r['gross'].mean():+.3f} pts ({r['gross'].mean() / cost:+.2f}x cost) t net {tstat(r['vu']):+.2f} yrs+ {(yr > 0).mean():.0%}")
    # VOL-02 on NQ
    ny, on = S["NQ"]["NY"], S["NQ"]["OVERNIGHT"]
    dv = pd.Series(np.where(np.isfinite(ny.prev_close), ny.prev_close, ny.px[:, 0]) * ny.rv20, index=ny.days)
    nyr = pd.Series(ny.px.max(axis=1) - ny.px.min(axis=1), index=ny.days) / dv
    onr = (pd.Series(on.px.max(axis=1) - on.px.min(axis=1), index=on.days).reindex(ny.days) / dv)
    d = pd.concat([onr.rename("on"), nyr.rename("ny")], axis=1).dropna()
    d = d[~d.index.isin(list(skip))]
    pct = d["on"].rolling(250, min_periods=120).rank(pct=True)
    comp = pct <= 1 / 3
    a, b = d["ny"][comp & pct.notna()], d["ny"][~comp & pct.notna()]
    out["VOL-02 range"] = {"rank_corr_on_ny": float(d["on"].corr(d["ny"], method="spearman")), "ny_range_after_compressed": float(a.mean()), "ny_range_other": float(b.mean()),
                           "t_diff": float((a.mean() - b.mean()) / np.sqrt(a.var() / len(a) + b.var() / len(b)))}
    st = stream(DEV_END, skip)
    st = st[st["round_trips"] > 0]
    vu = (st["net_pts"] / st["dvol_pts"])
    c2 = comp.reindex(vu.index); ok = pct.reindex(vu.index).notna()
    x, y = vu[ok & (c2 == True)], vu[ok & (c2 == False)]  # noqa: E712
    out["VOL-02 filter"] = {"n_compressed": int(len(x)), "mean_compressed": float(x.mean()), "mean_other": float(y.mean()), "t_diff": float((x.mean() - y.mean()) / np.sqrt(x.var() / len(x) + y.var() / len(y)))}
    print("VOL-02", json.dumps({k: v for k, v in out.items() if k.startswith("VOL")}))
    (ROOT / "reports/iter_18.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
