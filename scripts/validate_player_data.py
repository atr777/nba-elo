"""
Validate Player Boxscore Data Quality
========================================
Comprehensive validation of scraped player boxscore data.

Checks:
1. File integrity and size
2. Missing critical fields
3. Data completeness per game
4. Player ID consistency
5. Minutes per game totals
6. Star player sample verification
7. Date range alignment with team games

Usage:
    python scripts/validate_player_data.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Color codes for terminal output (Windows compatible)
class Colors:
    GREEN = ''
    RED = ''
    YELLOW = ''
    BLUE = ''
    RESET = ''

def validate_player_data():
    """Run comprehensive validation on player boxscore data"""

    print("=" * 80)
    print("NBA ELO PLAYER BOXSCORE DATA VALIDATION")
    print("=" * 80)

    # Paths
    player_data_path = Path('data/raw/player_boxscores_all.csv')
    team_data_path = Path('data/raw/nba_games_all.csv')

    # Load data
    print("\n[1/8] Loading player boxscore data...")
    if not player_data_path.exists():
        print(f"ERROR: File not found: {player_data_path}")
        return False

    try:
        player_df = pd.read_csv(player_data_path)
        print(f"  Loaded {len(player_df):,} player boxscore records")
        print(f"  File size: {player_data_path.stat().st_size / (1024*1024):.1f} MB")
    except Exception as e:
        print(f"ERROR: Failed to load player data: {e}")
        return False

    # Check columns
    print("\n[2/8] Checking data structure...")
    print(f"  Columns found: {list(player_df.columns)}")

    basic_columns = ['game_id', 'player_id', 'player_name', 'team_id', 'team_name', 'minutes']
    stat_columns = ['plus_minus', 'points', 'rebounds', 'assists', 'steals', 'blocks', 'turnovers']

    missing_basic = [col for col in basic_columns if col not in player_df.columns]
    missing_stats = [col for col in stat_columns if col not in player_df.columns]

    if missing_basic:
        print(f"  ERROR: Missing basic columns: {missing_basic}")
        return False
    else:
        print(f"  OK: All {len(basic_columns)} basic columns present")

    if missing_stats:
        print(f"  CRITICAL WARNING: Missing stat columns: {missing_stats}")
        print(f"  NOTE: These stats are REQUIRED for player ELO calculations!")
        print(f"  Current data only has: player identifiers, team, minutes, position")
        print(f"  Need to re-scrape with full box score stats enabled")
    else:
        print(f"  OK: All stat columns present")

    # Check for missing data
    print("\n[3/8] Checking for missing critical fields...")
    critical_fields = ['game_id', 'player_id', 'player_name', 'team_id', 'team_name', 'minutes']

    issues_found = False
    for field in critical_fields:
        if field in player_df.columns:
            missing_count = player_df[field].isna().sum()
            if missing_count > 0:
                print(f"  WARNING: {field} has {missing_count:,} missing values")
                issues_found = True

    if not issues_found:
        print("  OK: No missing values in basic fields")

    # Check if stats are available
    has_stats = all(col in player_df.columns for col in stat_columns)
    if not has_stats:
        print("\n  CRITICAL: Player stats (points, rebounds, assists, +/-) are MISSING!")
        print("  Phase 3 implementation CANNOT proceed without these stats.")
        print("  Recommendation: Re-run nba_box_scraper.py with stats enabled")

    # Check minutes distribution
    print("\n[4/8] Analyzing minutes distribution...")
    player_df['minutes'] = pd.to_numeric(player_df['minutes'], errors='coerce')

    total_minutes = player_df['minutes'].sum()
    avg_minutes = player_df['minutes'].mean()
    median_minutes = player_df['minutes'].median()

    print(f"  Average minutes per player: {avg_minutes:.1f}")
    print(f"  Median minutes per player: {median_minutes:.1f}")
    print(f"  Total minutes (all records): {total_minutes:,.0f}")

    # Minutes per game check
    print("\n[5/8] Validating minutes per game (should ~240)...")
    minutes_per_game = player_df.groupby('game_id')['minutes'].sum()

    avg_mpg = minutes_per_game.mean()
    games_with_data = len(minutes_per_game)

    print(f"  Games with player data: {games_with_data:,}")
    print(f"  Average minutes per game: {avg_mpg:.1f}")

    # Check for games with suspicious minutes
    low_minutes = minutes_per_game[minutes_per_game < 200].count()
    high_minutes = minutes_per_game[minutes_per_game > 280].count()

    if low_minutes > 0:
        print(f"  WARNING: {low_minutes:,} games with < 200 minutes (possible incomplete data)")
    if high_minutes > 0:
        print(f"  INFO: {high_minutes:,} games with > 280 minutes (overtime games)")

    if 235 <= avg_mpg <= 245:
        print("  OK: Average minutes per game is within expected range (235-245)")
    else:
        print(f"  WARNING: Average {avg_mpg:.1f} is outside expected range")

    # Check unique entities
    print("\n[6/8] Analyzing unique entities...")
    unique_players = player_df['player_id'].nunique()
    unique_teams = player_df['team_id'].nunique()
    unique_games = player_df['game_id'].nunique()

    print(f"  Unique players: {unique_players:,}")
    print(f"  Unique teams: {unique_teams}")
    print(f"  Unique games: {unique_games:,}")

    # Load team data and compare
    print("\n[7/8] Comparing with team game data...")
    try:
        team_df = pd.read_csv(team_data_path)

        # Filter completed games only
        completed_games = team_df[
            (team_df['home_score'].astype(int) > 0) |
            (team_df['away_score'].astype(int) > 0)
        ]

        total_team_games = len(completed_games)

        print(f"  Total completed team games: {total_team_games:,}")
        print(f"  Games with player data: {unique_games:,}")

        coverage_pct = (unique_games / total_team_games) * 100
        print(f"  Coverage: {coverage_pct:.1f}%")

        if coverage_pct >= 95:
            print("  OK: Excellent coverage (>95%)")
        elif coverage_pct >= 90:
            print("  INFO: Good coverage (>90%)")
        else:
            print(f"  WARNING: Low coverage ({coverage_pct:.1f}%)")

        # Extract dates from game_id (format: YYYYMMDDGGG where first 8 digits are date)
        player_df['date_extracted'] = player_df['game_id'].astype(str).str[:8].astype(int)
        player_min_date = player_df['date_extracted'].min()
        player_max_date = player_df['date_extracted'].max()

        team_dates = pd.to_numeric(completed_games['date'], errors='coerce')
        team_min_date = team_dates.min()
        team_max_date = team_dates.max()

        print(f"\n  Date ranges:")
        print(f"    Player data: {int(player_min_date)} to {int(player_max_date)}")
        print(f"    Team data:   {int(team_min_date)} to {int(team_max_date)}")

        if player_min_date == team_min_date and player_max_date == team_max_date:
            print("  OK: Date ranges match perfectly")
        else:
            print("  INFO: Date ranges differ slightly (expected for failed games)")

    except Exception as e:
        print(f"  WARNING: Could not compare with team data: {e}")

    # Sample star players
    print("\n[8/8] Spot-checking star players...")

    # Get players with most games
    player_game_counts = player_df.groupby(['player_id', 'player_name']).size()
    top_players = player_game_counts.nlargest(10)

    print("\n  Top 10 players by game appearances:")
    for (player_id, player_name), game_count in top_players.items():
        avg_min = player_df[player_df['player_id'] == player_id]['minutes'].mean()
        print(f"    {player_name}: {game_count} games, {avg_min:.1f} mpg")

    # If we have stats, show top scorers
    if 'points' in player_df.columns:
        # Only consider players with significant playing time
        regular_players = player_df[player_df['minutes'] >= 15]
        if len(regular_players) > 0:
            top_scorers = regular_players.groupby(['player_id', 'player_name'])['points'].mean().nlargest(10)

            print("\n  Top 10 scorers (min 15 mpg):")
            for (player_id, player_name), avg_points in top_scorers.items():
                games = len(player_df[(player_df['player_id'] == player_id) & (player_df['minutes'] >= 15)])
                avg_min = player_df[player_df['player_id'] == player_id]['minutes'].mean()
                print(f"    {player_name}: {avg_points:.1f} ppg, {avg_min:.1f} mpg ({games} games)")
    else:
        print("\n  SKIPPED: Cannot show scoring stats (points column not available)")

    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    print(f"\n  Total Records: {len(player_df):,}")
    print(f"  Unique Players: {unique_players:,}")
    print(f"  Unique Games: {unique_games:,}")

    try:
        print(f"  Date Range: {int(player_min_date)} to {int(player_max_date)}")
        print(f"  Average Minutes/Game: {avg_mpg:.1f}")
        if 'coverage_pct' in locals():
            print(f"  Coverage vs Team Games: {coverage_pct:.1f}%")
    except:
        pass

    print("\n  Data Quality: ", end="")

    # Check if we have stats
    has_stats = all(col in player_df.columns for col in ['plus_minus', 'points', 'rebounds', 'assists'])

    if not has_stats:
        print("INCOMPLETE [XX]")
        print("\n  CRITICAL ISSUE: Player statistics (points, rebounds, assists, +/-) are MISSING!")
        print("\n  Current data contains:")
        print("    - Player identifiers (player_id, player_name)")
        print("    - Team information (team_id, team_name)")
        print("    - Playing time (minutes, starter/bench)")
        print("    - Position and jersey number")
        print("\n  MISSING (required for Phase 3):")
        print("    - Points, rebounds, assists")
        print("    - Plus/minus (+/-)")
        print("    - Steals, blocks, turnovers")
        print("    - Field goals, 3-pointers, free throws")
        print("\n  ACTION REQUIRED:")
        print("    The nba_box_scraper.py script needs to be updated to collect full box score stats.")
        print("    Currently it only collects player metadata, not performance stats.")
        print("\n  Recommendation:")
        print("    1. Check scripts/nba_box_scraper.py for stat collection logic")
        print("    2. Verify ESPN API endpoints include box score stats")
        print("    3. Re-run scraper with full stats enabled")
        print("    4. Phase 3 cannot proceed without this data")
        return False
    elif 'coverage_pct' in locals() and coverage_pct >= 95 and 235 <= avg_mpg <= 245 and not issues_found:
        print("EXCELLENT [OK]")
        print("\n  The player boxscore data is complete and ready for Phase 3!")
        return True
    elif 'coverage_pct' in locals() and coverage_pct >= 90 and 230 <= avg_mpg <= 250:
        print("GOOD [OK]")
        print("\n  The player boxscore data has minor issues but is usable for Phase 3.")
        return True
    else:
        print("NEEDS ATTENTION [!!]")
        print("\n  Review warnings above before proceeding to Phase 3.")
        return False


if __name__ == '__main__':
    success = validate_player_data()
    sys.exit(0 if success else 1)
