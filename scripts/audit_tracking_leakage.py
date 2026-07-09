"""Audit the 2025-26 tracked accuracy for look-ahead leakage.

auto_track_predictions.py predicts past games using ratings computed from ALL
completed games, including the game being predicted. This script replays the
season walk-forward (predict each tracked game BEFORE processing its result)
to measure the honest accuracy on the exact same 657 games.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src.engines.team_elo_engine import TeamELOEngine


def main() -> None:
    tracked = pd.read_csv("data/exports/prediction_tracking_vps_final.csv")
    tracked_ids = set(
        f"{r.date}_{r.home_team_id}_{r.away_team_id}" for r in tracked.itertuples()
    )
    games = pd.read_csv("data/raw/nba_games_all_vps.csv")
    games = games[
        (games["home_score"].astype(int) > 0) | (games["away_score"].astype(int) > 0)
    ].copy()
    games = games.sort_values("date").reset_index(drop=True)

    player_ratings = pd.read_csv("data/exports/player_ratings_bpm_adjusted.csv")
    player_team_mapping = pd.read_csv("data/exports/player_team_mapping.csv")

    engine = TeamELOEngine(
        k_factor=20,
        home_advantage=60,
        use_mov=True,
        use_enhanced_features=True,
        use_top_player_concentration=True,
        player_ratings=player_ratings,
        player_team_mapping=player_team_mapping,
    )
    engine.reset_ratings()

    dates = pd.to_datetime(games["date"].astype(str), format="%Y%m%d", errors="coerce")
    season_years = dates.apply(lambda d: d.year if d.month >= 10 else d.year - 1)

    current_season_year = None
    rows = []
    for idx, game in games.iterrows():
        game_season = season_years.iloc[idx]
        if current_season_year is not None and game_season != current_season_year:
            # PINNED at 0.75 on purpose. This harness replays what the model
            # ACTUALLY predicted historically, and every logged 2025-26 prediction
            # was made with reversion 0.75. The deployed value is now 0.45
            # (config/settings.yaml), but changing it here would stop reproducing
            # the logged picks and would silently move the audited 70.6%.
            engine._apply_season_reversion(reversion_factor=0.75)
        current_season_year = game_season

        gid = f"{game['date']}_{game['home_team_id']}_{game['away_team_id']}"
        if gid in tracked_ids:
            try:
                pred = engine.predict_game(
                    home_team_id=game["home_team_id"],
                    away_team_id=game["away_team_id"],
                    game_date=game["date"],
                )
                p_home = pred["home_win_probability"]
                pick = "home" if p_home >= 0.5 else "away"
                actual = (
                    "home"
                    if int(game["home_score"]) > int(game["away_score"])
                    else "away"
                )
                rows.append(
                    {
                        "game_id": gid,
                        "date": game["date"],
                        "honest_home_prob": p_home,
                        "honest_pick": pick,
                        "actual": actual,
                        "honest_correct": pick == actual,
                        "home_rest_penalty": pred.get("home_rest_penalty", 0),
                        "away_rest_penalty": pred.get("away_rest_penalty", 0),
                    }
                )
            except Exception as e:
                rows.append({"game_id": gid, "error": str(e)})

        engine.process_game(game.to_dict())

    out = pd.DataFrame(rows)
    out.to_csv("data/exports/honest_walkforward_2025_26.csv", index=False)

    ok = out[out.get("error").isna()] if "error" in out.columns else out
    print(f"replayed {len(ok)} of {len(tracked_ids)} tracked games")
    print(f"HONEST accuracy: {ok.honest_correct.mean()*100:.2f}%")

    merged = tracked.copy()
    merged["game_id"] = [
        f"{r.date}_{r.home_team_id}_{r.away_team_id}" for r in tracked.itertuples()
    ]
    merged = merged.merge(ok[["game_id", "honest_correct", "honest_home_prob"]],
                          on="game_id", how="inner")
    merged["correct"] = merged["correct"].astype(bool)
    print(f"tracked (leaked) accuracy on same games: {merged.correct.mean()*100:.2f}%")
    same = (merged.correct == merged.honest_correct).mean()
    print(f"picks agree on {same*100:.1f}% of games")
    b2b = ok[(ok.home_rest_penalty != 0) | (ok.away_rest_penalty != 0)]
    print(f"games with a nonzero rest penalty: {len(b2b)} "
          f"(acc {b2b.honest_correct.mean()*100:.1f}%)")


if __name__ == "__main__":
    main()
