"""
Player Head-to-Head Matchup Analysis
Calculates H2H adjustments based on top 3 ELO contributors per team
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.utils.file_io import load_csv_to_dataframe


def get_top_contributors_for_game(team_name, game_id, player_ratings_df, boxscores_df):
    """
    Get top 3 ELO contributors for a team in a specific game.

    Args:
        team_name: Team name
        game_id: Game ID to analyze
        player_ratings_df: DataFrame with player ELO ratings
        boxscores_df: DataFrame with player boxscores

    Returns:
        List of dicts with player_id, player_name, rating, minutes
    """
    try:
        # Get players who played in this game for this team
        game_players = boxscores_df[
            (boxscores_df['game_id'] == game_id) &
            (boxscores_df['team_name'] == team_name) &
            (boxscores_df['minutes'] > 0)
        ].copy()

        if len(game_players) == 0:
            return []

        # Merge with player ratings
        game_players = game_players.merge(
            player_ratings_df[['player_id', 'player_name', 'rating_adjusted']],
            on='player_id',
            how='left'
        )

        # Filter out players without ratings
        game_players = game_players[game_players['rating_adjusted'].notna()].copy()

        if len(game_players) == 0:
            return []

        # Calculate weighted contribution (rating * minutes)
        game_players['contribution'] = game_players['rating_adjusted'] * game_players['minutes']

        # Sort by contribution and take top 3
        top_players = game_players.nlargest(3, 'contribution')

        result = []
        for _, player in top_players.iterrows():
            result.append({
                'player_id': player['player_id'],
                'player_name': player['player_name'],
                'rating': player['rating_adjusted'],
                'minutes': player['minutes'],
                'contribution': player['contribution']
            })

        return result

    except Exception as e:
        print(f"Error getting top contributors: {e}")
        return []


def get_player_h2h_history(player1_id, player2_id, boxscores_df, games_df, n_games=10):
    """
    Get head-to-head matchup history between two players.

    Args:
        player1_id: First player ID
        player2_id: Second player ID
        boxscores_df: DataFrame with player boxscores
        games_df: DataFrame with game results
        n_games: Number of recent games to analyze (default 10)

    Returns:
        Dict with H2H stats or None if insufficient data
    """
    try:
        # Get all games where both players played
        player1_games = boxscores_df[
            (boxscores_df['player_id'] == player1_id) &
            (boxscores_df['minutes'] > 0)
        ][['game_id', 'team_name', 'plus_minus', 'points', 'minutes']].copy()

        player2_games = boxscores_df[
            (boxscores_df['player_id'] == player2_id) &
            (boxscores_df['minutes'] > 0)
        ][['game_id', 'team_name', 'plus_minus', 'points', 'minutes']].copy()

        # Find games where they faced each other
        common_games = pd.merge(
            player1_games,
            player2_games,
            on='game_id',
            suffixes=('_p1', '_p2')
        )

        # Filter to games where they were on opposing teams
        common_games = common_games[
            common_games['team_name_p1'] != common_games['team_name_p2']
        ].copy()

        if len(common_games) < 3:
            return None  # Insufficient data

        # Merge with game results to determine winner
        common_games = common_games.merge(
            games_df[['game_id', 'home_team_name', 'away_team_name', 'home_score', 'away_score']],
            on='game_id',
            how='left'
        )

        # Sort by game_id descending (most recent first) and take last n_games
        common_games = common_games.sort_values('game_id', ascending=False).head(n_games)

        # Calculate stats
        player1_wins = 0
        player2_wins = 0
        player1_plus_minus_total = 0
        player2_plus_minus_total = 0
        player1_ppg = []
        player2_ppg = []

        for _, game in common_games.iterrows():
            # Determine winner
            home_won = game['home_score'] > game['away_score']

            p1_is_home = game['team_name_p1'] == game['home_team_name']
            p1_won = (p1_is_home and home_won) or (not p1_is_home and not home_won)

            if p1_won:
                player1_wins += 1
            else:
                player2_wins += 1

            # Accumulate stats
            player1_plus_minus_total += game['plus_minus_p1']
            player2_plus_minus_total += game['plus_minus_p2']
            player1_ppg.append(game['points_p1'])
            player2_ppg.append(game['points_p2'])

        return {
            'games_played': len(common_games),
            'player1_wins': player1_wins,
            'player2_wins': player2_wins,
            'player1_avg_plus_minus': player1_plus_minus_total / len(common_games),
            'player2_avg_plus_minus': player2_plus_minus_total / len(common_games),
            'player1_avg_points': np.mean(player1_ppg),
            'player2_avg_points': np.mean(player2_ppg),
            'plus_minus_differential': (player1_plus_minus_total - player2_plus_minus_total) / len(common_games)
        }

    except Exception as e:
        print(f"Error getting player H2H history: {e}")
        return None


def calculate_player_h2h_adjustment(
    home_team,
    away_team,
    player_ratings_df,
    boxscores_df,
    games_df,
    lookback_games=10,
    max_adjustment=30
):
    """
    Calculate H2H adjustment based on top 3 contributors from each team.

    Strategy:
    1. Identify top 3 ELO contributors for each team (based on current ratings)
    2. For each player matchup (up to 9 combinations), calculate H2H performance
    3. Weight adjustments by player ELO ratings
    4. Return aggregate adjustment for the matchup

    Args:
        home_team: Home team name
        away_team: Away team name
        player_ratings_df: DataFrame with player ratings
        boxscores_df: DataFrame with player boxscores
        games_df: DataFrame with game results
        lookback_games: Number of recent H2H games to analyze (default 10)
        max_adjustment: Maximum adjustment in ELO points (default 30)

    Returns:
        float: Adjustment for home team (-max_adjustment to +max_adjustment)
               Positive = home team has player H2H edge
               Negative = away team has player H2H edge
    """
    try:
        # Get current top 3 players for each team
        home_top3 = get_current_top_players(home_team, player_ratings_df, n=3)
        away_top3 = get_current_top_players(away_team, player_ratings_df, n=3)

        if len(home_top3) < 2 or len(away_top3) < 2:
            return 0  # Insufficient player data

        # Calculate H2H for each player matchup
        matchup_adjustments = []
        matchup_weights = []

        for home_player in home_top3:
            for away_player in away_top3:
                h2h = get_player_h2h_history(
                    home_player['player_id'],
                    away_player['player_id'],
                    boxscores_df,
                    games_df,
                    n_games=lookback_games
                )

                if h2h and h2h['games_played'] >= 3:
                    # Calculate adjustment based on plus/minus differential
                    # Every +5 plus/minus = +10 ELO points
                    pm_adjustment = (h2h['plus_minus_differential'] / 5.0) * 10.0

                    # Weight by combined player rating
                    combined_rating = home_player['rating'] + away_player['rating']
                    weight = combined_rating / 4000.0  # Normalize weight

                    matchup_adjustments.append(pm_adjustment)
                    matchup_weights.append(weight)

        if len(matchup_adjustments) == 0:
            return 0  # No matchup history found

        # Calculate weighted average adjustment
        total_weight = sum(matchup_weights)
        if total_weight == 0:
            return 0

        weighted_adjustment = sum(
            adj * weight for adj, weight in zip(matchup_adjustments, matchup_weights)
        ) / total_weight

        # Clip to max adjustment
        final_adjustment = np.clip(weighted_adjustment, -max_adjustment, max_adjustment)

        return final_adjustment

    except Exception as e:
        print(f"Error calculating player H2H adjustment: {e}")
        return 0


def get_current_top_players(team_name, player_ratings_df, n=3):
    """
    Get current top N players by ELO rating for a team.

    Args:
        team_name: Team name
        player_ratings_df: DataFrame with player ratings
        n: Number of top players to return (default 3)

    Returns:
        List of dicts with player_id, player_name, rating
    """
    try:
        # For now, use a simple approach: get top N players who last played for this team
        # In production, we'd want to check current roster from latest games

        # Load recent boxscores to find current roster
        boxscores = load_csv_to_dataframe('data/raw/player_boxscores_all.csv')

        # Get most recent games
        recent_games = boxscores[boxscores['team_name'] == team_name].copy()

        if len(recent_games) == 0:
            return []

        # Get most recent game_id for this team
        max_game_id = recent_games['game_id'].max()

        # Get players from recent games (last 5 games to catch rotation)
        recent_threshold = max_game_id - 10
        recent_players = recent_games[
            recent_games['game_id'] >= recent_threshold
        ]['player_id'].unique()

        # Filter player ratings to recent players
        team_players = player_ratings_df[
            player_ratings_df['player_id'].isin(recent_players)
        ].copy()

        if len(team_players) == 0:
            return []

        # Sort by rating and take top N
        top_players = team_players.nlargest(n, 'rating_adjusted')

        result = []
        for _, player in top_players.iterrows():
            result.append({
                'player_id': player['player_id'],
                'player_name': player['player_name'],
                'rating': player['rating_adjusted']
            })

        return result

    except Exception as e:
        print(f"Error getting current top players: {e}")
        return []


def analyze_player_matchup_impact(home_team, away_team, player_ratings_df, boxscores_df, games_df):
    """
    Detailed analysis of player matchup dynamics for a given game.

    Returns diagnostic information about key player matchups.

    Args:
        home_team: Home team name
        away_team: Away team name
        player_ratings_df: DataFrame with player ratings
        boxscores_df: DataFrame with player boxscores
        games_df: DataFrame with game results

    Returns:
        Dict with matchup analysis details
    """
    try:
        home_top3 = get_current_top_players(home_team, player_ratings_df, n=3)
        away_top3 = get_current_top_players(away_team, player_ratings_df, n=3)

        analysis = {
            'home_team': home_team,
            'away_team': away_team,
            'home_top_players': home_top3,
            'away_top_players': away_top3,
            'key_matchups': []
        }

        # Analyze key matchups
        for home_player in home_top3:
            for away_player in away_top3:
                h2h = get_player_h2h_history(
                    home_player['player_id'],
                    away_player['player_id'],
                    boxscores_df,
                    games_df,
                    n_games=10
                )

                if h2h and h2h['games_played'] >= 3:
                    analysis['key_matchups'].append({
                        'home_player': home_player['player_name'],
                        'away_player': away_player['player_name'],
                        'games_played': h2h['games_played'],
                        'home_player_wins': h2h['player1_wins'],
                        'away_player_wins': h2h['player2_wins'],
                        'plus_minus_differential': h2h['plus_minus_differential'],
                        'home_player_avg_points': h2h['player1_avg_points'],
                        'away_player_avg_points': h2h['player2_avg_points']
                    })

        return analysis

    except Exception as e:
        print(f"Error analyzing player matchup impact: {e}")
        return None


# Test functions
if __name__ == '__main__':
    print("Testing Player H2H Analysis...")
    print("=" * 80)

    # Load data
    print("\nLoading data...")
    player_ratings = load_csv_to_dataframe('data/exports/player_ratings_bpm_adjusted.csv')
    boxscores = load_csv_to_dataframe('data/raw/player_boxscores_all.csv')
    games = load_csv_to_dataframe('data/raw/nba_games_all.csv')

    print(f"Loaded {len(player_ratings)} player ratings")
    print(f"Loaded {len(boxscores)} boxscore entries")
    print(f"Loaded {len(games)} games")

    # Test 1: Get top players for a team
    print("\nTest 1: Top Players for Lakers")
    print("-" * 80)
    lakers_top3 = get_current_top_players("Los Angeles Lakers", player_ratings, n=3)
    for i, player in enumerate(lakers_top3, 1):
        print(f"{i}. {player['player_name']}: {player['rating']:.1f} ELO")

    # Test 2: Player H2H adjustment
    print("\nTest 2: Player H2H Adjustment - Lakers vs Celtics")
    print("-" * 80)
    adjustment = calculate_player_h2h_adjustment(
        "Los Angeles Lakers",
        "Boston Celtics",
        player_ratings,
        boxscores,
        games
    )
    print(f"Player H2H Adjustment: {adjustment:+.2f} ELO points for Lakers")

    # Test 3: Detailed matchup analysis
    print("\nTest 3: Detailed Matchup Analysis - Lakers vs Celtics")
    print("-" * 80)
    analysis = analyze_player_matchup_impact(
        "Los Angeles Lakers",
        "Boston Celtics",
        player_ratings,
        boxscores,
        games
    )

    if analysis:
        print(f"\nLakers Top 3:")
        for player in analysis['home_top_players']:
            print(f"  - {player['player_name']} ({player['rating']:.1f})")

        print(f"\nCeltics Top 3:")
        for player in analysis['away_top_players']:
            print(f"  - {player['player_name']} ({player['rating']:.1f})")

        print(f"\nKey Matchups with History ({len(analysis['key_matchups'])} found):")
        for matchup in analysis['key_matchups']:
            print(f"\n  {matchup['home_player']} vs {matchup['away_player']}")
            print(f"    Games: {matchup['games_played']}")
            print(f"    Record: {matchup['home_player_wins']}-{matchup['away_player_wins']}")
            print(f"    +/- Differential: {matchup['plus_minus_differential']:+.1f}")
            print(f"    PPG: {matchup['home_player_avg_points']:.1f} vs {matchup['away_player_avg_points']:.1f}")
