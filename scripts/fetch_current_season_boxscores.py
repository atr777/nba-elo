"""
Fetch Box Scores for 2025-26 Season
====================================

This script fetches player box score data for all completed games
in the 2025-26 season using the nba_api library.

Usage:
    python scripts/fetch_current_season_boxscores.py
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
from nba_api.stats.endpoints import leaguegamefinder, boxscoretraditionalv3
from datetime import datetime
import time

print("="*80)
print("FETCHING 2025-26 SEASON BOX SCORES")
print("="*80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Step 1: Load existing games to get game IDs
print("[STEP 1] Loading completed games from database...")
games = pd.read_csv('data/raw/nba_games_all.csv')
games['date'] = pd.to_datetime(games['date'], format='%Y%m%d')

# Filter for 2025-26 season completed games
season_games = games[
    (games['date'] >= '2025-10-01') &
    (games['date'] <= '2025-12-27') &
    (games['home_score'].notna())
].copy()

print(f"Found {len(season_games)} completed games in 2025-26 season")
print(f"Date range: {season_games['date'].min().date()} to {season_games['date'].max().date()}\n")

# Step 2: Load existing box scores
print("[STEP 2] Loading existing box score data...")
boxscore_file = 'data/raw/player_boxscores_all.csv'

try:
    existing_boxscores = pd.read_csv(boxscore_file)
    print(f"Loaded {len(existing_boxscores):,} existing box score records")
    existing_game_ids = set(existing_boxscores['game_id'].unique())
    print(f"Covering {len(existing_game_ids):,} unique games\n")
except FileNotFoundError:
    existing_boxscores = pd.DataFrame()
    existing_game_ids = set()
    print("No existing box score file found - will create new one\n")

# Step 3: Use nba_api to fetch box scores
print("[STEP 3] Fetching box scores from NBA API...")
print("This may take several minutes...\n")

# We need to map from our game format to NBA API game IDs
# For now, let's use the NBA API to fetch all games for the 2025-26 season

new_boxscore_records = []
errors = []

try:
    # Fetch all games from 2025-26 season using LeagueGameFinder
    print("Fetching game list from NBA API...")

    gamefinder = leaguegamefinder.LeagueGameFinder(
        season_nullable='2025-26',
        league_id_nullable='00',
        season_type_nullable='Regular Season'
    )

    nba_games = gamefinder.get_data_frames()[0]
    print(f"Found {len(nba_games)} game records from NBA API")

    # Get unique game IDs (each game appears twice, once for each team)
    unique_game_ids = nba_games['GAME_ID'].unique()
    print(f"Processing {len(unique_game_ids)} unique games...\n")

    # Filter to only games we don't have yet
    games_to_fetch = [g for g in unique_game_ids if g not in existing_game_ids]
    print(f"Need to fetch {len(games_to_fetch)} new games\n")

    if len(games_to_fetch) == 0:
        print("✅ All box scores are up to date!")
    else:
        for idx, game_id in enumerate(games_to_fetch, 1):
            try:
                print(f"[{idx}/{len(games_to_fetch)}] Fetching game {game_id}...", end=' ')

                # Fetch box score
                boxscore = boxscoretraditionalv3.BoxScoreTraditionalV3(game_id=game_id)
                player_stats = boxscore.get_data_frames()[0]  # PlayerStats dataframe

                # Transform to our format
                # Note: v3 API uses different column names than v2
                for _, player in player_stats.iterrows():
                    # Build player name from firstName and familyName
                    first_name = player.get('firstName', '')
                    family_name = player.get('familyName', '')
                    player_name = f"{first_name} {family_name}".strip() if first_name or family_name else None

                    record = {
                        'game_id': game_id,
                        'player_id': player.get('personId'),
                        'player_name': player_name,
                        'team_id': player.get('teamId'),
                        'team_name': player.get('teamTricode'),
                        'starter': player.get('position', '') != '',  # Players with position are starters
                        'position': player.get('position') if player.get('position', '') != '' else None,
                        'jersey': player.get('jerseyNum'),
                        'didNotPlay': player.get('minutes') is None or player.get('minutes') == '' or player.get('minutes') == '0:00',
                        'minutes': player.get('minutes'),
                        'points': int(player.get('points') or 0),
                        'fg_made': int(player.get('fieldGoalsMade') or 0),
                        'fg_attempted': int(player.get('fieldGoalsAttempted') or 0),
                        'three_pt_made': int(player.get('threePointersMade') or 0),
                        'three_pt_attempted': int(player.get('threePointersAttempted') or 0),
                        'ft_made': int(player.get('freeThrowsMade') or 0),
                        'ft_attempted': int(player.get('freeThrowsAttempted') or 0),
                        'rebounds': int(player.get('reboundsTotal') or 0),
                        'assists': int(player.get('assists') or 0),
                        'turnovers': int(player.get('turnovers') or 0),
                        'steals': int(player.get('steals') or 0),
                        'blocks': int(player.get('blocks') or 0),
                        'offensive_rebounds': int(player.get('reboundsOffensive') or 0),
                        'defensive_rebounds': int(player.get('reboundsDefensive') or 0),
                        'personal_fouls': int(player.get('foulsPersonal') or 0),
                        'plus_minus': player.get('plusMinusPoints')
                    }
                    new_boxscore_records.append(record)

                print(f"✓ ({len(player_stats)} players)")

                # Rate limiting - NBA API has rate limits
                time.sleep(0.6)  # ~100 requests per minute

            except Exception as e:
                print(f"✗ Error: {e}")
                errors.append((game_id, str(e)))
                time.sleep(1)  # Wait longer on error

        print(f"\n✅ Fetched box scores for {len(games_to_fetch) - len(errors)} games")
        if errors:
            print(f"⚠️  {len(errors)} games had errors")

except Exception as e:
    print(f"\n❌ Error fetching from NBA API: {e}")
    import traceback
    traceback.print_exc()

# Step 4: Combine and save
if len(new_boxscore_records) > 0:
    print(f"\n[STEP 4] Saving {len(new_boxscore_records):,} new box score records...")

    new_df = pd.DataFrame(new_boxscore_records)

    if len(existing_boxscores) > 0:
        combined = pd.concat([existing_boxscores, new_df], ignore_index=True)
    else:
        combined = new_df

    # Save
    combined.to_csv(boxscore_file, index=False)
    print(f"✅ Saved to {boxscore_file}")
    print(f"   Total records: {len(combined):,}")
    print(f"   Total games: {len(combined['game_id'].unique()):,}")
else:
    print("\n[STEP 4] No new records to save")

if errors:
    print(f"\n[ERRORS] {len(errors)} games failed:")
    for game_id, error in errors[:10]:  # Show first 10
        print(f"  - {game_id}: {error}")

print("\n" + "="*80)
print("COMPLETE")
print("="*80)
print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
