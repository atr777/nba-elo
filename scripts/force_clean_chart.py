"""
Force Clean Visualization - NBA Teams Only
==========================================
Loads data, filters to ONLY NBA teams, then creates chart.
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Official 30 NBA teams
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


def create_clean_league_chart():
    """Create league distribution chart with ONLY NBA teams."""
    
    print("=" * 70)
    print("FORCING CLEAN LEAGUE CHART - NBA TEAMS ONLY")
    print("=" * 70)
    
    # Try multiple file paths
    possible_paths = [
        "data/exports/team_elo_history_phase_1_5_clean.csv",
        "data/exports/team_elo_history_phase_1_5.csv",
        "data/exports/team_elo_with_travel_clean.csv",
        "data/exports/team_elo_with_travel.csv",
    ]
    
    data_path = None
    for path in possible_paths:
        if Path(path).exists():
            data_path = path
            break
    
    if not data_path:
        print("❌ No ELO data files found!")
        return
    
    print(f"\n📁 Loading: {data_path}")
    df = pd.read_csv(data_path)
    
    # Convert date if needed
    if df['date'].dtype == 'int64':
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
    else:
        df['date'] = pd.to_datetime(df['date'])
    
    print(f"   Original records: {len(df):,}")
    print(f"   Original unique teams: {df['team_name'].nunique()}")
    
    # FORCE filter to only NBA teams
    df_nba = df[df['team_name'].isin(NBA_TEAMS)].copy()
    
    print(f"\n🧹 After filtering to NBA teams only:")
    print(f"   Clean records: {len(df_nba):,}")
    print(f"   NBA teams: {df_nba['team_name'].nunique()}")
    
    # Show removed teams
    removed_teams = set(df['team_name'].unique()) - set(NBA_TEAMS)
    if removed_teams:
        print(f"\n   ❌ Removed {len(removed_teams)} non-NBA teams:")
        for team in sorted(removed_teams):
            print(f"      • {team}")
    
    # Get latest ratings for each NBA team
    latest_ratings = df_nba.groupby('team_name').tail(1)
    latest_ratings = latest_ratings.sort_values('rating_after', ascending=False)
    
    # Verify we have 30 teams
    if len(latest_ratings) != 30:
        print(f"\n⚠️  Warning: Found {len(latest_ratings)} NBA teams, expected 30")
        missing = set(NBA_TEAMS) - set(latest_ratings['team_name'].unique())
        if missing:
            print(f"   Missing teams: {missing}")
    
    # Create chart
    fig, ax = plt.subplots(figsize=(14, 10))
    
    bars = ax.barh(range(len(latest_ratings)), latest_ratings['rating_after'],
                  color='steelblue', alpha=0.7)
    
    # Color code by strength
    for i, (idx, row) in enumerate(latest_ratings.iterrows()):
        if row['rating_after'] > 1600:
            bars[i].set_color('green')
        elif row['rating_after'] < 1400:
            bars[i].set_color('red')
    
    ax.set_yticks(range(len(latest_ratings)))
    ax.set_yticklabels(latest_ratings['team_name'], fontsize=9)
    ax.set_xlabel('ELO Rating', fontsize=12)
    ax.set_title('NBA Team ELO Ratings - Current Standings (CLEAN - 30 TEAMS ONLY)', 
                fontsize=14, fontweight='bold', pad=15)
    ax.grid(True, alpha=0.3, axis='x')
    ax.axvline(x=1500, color='gray', linestyle='--', alpha=0.6, linewidth=1.5)
    
    # Add rating values on bars
    for i, (idx, row) in enumerate(latest_ratings.iterrows()):
        ax.text(row['rating_after'] + 10, i, f"{row['rating_after']:.0f}",
               va='center', fontsize=8)
    
    plt.tight_layout()
    
    # Save
    output_dir = Path("data/exports/visualizations")
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / "league_elo_distribution_CLEAN.png"
    
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    print(f"\n✅ Saved clean chart to: {filepath}")
    print(f"   Chart shows: {len(latest_ratings)} NBA teams only!")
    
    plt.close()
    
    print("\n" + "=" * 70)
    print("CLEAN CHART CREATED SUCCESSFULLY!")
    print("=" * 70)
    print(f"\nOpen: {filepath}")


if __name__ == "__main__":
    create_clean_league_chart()
