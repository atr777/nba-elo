"""
Momentum & Streak Tracker

Adds ELO adjustments based on recent win/loss streaks to capture team momentum.
Teams on winning streaks have psychological/momentum advantages not captured by base ELO.

Expected improvement: +1-2% accuracy
"""

import pandas as pd
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class MomentumTracker:
    """Tracks team momentum based on recent game results."""

    def __init__(self, lookback_games: int = 5, max_adjustment: int = 30):
        """
        Initialize momentum tracker.

        Args:
            lookback_games: Number of recent games to consider for momentum
            max_adjustment: Maximum ELO adjustment (positive or negative)
        """
        self.lookback_games = lookback_games
        self.max_adjustment = max_adjustment

        logger.info(
            f"Momentum Tracker initialized: lookback={lookback_games} games, "
            f"max_adjustment=±{max_adjustment} ELO"
        )

    def get_streak_adjustment(
        self,
        team_id: int,
        games_history: pd.DataFrame,
        game_date: Optional[pd.Timestamp] = None
    ) -> float:
        """
        Calculate streak-based ELO adjustment.

        Args:
            team_id: Team identifier
            games_history: Historical game data
            game_date: Date to calculate streak up to (defaults to most recent)

        Returns:
            ELO adjustment (-30 to +30)
        """
        # Filter games for this team
        team_games = games_history[
            (games_history['home_team_id'] == team_id) |
            (games_history['away_team_id'] == team_id)
        ].copy()

        if len(team_games) == 0:
            return 0.0

        # Filter to games before the specified date
        if game_date is not None:
            team_games = team_games[team_games['date'] < game_date]

        if len(team_games) == 0:
            return 0.0

        # Sort by date descending and take last N games
        team_games = team_games.sort_values('date', ascending=False).head(
            self.lookback_games
        )

        # Count wins in recent games
        wins = 0
        for _, game in team_games.iterrows():
            if game['home_team_id'] == team_id:
                # Team was home
                if game['home_score'] > game['away_score']:
                    wins += 1
            else:
                # Team was away
                if game['away_score'] > game['home_score']:
                    wins += 1

        total_games = len(team_games)

        # Calculate adjustment based on recent form
        # 0-1 wins in last 5: -30 to -10 ELO (cold streak)
        # 2-3 wins in last 5: 0 ELO (neutral)
        # 4-5 wins in last 5: +10 to +30 ELO (hot streak)

        if wins >= 4:  # Hot streak (4-5 wins out of last 5)
            adjustment = min((wins - 3) * 15, self.max_adjustment)
            logger.debug(
                f"Hot streak for team {team_id}: {wins}/{total_games} wins → "
                f"+{adjustment:.0f} ELO"
            )
        elif wins <= 1:  # Cold streak (0-1 wins out of last 5)
            adjustment = max((wins - 2) * 15, -self.max_adjustment)
            logger.debug(
                f"Cold streak for team {team_id}: {wins}/{total_games} wins → "
                f"{adjustment:.0f} ELO"
            )
        else:  # Neutral (2-3 wins out of last 5)
            adjustment = 0.0
            logger.debug(
                f"Neutral form for team {team_id}: {wins}/{total_games} wins → "
                f"0 ELO"
            )

        return adjustment


# Singleton instance
_momentum_tracker = None


def get_momentum_tracker() -> MomentumTracker:
    """Get or create the Momentum Tracker singleton."""
    global _momentum_tracker
    if _momentum_tracker is None:
        _momentum_tracker = MomentumTracker()
    return _momentum_tracker
