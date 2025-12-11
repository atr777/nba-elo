"""
Backfill Performance Tracking Data

This script generates predictions for historical completed games and logs them
to the prediction tracking CSV so you can see performance metrics.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pandas as pd
from datetime import datetime
from predictors.hybrid_team_player import predict_game_hybrid
from analytics.model_performance_tracker import ModelPerformanceTracker
from utils.file_io import load_csv_to_dataframe


def backfill_predictions(num_games: int = 100):
    """
    Backfill prediction tracking with historical games.

    Args:
        num_games: Number of recent completed games to backfill
    """

    print(f"\n{'='*80}")
    print("BACKFILLING PERFORMANCE TRACKING DATA")
    print(f"{'='*80}\n")

    # Load data
    print("[1/6] Loading game data...")
    games_raw = load_csv_to_dataframe('data/raw/nba_games_all.csv')

    # Convert dates to datetime
    games = games_raw.copy()
    games['date'] = pd.to_datetime(games['date'], format='%Y%m%d')

    print("[2/6] Loading team ratings...")
    team_ratings = load_csv_to_dataframe('data/exports/team_ratings.csv')

    print("[3/6] Loading player ratings...")
    player_ratings = load_csv_to_dataframe('data/exports/player_ratings_bpm_adjusted.csv')

    print("[4/6] Loading player-team mapping...")
    player_team_mapping = load_csv_to_dataframe('data/exports/player_team_mapping.csv')

    print("[5/6] Loading team locations...")
    team_locations_df = load_csv_to_dataframe('data/team_locations.csv')
    team_locations = {}
    for _, row in team_locations_df.iterrows():
        team_locations[row['team_id']] = (row['latitude'], row['longitude'])

    # Get recent completed games
    recent_games = games[games['date'] >= '2024-12-01'].sort_values('date', ascending=False).head(num_games)

    print(f"\n[6/6] Generating predictions for {len(recent_games)} games...")
    print(f"Date range: {recent_games['date'].min()} to {recent_games['date'].max()}\n")

    # Initialize tracker
    tracker = ModelPerformanceTracker()

    success_count = 0
    error_count = 0

    for idx, game in recent_games.iterrows():
        try:
            home_team_id = int(game['home_team_id'])
            away_team_id = int(game['away_team_id'])
            game_date = game['date']

            # Get team names
            home_team_name = team_ratings[team_ratings['team_id'] == home_team_id]['team_name'].iloc[0]
            away_team_name = team_ratings[team_ratings['team_id'] == away_team_id]['team_name'].iloc[0]

            # Generate prediction
            prediction = predict_game_hybrid(
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                team_ratings=team_ratings,
                player_ratings=player_ratings,
                player_team_mapping=player_team_mapping,
                home_injuries=[],  # No injury data for historical games
                away_injuries=[],
                games_history=games,
                team_locations=team_locations,
                game_date=game_date
            )

            # Determine actual winner
            actual_home_score = int(game['home_score'])
            actual_away_score = int(game['away_score'])
            actual_winner = 'home' if actual_home_score > actual_away_score else 'away'

            # Generate game_id
            game_id = f"{game_date.strftime('%Y%m%d')}_{home_team_id}_{away_team_id}"

            # Log prediction
            tracker.log_prediction(
                game_id=game_id,
                game_date=game_date.strftime('%Y%m%d'),
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                home_team_name=home_team_name,
                away_team_name=away_team_name,
                prediction=prediction,
                actual_winner=actual_winner,
                actual_home_score=actual_home_score,
                actual_away_score=actual_away_score
            )

            success_count += 1

            # Progress indicator
            if success_count % 10 == 0:
                print(f"  [OK] Processed {success_count}/{len(recent_games)} games...")

        except Exception as e:
            error_count += 1
            print(f"  [ERROR] Error processing game {idx}: {e}")
            continue

    print(f"\n{'='*80}")
    print(f"BACKFILL COMPLETE")
    print(f"{'='*80}")
    print(f"Successfully processed: {success_count} games")
    print(f"Errors: {error_count} games")
    print(f"\nPerformance data saved to: {tracker.tracking_file}")
    print(f"\nYou can now view performance metrics at: http://localhost:5001/performance")
    print(f"{'='*80}\n")

    # Generate quick summary
    print("\nQuick Performance Summary:")
    print("-" * 80)
    stats = tracker.get_performance_summary()
    if 'summary' in stats:
        print(f"Overall Accuracy: {stats['summary']['overall_accuracy']:.2%}")
        print(f"Total Games: {stats['summary']['total_games']}")
        print(f"Correct Predictions: {stats['summary']['correct_predictions']}")
    print("-" * 80)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Backfill performance tracking data')
    parser.add_argument('--num-games', type=int, default=100,
                       help='Number of recent games to backfill (default: 100)')

    args = parser.parse_args()

    backfill_predictions(num_games=args.num_games)
