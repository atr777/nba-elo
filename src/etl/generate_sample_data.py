"""
Sample NBA Data Generator
Creates realistic sample game data for testing the ELO system.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.utils.file_io import save_dataframe_to_csv, get_data_path


# NBA Teams (ESPN IDs and names)
NBA_TEAMS = {
    '1': 'Atlanta Hawks',
    '2': 'Boston Celtics',
    '3': 'Brooklyn Nets',
    '4': 'Charlotte Hornets',
    '5': 'Chicago Bulls',
    '6': 'Cleveland Cavaliers',
    '7': 'Dallas Mavericks',
    '8': 'Denver Nuggets',
    '9': 'Detroit Pistons',
    '10': 'Golden State Warriors',
    '11': 'Houston Rockets',
    '12': 'Indiana Pacers',
    '13': 'LA Clippers',
    '14': 'Los Angeles Lakers',
    '15': 'Memphis Grizzlies',
    '16': 'Miami Heat',
    '17': 'Milwaukee Bucks',
    '18': 'Minnesota Timberwolves',
    '19': 'New Orleans Pelicans',
    '20': 'New York Knicks',
    '21': 'Oklahoma City Thunder',
    '22': 'Orlando Magic',
    '23': 'Philadelphia 76ers',
    '24': 'Phoenix Suns',
    '25': 'Portland Trail Blazers',
    '26': 'Sacramento Kings',
    '27': 'San Antonio Spurs',
    '28': 'Toronto Raptors',
    '29': 'Utah Jazz',
    '30': 'Washington Wizards'
}


def generate_sample_season(start_date='20231024', end_date='20231130', num_games=100):
    """
    Generate sample NBA season data.
    
    Args:
        start_date: Start date (YYYYMMDD)
        end_date: End date (YYYYMMDD)  
        num_games: Number of games to generate
        
    Returns:
        DataFrame with sample games
    """
    np.random.seed(42)  # For reproducibility
    
    team_ids = list(NBA_TEAMS.keys())
    games = []
    
    start = datetime.strptime(start_date, '%Y%m%d')
    end = datetime.strptime(end_date, '%Y%m%d')
    date_range = (end - start).days
    
    for i in range(num_games):
        # Random date in range
        random_days = np.random.randint(0, date_range + 1)
        game_date = start + timedelta(days=random_days)
        
        # Random matchup
        home_team_id = np.random.choice(team_ids)
        away_team_id = np.random.choice([t for t in team_ids if t != home_team_id])
        
        # Generate scores (realistic NBA scores)
        base_score = np.random.randint(95, 120)
        point_diff = np.random.randint(-15, 15)
        
        home_score = base_score + (point_diff if point_diff > 0 else 0)
        away_score = base_score - (point_diff if point_diff < 0 else 0)
        
        winner_team_id = home_team_id if home_score > away_score else away_team_id
        
        games.append({
            'game_id': f'4012300{i:04d}',
            'date': game_date.strftime('%Y%m%d'),
            'home_team_id': home_team_id,
            'home_team_name': NBA_TEAMS[home_team_id],
            'away_team_id': away_team_id,
            'away_team_name': NBA_TEAMS[away_team_id],
            'home_score': home_score,
            'away_score': away_score,
            'winner_team_id': winner_team_id
        })
    
    df = pd.DataFrame(games)
    df = df.sort_values('date').reset_index(drop=True)
    
    return df


def main():
    """Generate and save sample data."""
    print("Generating sample NBA season data...")
    
    df = generate_sample_season(
        start_date='20231024',
        end_date='20231231',
        num_games=300
    )
    
    output_path = get_data_path('raw', 'nba_games_sample.csv')
    save_dataframe_to_csv(df, output_path)
    
    print(f"\n✓ Generated {len(df)} sample games")
    print(f"  Date range: {df['date'].min()} - {df['date'].max()}")
    print(f"  Teams: {df['home_team_id'].nunique()}")
    print(f"  Saved to: {output_path}")


if __name__ == "__main__":
    main()
