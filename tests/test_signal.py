import numpy as np
import pandas as pd
import pytest

from sniper.signal import (
    assert_no_lookahead,
    forward_returns,
    half_life,
    holm,
    ic_t_newey_west,
    ic_t_nonoverlapping,
    passes_stage1,
    signal_test,
    spearman_ic,
)


def _random_walk(n=20000, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n, freq="min", tz="UTC")
    ret = rng.normal(0, 1e-3, n)
    close = pd.Series(5000 * np.exp(np.cumsum(ret)), index=idx)
    return close, pd.Series(ret, index=idx)


def test_forward_returns_do_not_cross_segments():
    idx = pd.date_range("2024-01-01", periods=6, freq="min", tz="UTC")
    close = pd.Series([100, 101, 102, 200, 201, 202], index=idx, dtype=float)
    seg = pd.Series([0, 0, 0, 1, 1, 1], index=idx)  # a roll between bar 2 and 3
    fwd = forward_returns(close, [1, 2], seg)
    assert np.isclose(fwd[1].iloc[0], np.log(101 / 100))
    assert np.isnan(fwd[1].iloc[2]) and np.isnan(fwd[2].iloc[1])
    assert np.isclose(fwd[2].iloc[3], np.log(202 / 200))
    assert fwd[1].iloc[-1] != fwd[1].iloc[-1]  # NaN at the end


def test_spearman_matches_scipy():
    rng = np.random.default_rng(1)
    x = pd.Series(rng.normal(size=500))
    y = pd.Series(x * 0.3 + rng.normal(size=500))
    from scipy.stats import spearmanr
    assert spearman_ic(x, y) == pytest.approx(spearmanr(x, y).statistic)


def test_real_signal_is_detected():
    close, ret = _random_walk()
    # Feature sees next-minute return with noise: a genuine (if impossible) signal.
    feat = ret.shift(-1) + np.random.default_rng(2).normal(0, 3e-3, len(ret))
    fwd = forward_returns(close, [1, 5, 15, 30])
    rep = signal_test(feat, fwd)
    assert rep.horizons[1].ic > 0.2
    assert rep.horizons[1].t > 10
    assert rep.peak == 1
    assert rep.half_life is not None


def test_overlap_correction_deflates_naive_t():
    """A random feature that is persistent (like most real features) against a
    30-bar overlapping return: the naive t is inflated, the corrected ones are not."""
    close, _ = _random_walk(seed=3)
    rng = np.random.default_rng(4)
    feat = pd.Series(rng.normal(size=len(close)), index=close.index).rolling(30).mean()
    fwd = forward_returns(close, [30])[30]
    naive_ts, corrected_ts = [], []
    for seed in range(5):
        c, _ = _random_walk(seed=10 + seed)
        f = forward_returns(c, [30])[30]
        f.index = feat.index
        ic, t_nw, n = ic_t_newey_west(feat, f, lags=29)
        naive_ts.append(ic * np.sqrt((n - 2) / (1 - ic**2)))
        corrected_ts.append(ic_t_nonoverlapping(feat, f, 30)[1])
    assert np.std(naive_ts) > 3 * np.std(corrected_ts)


def test_noise_feature_fails_stage1():
    close, _ = _random_walk(seed=5)
    feat = pd.Series(np.random.default_rng(6).normal(size=len(close)), index=close.index)
    fwd = forward_returns(close, [1, 5, 15])
    year = pd.Series(np.arange(len(close)) // 4000, index=close.index)
    rep = signal_test(feat, fwd, slices={"year": year})
    ok, reasons = passes_stage1(rep, sign=+1)
    assert not ok and reasons


def test_wrong_sign_fails_stage1():
    close, ret = _random_walk(seed=7)
    feat = -ret.shift(-1)  # strong but opposite to the registered sign
    fwd = forward_returns(close, [1])
    rep = signal_test(feat, fwd)
    ok, reasons = passes_stage1(rep, sign=+1)
    assert not ok


def test_holm():
    adj = holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adj["a"] == pytest.approx(0.03)
    assert adj["c"] == pytest.approx(0.06)
    assert adj["b"] == pytest.approx(0.06)


def test_half_life():
    assert half_life({1: 0.02, 5: 0.05, 15: 0.03, 30: 0.02}) == (5, 30)
    assert half_life({1: 0.05, 5: 0.04}) == (1, None)


def test_lookahead_guard_catches_centered_window():
    close, _ = _random_walk(n=500)
    data = close.to_frame("close")
    honest = lambda d: d["close"].rolling(10).mean()
    cheat = lambda d: d["close"].rolling(10, center=True).mean()
    assert_no_lookahead(honest, data)
    with pytest.raises(AssertionError):
        assert_no_lookahead(cheat, data)
