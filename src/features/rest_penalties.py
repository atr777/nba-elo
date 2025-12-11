"""
Rest and Fatigue Penalties
Adjusts team ratings based on rest days between games.
"""

import pandas as pd
import logging
from typing import Dict, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# Rest penalty constants (based on FiveThirtyEight research)
BACK_TO_BACK_PENALTY = 46  # 0 days rest
ONE_DAY_REST_PENALTY = 15  # 1 day rest
TWO_PLUS_DAYS_REST = 0     # 2+ days rest (no penalty)


class RestTracker:
    """
    Tracks team rest days and applies fatigue penalties.

    Based on FiveThirtyEight methodology:
    - Back-to-back (0 days rest): -46 ELO points
    - 1 day rest: -15 ELO points
    - 2+ days rest: No penalty
    """

    def __init__(
        self,
        b2b_penalty: float = BACK_TO_BACK_PENALTY,
        one_day_penalty: float = ONE_DAY_REST_PENALTY
    ):
        """
        Initialize rest tracker.

        Args:
            b2b_penalty: ELO penalty for back-to-back games
            one_day_penalty: ELO penalty for 1 day rest
        """
        self.b2b_penalty = b2b_penalty
        self.one_day_penalty = one_day_penalty

        # Track last game date for each team: {team_id: date_integer}
        self.team_last_game = {}

        logger.info(
            f"Rest Tracker initialized: B2B penalty={b2b_penalty}, "
            f"1-day penalty={one_day_penalty}"
        )

    def update_last_game(self, team_id: str, game_date: int):
        """
        Update the last game date for a team.

        Args:
            team_id: Team identifier
            game_date: Game date as integer (YYYYMMDD format)
        """
        self.team_last_game[team_id] = game_date

    def calculate_rest_days(
        self,
        team_id: str,
        current_game_date: int
    ) -> int:
        """
        Calculate days of rest since last game.

        Args:
            team_id: Team identifier
            current_game_date: Current game date (YYYYMMDD format)

        Returns:
            Number of days since last game (None if no previous game)
        """
        if team_id not in self.team_last_game:
            return None

        last_date = self.team_last_game[team_id]

        # Convert YYYYMMDD integers to datetime
        try:
            last_dt = datetime.strptime(str(last_date), '%Y%m%d')
            current_dt = datetime.strptime(str(current_game_date), '%Y%m%d')

            # Calculate days difference
            rest_days = (current_dt - last_dt).days - 1  # Subtract 1 to get rest days

            return max(0, rest_days)  # Can't be negative

        except ValueError:
            logger.warning(f"Invalid date format: {last_date} or {current_game_date}")
            return None

    def get_rest_penalty(self, team_id: str, game_date: int) -> float:
        """
        Calculate ELO penalty based on rest days.

        Args:
            team_id: Team identifier
            game_date: Current game date (YYYYMMDD format)

        Returns:
            ELO penalty points (negative value)
        """
        rest_days = self.calculate_rest_days(team_id, game_date)

        if rest_days is None:
            # First game of season or no history
            return 0.0

        if rest_days == 0:
            # Back-to-back game
            penalty = -self.b2b_penalty
            logger.debug(f"Team {team_id}: Back-to-back penalty {penalty:.0f}")
            return penalty

        elif rest_days == 1:
            # 1 day rest
            penalty = -self.one_day_penalty
            logger.debug(f"Team {team_id}: 1-day rest penalty {penalty:.0f}")
            return penalty

        else:
            # 2+ days rest - no penalty
            logger.debug(f"Team {team_id}: {rest_days} days rest, no penalty")
            return 0.0

    def get_rest_stats(self, team_id: str, game_date: int) -> Dict:
        """
        Get detailed rest statistics for a team.

        Args:
            team_id: Team identifier
            game_date: Current game date (YYYYMMDD format)

        Returns:
            Dictionary with rest statistics
        """
        rest_days = self.calculate_rest_days(team_id, game_date)
        penalty = self.get_rest_penalty(team_id, game_date)

        if rest_days is None:
            rest_category = 'first_game'
        elif rest_days == 0:
            rest_category = 'back_to_back'
        elif rest_days == 1:
            rest_category = 'one_day_rest'
        elif rest_days >= 2 and rest_days <= 3:
            rest_category = 'normal_rest'
        else:
            rest_category = 'extended_rest'

        return {
            'rest_days': rest_days if rest_days is not None else -1,
            'rest_category': rest_category,
            'rest_penalty': penalty,
            'last_game_date': self.team_last_game.get(team_id)
        }

    def clear_team_history(self, team_id: str):
        """Clear rest history for a team (e.g., new season)."""
        if team_id in self.team_last_game:
            del self.team_last_game[team_id]

    def clear_all_history(self):
        """Clear all rest history (e.g., new season start)."""
        self.team_last_game.clear()


def apply_rest_penalties(
    home_rating: float,
    away_rating: float,
    home_team_id: str,
    away_team_id: str,
    game_date: int,
    rest_tracker: RestTracker
) -> Tuple[float, float]:
    """
    Apply rest penalties to team ratings.

    Args:
        home_rating: Home team's base ELO rating
        away_rating: Away team's base ELO rating
        home_team_id: Home team identifier
        away_team_id: Away team identifier
        game_date: Game date (YYYYMMDD format)
        rest_tracker: RestTracker instance

    Returns:
        Tuple of (adjusted_home_rating, adjusted_away_rating)
    """
    home_penalty = rest_tracker.get_rest_penalty(home_team_id, game_date)
    away_penalty = rest_tracker.get_rest_penalty(away_team_id, game_date)

    adjusted_home = home_rating + home_penalty
    adjusted_away = away_rating + away_penalty

    logger.debug(
        f"Rest penalties: home {home_rating:.0f} + {home_penalty:+.0f} = {adjusted_home:.0f}, "
        f"away {away_rating:.0f} + {away_penalty:+.0f} = {adjusted_away:.0f}"
    )

    return adjusted_home, adjusted_away


def analyze_rest_impact(games_df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze the impact of rest on game outcomes.

    Args:
        games_df: DataFrame with columns ['home_team_id', 'away_team_id',
                  'home_score', 'away_score', 'date']

    Returns:
        DataFrame with rest analysis results
    """
    tracker = RestTracker()
    results = []

    # Sort by date
    games_df = games_df.sort_values('date').reset_index(drop=True)

    for idx, game in games_df.iterrows():
        home_id = game['home_team_id']
        away_id = game['away_team_id']
        game_date = game['date']

        # Get rest stats before this game
        home_rest = tracker.get_rest_stats(home_id, game_date)
        away_rest = tracker.get_rest_stats(away_id, game_date)

        # Actual result
        home_won = game['home_score'] > game['away_score']

        # Update tracker with this game
        tracker.update_last_game(home_id, game_date)
        tracker.update_last_game(away_id, game_date)

        # Record analysis
        results.append({
            'game_id': game.get('game_id', idx),
            'date': game_date,
            'home_team': home_id,
            'away_team': away_id,
            'home_won': home_won,
            'home_rest_days': home_rest['rest_days'],
            'away_rest_days': away_rest['rest_days'],
            'home_rest_category': home_rest['rest_category'],
            'away_rest_category': away_rest['rest_category'],
            'home_rest_penalty': home_rest['rest_penalty'],
            'away_rest_penalty': away_rest['rest_penalty'],
            'rest_advantage': away_rest['rest_penalty'] - home_rest['rest_penalty']
        })

    return pd.DataFrame(results)


def detect_back_to_back_games(games_df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect back-to-back games in the dataset.

    Args:
        games_df: DataFrame with game data

    Returns:
        DataFrame with only back-to-back games
    """
    analysis = analyze_rest_impact(games_df)

    # Filter for back-to-back situations
    b2b_games = analysis[
        (analysis['home_rest_category'] == 'back_to_back') |
        (analysis['away_rest_category'] == 'back_to_back')
    ].copy()

    return b2b_games


def calculate_rest_advantage_impact(games_df: pd.DataFrame) -> Dict:
    """
    Calculate how rest advantage affects win probability.

    Args:
        games_df: DataFrame with game data

    Returns:
        Dictionary with rest advantage statistics
    """
    analysis = analyze_rest_impact(games_df)

    # Remove first games (no rest data)
    analysis = analysis[
        (analysis['home_rest_days'] >= 0) &
        (analysis['away_rest_days'] >= 0)
    ].copy()

    # Calculate win rates by rest advantage
    stats = {}

    # Home team on back-to-back
    home_b2b = analysis[analysis['home_rest_category'] == 'back_to_back']
    if len(home_b2b) > 0:
        stats['home_b2b_win_rate'] = home_b2b['home_won'].mean()
        stats['home_b2b_games'] = len(home_b2b)

    # Away team on back-to-back
    away_b2b = analysis[analysis['away_rest_category'] == 'back_to_back']
    if len(away_b2b) > 0:
        stats['away_b2b_win_rate'] = away_b2b['home_won'].mean()  # Home team winning
        stats['away_b2b_games'] = len(away_b2b)

    # Both teams rested
    both_rested = analysis[
        (analysis['home_rest_days'] >= 2) &
        (analysis['away_rest_days'] >= 2)
    ]
    if len(both_rested) > 0:
        stats['both_rested_home_win_rate'] = both_rested['home_won'].mean()
        stats['both_rested_games'] = len(both_rested)

    return stats
