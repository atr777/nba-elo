"""
Check Data Status
==================
Quick utility to check completed vs scheduled games in the dataset.
"""

import pandas as pd
from datetime import datetime


def check_data_status(data_path='data/raw/nba_games_all.csv'):
    """
    Analyze the current state of game data.

    Shows:
    - Latest completed game
    - Number of scheduled games
    - Data freshness
    """
    print("=" * 70)
    print("NBA ELO DATA STATUS CHECK")
    print("=" * 70)

    # Load data
    df = pd.read_csv(data_path)

    # Separate completed from scheduled
    completed = df[
        (df['home_score'].astype(int) > 0) |
        (df['away_score'].astype(int) > 0)
    ]

    scheduled = df[
        (df['home_score'].astype(int) == 0) &
        (df['away_score'].astype(int) == 0)
    ]

    # Stats
    print(f"\nTOTAL GAMES IN FILE: {len(df):,}")
    print(f"  [OK] Completed games:  {len(completed):,}")
    print(f"  [..] Scheduled games:  {len(scheduled):,}")

    # Latest completed game
    if len(completed) > 0:
        latest_completed = completed.sort_values('date', ascending=False).iloc[0]
        latest_date = str(latest_completed['date'])
        formatted_date = f"{latest_date[0:4]}-{latest_date[4:6]}-{latest_date[6:8]}"

        print(f"\nLATEST COMPLETED GAME:")
        print(f"  Date: {formatted_date}")
        print(f"  {latest_completed['away_team_name']} @ {latest_completed['home_team_name']}")
        print(f"  Score: {int(latest_completed['away_score'])}-{int(latest_completed['home_score'])}")

        # Check freshness
        latest_dt = datetime.strptime(latest_date, '%Y%m%d')
        today = datetime.now()
        days_behind = (today - latest_dt).days

        if days_behind == 0:
            print(f"  Status: [OK] UP TO DATE (today)")
        elif days_behind == 1:
            print(f"  Status: [OK] CURRENT (1 day behind)")
        elif days_behind <= 3:
            print(f"  Status: [!!] MOSTLY CURRENT ({days_behind} days behind)")
        else:
            print(f"  Status: [XX] OUTDATED ({days_behind} days behind)")

    # Scheduled games
    if len(scheduled) > 0:
        scheduled_dates = scheduled['date'].unique()
        earliest_scheduled = min(scheduled_dates)
        latest_scheduled = max(scheduled_dates)

        earliest_str = str(earliest_scheduled)
        latest_str = str(latest_scheduled)

        print(f"\nSCHEDULED GAMES:")
        print(f"  Date range: {earliest_str[0:4]}-{earliest_str[4:6]}-{earliest_str[6:8]} to "
              f"{latest_str[0:4]}-{latest_str[4:6]}-{latest_str[6:8]}")
        print(f"  Count: {len(scheduled)} games across {len(scheduled_dates)} dates")

    # Date range
    earliest = str(df['date'].min())
    latest = str(df['date'].max())

    print(f"\nDATE RANGE (ALL DATA):")
    print(f"  From: {earliest[0:4]}-{earliest[4:6]}-{earliest[6:8]}")
    print(f"  To:   {latest[0:4]}-{latest[4:6]}-{latest[6:8]}")

    # Unique teams
    all_teams = pd.concat([df['home_team_name'], df['away_team_name']]).unique()
    print(f"\nTEAMS: {len(all_teams)} unique teams tracked")

    # Recommendation
    print("\n" + "=" * 70)
    if len(scheduled) > 0:
        print("RECOMMENDATION:")
        print("  Scheduled games (0-0 scores) are kept in raw data but")
        print("  automatically filtered out during ELO calculations.")
        print("  No action needed - this is working as intended! [OK]")
    else:
        print("DATA STATUS: All games have scores. No scheduled games found. [OK]")
    print("=" * 70)


if __name__ == '__main__':
    import sys

    data_path = sys.argv[1] if len(sys.argv) > 1 else 'data/raw/nba_games_all.csv'
    check_data_status(data_path)
