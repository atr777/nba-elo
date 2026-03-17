"""
Player ELO Engine
Computes and tracks player-level ELO ratings based on individual performance.

Uses plus/minus as the primary performance metric, weighted by minutes played.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.utils.file_io import load_csv_to_dataframe, save_dataframe_to_csv
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Position-based ELO adjustment multipliers
#
# BPM systematically OVERVALUES rim protectors (high rebounds, low turnovers,
# team defense credit) and UNDERVALUES elite shot creators (gravity, spacing,
# pick-and-roll mastery don't show in box score).
#
# Multipliers are applied post-hoc to stored ELO ratings.
# To add a player: put their exact name and the multiplier.
# ---------------------------------------------------------------------------

# Rim protectors: BPM inflated by ~250-300 pts — reduce by 10%
RIM_PROTECTORS = {
    'Rudy Gobert', 'Jarrett Allen', 'Ivica Zubac', 'Brook Lopez',
    'Mitchell Robinson', 'Clint Capela', 'Walker Kessler', 'Mark Williams',
    'Isaiah Hartenstein', 'Onyeka Okongwu', 'Robert Williams III',
    'Precious Achiuwa', 'Bismack Biyombo', 'Nerlens Noel',
}
RIM_PROTECTOR_MULTIPLIER = 0.90

# Elite shot creators / playmakers: BPM undervalues gravity, spacing, creation
# off the dribble. Boost by 8%.
SHOT_CREATORS = {
    'Stephen Curry', 'Steph Curry',
    'James Harden',
    'Damian Lillard',
    'Trae Young',
    'De\'Aaron Fox',
    'Tyrese Haliburton',
    'LaMelo Ball',
}
SHOT_CREATOR_MULTIPLIER = 1.08

# Build a single lookup: name (lower) -> multiplier
POSITION_MULTIPLIERS: Dict[str, float] = {}
for _name in RIM_PROTECTORS:
    POSITION_MULTIPLIERS[_name.lower()] = RIM_PROTECTOR_MULTIPLIER
for _name in SHOT_CREATORS:
    POSITION_MULTIPLIERS[_name.lower()] = SHOT_CREATOR_MULTIPLIER


class PlayerELOEngine:
    """Engine for computing player-level ELO ratings."""

    def __init__(
        self,
        base_rating: float = 1500,
        k_factor: float = 20,
        regression_to_mean: float = 0.33,
        performance_metric: str = 'plus_minus'
    ):
        """
        Initialize the Player ELO Engine.

        Args:
            base_rating: Starting ELO rating for all players
            k_factor: K-factor for rating updates (sensitivity parameter)
            regression_to_mean: Regression factor between seasons (0-1)
            performance_metric: Performance metric to use ('plus_minus' or 'bpm')
        """
        self.base_rating = base_rating
        self.k_factor = k_factor
        self.regression_to_mean = regression_to_mean
        self.performance_metric = performance_metric

        # Current ratings dictionary {player_id: rating}
        self.current_ratings = {}

        # Player metadata {player_id: {'name': str, 'games': int, 'last_season': int}}
        self.player_metadata = defaultdict(lambda: {'name': '', 'games': 0, 'last_season': None})

        # History tracking
        self.rating_history = []

        # Track which seasons have had regression applied
        self.seasons_regressed = set()

        logger.info(f"Player ELO Engine initialized: base={base_rating}, K={k_factor}, regression={regression_to_mean}, metric={performance_metric}")

    def reset_ratings(self):
        """Reset all player ratings to base rating."""
        self.current_ratings = {}
        self.player_metadata = defaultdict(lambda: {'name': '', 'games': 0, 'last_season': None})
        self.rating_history = []
        self.seasons_regressed = set()
        logger.info("Player ratings reset to base")

    def _ensure_player_exists(self, player_id: str, player_name: str):
        """Ensure a player has an initialized rating."""
        if player_id not in self.current_ratings:
            self.current_ratings[player_id] = self.base_rating
            self.player_metadata[player_id]['name'] = player_name
            logger.debug(f"Initialized {player_name} (ID: {player_id}) at {self.base_rating}")

    def _apply_season_regression(self, current_season: int):
        """
        Apply regression to mean for players between seasons.
        Only applies once per season to avoid redundant calculations.

        Args:
            current_season: Current season (e.g., 2024)
        """
        # Skip if regression already applied for this season
        if current_season in self.seasons_regressed:
            return

        regressed_count = 0
        for player_id in self.current_ratings:
            last_season = self.player_metadata[player_id]['last_season']

            # If player hasn't played yet this season, regress their rating
            if last_season is not None and last_season < current_season:
                old_rating = self.current_ratings[player_id]
                # Regress toward mean (1500)
                self.current_ratings[player_id] = old_rating + self.regression_to_mean * (self.base_rating - old_rating)
                regressed_count += 1

        if regressed_count > 0:
            logger.info(f"Season {current_season}: Applied regression to {regressed_count} players from previous seasons")
            self.seasons_regressed.add(current_season)

    def process_game(self, game_id: str, date: int, players: List[Dict]) -> Dict:
        """
        Process a single game and update player ratings.

        Args:
            game_id: Unique game identifier
            date: Game date (YYYYMMDD format)
            players: List of player dictionaries from boxscore:
                {
                    'player_id': str,
                    'player_name': str,
                    'team_id': str,
                    'minutes': float,
                    'plus_minus': int,
                    'didNotPlay': bool
                }

        Returns:
            Dictionary with average rating changes
        """
        # Extract season from date (first 4 digits)
        season = int(str(date)[:4])

        # Apply season regression if needed (done once per season)
        self._apply_season_regression(season)

        # Process only players who actually played
        active_players = [p for p in players if not p.get('didNotPlay', False) and p.get('minutes', 0) > 0]

        if len(active_players) == 0:
            logger.warning(f"Game {game_id}: No active players found")
            return {'avg_change': 0.0, 'players_updated': 0}

        rating_changes = []

        for player in active_players:
            player_id = player['player_id']
            player_name = player['player_name']
            minutes = player.get('minutes', 0)
            plus_minus = player.get('plus_minus', 0)  # Get for logging

            # Ensure player exists
            self._ensure_player_exists(player_id, player_name)

            # Update player metadata
            self.player_metadata[player_id]['name'] = player_name
            self.player_metadata[player_id]['games'] += 1
            self.player_metadata[player_id]['last_season'] = season

            # Calculate performance score based on selected metric
            if minutes > 0:
                if self.performance_metric == 'bpm':
                    # Use Box Plus/Minus (BPM) metric
                    # BPM scale: -10 to +10 (typical range), with 0 = league average
                    bpm = player.get('bpm', 0.0)
                    bpm_clamped = max(-10, min(10, bpm))
                    performance_score = (bpm_clamped + 10) / 20  # 0 to 1 scale
                else:
                    # Use plus/minus metric (default)
                    # Normalize plus/minus to per-game rate
                    pm_per_48 = (plus_minus / minutes) * 48

                    # Convert to 0-1 scale (clamped between -30 and +30)
                    pm_clamped = max(-30, min(30, pm_per_48))
                    performance_score = (pm_clamped + 30) / 60  # 0 to 1 scale

                # Weight by minutes played (0-1 scale, 48 minutes = 1.0)
                minutes_weight = min(1.0, minutes / 48)

                # Adjust K-factor by minutes played (full game = full K)
                adjusted_k = self.k_factor * minutes_weight

                # Expected score is 0.5 (average performance)
                expected_score = 0.5

                # Calculate rating change
                rating_change = adjusted_k * (performance_score - expected_score)

                # Update rating
                old_rating = self.current_ratings[player_id]
                new_rating = old_rating + rating_change
                self.current_ratings[player_id] = new_rating

                # Record in history
                self._record_history(game_id, date, player, old_rating, new_rating, rating_change)

                rating_changes.append(rating_change)

                logger.debug(f"{player_name}: {old_rating:.1f} -> {new_rating:.1f} ({rating_change:+.1f}) | "
                           f"{minutes:.0f}min, +/-={plus_minus:+d}")

        return {
            'avg_change': np.mean(np.abs(rating_changes)) if rating_changes else 0.0,
            'players_updated': len(rating_changes)
        }

    def _record_history(self, game_id: str, date: int, player: Dict, old_rating: float,
                       new_rating: float, rating_change: float):
        """Record player rating change in history."""
        self.rating_history.append({
            'game_id': game_id,
            'date': date,
            'player_id': player['player_id'],
            'player_name': player['player_name'],
            'team_id': player.get('team_id', ''),
            'minutes': player.get('minutes', 0),
            'plus_minus': player.get('plus_minus', 0),
            'rating_before': old_rating,
            'rating_after': new_rating,
            'rating_change': rating_change
        })

    def _get_position_multiplier(self, player_id: str) -> float:
        """Return the position-adjustment multiplier for a player (default 1.0)."""
        name = self.player_metadata[player_id].get('name', '').lower()
        return POSITION_MULTIPLIERS.get(name, 1.0)

    def get_player_rating(self, player_id: str) -> float:
        """Get position-adjusted rating for a player."""
        raw = self.current_ratings.get(player_id, self.base_rating)
        multiplier = self._get_position_multiplier(player_id)
        return raw * multiplier

    def get_team_rating(self, player_ids: List[str], minutes: List[float]) -> float:
        """
        Calculate team rating as weighted average of player ratings.

        Args:
            player_ids: List of player IDs on the team
            minutes: List of minutes played for each player

        Returns:
            Weighted average team rating
        """
        if len(player_ids) == 0 or sum(minutes) == 0:
            return self.base_rating

        total_weighted_rating = 0.0
        total_weight = 0.0

        for player_id, mins in zip(player_ids, minutes):
            if mins > 0:
                player_rating = self.get_player_rating(player_id)
                total_weighted_rating += player_rating * mins
                total_weight += mins

        if total_weight == 0:
            return self.base_rating

        return total_weighted_rating / total_weight

    def get_top_players(self, n: int = 10, min_games: int = 10) -> List[Tuple[str, str, float, int]]:
        """
        Get top N players by rating.

        Args:
            n: Number of players to return
            min_games: Minimum games played to qualify

        Returns:
            List of tuples: (player_id, player_name, rating, games_played)
        """
        qualified_players = []

        for player_id, raw_rating in self.current_ratings.items():
            games = self.player_metadata[player_id]['games']
            if games >= min_games:
                player_name = self.player_metadata[player_id]['name']
                adjusted = raw_rating * self._get_position_multiplier(player_id)
                qualified_players.append((player_id, player_name, adjusted, games))

        # Sort by rating descending
        qualified_players.sort(key=lambda x: x[2], reverse=True)

        return qualified_players[:n]

    def export_history(self) -> pd.DataFrame:
        """Export rating history as DataFrame."""
        if not self.rating_history:
            return pd.DataFrame()

        return pd.DataFrame(self.rating_history)

    def export_current_ratings(self) -> pd.DataFrame:
        """Export current player ratings as DataFrame (position-adjusted)."""
        data = []
        for player_id, raw_rating in self.current_ratings.items():
            metadata = self.player_metadata[player_id]
            multiplier = self._get_position_multiplier(player_id)
            adjusted = raw_rating * multiplier
            data.append({
                'player_id': player_id,
                'player_name': metadata['name'],
                'rating': adjusted,           # position-adjusted (used everywhere)
                'raw_rating': raw_rating,     # pre-adjustment (for diagnostics)
                'position_multiplier': multiplier,
                'games_played': metadata['games'],
                'last_season': metadata['last_season']
            })

        df = pd.DataFrame(data)
        df = df.sort_values('rating', ascending=False)
        return df


def run_player_elo_engine(
    games_file: str,
    player_boxscores_file: str,
    output_history_file: str,
    output_ratings_file: str,
    k_factor: float = 20,
    regression_to_mean: float = 0.33,
    performance_metric: str = 'plus_minus'
):
    """
    Run the player ELO engine on historical data.

    Args:
        games_file: Path to team games CSV
        player_boxscores_file: Path to player boxscores CSV
        output_history_file: Path to save rating history
        output_ratings_file: Path to save current ratings
        k_factor: K-factor for rating updates
        regression_to_mean: Regression factor between seasons
        performance_metric: Performance metric to use ('plus_minus' or 'bpm')
    """
    logger.info("=" * 70)
    logger.info("PLAYER ELO ENGINE - Starting")
    logger.info("=" * 70)

    # Load data
    logger.info(f"Loading games from {games_file}")
    games_df = load_csv_to_dataframe(games_file)

    logger.info(f"Loading player boxscores from {player_boxscores_file}")
    players_df = load_csv_to_dataframe(player_boxscores_file)

    # Filter completed games only
    games_df = games_df[(games_df['home_score'] > 0) | (games_df['away_score'] > 0)]
    games_df = games_df.sort_values('date')

    logger.info(f"Loaded {len(games_df):,} completed games")
    logger.info(f"Loaded {len(players_df):,} player boxscore records")

    # Initialize engine
    engine = PlayerELOEngine(k_factor=k_factor, regression_to_mean=regression_to_mean, performance_metric=performance_metric)

    # Process games chronologically
    logger.info("Processing games...")

    games_processed = 0
    total_players_updated = 0

    for idx, game in games_df.iterrows():
        game_id = game['game_id']
        date = game['date']

        # Get player data for this game
        game_players = players_df[players_df['game_id'] == game_id].to_dict('records')

        if len(game_players) == 0:
            logger.warning(f"Game {game_id}: No player data found")
            continue

        # Process game
        result = engine.process_game(game_id, date, game_players)

        games_processed += 1
        total_players_updated += result['players_updated']

        # Progress logging
        if games_processed % 1000 == 0:
            logger.info(f"Progress: {games_processed:,}/{len(games_df):,} games "
                       f"({games_processed/len(games_df)*100:.1f}%)")

    logger.info(f"Processed {games_processed:,} games")
    logger.info(f"Updated {total_players_updated:,} player-game records")

    # Export results
    logger.info("Exporting rating history...")
    history_df = engine.export_history()
    save_dataframe_to_csv(history_df, output_history_file)
    logger.info(f"Saved {len(history_df):,} history records to {output_history_file}")

    logger.info("Exporting current ratings...")
    ratings_df = engine.export_current_ratings()
    save_dataframe_to_csv(ratings_df, output_ratings_file)
    logger.info(f"Saved {len(ratings_df):,} player ratings to {output_ratings_file}")

    # Show top players
    top_players = engine.get_top_players(n=10, min_games=100)
    logger.info("\nTop 10 Players (min 100 games):")
    for i, (player_id, name, rating, games) in enumerate(top_players, 1):
        logger.info(f"  {i}. {name}: {rating:.1f} ({games} games)")

    logger.info("=" * 70)
    logger.info("PLAYER ELO ENGINE - Complete")
    logger.info("=" * 70)

    return engine


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Run Player ELO Engine')
    parser.add_argument('--games', default='data/raw/nba_games_all.csv', help='Team games CSV file')
    parser.add_argument('--players', default='data/raw/player_boxscores_with_bpm.csv', help='Player boxscores CSV file')
    parser.add_argument('--output-history', default='data/exports/player_elo_history.csv', help='Output history file')
    parser.add_argument('--output-ratings', default='data/exports/player_ratings.csv', help='Output ratings file')
    parser.add_argument('--k-factor', type=float, default=20, help='K-factor for rating updates')
    parser.add_argument('--regression', type=float, default=0.33, help='Regression to mean between seasons')
    parser.add_argument('--metric', default='bpm', choices=['plus_minus', 'bpm'], help='Performance metric (plus_minus or bpm)')

    args = parser.parse_args()

    run_player_elo_engine(
        games_file=args.games,
        player_boxscores_file=args.players,
        output_history_file=args.output_history,
        output_ratings_file=args.output_ratings,
        k_factor=args.k_factor,
        regression_to_mean=args.regression,
        performance_metric=args.metric
    )
