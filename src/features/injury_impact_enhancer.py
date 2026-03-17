"""
Enhanced Injury Impact Analyzer
Extends basic injury tracking with returning player discount and injury history.

Priority 2 Enhancement: Advanced injury impact modeling

Features:
- Returning player discount (first game back = 70-80% effectiveness)
- Injury history tracking (multiple injuries compound)
- Cumulative injury load calculation
- Expected recovery curves

Research: Players returning from injury typically need 1-3 games to regain full effectiveness.
Long-term injuries (>2 weeks) have longer recovery curves than short-term injuries.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd

logger = logging.getLogger(__name__)


class InjuryImpactEnhancer:
    """
    Enhanced injury impact analysis with returning player modeling.

    Tracks:
    - Current injuries (standard)
    - Returning players (new)
    - Injury history (new)
    - Cumulative load (new)
    """

    def __init__(
        self,
        returning_player_effectiveness: float = 0.75,
        recovery_games: int = 3,
        long_term_injury_days: int = 14
    ):
        """
        Initialize injury impact enhancer.

        Args:
            returning_player_effectiveness: Effectiveness on first game back (default: 75%)
            recovery_games: Games needed to return to 100% (default: 3)
            long_term_injury_days: Days to qualify as long-term injury (default: 14)
        """
        self.returning_effectiveness = returning_player_effectiveness
        self.recovery_games = recovery_games
        self.long_term_threshold = long_term_injury_days

        # Injury history: {player_name: [injury_dates]}
        self.injury_history = {}

        # Returning player tracking: {player_name: {'return_date': date, 'games_since': int}}
        self.returning_players = {}

        logger.info(
            f"Injury Impact Enhancer initialized: "
            f"returning_eff={returning_player_effectiveness:.0%}, "
            f"recovery_games={recovery_games}"
        )

    def calculate_enhanced_injury_adjustment(
        self,
        team_id: str,
        injured_players: List[str],
        returning_players: List[str],
        player_ratings: pd.DataFrame,
        player_team_mapping: pd.DataFrame,
        game_date: datetime,
        base_adjustment: float
    ) -> Dict:
        """
        Calculate enhanced injury adjustment with returning player discount.

        Args:
            team_id: Team identifier
            injured_players: List of currently injured player names
            returning_players: List of players returning from injury
            player_ratings: Player ratings DataFrame
            player_team_mapping: Player-team mapping DataFrame
            game_date: Game date
            base_adjustment: Base injury adjustment from calculate_injury_adjustment_enhanced()

        Returns:
            Dictionary with:
                - total_adjustment: Final ELO adjustment
                - base_injury_adjustment: Original injury adjustment
                - returning_player_boost: Boost from returning players
                - returning_player_details: List of returning player info
                - cumulative_injury_load: Total injury burden on team
        """
        returning_boost = 0.0
        returning_details = []

        # Calculate returning player boost
        for player_name in returning_players:
            # Get player rating
            player_data = player_ratings[player_ratings['player_name'] == player_name]

            if len(player_data) == 0:
                logger.debug(f"Returning player {player_name} not found in ratings")
                continue

            player_rating = player_data.iloc[0]['rating']

            # Check if this is first game back or early in recovery
            games_since_return = self._get_games_since_return(player_name, game_date)

            # Calculate recovery multiplier (improves over time)
            recovery_multiplier = self._calculate_recovery_multiplier(games_since_return)

            # Calculate boost (fraction of full player value)
            # A returning player is worth less than full value initially
            full_value = (player_rating - 1500) / 10.0  # ELO impact
            discounted_value = full_value * recovery_multiplier

            # The "boost" is the difference from being fully out
            # Boost = discounted_value (we get something back, but not full value)
            returning_boost += discounted_value

            returning_details.append({
                'name': player_name,
                'rating': player_rating,
                'games_since_return': games_since_return,
                'recovery_multiplier': recovery_multiplier,
                'boost': discounted_value
            })

            logger.info(
                f"Returning player: {player_name} ({player_rating:.0f} ELO) - "
                f"Game {games_since_return} back, {recovery_multiplier:.0%} effective, "
                f"+{discounted_value:.1f} ELO boost"
            )

            # Update tracking
            self._update_returning_player_tracking(player_name, game_date)

        # Calculate cumulative injury load
        injury_load = self._calculate_cumulative_injury_load(
            team_id, injured_players, returning_players
        )

        # Total adjustment = base injury penalty + returning player boost
        total_adjustment = base_adjustment + returning_boost

        return {
            'total_adjustment': total_adjustment,
            'base_injury_adjustment': base_adjustment,
            'returning_player_boost': returning_boost,
            'returning_player_details': returning_details,
            'cumulative_injury_load': injury_load,
            'returning_players_count': len(returning_players)
        }

    def _calculate_recovery_multiplier(self, games_since_return: int) -> float:
        """
        Calculate recovery multiplier based on games since return.

        Research: Players typically need 1-3 games to return to full effectiveness.

        Recovery curve:
        - Game 1: 75% effectiveness
        - Game 2: 85% effectiveness
        - Game 3: 95% effectiveness
        - Game 4+: 100% effectiveness

        Args:
            games_since_return: Number of games since returning from injury

        Returns:
            Recovery multiplier (0.75 to 1.0)
        """
        if games_since_return == 0:
            # First game back
            return self.returning_effectiveness  # 75%

        elif games_since_return == 1:
            # Second game back
            return 0.85

        elif games_since_return == 2:
            # Third game back
            return 0.95

        else:
            # Fully recovered
            return 1.0

    def _get_games_since_return(self, player_name: str, current_date: datetime) -> int:
        """
        Get number of games since player returned from injury.

        Args:
            player_name: Player name
            current_date: Current game date

        Returns:
            Number of games since return (0 = first game back)
        """
        if player_name not in self.returning_players:
            # Assume this is first game back if not tracked
            return 0

        return self.returning_players[player_name].get('games_since', 0)

    def _update_returning_player_tracking(self, player_name: str, game_date: datetime):
        """
        Update tracking for returning player.

        Args:
            player_name: Player name
            game_date: Game date
        """
        if player_name not in self.returning_players:
            self.returning_players[player_name] = {
                'return_date': game_date,
                'games_since': 0
            }
        else:
            # Increment games since return
            self.returning_players[player_name]['games_since'] += 1

        # Clean up players who have fully recovered (4+ games)
        if self.returning_players[player_name]['games_since'] >= self.recovery_games:
            logger.debug(f"{player_name} fully recovered, removing from tracking")
            del self.returning_players[player_name]

    def _calculate_cumulative_injury_load(
        self,
        team_id: str,
        injured_players: List[str],
        returning_players: List[str]
    ) -> float:
        """
        Calculate cumulative injury load on team.

        Multiple injuries create compound stress on roster (remaining players play more minutes).

        Formula:
            load = (injured_count + 0.5 * returning_count) / roster_size

        Args:
            team_id: Team identifier
            injured_players: List of injured players
            returning_players: List of returning players

        Returns:
            Injury load score (0.0 to 1.0+)
        """
        roster_size = 13  # Typical NBA active roster size

        # Injured players count as full load
        injured_load = len(injured_players)

        # Returning players count as half load (still not 100%)
        returning_load = 0.5 * len(returning_players)

        total_load = (injured_load + returning_load) / roster_size

        return total_load

    def track_injury(self, player_name: str, injury_date: datetime):
        """
        Track an injury for a player.

        Args:
            player_name: Player name
            injury_date: Date of injury
        """
        if player_name not in self.injury_history:
            self.injury_history[player_name] = []

        self.injury_history[player_name].append(injury_date)

        logger.debug(f"Tracked injury for {player_name} on {injury_date.strftime('%Y-%m-%d')}")

    def get_injury_count(self, player_name: str, lookback_days: int = 365) -> int:
        """
        Get number of injuries for a player in lookback period.

        Args:
            player_name: Player name
            lookback_days: Days to look back (default: 365)

        Returns:
            Number of injuries
        """
        if player_name not in self.injury_history:
            return 0

        cutoff_date = datetime.now() - timedelta(days=lookback_days)

        recent_injuries = [
            d for d in self.injury_history[player_name]
            if d >= cutoff_date
        ]

        return len(recent_injuries)

    def is_injury_prone(self, player_name: str, threshold: int = 3) -> bool:
        """
        Check if player is injury-prone.

        Args:
            player_name: Player name
            threshold: Injury count threshold (default: 3 in last year)

        Returns:
            True if injury-prone
        """
        injury_count = self.get_injury_count(player_name, lookback_days=365)

        return injury_count >= threshold


# Singleton instance
_injury_impact_enhancer = None

def get_injury_impact_enhancer() -> InjuryImpactEnhancer:
    """Get or create the InjuryImpactEnhancer singleton."""
    global _injury_impact_enhancer
    if _injury_impact_enhancer is None:
        _injury_impact_enhancer = InjuryImpactEnhancer()
        logger.info("Injury Impact Enhancer initialized")
    return _injury_impact_enhancer
