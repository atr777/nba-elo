"""
Merge newly scraped Nov 23-24 games into main dataset and recalculate ELO
"""
import pandas as pd
import sys

print("="*80)
print("UPDATING DATABASE WITH NOV 23-24, 2025 GAMES")
print("="*80)

# Step 1: Load existing data
print("\n[1/5] Loading existing game data...")
existing_games = pd.read_csv('data/raw/nba_games_all.csv')
print(f"  Existing games: {len(existing_games):,}")
print(f"  Latest date: {existing_games['date'].max()}")

# Step 2: Load new games
print("\n[2/5] Loading newly scraped games...")
new_games = pd.read_csv('data/raw/nba_games_nov23_24_2025.csv')
print(f"  New games: {len(new_games)}")
print(f"  Dates: {new_games['date'].unique()}")

# Step 3: Remove any existing Nov 23-24 games (in case they were scheduled placeholders)
print("\n[3/5] Removing old Nov 23-24 placeholder data...")
existing_games = existing_games[
    ~existing_games['date'].isin([20251123, 20251124])
]
print(f"  After removal: {len(existing_games):,} games")

# Step 4: Merge datasets
print("\n[4/5] Merging datasets...")
merged_games = pd.concat([existing_games, new_games], ignore_index=True)
merged_games = merged_games.sort_values(['date', 'game_id']).reset_index(drop=True)
print(f"  Total games after merge: {len(merged_games):,}")
print(f"  Date range: {merged_games['date'].min()} to {merged_games['date'].max()}")

# Step 5: Save merged dataset
print("\n[5/5] Saving updated dataset...")
merged_games.to_csv('data/raw/nba_games_all.csv', index=False)
print(f"  [OK] Saved: data/raw/nba_games_all.csv")

# Verify Lakers game
print("\n" + "="*80)
print("VERIFICATION - Lakers Nov 23 game:")
print("="*80)
lakers_nov23 = merged_games[
    ((merged_games['home_team_name'] == 'Los Angeles Lakers') |
     (merged_games['away_team_name'] == 'Los Angeles Lakers')) &
    (merged_games['date'] == 20251123)
]
if len(lakers_nov23) > 0:
    for _, g in lakers_nov23.iterrows():
        home = g['home_team_name']
        away = g['away_team_name']
        score = f"{int(g['home_score'])}-{int(g['away_score'])}"
        winner = "Lakers WON" if g['winner_team_id'] == 13 else "Lakers LOST"
        print(f"  {away} @ {home}: {score} - {winner}")
else:
    print("  [ERROR] Lakers game not found!")

print("\n" + "="*80)
print("NEXT STEP: Run daily_update.py to recalculate ELO ratings")
print("="*80)
