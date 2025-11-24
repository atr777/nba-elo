"""
Quick Game ID Extractor
=======================
Extract game IDs from your nba_games_all.csv for testing
"""

import pandas as pd
import sys

def extract_game_ids(csv_path, from_season=None, n_games=10):
    """
    Extract game IDs from the CSV file
    
    Args:
        csv_path: Path to nba_games_all.csv
        from_season: Optional season filter (e.g., '2024' or '2023-24')
        n_games: Number of games to extract
    """
    try:
        # Load the data
        df = pd.read_csv(csv_path)
        print(f"✓ Loaded {len(df)} games")
        print(f"✓ Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"✓ Columns: {df.columns.tolist()}\n")
        
        # Filter by season if specified
        if from_season:
            # Handle both 'YYYY' and 'YYYY-YY' formats
            if len(from_season) == 4:
                df = df[df['date'].astype(str).str.startswith(from_season)]
            else:
                # Extract year from YYYY-YY format
                year = from_season.split('-')[0]
                df = df[df['date'].astype(str).str.startswith(year)]
            
            print(f"✓ Filtered to {len(df)} games from {from_season} season\n")
        
        # Get most recent games
        df_sorted = df.sort_values('date', ascending=False)
        sample = df_sorted.head(n_games)
        
        # Find game_id column
        game_id_col = None
        for col in ['game_id', 'gameId', 'id', 'Game_ID']:
            if col in df.columns:
                game_id_col = col
                break
        
        if game_id_col is None:
            print("❌ Could not find game_id column!")
            return None
        
        # Extract game IDs
        game_ids = sample[game_id_col].tolist()
        
        print(f"📋 Extracted {len(game_ids)} game IDs:\n")
        print("Game IDs (copy these for testing):")
        print("-" * 40)
        for gid in game_ids:
            print(gid)
        print("-" * 40)
        
        # Also show with game info
        print("\n📊 Game Details:")
        print("-" * 80)
        cols_to_show = [game_id_col, 'date', 'home_team_name', 'away_team_name', 'home_score', 'away_score']
        cols_available = [col for col in cols_to_show if col in sample.columns]
        print(sample[cols_available].to_string(index=False))
        
        return game_ids
        
    except FileNotFoundError:
        print(f"❌ File not found: {csv_path}")
        print("\nPlease provide the correct path to your nba_games_all.csv file")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    # Check if CSV path provided as argument
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        print("Usage: python extract_game_ids.py <path_to_nba_games_all.csv> [season] [n_games]")
        print("\nExamples:")
        print("  python extract_game_ids.py nba_games_all.csv")
        print("  python extract_game_ids.py nba_games_all.csv 2024 10")
        print("  python extract_game_ids.py data/nba_games_all.csv 2023-24 5")
        sys.exit(1)
    
    # Optional parameters
    from_season = sys.argv[2] if len(sys.argv) > 2 else None
    n_games = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    
    game_ids = extract_game_ids(csv_path, from_season, n_games)
    
    if game_ids:
        print(f"\n✅ Successfully extracted {len(game_ids)} game IDs")
        print("\n💡 Next step: Use these game IDs with test_box_scraper_with_real_data.py")
