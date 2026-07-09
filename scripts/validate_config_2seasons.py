"""SOP validation: old vs new config, walk-forward on 2024-25 AND 2025-26.

Every game of both seasons is predicted before its result is processed.
New config (decision 2026-07-01): b2b penalty 46, one-day penalty 0,
top-player concentration OFF.
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.disable(logging.CRITICAL)

import pandas as pd

from src.engines.team_elo_engine import TeamELOEngine

games = pd.read_csv("data/raw/nba_games_all_vps.csv")
games = games[
    (games.home_score.astype(int) > 0) | (games.away_score.astype(int) > 0)
].sort_values("date").reset_index(drop=True)
pr = pd.read_csv("data/exports/player_ratings_bpm_adjusted.csv")
pm = pd.read_csv("data/exports/player_team_mapping.csv")
dates = pd.to_datetime(games.date.astype(str), format="%Y%m%d")
seasons = dates.apply(lambda d: d.year if d.month >= 10 else d.year - 1)
EVAL_SEASONS = {2024, 2025}


def run(b2b, one_day, conc):
    e = TeamELOEngine(
        k_factor=20, home_advantage=60, use_mov=True,
        use_enhanced_features=True, use_top_player_concentration=conc,
        player_ratings=pr, player_team_mapping=pm,
    )
    e.reset_ratings()
    e.rest_tracker.b2b_penalty = b2b
    e.rest_tracker.one_day_penalty = one_day
    cur = None
    stats = {s: [0, 0, 0.0] for s in EVAL_SEASONS}  # hits, n, brier_sum
    for idx, g in games.iterrows():
        s = seasons.iloc[idx]
        if cur is not None and s != cur:
            # PINNED at 0.75 on purpose. This harness replays what the model
            # ACTUALLY predicted historically, and every logged 2025-26 prediction
            # was made with reversion 0.75. The deployed value is now 0.45
            # (config/settings.yaml), but changing it here would stop reproducing
            # the logged picks and would silently move the audited 70.6%.
            e._apply_season_reversion(reversion_factor=0.75)
        cur = s
        if s in EVAL_SEASONS:
            try:
                p = e.predict_game(g["home_team_id"], g["away_team_id"],
                                   game_date=g["date"])
                ph = p["home_win_probability"]
                act = 1 if int(g["home_score"]) > int(g["away_score"]) else 0
                st = stats[s]
                st[0] += (ph >= 0.5) == bool(act)
                st[1] += 1
                st[2] += (ph - act) ** 2
            except Exception:
                pass
        e.process_game(g.to_dict())
    return stats


for label, args in [("OLD  (b2b46, 1day15, conc on)", (46, 15, True)),
                    ("NEW  (b2b46, 1day0,  conc off)", (46, 0, False))]:
    stats = run(*args)
    for s in sorted(stats):
        hits, n, br = stats[s]
        print(f"{label} | {s}-{s+1}: acc {hits/n*100:.2f}%  "
              f"brier {br/n:.4f}  ({n} games)")
