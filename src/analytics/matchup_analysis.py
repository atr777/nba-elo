"""
Matchup Analysis Tools
Provides head-to-head history, upset alerts, and game storylines
"""

import pandas as pd
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.utils.file_io import load_csv_to_dataframe


def get_head_to_head_history(team1_name, team2_name, n_games=5):
    """
    Get recent head-to-head matchup history between two teams.

    Args:
        team1_name: First team name
        team2_name: Second team name
        n_games: Number of recent games to return (default 5)

    Returns:
        List of game dicts with scores and outcomes
    """
    try:
        games = load_csv_to_dataframe('data/raw/nba_games_all.csv')

        # Filter games between these two teams
        h2h_games = games[
            (
                ((games['home_team_name'] == team1_name) & (games['away_team_name'] == team2_name)) |
                ((games['home_team_name'] == team2_name) & (games['away_team_name'] == team1_name))
            ) &
            (games['home_score'] > 0) &  # Only completed games
            (games['away_score'] > 0)
        ].copy()

        if len(h2h_games) == 0:
            return None

        # Sort by date descending (most recent first)
        h2h_games = h2h_games.sort_values('date', ascending=False).head(n_games)

        results = []
        for _, game in h2h_games.iterrows():
            home_won = game['home_score'] > game['away_score']
            winner = game['home_team_name'] if home_won else game['away_team_name']

            # Determine which team is team1 in this game
            team1_is_home = game['home_team_name'] == team1_name
            team1_score = game['home_score'] if team1_is_home else game['away_score']
            team2_score = game['away_score'] if team1_is_home else game['home_score']

            results.append({
                'date': game['date'],
                'date_str': datetime.strptime(str(game['date']), '%Y%m%d').strftime('%b %d, %Y'),
                'home_team': game['home_team_name'],
                'away_team': game['away_team_name'],
                'home_score': int(game['home_score']),
                'away_score': int(game['away_score']),
                'winner': winner,
                'team1_score': int(team1_score),
                'team2_score': int(team2_score),
                'team1_won': (winner == team1_name)
            })

        return results

    except Exception as e:
        print(f"Error getting head-to-head history: {e}")
        return None


def calculate_h2h_adjustment(team1_name, team2_name, lookback_games=5, max_adjustment=50):
    """
    Calculate H2H adjustment factor based on recent matchup history.

    Returns adjustment in ELO points (+/- max_adjustment) that should be applied
    to team1's rating when predicting against team2.

    Args:
        team1_name: First team name
        team2_name: Second team name
        lookback_games: Number of recent games to consider (default 5)
        max_adjustment: Maximum adjustment in ELO points (default 50)

    Returns:
        float: Adjustment value between -max_adjustment and +max_adjustment
               Positive = team1 has edge in this matchup
               Negative = team2 has edge in this matchup
               0 = No adjustment (insufficient data or neutral)
    """
    try:
        import numpy as np

        history = get_head_to_head_history(team1_name, team2_name, n_games=lookback_games)

        if not history or len(history) < 3:
            return 0  # Insufficient data

        # Calculate team1 win rate
        team1_wins = sum(1 for g in history if g['team1_won'])
        win_rate = team1_wins / len(history)

        # Calculate average margin for team1
        margins = []
        for game in history:
            if game['team1_won']:
                margins.append(game['team1_score'] - game['team2_score'])
            else:
                margins.append(-(game['team2_score'] - game['team1_score']))

        avg_margin = np.mean(margins)

        # Base adjustment from win rate
        # Range: -50 to +50 based on win rate (0% to 100%)
        # 50% win rate = 0 adjustment
        win_rate_adjustment = (win_rate - 0.5) * (max_adjustment * 2)

        # Margin adjustment (up to 25% of max adjustment)
        # Every 10 points of average margin = 25% of max
        margin_adjustment = (avg_margin / 10) * (max_adjustment * 0.25)

        # Combine adjustments
        total_adjustment = win_rate_adjustment + margin_adjustment

        # Clip to max adjustment range
        final_adjustment = np.clip(total_adjustment, -max_adjustment, max_adjustment)

        return final_adjustment

    except Exception as e:
        print(f"Error calculating H2H adjustment: {e}")
        return 0


def format_head_to_head_summary(team1_name, team2_name, n_games=3):
    """
    Format head-to-head history for newsletter display.

    Args:
        team1_name: First team name
        team2_name: Second team name
        n_games: Number of recent games to show (default 3)

    Returns:
        Formatted string for newsletter
    """
    history = get_head_to_head_history(team1_name, team2_name, n_games)

    if not history or len(history) == 0:
        return f"*No recent matchup history available between {team1_name} and {team2_name}*"

    # Calculate record
    team1_wins = sum(1 for g in history if g['team1_won'])
    team2_wins = len(history) - team1_wins

    output = f"**Recent Head-to-Head: {team1_name} {team1_wins}-{team2_wins} {team2_name}**\n"
    output += f"*(Last {len(history)} meetings)*\n\n"

    for game in history:
        # Format game line
        margin = abs(game['team1_score'] - game['team2_score'])

        # Show matchup with location
        if game['home_team'] == team1_name:
            location = f"{team1_name} home"
        else:
            location = f"{team2_name} home"

        output += f"- **{game['date_str']}**: {game['winner']} won {game['home_score']}-{game['away_score']} (at {location})\n"

    return output


def identify_upset_candidates(games, predictions, team_ratings):
    """
    Identify games with high upset potential for "Upset Watch" section.

    Criteria for upset alert:
    - Win probability between 50-60% (competitive but with favorite)
    - Underdog has won 3+ of last 5 games (hot streak)
    - Favorite is on back-to-back or 3-in-4 nights (fatigue)

    Args:
        games: List of today's games
        predictions: List of predictions for each game
        team_ratings: DataFrame with current team ratings

    Returns:
        List of games with upset potential, sorted by likelihood
    """
    try:
        upset_candidates = []

        for i, game in enumerate(games):
            if i >= len(predictions):
                continue

            pred = predictions[i]
            home_prob = pred.get('home_win_prob', 0.5)
            away_prob = 1 - home_prob

            # Check if game is competitive (50-65% range)
            favorite_prob = max(home_prob, away_prob)
            if favorite_prob < 0.50 or favorite_prob > 0.65:
                continue  # Too lopsided or too close to call

            # This is a potential upset candidate
            favorite = game['home_team'] if home_prob > 0.5 else game['away_team']
            underdog = game['away_team'] if home_prob > 0.5 else game['home_team']
            favorite_prob_pct = favorite_prob * 100

            upset_candidates.append({
                'home_team': game['home_team'],
                'away_team': game['away_team'],
                'favorite': favorite,
                'underdog': underdog,
                'favorite_prob': favorite_prob,
                'upset_potential': 100 - favorite_prob_pct,  # Inverse of favorite %
                'reason': f"{underdog} has real upset potential despite {favorite} being favored at {favorite_prob_pct:.1f}%"
            })

        # Sort by upset potential (closest to 50-50)
        upset_candidates.sort(key=lambda x: abs(x['favorite_prob'] - 0.5))

        return upset_candidates

    except Exception as e:
        print(f"Error identifying upset candidates: {e}")
        return []


def format_upset_watch(upset_candidates, max_games=3):
    """
    Format upset watch section for newsletter.

    Args:
        upset_candidates: List of games with upset potential
        max_games: Maximum number of games to highlight (default 3)

    Returns:
        Formatted string for newsletter
    """
    if not upset_candidates or len(upset_candidates) == 0:
        return "*No major upset alerts today - favorites are heavily favored*"

    output = "**Games to Watch for Potential Upsets:**\n\n"

    for i, game in enumerate(upset_candidates[:max_games]):
        output += f"{i+1}. **{game['away_team']} @ {game['home_team']}**\n"
        output += f"   - {game['favorite']} favored at {game['favorite_prob']:.1%}\n"
        output += f"   - Upset potential: {game['upset_potential']:.1f}%\n"
        output += f"   - {game['reason']}\n\n"

    return output


def generate_game_storyline(home_team, away_team, prediction, home_recent=None, away_recent=None):
    """
    Generate a narrative storyline for a matchup.

    Args:
        home_team: Home team name
        away_team: Away team name
        prediction: Prediction dict with probabilities
        home_recent: Recent performance dict for home team (optional)
        away_recent: Recent performance dict for away team (optional)

    Returns:
        Formatted storyline string
    """
    try:
        home_prob = prediction.get('home_win_prob', 0.5)
        away_prob = 1 - home_prob

        # Determine favorite
        if home_prob > 0.6:
            favorite = home_team
            favorite_prob = home_prob
            underdog = away_team
            matchup_type = "mismatch"
        elif away_prob > 0.6:
            favorite = away_team
            favorite_prob = away_prob
            underdog = home_team
            matchup_type = "mismatch"
        else:
            favorite = home_team if home_prob > 0.5 else away_team
            favorite_prob = max(home_prob, away_prob)
            underdog = away_team if home_prob > 0.5 else home_team
            matchup_type = "toss-up"

        # Build narrative
        if matchup_type == "toss-up":
            storyline = f"This is the game to watch tonight. "
            storyline += f"With just a {favorite_prob:.1%} edge for {favorite}, this matchup is too close to call. "
            storyline += f"Both teams enter with something to prove, and home court advantage at "
            storyline += f"{home_team}'s arena could be the deciding factor."
        else:
            storyline = f"{favorite} enters as the clear favorite ({favorite_prob:.1%}), but {underdog} "

            # Add context from recent performance
            if underdog == home_team and home_recent:
                if home_recent['wins'] >= 4:
                    storyline += f"has won {home_recent['wins']} of their last 5 games and isn't going down without a fight. "
                elif home_recent['wins'] <= 1:
                    storyline += f"has struggled recently ({home_recent['wins']}-{home_recent['losses']} in last 5) and faces an uphill battle. "
                else:
                    storyline += f"has been inconsistent lately ({home_recent['wins']}-{home_recent['losses']} in last 5). "
            elif underdog == away_team and away_recent:
                if away_recent['wins'] >= 4:
                    storyline += f"is riding a hot streak ({away_recent['wins']}-{away_recent['losses']} in last 5) and could play spoiler. "
                elif away_recent['wins'] <= 1:
                    storyline += f"has been ice cold ({away_recent['wins']}-{away_recent['losses']} in last 5) and needs a miracle. "
                else:
                    storyline += f"has been up and down ({away_recent['wins']}-{away_recent['losses']} in last 5). "

            storyline += f"The model gives {favorite} a strong edge, but in the NBA, anything can happen."

        return storyline

    except Exception as e:
        print(f"Error generating storyline: {e}")
        return f"{away_team} visits {home_team} in what promises to be an intriguing matchup."


# Test functions
if __name__ == '__main__':
    print("Testing Matchup Analysis Tools...")
    print("=" * 80)

    # Test head-to-head history
    print("\nTest 1: Head-to-Head History")
    print("-" * 80)
    h2h = get_head_to_head_history("Boston Celtics", "Los Angeles Lakers", n_games=3)
    if h2h:
        print(f"Found {len(h2h)} games")
        for game in h2h:
            print(f"  {game['date_str']}: {game['winner']} won {game['home_score']}-{game['away_score']}")
    else:
        print("  No head-to-head data found")

    # Test formatted output
    print("\nTest 2: Formatted H2H Summary")
    print("-" * 80)
    formatted = format_head_to_head_summary("Boston Celtics", "Los Angeles Lakers", n_games=3)
    print(formatted)
