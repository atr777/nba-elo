"""
Auto-Track Daily Predictions
Automatically makes predictions for recent games and tracks results.

Usage:
    python scripts/auto_track_predictions.py [--days-back N]
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.utils.file_io import load_csv_to_dataframe
from src.engines.team_elo_engine import TeamELOEngine

TRACKING_FILE = Path('data/exports/prediction_tracking.csv')

def log(message):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def load_tracking_data():
    """Load existing prediction tracking data."""
    if not TRACKING_FILE.exists():
        log("No existing tracking file found, will create new one")
        return pd.DataFrame()

    return pd.read_csv(TRACKING_FILE)

def get_recent_games(days_back=7):
    """
    Get completed games from recent days that need tracking.

    Args:
        days_back: Number of days to look back

    Returns:
        DataFrame of games to track
    """
    games = load_csv_to_dataframe('data/raw/nba_games_all.csv')

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    start_date_int = int(start_date.strftime('%Y%m%d'))
    end_date_int = int(end_date.strftime('%Y%m%d'))

    # Filter completed games in date range (must have scores)
    recent_games = games[
        (games['date'] >= start_date_int) &
        (games['date'] < end_date_int) &
        (games['home_score'] > 0) &
        (games['away_score'] > 0)
    ].copy()

    return recent_games

def track_predictions(days_back=7):
    """
    Track predictions for recent games.

    Args:
        days_back: Number of days to look back
    """
    log(f"Starting prediction tracking (looking back {days_back} days)...")

    # Load existing tracking data
    existing_tracking = load_tracking_data()
    existing_game_ids = set(existing_tracking['game_id'].values) if len(existing_tracking) > 0 else set()

    # Load data needed for predictions
    log("Loading ELO data...")
    team_history = load_csv_to_dataframe('data/exports/team_elo_history_phase_1_6.csv')
    latest_teams = team_history.sort_values('date').groupby('team_id').last().reset_index()
    latest_teams['rating'] = latest_teams['rating_after']
    team_ratings = latest_teams[['team_id', 'team_name', 'rating']].copy()

    player_ratings = load_csv_to_dataframe('data/exports/player_ratings_bpm_adjusted.csv')
    player_team_mapping = load_csv_to_dataframe('data/exports/player_team_mapping.csv')

    # Load games for ELO engine
    games_raw = load_csv_to_dataframe('data/raw/nba_games_all.csv')

    # Initialize ELO engine with player data for top player concentration
    log("Initializing ELO engine...")
    elo_engine = TeamELOEngine(
        k_factor=20,
        home_advantage=20,  # Phase 4: Reduced from 30 to 20
        use_mov=True,
        use_enhanced_features=True,
        use_top_player_concentration=True,
        player_ratings=player_ratings,
        player_team_mapping=player_team_mapping
    )
    elo_engine.compute_season_elo(games_raw, reset=True)

    # Get recent completed games
    recent_games = get_recent_games(days_back)
    log(f"Found {len(recent_games)} completed games in the last {days_back} days")

    # Filter out games we've already tracked
    new_games = recent_games[~recent_games.apply(
        lambda row: f"{row['date']}_{row['home_team_id']}_{row['away_team_id']}" in existing_game_ids,
        axis=1
    )]

    log(f"Found {len(new_games)} new games to track")

    if len(new_games) == 0:
        log("No new games to track. Tracking is up to date!")
        return

    # Track each new game
    new_rows = []
    for _, game in new_games.iterrows():
        game_id = f"{game['date']}_{game['home_team_id']}_{game['away_team_id']}"

        try:
            # Get prediction from ELO engine
            prediction = elo_engine.predict_game(
                home_team_id=game['home_team_id'],
                away_team_id=game['away_team_id'],
                game_date=game['date']
            )

            home_win_prob = prediction['home_win_probability']
            away_win_prob = 1 - home_win_prob

            # Determine predicted winner
            if home_win_prob > 0.5:
                predicted_winner = 'home'
                confidence = home_win_prob
            else:
                predicted_winner = 'away'
                confidence = away_win_prob

            # Determine actual winner
            if game['home_score'] > game['away_score']:
                actual_winner = 'home'
            else:
                actual_winner = 'away'

            # Check if correct
            correct = (predicted_winner == actual_winner)

            # Calculate margin of victory
            margin_of_victory = abs(game['home_score'] - game['away_score'])

            # Check if upset (underdog won with low probability)
            upset = (confidence > 0.6 and not correct)

            # Create tracking row
            new_row = {
                'game_id': game_id,
                'date': game['date'],
                'timestamp': datetime.now().isoformat(),
                'home_team_id': game['home_team_id'],
                'away_team_id': game['away_team_id'],
                'home_team_name': game['home_team_name'],
                'away_team_name': game['away_team_name'],
                'predicted_winner': predicted_winner,
                'predicted_home_prob': home_win_prob,
                'predicted_away_prob': away_win_prob,
                'confidence': confidence,
                'actual_winner': actual_winner,
                'actual_home_score': int(game['home_score']),
                'actual_away_score': int(game['away_score']),
                'correct': correct,
                'elo_diff': prediction.get('home_rating', 0) - prediction.get('away_rating', 0),
                'is_close_game': abs(prediction.get('home_rating', 0) - prediction.get('away_rating', 0)) < 100,
                'is_toss_up': abs(home_win_prob - 0.5) < 0.1,
                'home_back_to_back': False,  # Could be enhanced later
                'away_back_to_back': False,
                'rest_fatigue_active': True,
                'close_game_enhancement_active': abs(prediction.get('home_rating', 0) - prediction.get('away_rating', 0)) < 100,
                'momentum_active': True,
                'home_momentum_adjustment': prediction.get('home_form_adjustment', 0),
                'away_momentum_adjustment': prediction.get('away_form_adjustment', 0),
                'home_elo': prediction.get('home_rating', 0),
                'away_elo': prediction.get('away_rating', 0),
                'margin_of_victory': margin_of_victory,
                'upset': upset,
                'predicted_home_score': prediction.get('predicted_home_score', None),
                'predicted_away_score': prediction.get('predicted_away_score', None),
                'predicted_margin': prediction.get('predicted_margin', None),
                # Quarter predictions (Sprint 3)
                'predicted_home_q1': prediction.get('predicted_home_q1', None),
                'predicted_home_q2': prediction.get('predicted_home_q2', None),
                'predicted_home_q3': prediction.get('predicted_home_q3', None),
                'predicted_home_q4': prediction.get('predicted_home_q4', None),
                'predicted_away_q1': prediction.get('predicted_away_q1', None),
                'predicted_away_q2': prediction.get('predicted_away_q2', None),
                'predicted_away_q3': prediction.get('predicted_away_q3', None),
                'predicted_away_q4': prediction.get('predicted_away_q4', None),
            }

            new_rows.append(new_row)

        except Exception as e:
            log(f"Error tracking game {game_id}: {e}")
            continue

    if len(new_rows) == 0:
        log("No new predictions to add")
        return

    # Append new rows to tracking file
    new_df = pd.DataFrame(new_rows)

    if len(existing_tracking) > 0:
        updated_tracking = pd.concat([existing_tracking, new_df], ignore_index=True)
    else:
        updated_tracking = new_df

    # Sort by date descending
    updated_tracking = updated_tracking.sort_values('date', ascending=False)

    # Save to file
    updated_tracking.to_csv(TRACKING_FILE, index=False)

    # Calculate accuracy for new games
    correct_count = sum(row['correct'] for row in new_rows)
    accuracy = (correct_count / len(new_rows) * 100) if len(new_rows) > 0 else 0

    log(f"[OK] Tracked {len(new_rows)} new games")
    log(f"  Accuracy: {correct_count}/{len(new_rows)} ({accuracy:.1f}%)")
    log(f"  Saved to: {TRACKING_FILE}")

def main():
    """Main function."""
    # Parse arguments
    days_back = 7
    if '--days-back' in sys.argv:
        idx = sys.argv.index('--days-back')
        if idx + 1 < len(sys.argv):
            days_back = int(sys.argv[idx + 1])

    log("="*80)
    log("AUTO-TRACK PREDICTIONS")
    log("="*80)

    track_predictions(days_back=days_back)

    log("="*80)
    log("TRACKING COMPLETE")
    log("="*80)

if __name__ == '__main__':
    main()
