"""
Quick diagnostic to inspect the ELO engine output format
"""

import pandas as pd
from pathlib import Path

def inspect_elo_output():
    """Inspect the structure of the ELO output file"""
    
    elo_file = "data/exports/team_elo_history_phase_1_5.csv"
    
    if not Path(elo_file).exists():
        print(f"❌ File not found: {elo_file}")
        print("Run the ELO engine first:")
        print("  python src/engines/team_elo_engine.py \\")
        print("      --input data/raw/nba_games_all.csv \\")
        print("      --output data/exports/team_elo_history_phase_1_5.csv")
        return
    
    # Load first few rows
    df = pd.read_csv(elo_file, nrows=5)
    
    print("=" * 70)
    print("ELO OUTPUT FILE INSPECTION")
    print("=" * 70)
    
    print(f"\n📁 File: {elo_file}")
    print(f"📊 Total rows: {len(pd.read_csv(elo_file)):,}")
    
    print(f"\n📋 Columns ({len(df.columns)}):")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i:2d}. {col}")
    
    print(f"\n🔍 Sample Data (first 5 rows):")
    print(df.to_string(index=False))
    
    print(f"\n✅ Data Types:")
    for col, dtype in df.dtypes.items():
        print(f"  {col:30s} : {dtype}")
    
    # Check for key columns
    print(f"\n🎯 Key Column Check:")
    required_cols = {
        'game_id': ['game_id'],
        'team_id': ['team_id', 'team'],
        'elo_rating': ['elo_rating', 'elo', 'rating', 'elo_before', 'elo_rating_before'],
        'home_indicator': ['is_home', 'home', 'is_home_team', 'home_team'],
        'win_indicator': ['won', 'win', 'winner', 'is_winner']
    }
    
    for key, possible_names in required_cols.items():
        found = None
        for name in possible_names:
            if name in df.columns:
                found = name
                break
        if found:
            print(f"  ✓ {key:20s} → Found as '{found}'")
        else:
            print(f"  ✗ {key:20s} → NOT FOUND (expected one of: {possible_names})")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    inspect_elo_output()
