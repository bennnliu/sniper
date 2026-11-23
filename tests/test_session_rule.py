import numpy as np
import pandas as pd

from sniper import features as F
from sniper.noise import run_rule
from sniper.session_rule import build_session, run_session
from tests.test_features import _bars


def test_ny_session_matches_frozen_rule():
    df = _bars(60, seed=3)
    old = run_rule(df, F.day_grid(df), 0.69, delay=1)
    _, new = run_session(build_session(df, "NY"), 0.69)
    j = old.join(new, rsuffix="_new", how="inner")
    assert len(j) > 20 and (j["round_trips"] > 0).sum() > 5
    assert np.allclose(j["net_pts"], j["net_pts_new"]) and np.allclose(j["mae_pts"], j["mae_pts_new"])


def test_risk_limits_only_reduce_exposure():
    df = _bars(60, seed=4)
    sd = build_session(df, "NY")
    base, _ = run_session(sd, 0.69)
    one, _ = run_session(sd, 0.69, max_entries=1)
    stp, _ = run_session(sd, 0.69, trade_stop_sigma=0.05)
    assert one.groupby("day").size().max() == 1 and len(one) <= len(base)
    assert stp["minutes_held"].sum() <= base["minutes_held"].sum()
    assert (stp["exit_reason"] == "trade_stop").any()
    lo, _ = run_session(sd, 0.69, allow_short=False)
    assert (lo["dir"] == 1).all()


def test_trade_features_do_not_change_when_later_days_are_removed():
    df = _bars(60, seed=5)
    full, _ = run_session(build_session(df, "NY"), 0.69)
    cut = full["day"].iloc[len(full) // 2]
    part, _ = run_session(build_session(df[df["trading_day"] <= cut], "NY"), 0.69)
    a = full[full["day"] <= cut].reset_index(drop=True)
    cols = [c for c in a.columns if c.startswith("f_")] + ["entry_px", "net_pts"]
    pd.testing.assert_frame_equal(a[cols], part.reset_index(drop=True)[cols])
