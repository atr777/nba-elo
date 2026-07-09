"""Fit rookie priors as a function of draft position.

roster_delta prices a player with no NBA history at a flat (1450 rating, 12 mpg).
That is wrong in two ways, both visible in our own data:

  * 1450 sits well below the actual rookie mean end-of-season rating (~1479).
  * The real draft signal is MINUTES, not rating. Top-3 picks average 27.3 mpg;
    picks 46-61 average 9.3. Their end-of-rookie ratings run BACKWARDS
    (1466 for top-3 vs 1493 for late seconds), because our player ELO moves in
    proportion to minutes: a lottery pick logging heavy below-average rookie
    minutes falls further than a bench guy logging nine.

So the prior mostly needs to set the ROLE WEIGHT correctly.

Fit is deliberately restricted to rookie seasons <= FIT_THROUGH so that the
rolling out-of-sample validation window (2013-2025) never informs the curve.

    python scripts/fit_rookie_priors.py
"""

import json
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

HISTORY = "data/exports/player_elo_history_bpm.csv"
DRAFT = "data/raw/draft_history.csv"
OUT = Path("config/rookie_priors.json")

FIT_FROM = 2001          # our box-score history starts in 2000
FIT_THROUGH = 2012       # everything after this is held out for validation
MAX_MPG = 38.0


def norm(s):
    if not isinstance(s, str):
        return ""
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return s.lower().strip()


def rookie_table():
    h = pd.read_csv(HISTORY, usecols=["date", "player_name", "minutes", "rating_after"])
    dt = pd.to_datetime(h.date.astype(str), format="%Y%m%d")
    h["season"] = dt.dt.year.where(dt.dt.month >= 10, dt.dt.year - 1)
    h["dt"] = dt
    h["key"] = h.player_name.map(norm)
    h["minutes"] = pd.to_numeric(h.minutes, errors="coerce").fillna(0.0)

    first = h.groupby("key").season.min().rename("first_season")
    h = h.join(first, on="key")
    rook = h[h.season == h.first_season]

    end = rook.sort_values("dt").groupby("key").rating_after.last().rename("rook_rating")
    g = rook.groupby("key").minutes.agg(["sum", "size"])
    mpg = (g["sum"] / g["size"]).clip(upper=MAX_MPG).rename("rook_mpg")
    return pd.concat([end, mpg, first], axis=1).reset_index()


def main():
    r = rookie_table()
    d = pd.read_csv(DRAFT)
    d["key"] = d.PLAYER_NAME.map(norm)
    d["SEASON"] = pd.to_numeric(d.SEASON, errors="coerce")
    d = d.dropna(subset=["SEASON", "OVERALL_PICK"])

    m = r.merge(d[["key", "SEASON", "OVERALL_PICK"]], on="key", how="left")
    m = m[(m.first_season >= FIT_FROM)]
    drafted = m[(m.SEASON == m.first_season)].copy()      # drafted, and this is his rookie year
    undrafted = m[m.SEASON.isna()]

    fit = drafted[drafted.first_season <= FIT_THROUGH]
    und_fit = undrafted[undrafted.first_season <= FIT_THROUGH]
    print(f"fit window {FIT_FROM}-{FIT_THROUGH}: {len(fit)} drafted rookies, "
          f"{len(und_fit)} undrafted")
    print(f"held out  {FIT_THROUGH+1}+       : {len(drafted)-len(fit)} drafted rookies\n")

    x = np.log(fit.OVERALL_PICK.values.astype(float))
    # rating ~ a + b*log(pick)   |   mpg ~ c + d*log(pick)
    b_r, a_r = np.polyfit(x, fit.rook_rating.values, 1)
    b_m, a_m = np.polyfit(x, fit.rook_mpg.values, 1)

    def pred_rating(p):
        return float(a_r + b_r * np.log(max(1, p)))

    def pred_mpg(p):
        return float(np.clip(a_m + b_m * np.log(max(1, p)), 3.0, MAX_MPG))

    params = {
        "fit_window": [FIT_FROM, FIT_THROUGH],
        "n_drafted": int(len(fit)),
        "rating": {"intercept": float(a_r), "log_pick_coef": float(b_r)},
        "mpg": {"intercept": float(a_m), "log_pick_coef": float(b_m)},
        "undrafted": {
            "rating": float(und_fit.rook_rating.mean()) if len(und_fit) else 1490.0,
            "mpg": float(und_fit.rook_mpg.clip(upper=MAX_MPG).mean()) if len(und_fit) else 8.0,
        },
        "note": "Fitted on rookie seasons <= FIT_THROUGH so the 2013-2025 rolling "
                "OOS validation window never informs the curve.",
    }

    print("fitted curves (log-pick):")
    print(f"  rating = {a_r:.1f} {b_r:+.2f} * ln(pick)")
    print(f"  mpg    = {a_m:.2f} {b_m:+.2f} * ln(pick)")
    print(f"  undrafted: rating {params['undrafted']['rating']:.1f}, "
          f"mpg {params['undrafted']['mpg']:.1f}")
    print(f"  current flat prior: rating 1450.0, mpg 12.0\n")

    print(f"{'pick':>6} {'pred rating':>12} {'pred mpg':>9}   |  held-out actual (rating / mpg)")
    for p in (1, 3, 5, 10, 20, 30, 45, 58):
        ho = drafted[(drafted.first_season > FIT_THROUGH) &
                     (drafted.OVERALL_PICK.between(max(1, p - 2), p + 2))]
        act = (f"{ho.rook_rating.mean():.1f} / {ho.rook_mpg.mean():.1f} (n={len(ho)})"
               if len(ho) >= 5 else "n/a")
        print(f"{p:>6} {pred_rating(p):>12.1f} {pred_mpg(p):>9.1f}   |  {act}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(params, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
