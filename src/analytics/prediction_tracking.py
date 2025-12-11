"""
Prediction Tracking and Accuracy Analysis
Compares predictions vs actual results for model performance tracking
"""

import pandas as pd
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.utils.file_io import load_csv_to_dataframe


def get_yesterdays_results(target_date=None):
    """
    Get completed games from yesterday with predictions vs actual results.

    Args:
        target_date: YYYYMMDD integer or None for yesterday

    Returns:
        List of game results with predictions
    """
    try:
        # Load games database
        games = load_csv_to_dataframe('data/raw/nba_games_all.csv')

        # Load latest team ratings
        team_history = load_csv_to_dataframe('data/exports/team_elo_history_phase_1_5.csv')
        latest_teams = team_history.sort_values('date').groupby('team_id').last().reset_index()
        latest_teams['rating'] = latest_teams['rating_after']

        # Determine yesterday's date
        if target_date is None:
            yesterday = datetime.now() - timedelta(days=1)
            target_date = int(yesterday.strftime('%Y%m%d'))

        # Filter games from yesterday with completed scores
        yesterday_games = games[
            (games['date'] == target_date) &
            (games['home_score'] > 0) &
            (games['away_score'] > 0)
        ].copy()

        if len(yesterday_games) == 0:
            return None

        results = []

        for _, game in yesterday_games.iterrows():
            # Get team ratings
            home_team_data = latest_teams[latest_teams['team_id'] == game['home_team_id']]
            away_team_data = latest_teams[latest_teams['team_id'] == game['away_team_id']]

            if len(home_team_data) == 0 or len(away_team_data) == 0:
                continue

            home_rating = home_team_data['rating'].iloc[0]
            away_rating = away_team_data['rating'].iloc[0]

            # Calculate prediction
            home_advantage = 30  # Calibrated
            rating_diff = home_rating - away_rating + home_advantage
            home_win_prob = 1 / (1 + 10 ** (-rating_diff / 400))

            # Determine predicted winner
            predicted_winner = game['home_team_name'] if home_win_prob > 0.5 else game['away_team_name']
            predicted_prob = max(home_win_prob, 1 - home_win_prob)

            # Determine actual winner
            actual_winner = game['home_team_name'] if game['home_score'] > game['away_score'] else game['away_team_name']

            # Check if prediction was correct
            correct = (predicted_winner == actual_winner)

            # Check if upset (underdog won)
            upset = (predicted_prob > 0.6 and not correct)

            results.append({
                'home_team': game['home_team_name'],
                'away_team': game['away_team_name'],
                'home_score': int(game['home_score']),
                'away_score': int(game['away_score']),
                'actual_winner': actual_winner,
                'predicted_winner': predicted_winner,
                'predicted_prob': predicted_prob,
                'home_win_prob': home_win_prob,
                'correct': correct,
                'upset': upset
            })

        return results

    except Exception as e:
        print(f"Error getting yesterday's results: {e}")
        return None


def get_accuracy_stats(days_back=7):
    """
    Calculate model accuracy statistics for recent period.

    Args:
        days_back: Number of days to look back

    Returns:
        Dict with accuracy stats
    """
    try:
        games = load_csv_to_dataframe('data/raw/nba_games_all.csv')
        team_history = load_csv_to_dataframe('data/exports/team_elo_history_phase_1_5.csv')
        latest_teams = team_history.sort_values('date').groupby('team_id').last().reset_index()
        latest_teams['rating'] = latest_teams['rating_after']

        # Get date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        start_date_int = int(start_date.strftime('%Y%m%d'))
        end_date_int = int(end_date.strftime('%Y%m%d'))

        # Filter completed games in date range
        recent_games = games[
            (games['date'] >= start_date_int) &
            (games['date'] < end_date_int) &
            (games['home_score'] > 0) &
            (games['away_score'] > 0)
        ].copy()

        if len(recent_games) == 0:
            return None

        correct_predictions = 0
        total_predictions = 0
        current_streak = 0
        streak_type = None  # 'W' for wins, 'L' for losses

        # Sort by date to calculate streak
        recent_games = recent_games.sort_values('date')

        for _, game in recent_games.iterrows():
            home_team_data = latest_teams[latest_teams['team_id'] == game['home_team_id']]
            away_team_data = latest_teams[latest_teams['team_id'] == game['away_team_id']]

            if len(home_team_data) == 0 or len(away_team_data) == 0:
                continue

            home_rating = home_team_data['rating'].iloc[0]
            away_rating = away_team_data['rating'].iloc[0]

            # Calculate prediction
            rating_diff = home_rating - away_rating + 70  # home advantage
            home_win_prob = 1 / (1 + 10 ** (-rating_diff / 400))

            predicted_winner_is_home = home_win_prob > 0.5
            actual_winner_is_home = game['home_score'] > game['away_score']

            correct = (predicted_winner_is_home == actual_winner_is_home)

            if correct:
                correct_predictions += 1
                if streak_type == 'W' or streak_type is None:
                    current_streak += 1
                    streak_type = 'W'
                else:
                    current_streak = 1
                    streak_type = 'W'
            else:
                if streak_type == 'L' or streak_type is None:
                    current_streak += 1
                    streak_type = 'L'
                else:
                    current_streak = 1
                    streak_type = 'L'

            total_predictions += 1

        accuracy = (correct_predictions / total_predictions * 100) if total_predictions > 0 else 0

        return {
            'accuracy': accuracy,
            'correct': correct_predictions,
            'total': total_predictions,
            'current_streak': current_streak,
            'streak_type': streak_type
        }

    except Exception as e:
        print(f"Error calculating accuracy: {e}")
        return None


def format_yesterdays_results_with_predictions(target_date=None):
    """
    Format yesterday's results WITH prediction tracking (correct/incorrect).
    NO EMOJIS - uses [CORRECT] and [MISSED] text.

    Args:
        target_date: YYYYMMDD integer or None for yesterday

    Returns:
        Formatted string for newsletter
    """
    results = get_yesterdays_results(target_date)

    if not results:
        return "*No completed games available*"

    # Determine date
    if target_date:
        date_str = datetime.strptime(str(target_date), '%Y%m%d').strftime("%B %d, %Y")
    else:
        yesterday = datetime.now() - timedelta(days=1)
        date_str = yesterday.strftime("%B %d, %Y")

    # Calculate accuracy
    correct_count = sum(1 for r in results if r['correct'])
    total_count = len(results)
    accuracy = (correct_count / total_count * 100) if total_count > 0 else 0

    output = f"**{date_str} - {total_count} Games ({correct_count}-{total_count - correct_count}, {accuracy:.1f}% accurate)**\n\n"

    # Separate correct and incorrect predictions
    correct_preds = [r for r in results if r['correct']]
    incorrect_preds = [r for r in results if not r['correct']]

    # Show correct predictions
    if correct_preds:
        output += "*Correct Predictions:*\n"
        for result in correct_preds:
            output += f"[CORRECT] Predicted {result['predicted_winner']} ({result['predicted_prob']:.1%}) - Won {result['home_score']}-{result['away_score']}\n"

    # Show missed predictions
    if incorrect_preds:
        output += "\n*Missed Predictions:*\n"
        for result in incorrect_preds:
            upset_tag = " (UPSET)" if result['upset'] else ""
            output += f"[MISSED] Predicted {result['predicted_winner']} ({result['predicted_prob']:.1%}) - {result['actual_winner']} won {result['home_score']}-{result['away_score']}{upset_tag}\n"

    return output


def format_yesterdays_results(target_date=None):
    """
    Format yesterday's results for newsletter display - SIMPLE VERSION.
    Just shows game outcomes without prediction accuracy.

    Args:
        target_date: YYYYMMDD integer or None for yesterday

    Returns:
        Formatted string for newsletter
    """
    try:
        # Load games database
        games = load_csv_to_dataframe('data/raw/nba_games_all.csv')

        # Determine yesterday's date
        if target_date is None:
            yesterday = datetime.now() - timedelta(days=1)
            target_date = int(yesterday.strftime('%Y%m%d'))

        # Filter games from yesterday with completed scores
        yesterday_games = games[
            (games['date'] == target_date) &
            (games['home_score'] > 0) &
            (games['away_score'] > 0)
        ].copy()

        if len(yesterday_games) == 0:
            return "*No games available for yesterday*"

        # Format date
        date_str = datetime.strptime(str(target_date), '%Y%m%d').strftime("%B %d, %Y")

        output = f"""**{date_str} - {len(yesterday_games)} Games**

"""

        # Show all games - simple format
        for _, game in yesterday_games.iterrows():
            home_score = int(game['home_score'])
            away_score = int(game['away_score'])

            # Format score with winner in bold
            if home_score > away_score:
                score_display = f"**{home_score}**-{away_score}"
                winner_indicator = ""
            else:
                score_display = f"{home_score}-**{away_score}**"
                winner_indicator = ""

            # Simple line format
            output += f"{game['away_team_name']} @ {game['home_team_name']}: {score_display}\n"

        return output

    except Exception as e:
        print(f"Error getting yesterday's results: {e}")
        return "*Yesterday's results unavailable*"


# Test function
if __name__ == '__main__':
    print("Testing Prediction Tracking...")
    print("="*80)

    # Test with a specific date (Nov 23, 2025)
    test_date = 20251123
    print(f"\nResults for {test_date}:")
    print("-"*80)
    results_text = format_yesterdays_results(test_date)
    print(results_text)

    # Test with yesterday
    print("\n\nYesterday's results:")
    print("-"*80)
    yesterday_text = format_yesterdays_results()
    print(yesterday_text)
