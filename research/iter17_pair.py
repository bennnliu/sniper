"""Iteration 17: PAIR-01, daily-horizon NQ/ES relative value. Hypothesis in reports/SECOND_EDGE_LOG.md."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.iter12_second_edge import news, tstat  # noqa: E402
from research.iter13_tests import bars  # noqa: E402
from sniper.data import DEV_END  # noqa: E402
from sniper.session_rule import build_session  # noqa: E402

COST = 4.49e-4  # two-leg micro round trip, from iteration 12


def main():
    skip = news()
    S = {s: {w: build_session(bars(s, DEV_END), w) for w in ("NY", "OVERNIGHT")} for s in ("ES", "NQ")}
    def ser(s, w, f):
        sd = S[s][w]
        return pd.Series(f(sd), index=sd.days)
    cc = {s: ser(s, "NY", lambda sd: sd.px[:, -1] / sd.prev_close - 1) for s in S}
    j = pd.concat(cc, axis=1).dropna()
    beta = (j["NQ"].rolling(60).cov(j["ES"]) / j["ES"].rolling(60).var()).shift(1)
    spread = (j["NQ"] - beta * j["ES"]).dropna()
    out = []
    for w in ("OVERNIGHT", "NY"):
        r = pd.concat({s: ser(s, w, lambda sd: sd.px[:, -1] / sd.px[:, 0] - 1) for s in S}, axis=1).dropna()
        tgt = (r["NQ"] - beta.reindex(r.index) * r["ES"]).dropna()
        tgt = tgt[~tgt.index.isin(list(skip))]
        for k in (1, 5, 20):
            sig = spread.rolling(k).sum().shift(1).reindex(tgt.index)  # known at the prior 15:00 close
            d = pd.concat([sig.rename("s"), tgt.rename("y")], axis=1).dropna()
            ic = d.groupby(d.index.year).apply(lambda g: g["s"].corr(g["y"], method="spearman"))
            ic_all = d["s"].corr(d["y"], method="spearman")
            t_ic = ic_all * np.sqrt(len(d) - 2) / np.sqrt(1 - ic_all ** 2)
            sign = np.sign(ic_all)
            pnl = sign * np.sign(d["s"]) * d["y"]
            net = pnl - COST
            yr = net.groupby(net.index.year).mean()
            row = {"session": w, "lookback": k, "n": int(len(d)), "ic": float(ic_all), "t_ic": float(t_ic), "years_same_sign": float((np.sign(ic) == sign).mean()),
                   "gross_bp": float(pnl.mean() * 1e4), "net_bp": float(net.mean() * 1e4), "t_gross": tstat(pnl), "t_net": tstat(net), "years_pos_net": float((yr > 0).mean()),
                   "spread_std_bp": float(d["y"].std() * 1e4)}
            out.append(row)
            print(f"{w:9s} k={k:2d}: n {row['n']} IC {row['ic']:+.4f} (t {row['t_ic']:+.2f}, {row['years_same_sign']:.0%} yrs same sign) gross {row['gross_bp']:+.2f} bp net {row['net_bp']:+.2f} bp "
                  f"t gross {row['t_gross']:+.2f} t net {row['t_net']:+.2f} yrs+ {row['years_pos_net']:.0%} | spread std {row['spread_std_bp']:.0f} bp")
    (ROOT / "reports/iter_17.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
