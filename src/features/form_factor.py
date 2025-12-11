"""
Form Factor (Momentum) Tracking
Tracks recent team performance to adjust predictions based on hot/cold streaks.
"""

import pandas as pd
import logging
from typing import Dict, List, Tuple
from collections import deque

logger = logging.getLogger(__name__)


class FormTracker:
    """
    Tracks team form (hot/cold streaks) based on recent game performance.

    Uses last N games to calculate:
    - Average point differential
    - Win rate
    - Form adjustment factor
    """

    def __init__(self, lookback_games: int = 5, form_weight: float = 0.1):
        """
        Initialize form tracker.

        Args:
            lookback_games: Number of recent games to consider (default 5)
            form_weight: Weight to apply to form adjustment (default 0.1 = 10%)
        """
        self.lookback_games = lookback_games
        self.form_weight = form_weight

        # Track recent games for each team: {team_id: deque([point_diffs])}
        self.team_recent_games = {}

        logger.info(
            f"Form Tracker initialized: lookback={lookback_games}, "
            f"weight={form_weight}"
        )

    def add_game_result(
        self,
        team_id: str,
        point_differential: int
    ):
        """
        Add a game result to team's recent history.

        Args:
            team_id: Team identifier
            point_differential: Points scored - points allowed (positive = win)
        """
        if team_id not in self.team_recent_games:
            self.team_recent_games[team_id] = deque(maxlen=self.lookback_games)

        self.team_recent_games[team_id].append(point_differential)

    def get_form_adjustment(self, team_id: str) -> float:
        """
        Calculate form adjustment for a team based on recent performance.

        Formula: avg_point_diff * form_weight * momentum_multiplier

        Where momentum_multiplier amplifies consistent trends:
        - All wins or all losses: 1.2x multiplier
        - Mixed results: 1.0x multiplier

        Args:
            team_id: Team identifier

        Returns:
            ELO adjustment points (positive for hot, negative for cold)
        """
        if team_id not in self.team_recent_games:
            return 0.0

        recent = list(self.team_recent_games[team_id])

        if len(recent) == 0:
            return 0.0

        # Calculate average point differential
        avg_diff = sum(recent) / len(recent)

        # Calculate momentum multiplier (amplify consistent streaks)
        if len(recent) >= 3:
            # Check if on winning or losing streak
            all_wins = all(diff > 0 for diff in recent)
            all_losses = all(diff < 0 for diff in recent)

            if all_wins or all_losses:
                momentum_multiplier = 1.2  # Amplify consistent streaks
            else:
                momentum_multiplier = 1.0
        else:
            momentum_multiplier = 1.0

        # Convert average point diff to ELO adjustment
        # Scale: 10 point avg differential = ~50 ELO points with default weight
        adjustment = avg_diff * (self.form_weight * 50) * momentum_multiplier

        logger.debug(
            f"Team {team_id} form: avg_diff={avg_diff:.1f}, "
            f"multiplier={momentum_multiplier:.1f}, adjustment={adjustment:.1f}"
        )

        return adjustment

    def get_form_stats(self, team_id: str) -> Dict:
        """
        Get detailed form statistics for a team.

        Args:
            team_id: Team identifier

        Returns:
            Dictionary with form statistics
        """
        if team_id not in self.team_recent_games:
            return {
                'games_tracked': 0,
                'avg_point_diff': 0.0,
                'win_rate': 0.0,
                'form_adjustment': 0.0,
                'streak_type': 'none'
            }

        recent = list(self.team_recent_games[team_id])

        if len(recent) == 0:
            return {
                'games_tracked': 0,
                'avg_point_diff': 0.0,
                'win_rate': 0.0,
                'form_adjustment': 0.0,
                'streak_type': 'none'
            }

        avg_diff = sum(recent) / len(recent)
        wins = sum(1 for diff in recent if diff > 0)
        win_rate = wins / len(recent)
        adjustment = self.get_form_adjustment(team_id)

        # Determine streak type
        if len(recent) >= 3:
            if all(diff > 0 for diff in recent):
                streak_type = 'winning'
            elif all(diff < 0 for diff in recent):
                streak_type = 'losing'
            else:
                streak_type = 'mixed'
        else:
            streak_type = 'insufficient_data'

        return {
            'games_tracked': len(recent),
            'avg_point_diff': avg_diff,
            'win_rate': win_rate,
            'form_adjustment': adjustment,
            'streak_type': streak_type
        }

    def clear_team_history(self, team_id: str):
        """Clear form history for a team (e.g., new season)."""
        if team_id in self.team_recent_games:
            self.team_recent_games[team_id].clear()

    def clear_all_history(self):
        """Clear all form history (e.g., new season start)."""
        self.team_recent_games.clear()


def apply_form_adjustments(
    home_rating: float,
    away_rating: float,
    home_team_id: str,
    away_team_id: str,
    form_tracker: FormTracker
) -> Tuple[float, float]:
    """
    Apply form adjustments to team ratings.

    Args:
        home_rating: Home team's base ELO rating
        away_rating: Away team's base ELO rating
        home_team_id: Home team identifier
        away_team_id: Away team identifier
        form_tracker: FormTracker instance with recent game history

    Returns:
        Tuple of (adjusted_home_rating, adjusted_away_rating)
    """
    home_adjustment = form_tracker.get_form_adjustment(home_team_id)
    away_adjustment = form_tracker.get_form_adjustment(away_team_id)

    adjusted_home = home_rating + home_adjustment
    adjusted_away = away_rating + away_adjustment

    logger.debug(
        f"Form adjustments: home {home_rating:.0f} + {home_adjustment:+.0f} = {adjusted_home:.0f}, "
        f"away {away_rating:.0f} + {away_adjustment:+.0f} = {adjusted_away:.0f}"
    )

    return adjusted_home, adjusted_away


def analyze_form_impact(games_df: pd.DataFrame, lookback: int = 5) -> pd.DataFrame:
    """
    Analyze the impact of form on game outcomes.

    Args:
        games_df: DataFrame with columns ['home_team_id', 'away_team_id',
                  'home_score', 'away_score', 'date']
        lookback: Number of games to consider for form

    Returns:
        DataFrame with form analysis results
    """
    tracker = FormTracker(lookback_games=lookback)
    results = []

    # Sort by date
    games_df = games_df.sort_values('date').reset_index(drop=True)

    for idx, game in games_df.iterrows():
        home_id = game['home_team_id']
        away_id = game['away_team_id']

        # Get form before this game
        home_form = tracker.get_form_stats(home_id)
        away_form = tracker.get_form_stats(away_id)

        # Actual result
        home_won = game['home_score'] > game['away_score']

        # Update tracker with this game's result
        home_diff = game['home_score'] - game['away_score']
        away_diff = game['away_score'] - game['home_score']

        tracker.add_game_result(home_id, home_diff)
        tracker.add_game_result(away_id, away_diff)

        # Record analysis
        results.append({
            'game_id': game.get('game_id', idx),
            'date': game['date'],
            'home_team': home_id,
            'away_team': away_id,
            'home_won': home_won,
            'home_form_avg_diff': home_form['avg_point_diff'],
            'away_form_avg_diff': away_form['avg_point_diff'],
            'home_form_adjustment': home_form['form_adjustment'],
            'away_form_adjustment': away_form['form_adjustment'],
            'form_differential': home_form['form_adjustment'] - away_form['form_adjustment'],
            'home_streak': home_form['streak_type'],
            'away_streak': away_form['streak_type']
        })

    return pd.DataFrame(results)
