"""Load, clean and store CME bars (DATA.md).

Raw Databento DBN files go in ``data/raw``; cleaned bars are written as
Parquet in ``data/bars``. The loader refuses holdout dates (METHOD.md §1)
unless called with ``holdout=True``.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
BARS_DIR = DATA_DIR / "bars"
CT = "America/Chicago"

# METHOD.md section 1
DEV_END = pd.Timestamp("2024-11-01", tz=CT)
WALK_FORWARD_END = pd.Timestamp("2025-11-01", tz=CT)
HOLDOUT_START = WALK_FORWARD_END


class HoldoutError(RuntimeError):
    pass


def add_session_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add Chicago time, Topstep trading day and session flags.

    The trading day runs 5:00 PM CT to 3:10 PM CT and is labelled by the date
    it ends (same convention as TopstepSim). ``rth`` marks the 8:30-15:00 CT
    cash session. ``in_topstep_session`` is False from 3:10 to 5:00 PM CT.
    """
    ts = df.index.tz_convert(CT)
    shifted = ts + pd.Timedelta(hours=7)
    out = df.copy()
    out["ts_ct"] = ts
    out["trading_day"] = pd.to_datetime(shifted.date)
    minutes = ts.hour * 60 + ts.minute
    out["minute_ct"] = minutes
    out["rth"] = (minutes >= 8 * 60 + 30) & (minutes < 15 * 60)
    out["in_topstep_session"] = ~((minutes >= 15 * 60 + 10) & (minutes < 17 * 60))
    return out


def flag_days(df: pd.DataFrame) -> pd.DataFrame:
    """Per trading day: number of RTH bars, last RTH bar time, half-day flag.

    A half day (early close) is detected from the data: the last bar of the
    day session ends before 12:30 PM CT.
    """
    rth = df[df["rth"]]
    g = rth.groupby("trading_day")
    days = pd.DataFrame({
        "rth_bars": g.size(),
        "last_rth_minute": g["minute_ct"].max(),
        "first_rth_minute": g["minute_ct"].min(),
    })
    days["half_day"] = days["last_rth_minute"] < 12 * 60 + 30
    return days


def dbn_to_bars(path: str | Path | list, root_symbol: str) -> pd.DataFrame:
    """Read one or more Databento ohlcv DBN files into a clean bar frame (UTC index)."""
    import databento as db  # imported lazily: research code may run without it

    paths = path if isinstance(path, (list, tuple)) else [path]
    raw = pd.concat([db.DBNStore.from_file(str(p)).to_df() for p in paths])
    df = raw[["instrument_id", "open", "high", "low", "close", "volume"]].copy()
    df.index.name = "ts_event"
    df["symbol"] = root_symbol
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df = add_session_columns(df)
    df["segment"] = df["instrument_id"].astype(str) + "|" + df["trading_day"].dt.strftime("%Y-%m-%d")
    return df


@dataclass
class QualityReport:
    rows: int
    duplicates: int
    bad_hilo: int
    nonpositive_price: int
    rolls: int
    rth_zero_volume: int
    rth_gaps_over_5m: int
    half_days: int
    trading_days: int
    degraded_days: list

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def quality_report(df: pd.DataFrame, degraded_days: list | None = None) -> QualityReport:
    rth = df[df["rth"]]
    gaps = 0
    for _, day in rth.groupby("trading_day"):
        d = day.index.to_series().diff().dt.total_seconds().div(60)
        gaps += int((d > 5).sum())
    days = flag_days(df)
    return QualityReport(
        rows=len(df),
        duplicates=int(df.index.duplicated().sum()),
        bad_hilo=int((df["high"] < df["low"]).sum() + (df["close"] > df["high"]).sum() + (df["close"] < df["low"]).sum()),
        nonpositive_price=int((df[["open", "high", "low", "close"]] <= 0).any(axis=1).sum()),
        rolls=int((df["instrument_id"] != df["instrument_id"].shift()).sum() - 1),
        rth_zero_volume=int((rth["volume"] == 0).sum()),
        rth_gaps_over_5m=gaps,
        half_days=int(days["half_day"].sum()),
        trading_days=int(len(days)),
        degraded_days=list(degraded_days or []),
    )


def save_bars(df: pd.DataFrame, root_symbol: str) -> Path:
    out = BARS_DIR / f"{root_symbol}_1m.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.drop(columns=["ts_ct"]).to_parquet(out)
    return out


def load_bars(root_symbol: str, start=None, end=None, holdout: bool = False, path: Path | None = None) -> pd.DataFrame:
    """Load cleaned 1-minute bars. Raises HoldoutError for holdout dates."""
    df = pd.read_parquet(path or BARS_DIR / f"{root_symbol}_1m.parquet")
    end_ts = pd.Timestamp(end, tz=CT) if end is not None and pd.Timestamp(end).tzinfo is None else (
        pd.Timestamp(end) if end is not None else None)
    if not holdout:
        if end_ts is None or end_ts > HOLDOUT_START:
            if (df.index >= HOLDOUT_START).any():
                raise HoldoutError("bars on or after the holdout start; pass end<=2025-11-01 or holdout=True")
            end_ts = end_ts or HOLDOUT_START
    if start is not None:
        s = pd.Timestamp(start)
        df = df[df.index >= (s if s.tzinfo else s.tz_localize(CT))]
    if end_ts is not None:
        df = df[df.index < end_ts]
    df = df.copy()
    df["ts_ct"] = df.index.tz_convert(CT)
    return df


def rth_session_bars(df: pd.DataFrame, exclude_half_days: bool = True) -> pd.DataFrame:
    """Day-session bars (8:30-15:00 CT), optionally without half days."""
    out = df[df["rth"]]
    if exclude_half_days:
        days = flag_days(df)
        keep = days.index[~days["half_day"]]
        out = out[out["trading_day"].isin(keep)]
    return out


def pivot_times(df: pd.DataFrame, minutes: list[int], col: str = "close") -> pd.DataFrame:
    """Value of ``col`` at given CT minutes-of-day for each trading day.

    Uses the bar that *ends* at the given minute: Databento ohlcv timestamps
    mark the bar open, so the close at 9:00 is the bar stamped 8:59.
    """
    sub = df[df["minute_ct"].isin([m - 1 for m in minutes])]
    out = sub.pivot_table(index="trading_day", columns="minute_ct", values=col, aggfunc="last")
    out.columns = [c + 1 for c in out.columns]
    return out.reindex(columns=minutes)
