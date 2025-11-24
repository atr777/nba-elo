"""
Test the updated box score scraper with a single game
"""

import sys
sys.path.insert(0, 'scripts')

from nba_box_scraper import NBABoxScraper
import pandas as pd

# Test with a recent game
test_game_id = '401584901'  # Recent Warriors vs Clippers game

print("Testing updated NBA Box Score Scraper")
print("=" * 70)
print(f"Test game ID: {test_game_id}")
print()

# Initialize scraper
scraper = NBABoxScraper()

# Fetch boxscore
print("Fetching boxscore...")
players = scraper.fetch_boxscore(test_game_id)

if players:
    print(f"[OK] Successfully fetched {len(players)} player records")
    print()

    # Convert to DataFrame for analysis
    df = pd.DataFrame(players)

    # Show columns
    print("Columns extracted:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i}. {col}")
    print()

    # Check for stats
    required_stats = ['points', 'rebounds', 'assists', 'plus_minus']
    missing_stats = [stat for stat in required_stats if stat not in df.columns]

    if missing_stats:
        print(f"[ERROR] MISSING STATS: {missing_stats}")
    else:
        print("[OK] All required stats present!")
    print()

    # Show sample data (top scorer)
    if 'points' in df.columns:
        df_sorted = df.sort_values('points', ascending=False)
        top_scorer = df_sorted.iloc[0]

        print("Top Scorer:")
        print(f"  Player: {top_scorer['player_name']}")
        print(f"  Team: {top_scorer['team_name']}")
        print(f"  Minutes: {top_scorer['minutes']:.1f}")
        print(f"  Points: {top_scorer.get('points', 'N/A')}")
        print(f"  Rebounds: {top_scorer.get('rebounds', 'N/A')}")
        print(f"  Assists: {top_scorer.get('assists', 'N/A')}")
        print(f"  Plus/Minus: {top_scorer.get('plus_minus', 'N/A')}")
        print(f"  FG: {top_scorer.get('fg_made', 'N/A')}-{top_scorer.get('fg_attempted', 'N/A')}")
        print()

        # Stats summary
        print("Stats Summary:")
        print(f"  Total points: {df['points'].sum()}")
        print(f"  Total rebounds: {df['rebounds'].sum()}")
        print(f"  Total assists: {df['assists'].sum()}")
        print(f"  Avg minutes: {df['minutes'].mean():.1f}")
        print()

        # Show all players with stats
        print("All players (first 5):")
        print(df[['player_name', 'minutes', 'points', 'rebounds', 'assists', 'plus_minus']].head())
        print()

        print("=" * 70)
        print("[OK] TEST PASSED: Scraper successfully extracts full box score stats!")
        print("=" * 70)
    else:
        print("[ERROR] TEST FAILED: Points column not found")
        print("Available columns:", list(df.columns))
else:
    print("[ERROR] TEST FAILED: No data returned")
    sys.exit(1)
