"""
Mock Box Score Data Generator
==============================
Generate realistic fake box score data for Phase 3 Player ELO development
while waiting for real ESPN data scraping to complete.

USAGE:
    python generate_mock_boxscores.py --games 1000 --output mock_boxscores.csv
"""

import pandas as pd
import numpy as np
import argparse
from datetime import datetime, timedelta
import random

# Realistic NBA player name components
FIRST_NAMES = [
    'LeBron', 'Stephen', 'Kevin', 'James', 'Anthony', 'Damian', 'Giannis',
    'Nikola', 'Luka', 'Joel', 'Jayson', 'Devin', 'Kawhi', 'Paul', 'Jimmy',
    'Kyrie', 'Donovan', 'Trae', 'Zion', 'Ja', 'Brandon', 'Darius', 'Tyler'
]

LAST_NAMES = [
    'James', 'Curry', 'Durant', 'Harden', 'Davis', 'Lillard', 'Antetokounmpo',
    'Jokic', 'Doncic', 'Embiid', 'Tatum', 'Booker', 'Leonard', 'George', 'Butler',
    'Irving', 'Mitchell', 'Young', 'Williamson', 'Morant', 'Ingram', 'Garland', 'Herro'
]

NBA_TEAMS = [
    ('1610612737', 'Atlanta Hawks'),
    ('1610612738', 'Boston Celtics'),
    ('1610612751', 'Brooklyn Nets'),
    ('1610612766', 'Charlotte Hornets'),
    ('1610612741', 'Chicago Bulls'),
    ('1610612739', 'Cleveland Cavaliers'),
    ('1610612742', 'Dallas Mavericks'),
    ('1610612743', 'Denver Nuggets'),
    ('1610612765', 'Detroit Pistons'),
    ('1610612744', 'Golden State Warriors'),
    ('1610612745', 'Houston Rockets'),
    ('1610612754', 'Indiana Pacers'),
    ('1610612746', 'LA Clippers'),
    ('1610612747', 'Los Angeles Lakers'),
    ('1610612763', 'Memphis Grizzlies'),
    ('1610612748', 'Miami Heat'),
    ('1610612749', 'Milwaukee Bucks'),
    ('1610612750', 'Minnesota Timberwolves'),
    ('1610612740', 'New Orleans Pelicans'),
    ('1610612752', 'New York Knicks'),
    ('1610612760', 'Oklahoma City Thunder'),
    ('1610612753', 'Orlando Magic'),
    ('1610612755', 'Philadelphia 76ers'),
    ('1610612756', 'Phoenix Suns'),
    ('1610612757', 'Portland Trail Blazers'),
    ('1610612758', 'Sacramento Kings'),
    ('1610612759', 'San Antonio Spurs'),
    ('1610612761', 'Toronto Raptors'),
    ('1610612762', 'Utah Jazz'),
    ('1610612764', 'Washington Wizards')
]

POSITIONS = ['PG', 'SG', 'SF', 'PF', 'C']


class MockBoxScoreGenerator:
    """Generate realistic mock box score data"""
    
    def __init__(self, seed=42):
        """Initialize generator with random seed for reproducibility"""
        random.seed(seed)
        np.random.seed(seed)
        self.players = self._generate_player_pool()
        self.team_rosters = self._assign_rosters()
    
    def _generate_player_pool(self, n_players=450):
        """Create pool of fake players (NBA has ~450 active players)"""
        players = []
        
        for i in range(n_players):
            player = {
                'player_id': f'mock_{i+1:04d}',
                'player_name': f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                'position': random.choice(POSITIONS),
                'jersey': str(random.randint(0, 99)),
                'skill_level': np.random.beta(2, 5)  # Most players average, few stars
            }
            players.append(player)
        
        return players
    
    def _assign_rosters(self, roster_size=15):
        """Assign players to teams"""
        rosters = {}
        player_pool = self.players.copy()
        random.shuffle(player_pool)
        
        for team_id, team_name in NBA_TEAMS:
            team_players = []
            for _ in range(roster_size):
                if player_pool:
                    player = player_pool.pop()
                    player['team_id'] = team_id
                    player['team_name'] = team_name
                    team_players.append(player)
            rosters[team_id] = team_players
        
        return rosters
    
    def generate_game_boxscore(self, game_id, home_team_id, away_team_id):
        """
        Generate box score for a single game
        
        Args:
            game_id: Unique game identifier
            home_team_id: Home team ID
            away_team_id: Away team ID
            
        Returns:
            List of player records
        """
        records = []
        
        for team_id in [home_team_id, away_team_id]:
            team_roster = self.team_rosters.get(team_id, [])
            
            # Select 8-10 players who played (injuries/DNPs are realistic)
            n_players = random.randint(8, 10)
            active_players = random.sample(team_roster, min(n_players, len(team_roster)))
            
            # Sort by skill level (starters are typically better)
            active_players.sort(key=lambda p: p['skill_level'], reverse=True)
            
            # Total game minutes = 48 minutes × 5 players = 240
            available_minutes = 240
            
            for i, player in enumerate(active_players):
                # Starters (first 5) play more minutes
                is_starter = i < 5
                
                if is_starter:
                    # Starters: 28-38 minutes
                    base_minutes = 33
                    variation = np.random.normal(0, 3)
                else:
                    # Bench: 10-25 minutes
                    base_minutes = 17
                    variation = np.random.normal(0, 4)
                
                # Skill-based adjustment (better players play more)
                skill_bonus = player['skill_level'] * 5
                
                minutes = max(5, min(48, base_minutes + variation + skill_bonus))
                minutes = min(minutes, available_minutes)
                available_minutes -= minutes
                
                record = {
                    'game_id': game_id,
                    'player_id': player['player_id'],
                    'player_name': player['player_name'],
                    'team_id': team_id,
                    'team_name': player['team_name'],
                    'minutes': round(minutes, 1),
                    'starter': is_starter,
                    'position': player['position'],
                    'jersey': player['jersey'],
                    'didNotPlay': False
                }
                
                records.append(record)
            
            # Add 2-3 DNPs (did not play)
            remaining_roster = [p for p in team_roster if p not in active_players]
            dnps = random.sample(remaining_roster, min(2, len(remaining_roster)))
            
            for player in dnps:
                record = {
                    'game_id': game_id,
                    'player_id': player['player_id'],
                    'player_name': player['player_name'],
                    'team_id': team_id,
                    'team_name': player['team_name'],
                    'minutes': 0.0,
                    'starter': False,
                    'position': player['position'],
                    'jersey': player['jersey'],
                    'didNotPlay': True
                }
                records.append(record)
        
        return records
    
    def generate_season(self, n_games=1000, start_date='2023-10-01'):
        """
        Generate box scores for a full season
        
        Args:
            n_games: Number of games to generate
            start_date: Season start date
            
        Returns:
            DataFrame with all player records
        """
        print(f"Generating {n_games} mock games...")
        
        all_records = []
        current_date = datetime.strptime(start_date, '%Y-%m-%d')
        
        for game_num in range(n_games):
            # Generate game ID (format similar to ESPN)
            game_id = f'mock_{400000000 + game_num}'
            
            # Random matchup
            home_team = random.choice(NBA_TEAMS)
            away_team = random.choice([t for t in NBA_TEAMS if t != home_team])
            
            # Generate box score
            records = self.generate_game_boxscore(
                game_id,
                home_team[0],
                away_team[0]
            )
            
            all_records.extend(records)
            
            # Progress logging
            if (game_num + 1) % 100 == 0:
                print(f"  Generated {game_num + 1}/{n_games} games...")
            
            # Advance date (games roughly every other day)
            if random.random() < 0.6:
                current_date += timedelta(days=1)
        
        df = pd.DataFrame(all_records)
        
        print(f"\n✓ Generated {len(df)} player records")
        print(f"  - Unique players: {df['player_id'].nunique()}")
        print(f"  - Unique games: {df['game_id'].nunique()}")
        print(f"  - Unique teams: {df['team_id'].nunique()}")
        print(f"  - Total starters: {df['starter'].sum()}")
        print(f"  - Average minutes: {df[df['minutes'] > 0]['minutes'].mean():.1f}")
        
        return df


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(
        description='Generate mock NBA box score data for development'
    )
    parser.add_argument(
        '--games',
        type=int,
        default=1000,
        help='Number of games to generate (default: 1000)'
    )
    parser.add_argument(
        '--output',
        default='mock_player_boxscores.csv',
        help='Output CSV file'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for reproducibility'
    )
    
    args = parser.parse_args()
    
    print("="*70)
    print("MOCK BOX SCORE DATA GENERATOR")
    print("="*70)
    print(f"Games to generate: {args.games}")
    print(f"Output file: {args.output}")
    print(f"Random seed: {args.seed}\n")
    
    # Generate data
    generator = MockBoxScoreGenerator(seed=args.seed)
    df = generator.generate_season(n_games=args.games)
    
    # Save to CSV
    df.to_csv(args.output, index=False)
    print(f"\n✓ Saved to: {args.output}")
    
    # Show sample
    print(f"\nSample data:")
    print("="*70)
    print(df.head(15).to_string(index=False))
    
    print("\n" + "="*70)
    print("✅ MOCK DATA GENERATION COMPLETE")
    print("="*70)
    print("\nThis mock data has:")
    print("  ✓ Realistic player names and positions")
    print("  ✓ Proper minute distributions (starters vs bench)")
    print("  ✓ DNP (Did Not Play) players")
    print("  ✓ Consistent team rosters")
    print("  ✓ All 30 NBA teams")
    print("\nYou can use this data to:")
    print("  1. Develop Phase 3 Player ELO logic")
    print("  2. Test minute-weighted calculations")
    print("  3. Validate trade handling")
    print("  4. Build visualizations")
    print("\nReplace with real ESPN data when scraping completes!")


if __name__ == "__main__":
    main()
