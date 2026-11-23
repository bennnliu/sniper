import numpy as np
import pandas as pd

from sniper import features as F
from sniper.data import add_session_columns


def _bars(n_days=45, seed=0):
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2023-01-02", periods=n_days)
    parts = []
    px = 4000.0
    for d in days:
        idx = pd.date_range(d.tz_localize("America/Chicago") + pd.Timedelta(hours=0, minutes=30),
                            d.tz_localize("America/Chicago") + pd.Timedelta(hours=15, minutes=29), freq="min")
        steps = rng.normal(0, 0.5, len(idx)).cumsum()
        c = px + steps
        px = c[-1]
        parts.append(pd.DataFrame({"instrument_id": 1, "open": c, "high": c + 0.25, "low": c - 0.25, "close": c,
                                   "volume": rng.integers(1, 100, len(idx))}, index=idx.tz_convert("UTC")))
    return add_session_columns(pd.concat(parts))


def _all_features(df):
    p = F.day_grid(df)
    ub, lb = F.noise_bands(p)
    out = pd.DataFrame({"eod": F.eod_reversal(p), "gtbr": F.gtbr_first30(p), "od": F.overnight_drift_condition(p),
                        "reg": F.opening_regime(df, p).astype(float), "ub": ub[600], "lb": lb[870]})
    out["vwap"] = F.session_vwap(df, p.index)[870]
    return out


def test_features_do_not_use_later_days():
    df = _bars()
    full = _all_features(df)
    cut_day = full.index[30]
    part = _all_features(df[df["trading_day"] <= cut_day])
    pd.testing.assert_frame_equal(full.loc[:cut_day], part.loc[:cut_day])
    assert full["ub"].notna().sum() > 10 and full["eod"].notna().sum() > 30


def test_features_do_not_use_bars_after_their_decision_time():
    df = _bars()
    full = _all_features(df)
    day = full.index[35]
    # Drop everything after 14:30 CT on that day: values known by 14:30 must not change.
    cut = df[(df["trading_day"] < day) | ((df["trading_day"] == day) & (df["minute_ct"] < 870))]
    p = F.day_grid(df)
    ub, lb = F.noise_bands(p)
    last = cut[cut["trading_day"] == day]
    assert np.isclose(F.eod_reversal(p).loc[day],
                      np.log(last[last["minute_ct"] == 839]["close"].iloc[0] / p["prev_close"].loc[day]))
    # bands depend only on earlier days, today's 8:30 price and the prior close
    p_prev = F.day_grid(df[df["trading_day"] < day])
    sig = pd.DataFrame({m: (p_prev[m] / p_prev[510] - 1).abs() for m in F.CHECKS}).tail(14).mean()
    hi = max(p[510].loc[day], p["prev_close"].loc[day])
    assert np.isclose(ub.loc[day, 600], hi * (1 + sig[600]))


def test_noise_bands_bracket_the_open():
    df = _bars()
    p = F.day_grid(df)
    ub, lb = F.noise_bands(p)
    ok = ub[540].notna()
    assert (ub[540][ok] >= p[510][ok]).all() and (lb[540][ok] <= p[510][ok]).all()
