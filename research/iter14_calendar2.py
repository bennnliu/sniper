"""Iteration 14: CYCLE-01 (FOMC-cycle even weeks) and HOL-01 (pre-holiday days). Hypotheses in reports/SECOND_EDGE_LOG.md.
Development data only. Run: python research/iter14_calendar2.py"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.tseries.holiday import (AbstractHolidayCalendar, GoodFriday, Holiday, USLaborDay, USMartinLutherKingJr,
                                    USMemorialDay, USPresidentsDay, USThanksgivingDay, nearest_workday)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.iter12_second_edge import MICRO, news, stats  # noqa: E402
from research.iter13_tests import bars, stream  # noqa: E402
from sniper.data import DEV_END  # noqa: E402
from sniper.session_rule import build_session, hold  # noqa: E402


class Mkt(AbstractHolidayCalendar):
    rules = [Holiday("NY", month=1, day=1, observance=nearest_workday), USMartinLutherKingJr, USPresidentsDay, GoodFriday, USMemorialDay,
             Holiday("Juneteenth", month=6, day=19, start_date="2022-01-01", observance=nearest_workday),
             Holiday("July4", month=7, day=4, observance=nearest_workday), USLaborDay, USThanksgivingDay,
             Holiday("Xmas", month=12, day=25, observance=nearest_workday)]


def cycle_day(days):
    ev = pd.read_csv(ROOT / "calendar_data" / "events.csv", parse_dates=["date"])
    fomc = np.sort(ev[ev.event == "FOMC"]["date"].to_numpy())
    wd = pd.bdate_range("2010-01-01", "2026-12-31")  # weekdays, holidays keep their slot (as in the paper)
    pos = pd.Series(np.arange(len(wd)), index=wd)
    fpos = pos.reindex(pd.DatetimeIndex(fomc)).dropna().to_numpy()
    out = []
    for d in days:
        p = pos.get(d)
        j = np.searchsorted(fpos, p + 1, side="right") - 1  # last meeting with position <= p+1 (day -1 belongs to the new cycle)
        out.append(np.nan if j < 0 else p - fpos[j])
    return pd.Series(out, index=days)


def main():
    skip = news()
    res, streams = [], {}
    for sym in ("ES", "NQ"):
        name = MICRO[sym][0]
        df = bars(sym, DEV_END)
        for w in ("NY", "OVERNIGHT"):
            sd = build_session(df, w)
            cd = cycle_day(sd.days)
            week = np.floor((cd + 1) / 5)
            even = (week % 2 == 0) & (week <= 6)
            odd = (week % 2 == 1) & (week <= 6)
            hol = Mkt().holidays("2010-01-01", "2026-12-31")
            nxt = pd.Series(sd.days, index=sd.days).shift(-1)
            gap = pd.Series([len(pd.bdate_range(a, b)) - 1 if pd.notna(b) else 1 for a, b in zip(sd.days, nxt)], index=sd.days)
            nextwd = sd.days + pd.offsets.BDay(1)
            pre = pd.Series(nextwd.isin(hol), index=sd.days)
            for label, mask in ((f"CYCLE-01 even weeks, {w}", even), (f"CYCLE-01 odd weeks, {w} (control)", odd), (f"HOL-01 pre-holiday, {w}", pre)):
                dd = hold(sd, mask.astype(float), MICRO[sym][2], skip)
                r = stats(dd, sym, label)
                res.append(r); streams[f"{label}|{name}"] = dd
                print(f"{label:38s} {name}: n {r['n']:4d} mean {r['mean_pts']:+7.2f} pts (gross {r['gross_x_cost']:5.1f}x cost) ${r['usd_per_micro']:+6.2f} t {r['t']:+5.2f} "
                      f"yrs+ {r['years_pos']:.2f} | to2017 {r['t_to_2017']:+.2f} 2018on {r['t_2018_on']:+.2f} | vol {r['t_by_vol']} {'PASS' if r['passes'] else ''}")
            e, o = streams[f"CYCLE-01 even weeks, {w}|{name}"], streams[f"CYCLE-01 odd weeks, {w} (control)|{name}"]
            ve = (e.net_pts / e.dvol_pts)[e.round_trips > 0].dropna(); vo = (o.net_pts / o.dvol_pts)[o.round_trips > 0].dropna()
            td = (ve.mean() - vo.mean()) / np.sqrt(ve.var() / len(ve) + vo.var() / len(vo))
            print(f"   even minus odd, {w} {name}: {ve.mean() - vo.mean():+.4f} daily-move units, t {td:+.2f}")
            res.append({"test": f"even-odd {w}", "symbol": name, "diff": float(ve.mean() - vo.mean()), "t": float(td)})
    b = stream(DEV_END, skip)
    for k in ("CYCLE-01 even weeks, NY|MNQ", "CYCLE-01 even weeks, OVERNIGHT|MNQ"):
        j = pd.concat([b.net_pts.rename("b"), streams[k].net_pts.rename("x")], axis=1).dropna()
        print(f"correlation of daily results, breakout vs {k}: {j.corr().iloc[0, 1]:+.3f}")
    (ROOT / "reports/iter_14.json").write_text(json.dumps(res, indent=1, default=float))
    pickle.dump(streams, open(ROOT / "data/iter14_streams.pkl", "wb"))


if __name__ == "__main__":
    main()
