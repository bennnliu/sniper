"""Dashboard run 1: rerun ENS-01 (nine-setting NQ breakout ensemble) with a full trade log.
No new hypothesis; this reproduces iteration 20 and adds descriptive statistics. Writes data/cache/dash01.pkl.
Period: development (to 31 Oct 2024) and the walk-forward year (to 31 Oct 2025, already used). Holdout not loaded."""
import pickle
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.iter13_tests import bars, news  # noqa: E402
from sniper.data import WALK_FORWARD_END  # noqa: E402
from sniper.ensemble import run_ensemble  # noqa: E402
from sniper.session_rule import build_session  # noqa: E402

COST = 1.11


def main():
    skip = news()
    nq = bars("NQ", WALK_FORWARD_END)
    out = {}
    for sess in ("NY", "ASIA", "LONDON"):
        sd = build_session(nq, sess)
        t0 = time.time()
        out[sess, "skip", 1] = run_ensemble(sd, COST, skip)
        print(sess, "skip-news", round(time.time() - t0, 1), "s", len(out[sess, "skip", 1][0]), "trades")
        if sess == "NY":
            out[sess, "skip", 2] = run_ensemble(sd, 2 * COST, skip)
            out[sess, "all", 1] = run_ensemble(sd, COST, None)
            out[sess, "all", 2] = run_ensemble(sd, 2 * COST, None)
            # minute prices for the days traded, for intraday curves
            out["px"] = {"days": sd.days, "px": sd.px}
    pickle.dump(out, open(ROOT / "data/cache/dash01.pkl", "wb"))


if __name__ == "__main__":
    main()
