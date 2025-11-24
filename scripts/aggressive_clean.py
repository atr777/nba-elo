"""
Aggressive Data Cleaning - Remove ALL Non-NBA Teams
===================================================
This script aggressively filters out any team that doesn't match
the 30 current NBA franchises.
"""

import pandas as pd
from pathlib import Path


# Official 30 NBA teams (as of 2024-25 season)
NBA_TEAMS = [
    'Atlanta Hawks',
    'Boston Celtics',
    'Brooklyn Nets',
    'Charlotte Hornets',
    'Chicago Bulls',
    'Cleveland Cavaliers',
    'Dallas Mavericks',
    'Denver Nuggets',
    'Detroit Pistons',
    'Golden State Warriors',
    'Houston Rockets',
    'Indiana Pacers',
    'Los Angeles Clippers',
    'Los Angeles Lakers',
    'Memphis Grizzlies',
    'Miami Heat',
    'Milwaukee Bucks',
    'Minnesota Timberwolves',
    'New Orleans Pelicans',
    'New York Knicks',
    'Oklahoma City Thunder',
    'Orlando Magic',
    'Philadelphia 76ers',
    'Phoenix Suns',
    'Portland Trail Blazers',
    'Sacramento Kings',
    'San Antonio Spurs',
    'Toronto Raptors',
    'Utah Jazz',
    'Washington Wizards',
]

# Historical NBA teams (for older data)
HISTORICAL_NBA_TEAMS = [
    'Seattle SuperSonics',  # Moved to OKC in 2008
    'New Jersey Nets',  # Became Brooklyn in 2012
    'Charlotte Bobcats',  # Became Hornets in 2014
    'Vancouver Grizzlies',  # Moved to Memphis in 2001
    'New Orleans Hornets',  # Became Pelicans in 2013
    'New Orleans/Oklahoma City Hornets',  # Temporary relocation
]

# Combine all valid NBA teams
ALL_VALID_NBA_TEAMS = NBA_TEAMS + HISTORICAL_NBA_TEAMS


def is_valid_nba_team(team_name: str) -> bool:
    """
    Check if a team is a valid NBA team (current or historical).
    
    Args:
        team_name: Team name to check
    
    Returns:
        True if valid NBA team, False otherwise
    """
    if pd.isna(team_name):
        return False
    
    # Exact match against whitelist
    return team_name in ALL_VALID_NBA_TEAMS


def aggressive_clean(input_path: str, output_path: str, verbose: bool = True):
    """
    Aggressively clean by keeping ONLY valid NBA teams.
    
    Args:
        input_path: Path to input CSV
        output_path: Path to save cleaned CSV
        verbose: Print details
    """
    if not Path(input_path).exists():
        print(f"❌ File not found: {input_path}")
        return
    
    if verbose:
        print(f"\n📁 Loading: {input_path}")
    
    df = pd.read_csv(input_path)
    original_count = len(df)
    original_games = df['game_id'].nunique() if 'game_id' in df.columns else 'N/A'
    
    if verbose:
        print(f"   Original: {original_count:,} records, {original_games} games")
    
    # Keep only rows where BOTH team and opponent are valid NBA teams
    df['team_valid'] = df['team_name'].apply(is_valid_nba_team)
    
    if 'opponent_name' in df.columns:
        df['opponent_valid'] = df['opponent_name'].apply(is_valid_nba_team)
        mask = df['team_valid'] & df['opponent_valid']
    else:
        mask = df['team_valid']
    
    # Show what's being removed
    if verbose:
        removed = df[~mask]
        if len(removed) > 0:
            removed_teams = set(removed['team_name'].unique())
            if 'opponent_name' in removed.columns:
                removed_teams.update(removed['opponent_name'].unique())
            
            # Remove valid teams from the removed list (to show only exhibition)
            exhibition_only = removed_teams - set(ALL_VALID_NBA_TEAMS)
            
            if exhibition_only:
                print(f"\n   ⚠️  Removing {len(removed):,} records with these teams:")
                for team in sorted(exhibition_only):
                    print(f"      ❌ {team}")
    
    # Clean
    df_clean = df[mask].copy()
    df_clean = df_clean.drop(columns=['team_valid'], errors='ignore')
    df_clean = df_clean.drop(columns=['opponent_valid'], errors='ignore')
    
    clean_count = len(df_clean)
    clean_games = df_clean['game_id'].nunique() if 'game_id' in df_clean.columns else 'N/A'
    
    if verbose:
        print(f"\n   ✅ Cleaned: {clean_count:,} records, {clean_games} games")
        print(f"   📊 Removed: {original_count - clean_count:,} records")
    
    # Save
    df_clean.to_csv(output_path, index=False)
    
    if verbose:
        print(f"   💾 Saved: {output_path}")
    
    return df_clean


def main():
    """Aggressively clean all ELO files."""
    print("=" * 70)
    print("AGGRESSIVE CLEANING - NBA TEAMS ONLY")
    print("=" * 70)
    print(f"\nWhitelist: {len(ALL_VALID_NBA_TEAMS)} valid NBA teams")
    print("Strategy: Keep ONLY games between valid NBA teams")
    
    files_to_clean = [
        ("data/exports/team_elo_history_phase_1_5.csv", 
         "data/exports/team_elo_history_phase_1_5_clean.csv"),
        ("data/exports/team_elo_with_travel.csv", 
         "data/exports/team_elo_with_travel_clean.csv"),
    ]
    
    for input_path, output_path in files_to_clean:
        if Path(input_path).exists():
            print("\n" + "-" * 70)
            aggressive_clean(input_path, output_path)
    
    print("\n" + "=" * 70)
    print("AGGRESSIVE CLEANING COMPLETE!")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Verify cleaning: python scripts/diagnostic_check_teams.py")
    print("2. Create visualizations: python src/analytics/elo_visualizer.py")


if __name__ == "__main__":
    main()
