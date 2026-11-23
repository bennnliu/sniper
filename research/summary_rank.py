"""Ranked summary of every strategy that has a daily result stream, scored the same way (development data, simulated).
Each stream is scaled to the same daily dollar risk as the breakout rule at 8 MNQ (about $700 standard deviation
over all days), capped at 50 micros, then run through the $50K Combine and XFA simulators."""
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.iter12_second_edge import news  # noqa: E402
from research.iter13_tests import bars, simulate  # noqa: E402
from sniper.data import DEV_END  # noqa: E402
from sniper.montecarlo import block_bootstrap  # noqa: E402
from sniper.propscore import score_stream  # noqa: E402
from sniper.rules import load_rules  # noqa: E402
from sniper.session_rule import build_session, run_session  # noqa: E402

RULES = load_rules()
TARGET_STD = 700.0
ONE = lambda c, need, left, dv: np.full_like(c, 1.0)  # noqa: E731


def score(label, dd, pv, contracts=None, flip_seed=None):
    dd = dd[dd["dvol_pts"].notna() & (dd["dvol_pts"] > 0)].copy()
    if flip_seed is not None:  # random direction: reverse the gross result on a coin flip
        f = np.random.default_rng(flip_seed).random(len(dd)) < 0.5
        cost = dd["round_trips"] * 1.11
        net = np.where(f, -(dd["net_pts"] + cost) - cost, dd["net_pts"])
        mae = np.where(f, np.minimum(-dd["mfe_pts"] - cost, 0), dd["mae_pts"])
        mfe = np.where(f, np.maximum(-dd["mae_pts"], 0), dd["mfe_pts"])
        dd["net_pts"], dd["mae_pts"], dd["mfe_pts"] = net, mae, mfe
    std1 = float(dd["net_pts"].std() * pv)
    n = contracts or int(np.clip(round(TARGET_STD / std1), 1, 50))
    pnl, mae = dd["net_pts"].to_numpy() * pv * n, dd["mae_pts"].to_numpy() * pv * n
    traded = (dd["round_trips"] > 0).to_numpy()
    s = score_stream(pnl, mae, traded, n_paths=4000)
    eq = dd.assign(net_pts=pnl / 2, mae_pts=mae / 2, mfe_pts=dd["mfe_pts"] * pv * n / 2)
    idx = block_bootstrap(len(eq), 10000, 30, 5, np.random.default_rng(1))
    p30, _ = simulate(eq, ONE, idx, RULES)
    spec = RULES.account("50K")
    p = s["pass"]
    fees_per_funded = s["cost_per_account"] / p if p > 0 else float("inf")
    return {"strategy": label, "contracts": n, "pass": p, "pass30": p30, "days_to_pass": s["days_to_pass"], "payout_rate": max(s["xfa_p_std"], s["xfa_p_cons"]),
            "payout": s["payout"], "fees_per_attempt": s["cost_per_account"], "profit_per_funded": s["payout"] - spec.activation_fee_standard - fees_per_funded,
            "profit_per_attempt": s["ev_per_attempt"], "usd_per_day": float(pnl.mean())}


def main():
    skip = news()
    rows = []
    nq, es = bars("NQ", DEV_END), bars("ES", DEV_END)
    S = {(s, w): build_session(df, w) for s, df in (("NQ", nq), ("ES", es)) for w in ("NY", "ASIA", "LONDON")}
    base = run_session(S["NQ", "NY"], 1.11, skip_days=skip)[1]
    allnews = run_session(S["NQ", "NY"], 1.11)[1]
    rows.append(score("Breakout NQ, New York, news days traded, 8 MNQ", allnews, 2, 8))
    rows.append(score("Breakout NQ, New York, news days skipped, 8 MNQ", base, 2, 8))
    rows.append(score("Breakout NQ, New York, news days skipped, 2 MNQ", base, 2, 2))
    rows.append(score("Breakout NQ, New York, news skipped, 16 MNQ", base, 2, 16))
    b = base[base["dvol_pts"].notna()]
    runs = [run_session(S["NQ", "NY"], 1.11, lookback=lb, vm=vm, skip_days=skip)[1].reindex(b.index) for lb in (7, 14, 28) for vm in (0.8, 1.0, 1.2)]
    ens = b.copy()
    for c in ("net_pts", "mae_pts", "mfe_pts", "round_trips"):
        ens[c] = np.mean([r[c].fillna(0).to_numpy() for r in runs], axis=0)
    rows.append(score("Breakout NQ, ensemble of nine settings", ens, 2))
    rows.append(score("Breakout ES, New York (MES)", run_session(S["ES", "NY"], 0.495, skip_days=skip)[1], 5))
    rows.append(score("Breakout NQ, Asia session", run_session(S["NQ", "ASIA"], 1.11, skip_days=skip)[1], 2))
    rows.append(score("Breakout NQ, London session", run_session(S["NQ", "LONDON"], 1.11, skip_days=skip)[1], 2))
    on = build_session(nq, "OVERNIGHT")
    onr = pd.Series(on.px.max(axis=1) - on.px.min(axis=1), index=on.days).reindex(b.index) / b["dvol_pts"]
    q = onr.rolling(250, min_periods=120).rank(pct=True) <= 1 / 3
    filt = b.copy()
    for c in ("net_pts", "mae_pts", "mfe_pts", "round_trips"):
        filt.loc[q, c] = 0.0
    rows.append(score("Breakout NQ, quiet nights skipped", filt, 2))
    ctl = [score("Random direction, same trades as the breakout, 8 MNQ", base, 2, 8, flip_seed=k) for k in range(5)]
    rows.append({k: (ctl[0][k] if isinstance(ctl[0][k], str) else float(np.mean([c[k] for c in ctl]))) for k in ctl[0]})
    names = {"ON-01 long OVERNIGHT|MNQ": "Long every night (MNQ)", "ON-01 long NY|MNQ": "Long every New York session (MNQ)", "ON-02 long after down NY|MNQ": "Long overnight after a down day (MNQ)",
             "ON-03 NY fades overnight move|MNQ": "New York fades the overnight move (MNQ)", "CAL-03 turn of month, NY|MNQ": "Turn of month, New York (MNQ)",
             "FADE-01 London breakout fade|MNQ": "Fade London breakouts (MNQ)", "ON-01 long ASIA|MNQ": "Long every Asia session (MNQ)"}
    st = pickle.load(open(ROOT / "data/iter12_streams.pkl", "rb"))
    for k, lab in names.items():
        d = st[k].copy(); d["mfe_pts"] = d.get("mfe_pts", 0.0)
        rows.append(score(lab, d, 2))
    st = pickle.load(open(ROOT / "data/iter14_streams.pkl", "rb"))
    rows.append(score("Pre-holiday long, New York (MES)", st["HOL-01 pre-holiday, NY|MES"], 5))
    rows.append(score("FOMC-cycle even weeks long, New York (MNQ)", st["CYCLE-01 even weeks, NY|MNQ"], 2))
    df = pd.DataFrame(rows).sort_values(["pass", "payout_rate", "profit_per_funded", "profit_per_attempt"], ascending=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 60)
    print(df.round(3).to_string(index=False))
    df.to_csv(ROOT / "reports/summary_rank.csv", index=False)


if __name__ == "__main__":
    main()
