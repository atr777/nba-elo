"""
Diagnostic: List All Teams in ELO Data
======================================
Shows all unique teams to verify cleaning worked.
"""

import pandas as pd
from pathlib import Path


def show_all_teams(filepath: str):
    """Show all unique teams in a file."""
    if not Path(filepath).exists():
        print(f"❌ File not found: {filepath}")
        return
    
    print(f"\n📁 Loading: {filepath}")
    df = pd.read_csv(filepath)
    
    teams = sorted(df['team_name'].unique())
    
    print(f"\n📊 Found {len(teams)} unique teams:\n")
    
    # Check for exhibition teams
    nba_teams = []
    exhibition_teams = []
    
    exhibition_keywords = [
        'team ', 'all star', 'all-star', 'eastern', 'western', 
        'world', 'usa', 'guangzhou', 'shanghai', 'beijing',
        'maccabi', 'cska', 'real madrid', 'barcelona', 'china',
        'select', 'chuck', 'shaq'
    ]
    
    for team in teams:
        team_lower = team.lower()
        is_exhibition = any(keyword in team_lower for keyword in exhibition_keywords)
        
        if is_exhibition:
            exhibition_teams.append(team)
        else:
            nba_teams.append(team)
    
    # Show NBA teams
    print(f"✅ NBA Teams ({len(nba_teams)}):")
    for i, team in enumerate(nba_teams, 1):
        print(f"  {i:2d}. {team}")
    
    # Show exhibition teams (if any)
    if exhibition_teams:
        print(f"\n⚠️  EXHIBITION TEAMS FOUND ({len(exhibition_teams)}):")
        for team in exhibition_teams:
            print(f"  ❌ {team}")
    else:
        print(f"\n✅ No exhibition teams found - data is clean!")


def main():
    """Check multiple files."""
    print("=" * 70)
    print("TEAM DIAGNOSTIC - CHECKING ALL FILES")
    print("=" * 70)
    
    files_to_check = [
        "data/raw/nba_games_all.csv",
        "data/raw/nba_games_all_clean.csv",
        "data/exports/team_elo_history_phase_1_5.csv",
        "data/exports/team_elo_history_phase_1_5_clean.csv",
        "data/exports/team_elo_with_travel.csv",
        "data/exports/team_elo_with_travel_clean.csv",
    ]
    
    for filepath in files_to_check:
        if Path(filepath).exists():
            show_all_teams(filepath)
            print("\n" + "-" * 70)
    
    print("\n" + "=" * 70)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
