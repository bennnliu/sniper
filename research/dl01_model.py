"""META-02, step 3: the losing-trade filter. Hypothesis and pass criteria are in reports/SECOND_EDGE_LOG.md
(iteration 24), committed before this file was first run.

Models score each New York high-volatility trade at its decision minute with the chance that it wins:
  logistic   logistic regression on the entry-time table                      (baseline)
  boosted    gradient-boosted trees on the same table                          (baseline)
  mlp        neural network, three hidden layers, on the same table
  cnn        neural network: 1-D convolutions over the last 60 one-minute price changes, joined with the table
             (PRIMARY: this is the deep-learning filter the hypothesis is about)
Walk-forward by calendar year: the model for year Y is trained only on trades from earlier years. Inside the
training years the last 15% of days (in time order) are held back; the networks stop training on them, and the
skip threshold is the 33rd percentile of the model's scores on them. A trade is skipped when its score is below
that threshold. Skipping means the bot does not take that position from its entry to its exit; the rule's own
bookkeeping is unchanged, so the remaining trades are exactly the logged ones.
Run: python research/dl01_model.py
"""
import os
import pickle
import sys
import warnings
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

LABELS = {
    "f_sigma_pct": "Noise width at this time of day (%)", "f_excess": "Distance past the band", "f_dist_vwap": "Distance from VWAP",
    "f_move_open": "Move from the open", "f_efficiency": "Straightness of the move since the open", "f_relvol": "Volume so far against normal",
    "f_rv20": "20-day volatility (%)", "f_gap": "Overnight gap in the trade's direction", "f_prior_pnl": "This setting's result so far today",
    "f_last30": "Move in the last 30 minutes", "f_dow": "Weekday", "check_min": "Minutes since the open", "entry_no": "Entry number today, this setting",
    "dir": "Direction (long = 1)", "lookback": "Setting: lookback", "vm": "Setting: band width",
    "g_dvol_ratio": "Expected daily move against its 250-day median", "g_on_range": "Overnight range", "g_on_ret": "Overnight move in the trade's direction",
    "g_prev_ret": "Previous day's move in the trade's direction", "g_prev_range": "Previous day's range", "g_range_sofar": "Today's range so far",
    "g_pos_in_range": "Where price sits in today's range (1 = at the extreme)", "g_first30": "First half hour's move in the trade's direction",
    "g_vol_last30": "Share of volume in the last 30 minutes", "g_es_move": "ES move from the open in the trade's direction", "g_rel_es": "NQ move minus ES move",
    "g_last5": "Move in the last 5 minutes", "g_pullback60": "Deepest pullback in the last hour", "g_time_left": "Share of the session left",
    "g_others_in": "Other settings already in, same direction", "g_enter_now": "Other settings entering now, same direction", "g_set_pnl": "All settings' closed result so far today",
}
FEATS = list(LABELS)
SKIP_Q = 1 / 3
HOLD = 0.15
MODELS = ("logistic", "boosted", "mlp", "cnn")
PRIMARY = "cnn"
FIRST_TEST_YEAR = 2016
SEEDS = (0, 1, 2)


def prep(train_X):
    med = np.nanmedian(train_X, axis=0)
    filled = np.where(np.isfinite(train_X), train_X, med)
    lo, hi = np.percentile(filled, [1, 99], axis=0)
    clipped = np.clip(filled, lo, hi)
    mu, sd = clipped.mean(axis=0), clipped.std(axis=0)
    sd = np.where(sd > 0, sd, 1.0)
    return lambda X: (np.clip(np.where(np.isfinite(X), X, med), lo, hi) - mu) / sd


def fit_predict(name, Xa, Sa, ya, Xb, Sb, yb, Xt, St):
    """Train on (a), early-stop / threshold on (b), score (b) and the test set."""
    if name == "logistic":
        from sklearn.linear_model import LogisticRegression
        m = LogisticRegression(C=0.1, max_iter=1000).fit(Xa, ya)
        return m.predict_proba(Xb)[:, 1], m.predict_proba(Xt)[:, 1]
    if name == "boosted":
        from sklearn.ensemble import HistGradientBoostingClassifier
        m = HistGradientBoostingClassifier(max_depth=3, max_iter=200, learning_rate=0.03, min_samples_leaf=40, l2_regularization=1.0, random_state=0).fit(Xa, ya)
        return m.predict_proba(Xb)[:, 1], m.predict_proba(Xt)[:, 1]
    import tensorflow as tf
    from tensorflow import keras as K
    pb, pt = [], []
    for seed in SEEDS:
        K.utils.set_random_seed(seed)
        reg = K.regularizers.l2(1e-4)
        tab = K.Input((Xa.shape[1],))
        h = tab
        if name == "cnn":
            sq = K.Input((Sa.shape[1], 1))
            c = K.layers.Conv1D(16, 5, activation="relu", padding="same", kernel_regularizer=reg)(sq)
            c = K.layers.MaxPooling1D(2)(c)
            c = K.layers.Conv1D(16, 5, activation="relu", padding="same", kernel_regularizer=reg)(c)
            c = K.layers.GlobalAveragePooling1D()(c)
            h = K.layers.Concatenate()([tab, c])
        for units in (64, 32, 16):
            h = K.layers.Dense(units, activation="relu", kernel_regularizer=reg)(h)
            h = K.layers.Dropout(0.3)(h)
        outp = K.layers.Dense(1, activation="sigmoid")(h)
        model = K.Model([tab, sq] if name == "cnn" else tab, outp)
        model.compile(K.optimizers.Adam(1e-3), "binary_crossentropy")
        ins = (lambda X, S: [X, S[..., None]]) if name == "cnn" else (lambda X, S: X)
        model.fit(ins(Xa, Sa), ya, validation_data=(ins(Xb, Sb), yb), epochs=80, batch_size=128, verbose=0,
                  callbacks=[K.callbacks.EarlyStopping(patience=8, restore_best_weights=True)])
        pb.append(model.predict(ins(Xb, Sb), verbose=0).ravel()); pt.append(model.predict(ins(Xt, St), verbose=0).ravel())
        K.backend.clear_session()
    return np.mean(pb, axis=0), np.mean(pt, axis=0)


def walk_forward(t, seq, models=MODELS):
    """Adds score_<model> and keep_<model> columns to the high-volatility trades of every test year and the
    walk-forward year. Returns the scored frame."""
    t = t[t.regime == "high"].copy()
    S = np.clip(seq[t["tid"].to_numpy()], -5, 5)
    t = t.reset_index(drop=True)
    X = t[FEATS].to_numpy(float); y = t["win"].to_numpy()
    year = t["day"].dt.year.to_numpy(); isdev = (t["period"] == "dev").to_numpy()
    folds = [(f"{yv}", isdev & (year < yv), isdev & (year == yv)) for yv in sorted(set(year[isdev])) if yv >= FIRST_TEST_YEAR]
    folds.append(("wf", isdev, ~isdev))
    for name in models:
        t[f"score_{name}"] = np.nan; t[f"keep_{name}"] = np.nan
    for lab, tr, te in folds:
        days = np.sort(t.loc[tr, "day"].unique())
        cut = days[int(len(days) * (1 - HOLD))]
        a = tr & (t["day"] < cut).to_numpy(); b = tr & (t["day"] >= cut).to_numpy()
        f = prep(X[a])
        for name in models:
            sb, st_ = fit_predict(name, f(X[a]), S[a], y[a], f(X[b]), S[b], y[b], f(X[te]), S[te])
            thr = np.quantile(sb, SKIP_Q)
            t.loc[te, f"score_{name}"] = st_; t.loc[te, f"keep_{name}"] = (st_ >= thr).astype(float)
        print("fold", lab, "train", int(a.sum()), "held back", int(b.sum()), "test", int(te.sum()), flush=True)
    return t[t[f"score_{models[0]}"].notna()].copy()


def main():
    d = pickle.load(open(ROOT / "data/cache/dl01.pkl", "rb"))
    scored = walk_forward(d["trades"], d["seq"])
    scored.to_pickle(ROOT / "data/cache/dl01_scored.pkl")
    from sklearn.metrics import roc_auc_score
    for name in MODELS:
        for p in ("dev", "wf"):
            g = scored[scored.period == p]
            k = g[f"keep_{name}"] == 1
            print(f"{name:9s} {p:3s} AUC {roc_auc_score(g.win, g[f'score_{name}']):.3f} kept {k.mean():.2f} kept avg pts {g.net_pts[k].mean():7.2f} skipped avg pts {g.net_pts[~k].mean():7.2f}")


if __name__ == "__main__":
    main()
