import pandas as pd
import pytest

from sniper.data import HoldoutError, add_session_columns, flag_days, load_bars, pivot_times


def _bars(start, periods):
    idx = pd.date_range(start, periods=periods, freq="min", tz="UTC")
    df = pd.DataFrame({"instrument_id": 1, "open": 1.0, "high": 1.0, "low": 1.0, "close": range(periods),
                       "volume": 1}, index=idx)
    return add_session_columns(df)


def test_session_columns_match_topstep_day():
    # 22:59 UTC on Mon 23 Nov 2026 = 16:59 CST (Monday's day); 23:00 UTC = 17:00 CST (Tuesday's).
    df = _bars("2026-11-23 22:59", 2)
    assert list(df["trading_day"].dt.strftime("%Y-%m-%d")) == ["2026-11-23", "2026-11-24"]
    df = _bars("2026-11-23 14:30", 1)  # 8:30 CST
    assert bool(df["rth"].iloc[0]) and df["minute_ct"].iloc[0] == 510
    df = _bars("2026-11-23 21:10", 1)  # 15:10 CST
    assert not df["in_topstep_session"].iloc[0]


def test_half_day_detection():
    full = _bars("2026-11-23 14:30", 390)  # 8:30-15:00 CST
    half = _bars("2026-11-27 14:30", 210)  # ends 12:00 CST
    days = flag_days(pd.concat([full, half]))
    assert list(days["half_day"]) == [False, True]


def test_pivot_times_uses_bar_ending_at_minute():
    df = _bars("2026-11-23 14:30", 60)  # bars opening 8:30..9:29 CST, close = 0..59
    p = pivot_times(df, [540])  # 9:00 CT -> bar opened 8:59 -> close 29
    assert p.iloc[0, 0] == 29


def test_loader_refuses_holdout(tmp_path):
    df = _bars("2025-10-31 14:30", 3000)  # runs into November 2025
    path = tmp_path / "X.parquet"
    df.drop(columns=["ts_ct"]).to_parquet(path)
    with pytest.raises(HoldoutError):
        load_bars("X", path=path)
    ok = load_bars("X", end="2025-11-01", path=path)
    assert ok.index.max() < pd.Timestamp("2025-11-01", tz="America/Chicago")
    assert len(load_bars("X", path=path, holdout=True)) == 3000
