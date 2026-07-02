"""Honest walk-forward ablations on the 657 tracked 2025-26 games.

Measures the real (leak-free) value of each feature so improvement work is
ranked by evidence, not vibes.
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.disable(logging.CRITICAL)

import pandas as pd

from src.engines.team_elo_engine import TeamELOEngine

tracked = pd.read_csv("data/exports/prediction_tracking_vps_final.csv")
tids = set(f"{r.date}_{r.home_team_id}_{r.away_team_id}" for r in tracked.itertuples())
games = pd.read_csv("data/raw/nba_games_all_vps.csv")
games = games[
    (games.home_score.astype(int) > 0) | (games.away_score.astype(int) > 0)
].sort_values("date").reset_index(drop=True)
pr = pd.read_csv("data/exports/player_ratings_bpm_adjusted.csv")
pm = pd.read_csv("data/exports/player_team_mapping.csv")
dates = pd.to_datetime(games.date.astype(str), format="%Y%m%d")
seasons = dates.apply(lambda d: d.year if d.month >= 10 else d.year - 1)


def run(b2b=46, one_day=15, form=True, conc=True, reversion=0.75):
    e = TeamELOEngine(
        k_factor=20,
        home_advantage=60,
        use_mov=True,
        use_enhanced_features=True,
        use_top_player_concentration=conc,
        player_ratings=pr,
        player_team_mapping=pm,
    )
    e.reset_ratings()
    e.rest_tracker.b2b_penalty = b2b
    e.rest_tracker.one_day_penalty = one_day
    if not form:
        e.form_tracker.get_form_adjustment = lambda t: 0.0
    cur = None
    hits = 0
    n = 0
    for idx, g in games.iterrows():
        s = seasons.iloc[idx]
        if cur is not None and s != cur and reversion is not None:
            e._apply_season_reversion(reversion_factor=reversion)
        cur = s
        gid = f"{g['date']}_{g['home_team_id']}_{g['away_team_id']}"
        if gid in tids:
            p = e.predict_game(g["home_team_id"], g["away_team_id"], game_date=g["date"])
            pick = "home" if p["home_win_probability"] >= 0.5 else "away"
            act = "home" if int(g["home_score"]) > int(g["away_score"]) else "away"
            hits += pick == act
            n += 1
        e.process_game(g.to_dict())
    return hits / n * 100, n


if __name__ == "__main__":
    variants = [
        ("baseline (all on)", {}),
        ("no rest penalties", {"b2b": 0, "one_day": 0}),
        ("b2b only (no 1-day penalty)", {"one_day": 0}),
        ("no form", {"form": False}),
        ("no player concentration", {"conc": False}),
        ("no season reversion", {"reversion": None}),
    ]
    for label, kw in variants:
        acc, n = run(**kw)
        print(f"{label}: {acc:.2f}%  ({n} games)")
