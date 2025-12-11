"""
Schedule Fetcher for Season Predictor
Phase 1: Core Simulator Component

Fetches remaining games and calculates current standings for Monte Carlo simulation.
"""

import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ScheduleFetcher:
    """Fetch remaining games and current standings for season simulation."""

    # 2025-26 NBA Season dates
    SEASON_START = 20251021
    SEASON_END = 20260412

    def __init__(self, games_df: pd.DataFrame):
        """
        Initialize with games DataFrame.

        Args:
            games_df: DataFrame from nba_games_all.csv with columns:
                      date, home_team_id, away_team_id, home_team_name,
                      away_team_name, home_score, away_score
        """
        self.games_df = games_df

        # Check if dates are datetime and convert season constants if needed
        if pd.api.types.is_datetime64_any_dtype(self.games_df['date']):
            self.season_start = pd.to_datetime(str(self.SEASON_START), format="%Y%m%d")
            self.season_end = pd.to_datetime(str(self.SEASON_END), format="%Y%m%d")
            self.date_is_datetime = True
        else:
            self.season_start = self.SEASON_START
            self.season_end = self.SEASON_END
            self.date_is_datetime = False

        # Calculate previous season start (approximately 1 year = 10000 in YYYYMMDD format)
        if self.date_is_datetime:
            self.prev_season_start = pd.to_datetime(str(self.SEASON_START - 10000), format="%Y%m%d")
        else:
            self.prev_season_start = self.SEASON_START - 10000
        
        logger.info(f"ScheduleFetcher initialized with {len(games_df)} total games (date format: {'datetime' if self.date_is_datetime else 'int'})")

    def get_remaining_games(self, as_of_date: Optional[int] = None, include_completed_future: bool = False) -> List[Dict]:
        """
        Get all games scheduled after as_of_date in current season.

        Args:
            as_of_date: Date in YYYYMMDD format (default: today)
            include_completed_future: If True, include games with scores even if in future
                                     (useful for testing with simulated data)

        Returns:
            List of dicts with game info:
            [
                {
                    'date': 20251203,
                    'home_id': 13,
                    'away_id': 9,
                    'home_team': 'Los Angeles Lakers',
                    'away_team': 'Golden State Warriors',
                    'is_scheduled': True  # True if no scores yet
                },
                ...
            ]
        """
        if as_of_date is None:
            as_of_date = int(datetime.now().strftime('%Y%m%d'))

        # Convert as_of_date to datetime if needed
        if self.date_is_datetime:
            as_of_date_compare = pd.to_datetime(str(as_of_date), format='%Y%m%d')
        else:
            as_of_date_compare = as_of_date

        # Filter to current season, after as_of_date
        remaining = self.games_df[
            (self.games_df['date'] > as_of_date_compare) &
            (self.games_df['date'] >= self.season_start) &
            (self.games_df['date'] <= self.season_end)
        ]

        # If not including completed future games, filter out games with scores
        if not include_completed_future:
            # Games are "remaining" only if they don't have scores yet
            remaining = remaining[
                (remaining['home_score'].isna()) | (remaining['away_score'].isna())
            ]

        games = []
        for _, row in remaining.iterrows():
            games.append({
                'date': int(row['date']),
                'home_id': int(row['home_team_id']),
                'away_id': int(row['away_team_id']),
                'home_team': row['home_team_name'],
                'away_team': row['away_team_name'],
                'is_scheduled': pd.isna(row['home_score']) or pd.isna(row['away_score'])
            })

        logger.info(f"Found {len(games)} remaining games after {as_of_date}")

        # If no scheduled games found, generate projected games based on 82-game season
        if len(games) == 0:
            logger.info("No scheduled games found - generating projected matchups for season simulation")
            games = self._generate_projected_games(as_of_date)

        return games

    def _generate_projected_games(self, as_of_date: int) -> List[Dict]:
        """
        Generate projected remaining games to complete an 82-game season.

        Uses historical matchup patterns to estimate remaining games when
        the official schedule hasn't been published yet.

        Args:
            as_of_date: Current date in YYYYMMDD format

        Returns:
            List of projected game matchups (without specific dates)
        """
        from collections import defaultdict
        import random

        # Get current standings to know games played
        current_standings = self.get_current_standings(as_of_date)

        # Calculate games remaining per team (target: 82 games)
        TARGET_GAMES = 82
        team_games_remaining = {}

        for team_id, stats in current_standings.items():
            games_played = stats['games_played']
            team_games_remaining[team_id] = max(0, TARGET_GAMES - games_played)

        # Get list of active teams
        active_teams = list(team_games_remaining.keys())

        # Analyze historical matchup frequency (from previous seasons)
        # Use games from the database to understand typical matchup patterns
        historical_games = self.games_df[
            (self.games_df['date'] < self.season_start) &
            (self.games_df['date'] >= self.prev_season_start)  # Previous season
        ]

        # Count how many times each pair of teams played
        matchup_counts = defaultdict(int)
        for _, game in historical_games.iterrows():
            home_id = int(game['home_team_id'])
            away_id = int(game['away_team_id'])

            # Only count active teams
            if home_id in active_teams and away_id in active_teams:
                # Store as sorted tuple to treat home/away symmetrically
                pair = tuple(sorted([home_id, away_id]))
                matchup_counts[pair] += 1

        # Typical NBA schedule: 4 games vs division (3-4 teams), 3-4 games vs conference, 2 games vs other conference
        # For projection, we'll use historical averages
        avg_games_per_matchup = {}
        for pair, count in matchup_counts.items():
            avg_games_per_matchup[pair] = count // (len(historical_games) // (30 * 82 // 2))  # Normalize

        # Generate matchups to fill remaining games
        generated_games = []

        # Convert as_of_date to datetime for proper date arithmetic
        date_str = str(as_of_date)
        current_date = datetime.strptime(date_str, '%Y%m%d')
        from datetime import timedelta
        current_date = current_date + timedelta(days=1)  # Start from next day

        # Create a balanced schedule
        team_home_away_balance = {tid: {'home': 0, 'away': 0} for tid in active_teams}

        # Sort teams by games remaining (most first) to distribute evenly
        teams_by_remaining = sorted(team_games_remaining.items(), key=lambda x: x[1], reverse=True)

        max_iterations = 10000  # Safety limit
        iterations = 0

        while any(team_games_remaining[tid] > 0 for tid in active_teams) and iterations < max_iterations:
            iterations += 1

            # Find two teams that both need games
            available_teams = [tid for tid in active_teams if team_games_remaining[tid] > 0]

            if len(available_teams) < 2:
                break

            # Pick two random teams
            random.shuffle(available_teams)
            home_id = available_teams[0]
            away_id = available_teams[1]

            # Create the matchup
            game_date_int = int(current_date.strftime('%Y%m%d'))
            generated_games.append({
                'date': game_date_int,
                'home_id': home_id,
                'away_id': away_id,
                'home_team': current_standings[home_id]['team_name'],
                'away_team': current_standings[away_id]['team_name'],
                'is_scheduled': True  # Projected game
            })

            # Decrement games remaining
            team_games_remaining[home_id] -= 1
            team_games_remaining[away_id] -= 1

            # Track home/away balance
            team_home_away_balance[home_id]['home'] += 1
            team_home_away_balance[away_id]['away'] += 1

            # Increment date periodically (roughly 15 games per day for 30 teams)
            if len(generated_games) % 15 == 0:
                current_date = current_date + timedelta(days=1)

        logger.info(f"Generated {len(generated_games)} projected matchups to complete 82-game season")

        return generated_games

    def get_current_standings(self, as_of_date: Optional[int] = None) -> Dict[int, Dict]:
        """
        Calculate current W-L records as of specific date.

        Args:
            as_of_date: Date in YYYYMMDD format (default: today)

        Returns:
            Dict mapping team_id -> standing info:
            {
                13: {
                    'team_id': 13,
                    'team_name': 'Los Angeles Lakers',
                    'wins': 15,
                    'losses': 10,
                    'games_played': 25,
                    'win_pct': 0.600
                },
                ...
            }
        """
        if as_of_date is None:
            as_of_date = int(datetime.now().strftime('%Y%m%d'))

        # Convert as_of_date to datetime if needed
        if self.date_is_datetime:
            as_of_date_compare = pd.to_datetime(str(as_of_date), format='%Y%m%d')
        else:
            as_of_date_compare = as_of_date

        # Filter to current season up to as_of_date
        completed = self.games_df[
            (self.games_df['date'] >= self.season_start) &
            (self.games_df['date'] <= as_of_date_compare)
        ]

        standings = {}

        for _, game in completed.iterrows():
            home_id = int(game['home_team_id'])
            away_id = int(game['away_team_id'])

            # Initialize if first time seeing team
            if home_id not in standings:
                standings[home_id] = {
                    'team_id': home_id,
                    'team_name': game['home_team_name'],
                    'wins': 0,
                    'losses': 0,
                    'games_played': 0
                }
            if away_id not in standings:
                standings[away_id] = {
                    'team_id': away_id,
                    'team_name': game['away_team_name'],
                    'wins': 0,
                    'losses': 0,
                    'games_played': 0
                }

            # Update records based on scores
            home_score = game['home_score']
            away_score = game['away_score']

            if home_score > away_score:
                standings[home_id]['wins'] += 1
                standings[away_id]['losses'] += 1
            else:
                standings[away_id]['wins'] += 1
                standings[home_id]['losses'] += 1

            standings[home_id]['games_played'] += 1
            standings[away_id]['games_played'] += 1

        # Calculate win percentage
        for team_id in standings:
            games = standings[team_id]['games_played']
            wins = standings[team_id]['wins']
            standings[team_id]['win_pct'] = wins / games if games > 0 else 0.0

        logger.info(f"Calculated standings for {len(standings)} teams as of {as_of_date}")
        return standings

    def get_season_summary(self, as_of_date: Optional[int] = None) -> Dict:
        """
        Get summary statistics about the season.

        Returns:
            {
                'as_of_date': 20251203,
                'season_start': 20251021,
                'season_end': 20260412,
                'games_played': 1200,
                'games_remaining': 860,
                'total_season_games': 2060,
                'season_pct_complete': 0.582
            }
        """
        if as_of_date is None:
            as_of_date = int(datetime.now().strftime('%Y%m%d'))


        # Convert as_of_date to datetime if needed
        if self.date_is_datetime:
            as_of_date_compare = pd.to_datetime(str(as_of_date), format="%Y%m%d")
        else:
            as_of_date_compare = as_of_date
        # Count games in date ranges
        completed = self.games_df[
            (self.games_df['date'] >= self.season_start) &
            (self.games_df['date'] <= as_of_date_compare)
        ]

        games_played = len(completed)

        # Use get_remaining_games() which includes projected games if needed
        remaining_games = self.get_remaining_games(as_of_date)
        games_remaining = len(remaining_games)

        # Total games in a full season (30 teams × 82 games / 2 since each game involves 2 teams)
        FULL_SEASON_GAMES = (30 * 82) // 2  # 1230 games
        total_games = max(games_played + games_remaining, FULL_SEASON_GAMES)

        summary = {
            'as_of_date': as_of_date,
            'season_start': self.season_start,
            'season_end': self.season_end,
            'games_played': games_played,
            'games_remaining': games_remaining,
            'total_season_games': total_games,
            'season_pct_complete': games_played / total_games if total_games > 0 else 0.0
        }

        logger.info(f"Season summary: {games_played} played, {games_remaining} remaining")
        return summary

    def get_team_remaining_schedule(self, team_id: int, as_of_date: Optional[int] = None) -> Dict:
        """
        Get remaining schedule analysis for a specific team.

        Args:
            team_id: Team ID to analyze
            as_of_date: Date in YYYYMMDD format (default: today)

        Returns:
            {
                'team_id': 13,
                'team_name': 'Los Angeles Lakers',
                'total_games': 57,
                'home_games': 28,
                'away_games': 29,
                'games': [...]  # List of remaining games
            }
        """
        if as_of_date is None:
            as_of_date = int(datetime.now().strftime('%Y%m%d'))

        remaining_games = self.get_remaining_games(as_of_date)

        # Filter to games involving this team
        team_games = [
            g for g in remaining_games
            if g['home_id'] == team_id or g['away_id'] == team_id
        ]

        # Count home vs away
        home_games = sum(1 for g in team_games if g['home_id'] == team_id)
        away_games = sum(1 for g in team_games if g['away_id'] == team_id)

        # Get team name (fallback to ID if no games found)
        if len(team_games) > 0:
            team_name = team_games[0]['home_team'] if home_games > 0 else team_games[0]['away_team']
        else:
            # Try to get from standings
            standings = self.get_current_standings(as_of_date)
            team_name = standings.get(team_id, {}).get('team_name', f'Team {team_id}')

        return {
            'team_id': team_id,
            'team_name': team_name,
            'total_games': len(team_games),
            'home_games': home_games,
            'away_games': away_games,
            'games': team_games
        }


if __name__ == '__main__':
    # Test the schedule fetcher
    import sys
    sys.path.insert(0, 'c:/Users/Aaron/Desktop/NBA_ELO/nba-elo-engine')
    from src.utils.file_io import load_csv_to_dataframe

    print("="*80)
    print("SCHEDULE FETCHER TEST")
    print("="*80)

    # Load games
    games = load_csv_to_dataframe('data/raw/nba_games_all.csv')
    print(f"\nLoaded {len(games)} total games from database")

    # Initialize fetcher
    fetcher = ScheduleFetcher(games)

    # Test with Dec 1 as cutoff (to get remaining games in simulation data)
    test_date = 20241201

    # Get season summary
    print(f"\n--- Season Summary (as of {test_date}) ---")
    summary = fetcher.get_season_summary(test_date)
    print(f"Games played: {summary['games_played']}")
    print(f"Games remaining: {summary['games_remaining']}")
    print(f"Season progress: {summary['season_pct_complete']*100:.1f}%")

    # Get current standings (top 5)
    print("\n--- Current Standings (Top 5) ---")
    standings = fetcher.get_current_standings(test_date)
    sorted_teams = sorted(standings.values(), key=lambda x: x['win_pct'], reverse=True)
    for i, team in enumerate(sorted_teams[:5], 1):
        print(f"{i}. {team['team_name']:30} {team['wins']}-{team['losses']} ({team['win_pct']:.3f})")

    # Get remaining games sample (include completed future games for testing)
    print("\n--- Remaining Games (First 5) ---")
    remaining = fetcher.get_remaining_games(test_date, include_completed_future=True)
    print(f"Total remaining: {len(remaining)}")
    for game in remaining[:5]:
        status = "Scheduled" if game['is_scheduled'] else "Completed (test data)"
        print(f"{game['date']}: {game['home_team']} vs {game['away_team']} [{status}]")

    # Get team schedule (Celtics example - for simulation testing)
    print("\n--- Celtics Remaining Schedule (for simulation) ---")
    celtics_id = 2  # Boston Celtics
    celtics_schedule = fetcher.get_team_remaining_schedule(celtics_id, test_date)
    print(f"Team: {celtics_schedule['team_name']}")
    print(f"Total games remaining: {celtics_schedule['total_games']}")
    print(f"Home: {celtics_schedule['home_games']}, Away: {celtics_schedule['away_games']}")
    if celtics_schedule['total_games'] > 0:
        print(f"Sample games:")
        for game in celtics_schedule['games'][:3]:
            opponent = game['away_team'] if game['home_id'] == celtics_id else game['home_team']
            location = "vs" if game['home_id'] == celtics_id else "@"
            print(f"  {game['date']}: {location} {opponent}")

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)
