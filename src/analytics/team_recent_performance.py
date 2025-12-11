"""
Team Recent Performance Analytics
Analyzes team performance over last N games for newsletter insights
"""

import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.utils.file_io import load_csv_to_dataframe


def get_recent_games_performance(team_name, last_n_games=10):
    """
    Get team's performance over their last N games.

    Args:
        team_name: Full team name (e.g., "Los Angeles Lakers")
        last_n_games: Number of recent games to analyze (default: 10)

    Returns:
        Dictionary with recent performance stats
    """
    try:
        # Load game results
        games = load_csv_to_dataframe('data/raw/nba_games_all.csv')

        # Filter games where this team played
        team_games = games[
            (games['home_team_name'] == team_name) |
            (games['away_team_name'] == team_name)
        ].copy()

        # Sort by date descending (most recent first)
        team_games = team_games.sort_values('date', ascending=False)

        # Take last N games
        recent_games = team_games.head(last_n_games)

        if len(recent_games) == 0:
            return None

        # Calculate stats
        wins = 0
        losses = 0
        points_for = []
        points_against = []
        margin_of_victory = []

        for _, game in recent_games.iterrows():
            is_home = game['home_team_name'] == team_name

            if is_home:
                team_score = game['home_score']
                opp_score = game['away_score']
            else:
                team_score = game['away_score']
                opp_score = game['home_score']

            points_for.append(team_score)
            points_against.append(opp_score)
            margin = team_score - opp_score
            margin_of_victory.append(margin)

            if margin > 0:
                wins += 1
            else:
                losses += 1

        # Calculate averages
        avg_points = sum(points_for) / len(points_for)
        avg_points_allowed = sum(points_against) / len(points_against)
        avg_margin = sum(margin_of_victory) / len(margin_of_victory)

        # Recent streak (W/L pattern)
        streak = []
        for _, game in recent_games.iterrows():
            is_home = game['home_team_name'] == team_name
            if is_home:
                margin = game['home_score'] - game['away_score']
            else:
                margin = game['away_score'] - game['home_score']

            streak.append('W' if margin > 0 else 'L')

        return {
            'games_analyzed': len(recent_games),
            'wins': wins,
            'losses': losses,
            'win_pct': wins / len(recent_games),
            'avg_points': avg_points,
            'avg_points_allowed': avg_points_allowed,
            'avg_margin': avg_margin,
            'streak': ''.join(streak),  # e.g., "WLWWLWLWWW"
            'current_streak_type': streak[0],  # W or L
            'current_streak_length': len([x for x in __import__('itertools').takewhile(lambda x: x == streak[0], streak)])
        }

    except Exception as e:
        print(f"Error analyzing recent performance for {team_name}: {e}")
        return None


def calculate_momentum_factor(team_name, lookback_games=5, max_adjustment=40):
    """
    Calculate momentum adjustment based on recent team performance.

    Hot teams (winning with large margins) get boosted.
    Cold teams (losing badly) get penalized.

    Args:
        team_name: Full team name (e.g., "Los Angeles Lakers")
        lookback_games: Number of recent games to analyze (default: 5)
        max_adjustment: Maximum ELO adjustment (+/-) (default: 40)

    Returns:
        float: Momentum adjustment in ELO points
               Positive = hot team (boost)
               Negative = cold team (penalty)
               0 = neutral form

    Adjustment Tiers:
        Hot Streaks (4+ wins in last 5):
            - Dominant (avg margin > 10): +35 ELO
            - Solid (avg margin 5-10): +25 ELO
            - Close wins (avg margin < 5): +15 ELO

        Cold Streaks (0-1 wins in last 5):
            - Getting blown out (avg margin < -10): -35 ELO
            - Losing decisively (avg margin -10 to -5): -25 ELO
            - Losing close games (avg margin > -5): -15 ELO

        Neutral (2-3 wins in last 5): 0 ELO
    """
    try:
        recent = get_recent_games_performance(team_name, last_n_games=lookback_games)

        if not recent:
            return 0  # No data available

        wins = recent['wins']
        avg_margin = recent['avg_margin']

        # Hot streak detection (4+ wins in last 5 games)
        if wins >= 4:
            if avg_margin > 10:  # Dominant victories
                return +35
            elif avg_margin > 5:  # Solid wins
                return +25
            else:  # Close games but winning
                return +15

        # Cold streak detection (0-1 wins in last 5 games)
        elif wins <= 1:
            if avg_margin < -10:  # Getting destroyed
                return -35
            elif avg_margin < -5:  # Losing badly
                return -25
            else:  # Close losses
                return -15

        # Neutral form (2-3 wins in last 5)
        # Could add subtle adjustments here based on margin trends
        else:
            # Slight adjustment for strong/weak neutral records
            if wins == 3 and avg_margin > 5:
                return +10  # Winning trend
            elif wins == 2 and avg_margin < -5:
                return -10  # Losing trend
            else:
                return 0  # True neutral

    except Exception as e:
        print(f"Error analyzing recent performance for {team_name}: {e}")
        return None


def format_recent_performance_summary(team_name, last_n_games=10):
    """
    Format recent performance for newsletter display.

    Args:
        team_name: Team name
        last_n_games: Number of games to analyze

    Returns:
        Formatted string for newsletter
    """
    perf = get_recent_games_performance(team_name, last_n_games)

    if not perf:
        return f"*Recent data unavailable for {team_name}*"

    # Determine form assessment
    if perf['win_pct'] >= 0.7:
        form = "[HOT]"
    elif perf['win_pct'] >= 0.6:
        form = "[STRONG]"
    elif perf['win_pct'] >= 0.5:
        form = "[AVERAGE]"
    elif perf['win_pct'] >= 0.4:
        form = "[STRUGGLING]"
    else:
        form = "[COLD]"

    # Current streak description
    streak_desc = f"{perf['current_streak_length']} game{'s' if perf['current_streak_length'] > 1 else ''}"
    if perf['current_streak_type'] == 'W':
        streak_text = f"Won last {streak_desc}" if perf['current_streak_length'] > 1 else "Won last game"
    else:
        streak_text = f"Lost last {streak_desc}" if perf['current_streak_length'] > 1 else "Lost last game"

    summary = f"""**{team_name} - Last {perf['games_analyzed']} Games: {form}**
- Record: {perf['wins']}-{perf['losses']} ({perf['win_pct']:.1%})
- {streak_text}
- Scoring: {perf['avg_points']:.1f} PPG | Allowing: {perf['avg_points_allowed']:.1f} PPG
- Point Differential: {perf['avg_margin']:+.1f} per game
- Recent results: {perf['streak']}"""

    return summary


def compare_recent_performance(home_team, away_team, last_n_games=10):
    """
    Compare recent performance of two teams.

    Args:
        home_team: Home team name
        away_team: Away team name
        last_n_games: Number of games to analyze

    Returns:
        Comparison dictionary with insights
    """
    home_perf = get_recent_games_performance(home_team, last_n_games)
    away_perf = get_recent_games_performance(away_team, last_n_games)

    if not home_perf or not away_perf:
        return None

    # Determine who has better recent form
    if home_perf['win_pct'] > away_perf['win_pct'] + 0.15:
        form_advantage = home_team
        form_text = "significantly better"
    elif home_perf['win_pct'] > away_perf['win_pct'] + 0.05:
        form_advantage = home_team
        form_text = "slightly better"
    elif away_perf['win_pct'] > home_perf['win_pct'] + 0.15:
        form_advantage = away_team
        form_text = "significantly better"
    elif away_perf['win_pct'] > home_perf['win_pct'] + 0.05:
        form_advantage = away_team
        form_text = "slightly better"
    else:
        form_advantage = None
        form_text = "similar"

    # Momentum analysis
    home_momentum = "up" if home_perf['current_streak_type'] == 'W' else "down"
    away_momentum = "up" if away_perf['current_streak_type'] == 'W' else "down"

    return {
        'home_performance': home_perf,
        'away_performance': away_perf,
        'form_advantage': form_advantage,
        'form_text': form_text,
        'home_momentum': home_momentum,
        'away_momentum': away_momentum,
        'scoring_advantage': home_team if home_perf['avg_points'] > away_perf['avg_points'] else away_team,
        'defense_advantage': home_team if home_perf['avg_points_allowed'] < away_perf['avg_points_allowed'] else away_team
    }


# Test function
if __name__ == '__main__':
    print("Testing Recent Performance Analytics...")
    print("="*80)

    # Test with Lakers
    test_team = "Los Angeles Lakers"
    print(f"\nAnalyzing {test_team} (Last 10 games):")
    print("-"*80)
    summary = format_recent_performance_summary(test_team, 10)
    print(summary)

    # Test comparison
    print("\n\nComparing Recent Form:")
    print("-"*80)
    comp = compare_recent_performance("Los Angeles Lakers", "Golden State Warriors", 10)
    if comp:
        print(f"\nForm advantage: {comp['form_advantage']} ({comp['form_text']})")
        print(f"Scoring advantage: {comp['scoring_advantage']}")
        print(f"Defense advantage: {comp['defense_advantage']}")
        print(f"Lakers momentum: {comp['home_momentum']}")
        print(f"Warriors momentum: {comp['away_momentum']}")
