import numpy as np
import pandas as pd

from sniper.session_rule import SessionData, run_session
from sniper.timing import run_flex


def _sd(seed=0, days=80, n=390):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2020-01-01", periods=days)
    px = np.empty((days, n + 1)); last = 10000.0
    prev = np.full(days, np.nan)
    for d in range(days):
        prev[d] = last if d else np.nan
        drift = rng.normal(0, 0.04)
        px[d] = last + rng.normal(0, 12) + np.concatenate([[0], np.cumsum(rng.normal(drift, 1.5, n))])
        last = px[d, -1]
    vol = np.ones((days, n + 1)).cumsum(axis=1)
    vwap = np.cumsum(px, axis=1) / np.arange(1, n + 2)
    absmove = np.concatenate([np.zeros((days, 1)), np.abs(np.diff(px, axis=1)).cumsum(axis=1)], axis=1)
    return SessionData("NY", idx, px, vwap, vol, absmove, prev, np.full(days, 0.01), n, 510)


def test_defaults_reproduce_the_frozen_rule():
    sd = _sd()
    for lb, vm in ((7, 0.8), (14, 1.0), (28, 1.2)):
        a = run_session(sd, 1.11, lookback=lb, vm=vm)[0]
        b = run_flex(sd, 1.11, lookback=lb, vm=vm)
        assert len(a) == len(b) and len(a) > 20
        for col in ("fill", "exit_min", "dir"):
            assert (a[col].to_numpy() == b[col].to_numpy()).all()
        assert np.allclose(a["net_pts"], b["net_pts"])


def test_trailing_stop_caps_giveback_and_target_caps_gain():
    sd = _sd(1)
    base = run_flex(sd, 0.0)
    tr = run_flex(sd, 0.0, trail_k=0.05)
    dvol = tr["dvol_pts"]
    assert (tr["exit_reason"] == "trail").any()
    hit = tr[tr["exit_reason"] == "trail"]
    assert (hit["minutes_held"] > 0).all()
    tg = run_flex(sd, 0.0, target_k=0.1)
    assert (tg["exit_reason"] == "target").any()
    assert tg["mfe_pts"].max() <= base["mfe_pts"].max() + 1e-9
    assert len(dvol) == len(tr)


def test_pullback_enters_at_the_band_or_not_at_all():
    sd = _sd(2)
    base = run_flex(sd, 0.0)
    pb = run_flex(sd, 0.0, pullback=True)
    assert 0 < len(pb) <= len(base)
