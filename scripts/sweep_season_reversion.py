"""Sweep the season-reversion factor. Motivated by a real diagnostic, not a hunch.

Team-season residuals (actual wins minus what the rating predicted) are
NEGATIVELY autocorrelated across seasons: corr(resid_S, resid_S+1) = -0.106,
p=0.0038, with a shuffled-label placebo at zero. Teams that beat their rating one
year miss it the next. That is the signature of an ELO that carries too much of
last season forward, i.e. of under-reverting at the season boundary.

The deployed factor is 0.75 (75% prior + 25% mean). It has never been swept.

Selection is done on TRAINING seasons only (< 2024); the two SOP seasons are held
out and only scored at the chosen value, so this cannot be test-set selection.

    python scripts/sweep_season_reversion.py
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.disable(logging.CRITICAL)

import numpy as np
import pandas as pd

from src.engines.team_elo_engine import TeamELOEngine

games = pd.read_csv("data/raw/nba_games_all.csv")
games = games[(games.home_score > 0) | (games.away_score > 0)].sort_values("date").reset_index(drop=True)
pr = pd.read_csv("data/exports/player_ratings_bpm_adjusted.csv")
pm = pd.read_csv("data/exports/player_team_mapping.csv")
dates = pd.to_datetime(games.date.astype(str), format="%Y%m%d")
seasons = dates.dt.year.where(dates.dt.month >= 10, dates.dt.year - 1)

TRAIN = set(range(2005, 2024))
EVAL = {2024, 2025}
GRID = [0.20, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.75]


def run(rev):
    e = TeamELOEngine(k_factor=20, home_advantage=60, use_mov=True,
                      use_enhanced_features=True, use_top_player_concentration=False,
                      player_ratings=pr, player_team_mapping=pm)
    e.reset_ratings()
    e.rest_tracker.b2b_penalty = 46
    e.rest_tracker.one_day_penalty = 0
    cur, rows = None, []
    for idx, g in games.iterrows():
        s = seasons.iloc[idx]
        if cur is not None and s != cur:
            e._apply_season_reversion(reversion_factor=rev)
        cur = s
        if s in TRAIN or s in EVAL:
            try:
                p = e.predict_game(g["home_team_id"], g["away_team_id"], game_date=g["date"])
                rows.append((s, g["game_id"], p["home_win_probability"],
                             1 if int(g["home_score"]) > int(g["away_score"]) else 0))
            except Exception:
                pass
        e.process_game(g.to_dict())
    return pd.DataFrame(rows, columns=["season", "game_id", "p", "y"]).set_index("game_id")


res = {}
print(f"{'reversion':>10} | {'TRAIN acc':>10} {'TRAIN brier':>12} | {'eval acc':>9} {'eval brier':>11}")
print("-" * 64)
for rev in GRID:
    d = run(rev)
    res[rev] = d
    tr = d[d.season.isin(TRAIN)]
    ev = d[d.season.isin(EVAL)]
    ta = ((tr.p >= 0.5) == (tr.y == 1)).mean(); tb = ((tr.p - tr.y) ** 2).mean()
    ea = ((ev.p >= 0.5) == (ev.y == 1)).mean(); eb = ((ev.p - ev.y) ** 2).mean()
    star = "  <- deployed" if rev == 0.75 else ""
    print(f"{rev:>10.2f} | {ta*100:>9.2f}% {tb:>12.5f} | {ea*100:>8.2f}% {eb:>11.5f}{star}")

best_b = min(GRID, key=lambda r: ((res[r][res[r].season.isin(TRAIN)].p -
                                   res[r][res[r].season.isin(TRAIN)].y) ** 2).mean())
best_a = max(GRID, key=lambda r: (((res[r][res[r].season.isin(TRAIN)].p >= 0.5) ==
                                   (res[r][res[r].season.isin(TRAIN)].y == 1)).mean()))
print(f"\nTRAINING picks (eval seasons never consulted): best brier {best_b}, best accuracy {best_a}")
print("Score the chosen value on the held-out SOP seasons with scripts/qa_season_reversion.py")

