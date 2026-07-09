"""SOP sweep: roster-delta preseason ratings, walk-forward on 2024-25 AND 2025-26.

At each season boundary the engine currently reverts every team 75/25 toward the
mean and carries on, blind to the fact that a franchise player changed teams.
This sweep adds one term:

    preseason(T,S) = 0.75*elo_end(S-1) + 0.25*1500 + K * delta(T,S)

where delta is the zero-sum, leak-free roster-talent change from
src/features/roster_delta.py (both rosters priced with season S-1 ratings and
minutes). K = 0 reproduces the deployed baseline EXACTLY, which is the
correctness check printed first.

Reports accuracy AND Brier per season (the SOP gate), plus the early-season
segment (each team's first 20 games), because that is the only place a preseason
prior can possibly help: by mid-season the ELO has seen the new roster play.

    python scripts/sweep_roster_delta.py
"""

import sys
import logging
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.disable(logging.CRITICAL)

import numpy as np
import pandas as pd

from src.engines.team_elo_engine import TeamELOEngine
from src.features.roster_delta import compute_deltas

games = pd.read_csv("data/raw/nba_games_all_vps.csv")
games = games[(games.home_score.astype(int) > 0) | (games.away_score.astype(int) > 0)]
games = games.sort_values("date").reset_index(drop=True)
pr = pd.read_csv("data/exports/player_ratings_bpm_adjusted.csv")
pm = pd.read_csv("data/exports/player_team_mapping.csv")
dates = pd.to_datetime(games.date.astype(str), format="%Y%m%d")
seasons = dates.apply(lambda d: d.year if d.month >= 10 else d.year - 1)
EVAL = {2024, 2025}
EARLY_GAMES = 20

print("computing roster deltas (leak-free, zero-sum)...")
DELTAS = compute_deltas(".")
print(f"  {len(DELTAS)} (season, team) deltas\n")


def run(K):
    e = TeamELOEngine(k_factor=20, home_advantage=60, use_mov=True,
                      use_enhanced_features=True, use_top_player_concentration=False,
                      player_ratings=pr, player_team_mapping=pm)
    e.reset_ratings()
    e.rest_tracker.b2b_penalty = 46
    e.rest_tracker.one_day_penalty = 0
    cur = None
    gp = defaultdict(int)
    rows = []
    for idx, g in games.iterrows():
        s = seasons.iloc[idx]
        if cur is not None and s != cur:
            e._apply_season_reversion(reversion_factor=0.75)
            if K != 0.0:
                for team, rating in list(e.current_ratings.items()):
                    d = DELTAS.get((s, team))
                    if d is not None:
                        e.current_ratings[team] = rating + K * d
        cur = s
        h, a = g["home_team_id"], g["away_team_id"]
        if s in EVAL:
            try:
                p = e.predict_game(h, a, game_date=g["date"])
                ph = p["home_win_probability"]
                y = 1 if int(g["home_score"]) > int(g["away_score"]) else 0
                rows.append((s, ph, y, min(gp[(s, h)], gp[(s, a)])))
            except Exception:
                pass
        gp[(s, h)] += 1
        gp[(s, a)] += 1
        e.process_game(g.to_dict())
    d = pd.DataFrame(rows, columns=["season", "p", "y", "min_gp"])
    d["correct"] = (d.p >= 0.5) == (d.y == 1)
    d["se"] = (d.p - d.y) ** 2
    return d


SWEEP = [0.0, 0.10, 0.20, 0.30, 0.40, 0.60, 0.80, 1.00]
base = None
print(f"{'K':>5} | {'2024-25 acc':>11} {'brier':>7} | {'2025-26 acc':>11} {'brier':>7} "
      f"| {'pooled acc':>10} {'brier':>7} | {'early acc':>9} {'early brier':>11}")
print("-" * 104)
results = {}
for K in SWEEP:
    d = run(K)
    results[K] = d
    if K == 0.0:
        base = d
    a24 = d[d.season == 2024]; a25 = d[d.season == 2025]
    early = d[d.min_gp < EARLY_GAMES]
    print(f"{K:>5.2f} | {a24.correct.mean()*100:>10.2f}% {a24.se.mean():>7.4f} "
          f"| {a25.correct.mean()*100:>10.2f}% {a25.se.mean():>7.4f} "
          f"| {d.correct.mean()*100:>9.2f}% {d.se.mean():>7.4f} "
          f"| {early.correct.mean()*100:>8.2f}% {early.se.mean():>11.4f}")

# correctness check: K=0 must reproduce the deployed config exactly
print()
b24 = base[base.season == 2024]; b25 = base[base.season == 2025]
print(f"K=0 check vs known deployed baseline (66.87% / 0.2133, 67.80% / 0.2089):")
print(f"  2024-25: {b24.correct.mean()*100:.2f}% / {b24.se.mean():.4f}")
print(f"  2025-26: {b25.correct.mean()*100:.2f}% / {b25.se.mean():.4f}")

best = max(SWEEP, key=lambda k: results[k].correct.mean())
bestb = min(SWEEP, key=lambda k: results[k].se.mean())
print(f"\nbest pooled accuracy: K={best}   best pooled brier: K={bestb}")
print("\nSOP gate: ships only if it does not hurt accuracy OR brier on EITHER "
      "season, and the gain survives a paired significance test.")
