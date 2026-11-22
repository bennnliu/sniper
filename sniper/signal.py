"""Stage 1 signal test (METHOD.md section 3): no trading rules, just information.

For a feature series and forward returns at several horizons this computes:

* the information coefficient (IC): Spearman rank correlation;
* two t-statistics that respect overlapping horizons: Newey-West on the
  per-sample rank products, and a plain t on non-overlapping subsamples.
  The smaller one is reported (``t``);
* Holm-adjusted p-values across horizons;
* IC by slice (year, time-of-day bucket, volatility tercile) for stability;
* decay: the horizon of peak |IC| and the half-life where it falls to half.

All inputs are pandas objects on the same index. NaNs are dropped pairwise.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------- returns
def forward_returns(close: pd.Series, horizons: list[int], segment: pd.Series | None = None) -> pd.DataFrame:
    """Log return from bar t to bar t+h for each h (in bars).

    ``segment`` labels contiguous blocks that a return must not cross, such as
    (contract, trading day). A return whose end bar is in a different segment
    is NaN, so no label ever spans a roll, a session gap or the 3:10 PM flat.
    """
    logp = np.log(close.astype(float))
    out = {}
    for h in horizons:
        r = logp.shift(-h) - logp
        if segment is not None:
            r = r.where(segment.shift(-h) == segment)
        out[h] = r
    return pd.DataFrame(out, index=close.index)


# -------------------------------------------------------------- statistics
def _ranks(x: pd.Series, y: pd.Series) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    df = pd.concat([x, y], axis=1).dropna()
    if len(df) < 3:
        return np.array([]), np.array([]), np.array([], dtype=int)
    pos = x.index.get_indexer(df.index)
    rx = stats.rankdata(df.iloc[:, 0].to_numpy())
    ry = stats.rankdata(df.iloc[:, 1].to_numpy())
    return rx, ry, pos


def spearman_ic(x: pd.Series, y: pd.Series) -> float:
    rx, ry, _ = _ranks(x, y)
    if len(rx) < 3 or rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def newey_west_se_of_mean(z: np.ndarray, lags: int) -> float:
    """Standard error of mean(z) with a Bartlett-kernel HAC variance."""
    n = len(z)
    u = z - z.mean()
    gamma0 = u @ u / n
    var = gamma0
    for k in range(1, min(lags, n - 1) + 1):
        w = 1.0 - k / (lags + 1.0)
        var += 2.0 * w * (u[k:] @ u[:-k]) / n
    return float(np.sqrt(max(var, 0.0) / n))


def ic_t_newey_west(x: pd.Series, y: pd.Series, lags: int) -> tuple[float, float, int]:
    """IC and its HAC t-statistic.

    Standardized ranks make the mean of their product equal the rank
    correlation; the HAC error of that mean accounts for the serial
    correlation that overlapping forward returns create.
    """
    rx, ry, _ = _ranks(x, y)
    n = len(rx)
    if n < 10 or rx.std() == 0 or ry.std() == 0:
        return float("nan"), float("nan"), n
    zx = (rx - rx.mean()) / rx.std()
    zy = (ry - ry.mean()) / ry.std()
    prod = zx * zy
    ic = float(prod.mean())
    se = newey_west_se_of_mean(prod, lags)
    return ic, ic / se if se > 0 else float("nan"), n


def ic_t_nonoverlapping(x: pd.Series, y: pd.Series, step: int) -> tuple[float, float, int]:
    """IC and plain t on every ``step``-th sample, so horizons do not overlap."""
    step = max(int(step), 1)
    xs, ys = x.iloc[::step], y.iloc[::step]
    ic = spearman_ic(xs, ys)
    n = int(pd.concat([xs, ys], axis=1).dropna().shape[0])
    if n < 10 or not np.isfinite(ic) or abs(ic) >= 1:
        return ic, float("nan"), n
    return ic, ic * np.sqrt((n - 2) / (1 - ic**2)), n


def holm(pvals: dict) -> dict:
    """Holm step-down adjusted p-values."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    out, running = {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out


def half_life(ic_by_horizon: dict) -> tuple[object, object]:
    """(peak horizon, first horizon after the peak where |IC| <= peak/2)."""
    clean = {h: v for h, v in ic_by_horizon.items() if np.isfinite(v)}
    if not clean:
        return None, None
    hs = list(clean)
    peak = max(hs, key=lambda h: abs(clean[h]))
    for h in hs[hs.index(peak) + 1:]:
        if abs(clean[h]) <= abs(clean[peak]) / 2:
            return peak, h
    return peak, None


# ----------------------------------------------------------------- report
@dataclass
class HorizonStat:
    horizon: object
    ic: float
    t_nw: float
    t_nonoverlap: float
    n: int

    @property
    def t(self) -> float:
        ts = [t for t in (self.t_nw, self.t_nonoverlap) if np.isfinite(t)]
        return min(ts, key=abs) if ts else float("nan")


@dataclass
class SignalReport:
    feature: str
    horizons: dict[object, HorizonStat]
    p_holm: dict
    slices: dict[str, dict] = field(default_factory=dict)  # slice name -> {label: {horizon: ic}}
    peak: object = None
    half_life: object = None

    def best(self, sign: int) -> HorizonStat:
        """Best horizon in the pre-registered direction."""
        return max(self.horizons.values(), key=lambda s: sign * s.t if np.isfinite(s.t) else -np.inf)

    def table(self) -> pd.DataFrame:
        rows = [
            {"horizon": s.horizon, "ic": s.ic, "t_nw": s.t_nw, "t_nonoverlap": s.t_nonoverlap,
             "t": s.t, "p_holm": self.p_holm.get(s.horizon), "n": s.n}
            for s in self.horizons.values()
        ]
        return pd.DataFrame(rows).set_index("horizon")


def signal_test(
    feature: pd.Series,
    fwd: pd.DataFrame,
    horizon_bars: dict | None = None,
    slices: dict[str, pd.Series] | None = None,
    name: str = "feature",
) -> SignalReport:
    """Run METHOD.md stage 1 on one feature.

    ``fwd`` has one column per horizon. ``horizon_bars`` maps each column to
    its length in bars (used for the overlap correction); integer columns
    are taken as their own length. ``slices`` maps a slice name (e.g. "year")
    to a label series on the same index.
    """
    horizon_bars = horizon_bars or {h: int(h) for h in fwd.columns}
    stats_by_h, pvals = {}, {}
    for h in fwd.columns:
        hb = max(int(horizon_bars[h]), 1)
        ic, t_nw, n = ic_t_newey_west(feature, fwd[h], lags=hb - 1 if hb > 1 else 0)
        _, t_no, _ = ic_t_nonoverlapping(feature, fwd[h], step=hb)
        s = HorizonStat(h, ic, t_nw, t_no, n)
        stats_by_h[h] = s
        if np.isfinite(s.t):
            pvals[h] = float(2 * stats.norm.sf(abs(s.t)))
    rep = SignalReport(name, stats_by_h, holm(pvals))
    rep.peak, rep.half_life = half_life({h: s.ic for h, s in stats_by_h.items()})
    for sname, labels in (slices or {}).items():
        rep.slices[sname] = {}
        for lab, idx in labels.groupby(labels).groups.items():
            rep.slices[sname][lab] = {h: spearman_ic(feature.loc[idx], fwd[h].loc[idx]) for h in fwd.columns}
    return rep


def passes_stage1(rep: SignalReport, sign: int, t_hurdle: float = 3.0, slice_share: float = 0.70,
                  vol_slice: str = "vol_tercile", year_slice: str = "year") -> tuple[bool, list[str]]:
    """METHOD.md section 3.4 pass rule. Returns (passed, reasons for failure)."""
    reasons = []
    best = rep.best(sign)
    if not (np.isfinite(best.t) and sign * best.t >= t_hurdle):
        reasons.append(f"best t in expected direction {best.t:.2f} < {t_hurdle}")
    if rep.p_holm.get(best.horizon, 1.0) >= 0.05:
        reasons.append("Holm-adjusted p >= 0.05")
    h = best.horizon
    if year_slice in rep.slices:
        ys = [v[h] for v in rep.slices[year_slice].values() if np.isfinite(v[h])]
        share = np.mean([np.sign(v) == sign for v in ys]) if ys else 0.0
        if share < slice_share:
            reasons.append(f"right sign in {share:.0%} of years < {slice_share:.0%}")
    if vol_slice in rep.slices:
        vs = [v[h] for v in rep.slices[vol_slice].values() if np.isfinite(v[h])]
        if sum(np.sign(v) == sign for v in vs) < 2:
            reasons.append("right sign in fewer than 2 of 3 volatility terciles")
    return (not reasons), reasons


# --------------------------------------------------------------- look-ahead
def assert_no_lookahead(feature_fn, data: pd.DataFrame, checkpoints: int = 20, seed: int = 0) -> None:
    """Fail if a feature at time t changes when data after t is removed.

    ``feature_fn(data) -> pd.Series`` on the same index. We recompute on
    truncated copies of the data at random cut points and compare the last
    value. Any feature that peeks at the future will differ.
    """
    full = feature_fn(data)
    rng = np.random.default_rng(seed)
    cuts = rng.choice(np.arange(10, len(data)), size=min(checkpoints, len(data) - 10), replace=False)
    for c in sorted(cuts):
        part = feature_fn(data.iloc[: c + 1])
        a, b = full.iloc[c], part.iloc[-1]
        if not ((pd.isna(a) and pd.isna(b)) or np.isclose(a, b, equal_nan=True)):
            raise AssertionError(f"look-ahead at {data.index[c]}: full={a!r} truncated={b!r}")
