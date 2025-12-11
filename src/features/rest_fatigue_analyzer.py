"""
Rest and Fatigue Analysis Module

Analyzes team schedules to calculate rest/fatigue adjustments for NBA predictions.
Implements Priority 3 features:
- Back-to-back game detection
- Schedule density tracking
- Rest differential calculation
"""

import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class RestFatigueAnalyzer:
    """Analyzes rest and fatigue factors for NBA predictions."""

    def __init__(self):
        """Initialize the Rest/Fatigue Analyzer."""
        logger.info("RestFatigueAnalyzer initialized")

    def analyze(self,
               home_team_id: int,
               away_team_id: int,
               game_date: datetime,
               games_history: Optional[pd.DataFrame] = None) -> Dict:
        """
        Analyze rest/fatigue for both teams.

        Args:
            home_team_id: Home team identifier
            away_team_id: Away team identifier
            game_date: Date of the game
            games_history: Historical games DataFrame

        Returns:
            Dictionary with rest/fatigue analysis for both teams
        """

        if games_history is None or len(games_history) == 0:
            # No history available, return neutral adjustments
            return self._neutral_result()

        # Convert game_date to datetime if it's a string
        if isinstance(game_date, str):
            game_date = datetime.strptime(game_date, '%Y%m%d')

        # Analyze home team
        home_b2b = self.is_back_to_back(home_team_id, game_date, games_history)
        home_days_rest = self.get_days_rest(home_team_id, game_date, games_history)
        home_games_4d = self.get_games_in_last_n_days(home_team_id, game_date, games_history, 4)
        home_games_5d = self.get_games_in_last_n_days(home_team_id, game_date, games_history, 5)

        # Analyze away team
        away_b2b = self.is_back_to_back(away_team_id, game_date, games_history)
        away_days_rest = self.get_days_rest(away_team_id, game_date, games_history)
        away_games_4d = self.get_games_in_last_n_days(away_team_id, game_date, games_history, 4)
        away_games_5d = self.get_games_in_last_n_days(away_team_id, game_date, games_history, 5)

        # Calculate penalties
        home_b2b_penalty = -50.0 if home_b2b else 0.0
        away_b2b_penalty = -50.0 if away_b2b else 0.0

        home_density_penalty = self.calculate_schedule_density_penalty(home_games_4d, home_games_5d)
        away_density_penalty = self.calculate_schedule_density_penalty(away_games_4d, away_games_5d)

        # Calculate rest differential advantage
        home_rest_adv, away_rest_adv = self.calculate_rest_differential(
            home_days_rest, away_days_rest
        )

        # Total adjustments
        home_total = home_b2b_penalty + home_density_penalty + home_rest_adv
        away_total = away_b2b_penalty + away_density_penalty + away_rest_adv

        return {
            # Home team
            'home_back_to_back': home_b2b,
            'home_days_rest': home_days_rest,
            'home_games_in_4_days': home_games_4d,
            'home_games_in_5_days': home_games_5d,
            'home_b2b_penalty': home_b2b_penalty,
            'home_density_penalty': home_density_penalty,
            'home_rest_advantage': home_rest_adv,
            'home_total_adjustment': home_total,

            # Away team
            'away_back_to_back': away_b2b,
            'away_days_rest': away_days_rest,
            'away_games_in_4_days': away_games_4d,
            'away_games_in_5_days': away_games_5d,
            'away_b2b_penalty': away_b2b_penalty,
            'away_density_penalty': away_density_penalty,
            'away_rest_advantage': away_rest_adv,
            'away_total_adjustment': away_total,

            # Summary
            'rest_fatigue_active': True,
            'net_adjustment': home_total - away_total
        }

    def is_back_to_back(self,
                       team_id: int,
                       game_date: datetime,
                       games_history: pd.DataFrame) -> bool:
        """
        Check if team played yesterday (back-to-back game).

        Args:
            team_id: Team identifier
            game_date: Current game date
            games_history: Historical games DataFrame

        Returns:
            True if team played yesterday, False otherwise
        """

        yesterday = game_date - timedelta(days=1)
        yesterday_str = yesterday.strftime('%Y%m%d')

        # Ensure date column is string format
        games_history = games_history.copy()
        if 'date' in games_history.columns:
            games_history['date'] = games_history['date'].astype(str)

        # Check if team played yesterday (home or away)
        played_yesterday = games_history[
            ((games_history['home_team_id'] == team_id) |
             (games_history['away_team_id'] == team_id)) &
            (games_history['date'] == yesterday_str)
        ]

        return len(played_yesterday) > 0

    def get_days_rest(self,
                     team_id: int,
                     game_date: datetime,
                     games_history: pd.DataFrame) -> int:
        """
        Get number of days since team's last game.

        Args:
            team_id: Team identifier
            game_date: Current game date
            games_history: Historical games DataFrame

        Returns:
            Number of days rest (0 = back-to-back, 1 = played yesterday, etc.)
        """

        # Get team's games before this date
        games_history = games_history.copy()
        if 'date' in games_history.columns:
            games_history['date'] = pd.to_datetime(games_history['date'], format='%Y%m%d')

        team_games = games_history[
            ((games_history['home_team_id'] == team_id) |
             (games_history['away_team_id'] == team_id)) &
            (games_history['date'] < game_date)
        ].sort_values('date', ascending=False)

        if len(team_games) == 0:
            return 7  # No previous games, assume well-rested

        last_game_date = team_games.iloc[0]['date']
        days_rest = (game_date - last_game_date).days - 1  # Subtract 1 because 0 = B2B

        return max(0, days_rest)

    def get_games_in_last_n_days(self,
                                 team_id: int,
                                 game_date: datetime,
                                 games_history: pd.DataFrame,
                                 days: int) -> int:
        """
        Count games team played in last N days.

        Args:
            team_id: Team identifier
            game_date: Current game date
            games_history: Historical games DataFrame
            days: Number of days to look back

        Returns:
            Number of games played in last N days
        """

        start_date = game_date - timedelta(days=days)

        games_history = games_history.copy()
        if 'date' in games_history.columns:
            games_history['date'] = pd.to_datetime(games_history['date'], format='%Y%m%d')

        recent_games = games_history[
            ((games_history['home_team_id'] == team_id) |
             (games_history['away_team_id'] == team_id)) &
            (games_history['date'] >= start_date) &
            (games_history['date'] < game_date)
        ]

        return len(recent_games)

    def calculate_schedule_density_penalty(self,
                                          games_in_4_days: int,
                                          games_in_5_days: int) -> float:
        """
        Calculate ELO penalty based on schedule density.

        Args:
            games_in_4_days: Number of games in last 4 days
            games_in_5_days: Number of games in last 5 days

        Returns:
            ELO penalty (0 or negative value)
        """

        # 3 games in 4 days (brutal schedule) - P4 optimization
        if games_in_4_days >= 3:
            return -30.0

        # 4 games in 5 days (exhausting)
        elif games_in_5_days >= 4:
            return -40.0

        # 4 games in 6 days (tiring)
        elif games_in_5_days + 1 >= 4:  # Approximation
            return -20.0

        return 0.0

    def calculate_rest_differential(self,
                                   home_days_rest: int,
                                   away_days_rest: int) -> Tuple[float, float]:
        """
        Calculate rest advantage when one team is much more rested.

        Args:
            home_days_rest: Days of rest for home team
            away_days_rest: Days of rest for away team

        Returns:
            Tuple of (home_adjustment, away_adjustment)
        """

        # Significant rest advantage (3+ days vs 0-1 days)
        if home_days_rest >= 3 and away_days_rest <= 1:
            return (+30.0, 0.0)
        elif away_days_rest >= 3 and home_days_rest <= 1:
            return (0.0, +30.0)

        # Moderate rest advantage (2 days vs 0 days)
        elif home_days_rest >= 2 and away_days_rest == 0:
            return (+15.0, 0.0)
        elif away_days_rest >= 2 and home_days_rest == 0:
            return (0.0, +15.0)

        return (0.0, 0.0)

    def _neutral_result(self) -> Dict:
        """Return neutral result when no game history available."""
        return {
            'home_back_to_back': False,
            'home_days_rest': 3,
            'home_games_in_4_days': 0,
            'home_games_in_5_days': 0,
            'home_b2b_penalty': 0.0,
            'home_density_penalty': 0.0,
            'home_rest_advantage': 0.0,
            'home_total_adjustment': 0.0,

            'away_back_to_back': False,
            'away_days_rest': 3,
            'away_games_in_4_days': 0,
            'away_games_in_5_days': 0,
            'away_b2b_penalty': 0.0,
            'away_density_penalty': 0.0,
            'away_rest_advantage': 0.0,
            'away_total_adjustment': 0.0,

            'rest_fatigue_active': False,
            'net_adjustment': 0.0
        }


# Singleton instance
_rest_fatigue_analyzer = None

def get_rest_fatigue_analyzer() -> RestFatigueAnalyzer:
    """Get or create the Rest/Fatigue Analyzer singleton."""
    global _rest_fatigue_analyzer
    if _rest_fatigue_analyzer is None:
        _rest_fatigue_analyzer = RestFatigueAnalyzer()
    return _rest_fatigue_analyzer
