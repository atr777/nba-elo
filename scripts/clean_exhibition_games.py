"""
Data Cleaning: Remove All-Star and Exhibition Games
===================================================
Filters out non-regular-season games from NBA data.

Teams to exclude:
- All-Star Game teams (Team LeBron, Team Giannis, Team Durant, Team Stephen, etc.)
- Rising Stars teams (Team Chuck, Team Shaq, World, USA)
- Exhibition games
"""

import pandas as pd
from pathlib import Path


def get_exhibition_team_patterns():
    """
    Return list of patterns that identify non-NBA regular season teams.
    
    Returns:
        List of team name patterns to exclude
    """
    exhibition_patterns = [
        'Team LeBron',
        'Team Giannis', 
        'Team Durant',
        'Team Stephen',
        'Team Curry',
        'Team Chuck',
        'Team Shaq',
        'Team World',
        'Team USA',
        'World Team',
        'USA Team',
        'East All-Stars',
        'West All-Stars',
        'Eastern Conference',
        'Western Conference',
    ]
    
    return exhibition_patterns


def is_exhibition_team(team_name: str) -> bool:
    """
    Check if a team name indicates an exhibition/All-Star game.
    
    Args:
        team_name: Team name to check
    
    Returns:
        True if team is exhibition/All-Star, False if regular NBA team
    """
    if pd.isna(team_name):
        return False
    
    team_name_lower = str(team_name).lower()
    
    # Check against patterns
    patterns = get_exhibition_team_patterns()
    for pattern in patterns:
        if pattern.lower() in team_name_lower:
            return True
    
    # Check for "Team" prefix (All-Star captain teams)
    if team_name.startswith('Team '):
        return True
    
    return False


def clean_elo_data(
    input_path: str,
    output_path: str,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Remove All-Star and exhibition games from ELO data.
    
    Args:
        input_path: Path to raw ELO history CSV
        output_path: Path to save cleaned data
        verbose: Print detailed info
    
    Returns:
        Cleaned DataFrame
    """
    if verbose:
        print("=" * 70)
        print("CLEANING NBA ELO DATA - REMOVING EXHIBITION GAMES")
        print("=" * 70)
        print()
    
    # Load data
    if verbose:
        print(f"Loading data from: {input_path}")
    df = pd.read_csv(input_path)
    original_count = len(df)
    original_games = df['game_id'].nunique()
    
    if verbose:
        print(f"✓ Loaded {original_count:,} records ({original_games:,} games)")
    
    # Identify exhibition teams
    df['is_exhibition'] = df['team_name'].apply(is_exhibition_team)
    df['opponent_is_exhibition'] = df['opponent_name'].apply(is_exhibition_team)
    
    # Remove any game involving exhibition teams
    exhibition_mask = df['is_exhibition'] | df['opponent_is_exhibition']
    exhibition_records = exhibition_mask.sum()
    exhibition_games = df[exhibition_mask]['game_id'].nunique()
    
    if verbose and exhibition_records > 0:
        print(f"\n⚠ Found exhibition games:")
        print(f"  Records: {exhibition_records:,}")
        print(f"  Unique games: {exhibition_games:,}")
        
        # Show which teams were found
        exhibition_teams = set()
        exhibition_teams.update(df[df['is_exhibition']]['team_name'].unique())
        exhibition_teams.update(df[df['opponent_is_exhibition']]['opponent_name'].unique())
        
        print(f"\n  Teams identified as exhibition:")
        for team in sorted(exhibition_teams):
            print(f"    - {team}")
    
    # Clean data
    df_clean = df[~exhibition_mask].copy()
    
    # Drop temporary columns
    df_clean = df_clean.drop(columns=['is_exhibition', 'opponent_is_exhibition'])
    
    clean_count = len(df_clean)
    clean_games = df_clean['game_id'].nunique()
    
    if verbose:
        print(f"\n✓ Cleaned data:")
        print(f"  Records: {clean_count:,} (removed {original_count - clean_count:,})")
        print(f"  Games: {clean_games:,} (removed {original_games - clean_games:,})")
        print(f"  Unique teams: {df_clean['team_name'].nunique()}")
    
    # Save cleaned data
    df_clean.to_csv(output_path, index=False)
    
    if verbose:
        print(f"\n✓ Saved cleaned data to: {output_path}")
        print("=" * 70)
    
    return df_clean


def clean_raw_game_data(
    input_path: str,
    output_path: str,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Remove All-Star games from raw game data.
    
    Args:
        input_path: Path to raw games CSV (e.g., nba_games_all.csv)
        output_path: Path to save cleaned games
        verbose: Print detailed info
    
    Returns:
        Cleaned DataFrame
    """
    if verbose:
        print("=" * 70)
        print("CLEANING RAW GAME DATA - REMOVING ALL-STAR GAMES")
        print("=" * 70)
        print()
    
    # Load data
    if verbose:
        print(f"Loading data from: {input_path}")
    df = pd.read_csv(input_path)
    original_count = len(df)
    
    if verbose:
        print(f"✓ Loaded {original_count:,} games")
    
    # Check both home and away teams
    df['home_is_exhibition'] = df['home_team_name'].apply(is_exhibition_team)
    df['away_is_exhibition'] = df['away_team_name'].apply(is_exhibition_team)
    
    exhibition_mask = df['home_is_exhibition'] | df['away_is_exhibition']
    exhibition_count = exhibition_mask.sum()
    
    if verbose and exhibition_count > 0:
        print(f"\n⚠ Found {exhibition_count:,} All-Star/exhibition games")
        
        exhibition_teams = set()
        exhibition_teams.update(df[df['home_is_exhibition']]['home_team_name'].unique())
        exhibition_teams.update(df[df['away_is_exhibition']]['away_team_name'].unique())
        
        print(f"\n  Teams identified:")
        for team in sorted(exhibition_teams):
            print(f"    - {team}")
    
    # Clean
    df_clean = df[~exhibition_mask].copy()
    df_clean = df_clean.drop(columns=['home_is_exhibition', 'away_is_exhibition'])
    
    clean_count = len(df_clean)
    
    if verbose:
        print(f"\n✓ Cleaned data:")
        print(f"  Games: {clean_count:,} (removed {original_count - clean_count:,})")
        print(f"  Unique teams: {df_clean['home_team_name'].nunique()}")
    
    # Save
    df_clean.to_csv(output_path, index=False)
    
    if verbose:
        print(f"\n✓ Saved cleaned data to: {output_path}")
        print("=" * 70)
    
    return df_clean


def main():
    """
    Main cleaning workflow.
    """
    print("\n" + "=" * 70)
    print("NBA DATA CLEANING - REMOVE ALL-STAR/EXHIBITION GAMES")
    print("=" * 70)
    print()
    
    # Clean ELO history
    if Path("data/exports/team_elo_history_phase_1_5.csv").exists():
        print("Step 1: Cleaning ELO history...")
        clean_elo_data(
            input_path="data/exports/team_elo_history_phase_1_5.csv",
            output_path="data/exports/team_elo_history_phase_1_5_clean.csv"
        )
        print()
    
    # Clean travel data if exists
    if Path("data/exports/team_elo_with_travel.csv").exists():
        print("Step 2: Cleaning travel data...")
        clean_elo_data(
            input_path="data/exports/team_elo_with_travel.csv",
            output_path="data/exports/team_elo_with_travel_clean.csv"
        )
        print()
    
    # Clean raw games if needed
    if Path("data/raw/nba_games_all.csv").exists():
        print("Step 3: Cleaning raw game data...")
        clean_raw_game_data(
            input_path="data/raw/nba_games_all.csv",
            output_path="data/raw/nba_games_all_clean.csv"
        )
        print()
    
    print("=" * 70)
    print("CLEANING COMPLETE!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Use cleaned files for visualizations:")
    print("   - team_elo_history_phase_1_5_clean.csv")
    print("   - team_elo_with_travel_clean.csv")
    print()
    print("2. Re-run ELO engine on cleaned raw data:")
    print("   python src/engines/team_elo_engine.py \\")
    print("       --input data/raw/nba_games_all_clean.csv \\")
    print("       --output data/exports/team_elo_clean.csv")
    print()


if __name__ == "__main__":
    main()
