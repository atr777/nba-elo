"""Leak-free prediction tracking (rebuild of auto_track_predictions.py).

The old tracker predicted COMPLETED games using ratings computed from all
completed games — so each game's own result leaked into the ratings that
"predicted" it, inflating accuracy (73.5% -> honest 70.6%).

This logs predictions BEFORE games are played and grades them after:

  reconcile()        grade any pending predictions whose games are now final,
                     appending honest rows to prediction_tracking.csv
  predict_pending()  log a locked prediction for each of today's scheduled
                     games (scores still 0-0, so the engine cannot see the
                     outcome), into pending_predictions.csv, once per game

Run daily (reconcile then log). Because the engine drops 0-0 games from rating
computation, a scheduled game's own result can never be in the ratings that
predict it. No leakage, by construction.

Config matches the deployed model (k=20, home advantage 60, MOV on, b2b 46,
one-day 0, top-player concentration OFF).
"""

import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd

from src.utils.file_io import load_csv_to_dataframe, load_yaml, get_config_path
from src.engines.team_elo_engine import TeamELOEngine, deployed_config
from src.utils.elo_math import elo_diff_to_expected_margin

GAMES_FILE = "data/raw/nba_games_all.csv"
TRACKING_FILE = Path("data/exports/prediction_tracking.csv")
PENDING_FILE = Path("data/exports/pending_predictions.csv")

PRED_COLS = [
    "game_id", "date", "timestamp", "home_team_id", "away_team_id",
    "home_team_name", "away_team_name", "predicted_winner",
    "predicted_home_prob", "predicted_away_prob", "confidence", "elo_diff",
    "is_close_game", "is_toss_up", "home_back_to_back", "away_back_to_back",
    "rest_fatigue_active", "close_game_enhancement_active", "momentum_active",
    "home_momentum_adjustment", "away_momentum_adjustment", "home_elo",
    "away_elo", "predicted_home_score", "predicted_away_score",
    "predicted_margin",
]
ACTUAL_COLS = ["actual_winner", "actual_home_score", "actual_away_score",
               "correct", "margin_of_victory", "upset"]


def log(msg):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}")


def _score_cfg():
    try:
        c = load_yaml(get_config_path("score_model.yaml")).get("score_model", {})
        return (c.get("coefficient", 0.034507), c.get("intercept", 2.8437),
                c.get("league_avg_ppg", 114.15))
    except Exception:
        return 0.034507, 2.8437, 114.15


def _roster_delta_config():
    """(deltas, k, start_season) from settings.yaml. All-off if disabled/absent.

    start_season guards this to the 2026-27 boundary, so it is a no-op today and
    the historical replay stays identical to every rating we have published.
    """
    try:
        cfg = load_yaml(get_config_path("settings.yaml")).get("roster_delta", {})
        if not cfg.get("enabled"):
            return {}, 0.0, None
        df = pd.read_csv(cfg.get("deltas_file", "data/exports/roster_deltas.csv"))
        deltas = {(int(s), int(t)): float(d)
                  for s, t, d in zip(df.season, df.team_id, df.delta)}
        return deltas, float(cfg.get("k", 0.0)), cfg.get("start_season")
    except Exception as e:
        log(f"[WARN] roster_delta disabled ({e})")
        return {}, 0.0, None


def build_engine(games):
    """Ratings from COMPLETED games only (compute_season_elo drops 0-0 rows)."""
    pr = load_csv_to_dataframe("data/exports/player_ratings_bpm_adjusted.csv")
    pm = load_csv_to_dataframe("data/exports/player_team_mapping.csv")
    deltas, k, start = _roster_delta_config()
    engine = TeamELOEngine(
        player_ratings=pr, player_team_mapping=pm,
        roster_deltas=deltas, roster_delta_k=k, roster_delta_start_season=start,
        **deployed_config())
    engine.compute_season_elo(games, reset=True)
    return engine


def game_id(row):
    return f"{row['date']}_{row['home_team_id']}_{row['away_team_id']}"


def predict_row(engine, game, coef, intc, league_avg):
    """A locked pre-game prediction (no actual result)."""
    p = engine.predict_game(game["home_team_id"], game["away_team_id"],
                            game_date=game["date"])
    hp = p["home_win_probability"]
    ap = 1 - hp
    winner = "home" if hp > 0.5 else "away"
    conf = hp if hp > 0.5 else ap
    diff = p.get("home_rating", 0) - p.get("away_rating", 0)
    margin = elo_diff_to_expected_margin(diff, coefficient=coef, intercept=intc)
    return {
        "game_id": game_id(game), "date": int(game["date"]),
        "timestamp": datetime.now().isoformat(),
        "home_team_id": game["home_team_id"], "away_team_id": game["away_team_id"],
        "home_team_name": game.get("home_team_name", ""),
        "away_team_name": game.get("away_team_name", ""),
        "predicted_winner": winner, "predicted_home_prob": hp,
        "predicted_away_prob": ap, "confidence": conf, "elo_diff": diff,
        "is_close_game": abs(diff) < 100, "is_toss_up": abs(hp - 0.5) < 0.1,
        "home_back_to_back": False, "away_back_to_back": False,
        "rest_fatigue_active": True,
        "close_game_enhancement_active": abs(diff) < 100, "momentum_active": True,
        "home_momentum_adjustment": p.get("home_form_adjustment", 0),
        "away_momentum_adjustment": p.get("away_form_adjustment", 0),
        "home_elo": p.get("home_rating", 0), "away_elo": p.get("away_rating", 0),
        "predicted_home_score": max(70, round(league_avg + margin / 2)),
        "predicted_away_score": max(70, round(league_avg - margin / 2)),
        "predicted_margin": round(margin, 1),
    }


def _load(path):
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def predict_pending(today_int=None, games=None):
    """Log locked predictions for today's still-unplayed games (once each)."""
    if today_int is None:
        today_int = int(datetime.now().strftime("%Y%m%d"))
    if games is None:
        games = load_csv_to_dataframe(GAMES_FILE)

    scheduled = games[
        (games["date"] == today_int)
        & (games["home_score"].astype(int) == 0)
        & (games["away_score"].astype(int) == 0)
    ].copy()

    pending, tracked = _load(PENDING_FILE), _load(TRACKING_FILE)
    known = set(pending["game_id"]) if len(pending) else set()
    known |= set(tracked["game_id"]) if len(tracked) else set()
    todo = [g for _, g in scheduled.iterrows() if game_id(g) not in known]
    if not todo:
        log(f"No new games to log for {today_int}")
        return 0

    engine = build_engine(games)
    coef, intc, avg = _score_cfg()
    rows = [predict_row(engine, g, coef, intc, avg) for g in todo]
    out = pd.concat([pending, pd.DataFrame(rows)], ignore_index=True)
    out.to_csv(PENDING_FILE, index=False)
    log(f"Logged {len(rows)} pre-game predictions to pending")
    return len(rows)


def reconcile(games=None):
    """Grade pending predictions whose games are now final; append to tracking."""
    pending = _load(PENDING_FILE)
    if pending.empty:
        log("No pending predictions to reconcile")
        return 0
    if games is None:
        games = load_csv_to_dataframe(GAMES_FILE)
    tracked = _load(TRACKING_FILE)
    tracked_ids = set(tracked["game_id"]) if len(tracked) else set()

    finals = games[(games["home_score"].astype(int) > 0)
                   | (games["away_score"].astype(int) > 0)].copy()
    finals["game_id"] = finals.apply(game_id, axis=1)
    finals = finals.set_index("game_id")

    graded, still = [], []
    for _, p in pending.iterrows():
        gid = p["game_id"]
        if gid in finals.index and gid not in tracked_ids:
            g = finals.loc[gid]
            hs, as_ = int(g["home_score"]), int(g["away_score"])
            actual = "home" if hs > as_ else "away"
            correct = bool(p["predicted_winner"] == actual)
            row = p.to_dict()
            row.update({
                "actual_winner": actual, "actual_home_score": hs,
                "actual_away_score": as_, "correct": correct,
                "margin_of_victory": abs(hs - as_),
                "upset": bool(p["confidence"] > 0.6 and not correct),
            })
            graded.append(row)
        elif gid not in tracked_ids:
            still.append(p.to_dict())

    if graded:
        new = pd.DataFrame(graded)
        combined = pd.concat([tracked, new], ignore_index=True) if len(tracked) \
            else new
        combined.to_csv(TRACKING_FILE, index=False)
    pd.DataFrame(still, columns=PRED_COLS).to_csv(PENDING_FILE, index=False)
    log(f"Graded {len(graded)} games; {len(still)} still pending")
    return len(graded)


def main():
    log("Pre-game tracking: reconcile then log")
    reconcile()
    predict_pending()


if __name__ == "__main__":
    main()
