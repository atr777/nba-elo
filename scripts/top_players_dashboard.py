"""
Top Players Dashboard
Quick visualization script showing top 50 players by current ELO rating.
"""

import pandas as pd
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.utils.file_io import load_csv_to_dataframe


def display_top_players(
    player_ratings_file: str = 'data/exports/player_ratings.csv',
    n: int = 50,
    min_games: int = 50
):
    """
    Display top N players by ELO rating.

    Args:
        player_ratings_file: Path to player ratings CSV
        n: Number of players to show
        min_games: Minimum games played to qualify
    """
    print("=" * 100)
    print(f"TOP {n} NBA PLAYERS BY ELO RATING (Minimum {min_games} games)")
    print("=" * 100)
    print()

    # Load player ratings
    df = load_csv_to_dataframe(player_ratings_file)

    # Filter by minimum games
    df = df[df['games_played'] >= min_games]

    # Sort by rating descending
    df = df.sort_values('rating', ascending=False).head(n)

    # Display header
    print(f"{'Rank':<6} {'Player':<30} {'Rating':<10} {'Games':<10} {'Season':<10}")
    print("-" * 100)

    # Display each player
    for idx, (_, player) in enumerate(df.iterrows(), 1):
        rank = f"#{idx}"
        name = player['player_name'][:28]  # Truncate long names
        rating = f"{player['rating']:.1f}"
        games = f"{player['games_played']:,}"
        season = str(player['last_season'])

        # Add visual indicator for elite players (rating > 1650)
        indicator = "*" if player['rating'] > 1650 else " "

        print(f"{rank:<6} {name:<30} {rating:<10} {games:<10} {season:<10} {indicator}")

    print()
    print("=" * 100)

    # Summary statistics
    print("\nSummary Statistics:")
    print(f"  Total players rated: {len(load_csv_to_dataframe(player_ratings_file)):,}")
    print(f"  Players shown: {len(df)}")
    print(f"  Highest rating: {df.iloc[0]['rating']:.1f} ({df.iloc[0]['player_name']})")
    print(f"  50th ranked: {df.iloc[min(49, len(df)-1)]['rating']:.1f} ({df.iloc[min(49, len(df)-1)]['player_name']})" if len(df) >= 50 else "")
    print(f"  Average rating (top {n}): {df['rating'].mean():.1f}")
    print(f"  Median rating (top {n}): {df['rating'].median():.1f}")
    print()

    # Elite tier breakdown
    elite_1700 = len(df[df['rating'] >= 1700])
    elite_1650 = len(df[df['rating'] >= 1650])
    elite_1600 = len(df[df['rating'] >= 1600])

    print("Elite Player Tiers:")
    print(f"  [MVP] 1700+ (MVP candidates): {elite_1700} players")
    print(f"  [ALL] 1650+ (All-Stars): {elite_1650} players")
    print(f"  [TOP] 1600+ (Above Average): {elite_1600} players")
    print()

    # Show rating distribution by decade of games
    print("Experience Distribution (Top 50):")
    rookies = len(df[df['games_played'] < 100])
    young = len(df[(df['games_played'] >= 100) & (df['games_played'] < 300)])
    prime = len(df[(df['games_played'] >= 300) & (df['games_played'] < 600)])
    veteran = len(df[df['games_played'] >= 600])

    print(f"  Rookies/Young (<100 games): {rookies}")
    print(f"  Developing (100-299 games): {young}")
    print(f"  Prime (300-599 games): {prime}")
    print(f"  Veterans (600+ games): {veteran}")
    print()


def compare_eras(player_ratings_file: str = 'data/exports/player_ratings.csv'):
    """
    Compare top players across different eras.

    Args:
        player_ratings_file: Path to player ratings CSV
    """
    df = load_csv_to_dataframe(player_ratings_file)

    print("=" * 100)
    print("TOP PLAYERS BY ERA")
    print("=" * 100)
    print()

    # Define eras based on last season played
    eras = [
        (2000, 2009, "2000s Era"),
        (2010, 2019, "2010s Era"),
        (2020, 2025, "2020s Era (Current)")
    ]

    for start_year, end_year, era_name in eras:
        era_df = df[(df['last_season'] >= start_year) & (df['last_season'] <= end_year)]
        era_df = era_df[era_df['games_played'] >= 100]  # Min 100 games
        era_df = era_df.sort_values('rating', ascending=False).head(10)

        print(f"\n{era_name} - Top 10:")
        print(f"{'Rank':<6} {'Player':<30} {'Rating':<10} {'Games':<10}")
        print("-" * 70)

        for idx, (_, player) in enumerate(era_df.iterrows(), 1):
            rank = f"#{idx}"
            name = player['player_name'][:28]
            rating = f"{player['rating']:.1f}"
            games = f"{player['games_played']:,}"

            print(f"{rank:<6} {name:<30} {rating:<10} {games:<10}")

    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Display top NBA players by ELO rating')
    parser.add_argument('--ratings', default='data/exports/player_ratings.csv',
                       help='Path to player ratings CSV file')
    parser.add_argument('--n', type=int, default=50,
                       help='Number of players to show (default: 50)')
    parser.add_argument('--min-games', type=int, default=50,
                       help='Minimum games played to qualify (default: 50)')
    parser.add_argument('--eras', action='store_true',
                       help='Show top players by era instead')

    args = parser.parse_args()

    if args.eras:
        compare_eras(args.ratings)
    else:
        display_top_players(args.ratings, args.n, args.min_games)
