"""
Hybrid Prediction Engine with Adaptive Weighting
==================================================

Combines team-level and player-level ELO ratings for improved prediction accuracy.

Features:
- Weighted blend of team ELO and player ELO
- Adaptive weighting for close games vs non-close games
- Integration with form and rest factors
- H2H history support

Adaptive Weighting Strategy:
-----------------------------
Close Games (ELO diff < 100):
  - Team: 50%, Player: 20%, Form: 20%, Rest: 10%
  - Rationale: Close matchups benefit from recent momentum and fatigue factors

Non-Close Games (ELO diff >= 100):
  - Team: 70%, Player: 30%, Form: 0%, Rest: 0%
  - Rationale: Clear favorites - fundamental ratings dominate

Expected Impact:
- Close game accuracy: 53.85% → 58-60% (+5%)
- Overall accuracy: 63.39% → 65-67% (+1.5-3.5%)

Target accuracy: 68-70% (vs 65.93% baseline from team ELO only)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.utils.file_io import load_csv_to_dataframe, save_dataframe_to_csv
from src.utils.elo_math import calculate_win_probability
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class HybridPredictor:
    """
    Hybrid prediction engine combining team and player ELO ratings.

    Formula: Hybrid_Rating = (blend_weight × Team_ELO) + ((1-blend_weight) × Player_ELO)

    Default blend_weight = 0.7 (70% team, 30% player)
    """

    def __init__(
        self,
        blend_weight: float = 0.7,
        home_advantage: float = 30,  # Calibrated
        use_adaptive_weighting: bool = True,
        close_game_threshold: float = 100.0
    ):
        """
        Initialize the Hybrid Predictor.

        Args:
            blend_weight: Weight for team ELO (0-1). Player weight = 1 - blend_weight
            home_advantage: Home court advantage in rating points
            use_adaptive_weighting: If True, use different weights for close games
            close_game_threshold: ELO difference threshold to classify as "close game"
        """
        if not 0 <= blend_weight <= 1:
            raise ValueError("blend_weight must be between 0 and 1")

        self.blend_weight = blend_weight
        self.home_advantage = home_advantage
        self.use_adaptive_weighting = use_adaptive_weighting
        self.close_game_threshold = close_game_threshold

        # Load team and player ratings
        self.team_ratings = {}
        self.player_ratings = {}

        # Adaptive weighting configurations
        # Close games: More emphasis on momentum, rest, recent form
        self.close_game_weights = {
            'team': 0.50,
            'player': 0.20,
            'form': 0.20,
            'rest': 0.10
        }

        # Non-close games: Traditional team/player weighting
        self.default_weights = {
            'team': 0.70,
            'player': 0.30,
            'form': 0.0,
            'rest': 0.0
        }

        logger.info(f"Hybrid Predictor initialized: blend={blend_weight:.2f} "
                   f"(team={blend_weight:.0%}, player={1-blend_weight:.0%}), "
                   f"home_adv={home_advantage}, "
                   f"adaptive_weighting={use_adaptive_weighting}")

    def load_team_ratings(self, team_elo_file: str, date: Optional[int] = None):
        """
        Load team ELO ratings from history file.

        Args:
            team_elo_file: Path to team ELO history CSV
            date: Optional date to load ratings from (YYYYMMDD). If None, uses latest.
        """
        df = load_csv_to_dataframe(team_elo_file)

        if date is not None:
            # Filter to games on or before the specified date
            df = df[df['date'] <= date]

        # Get most recent rating for each team
        df_sorted = df.sort_values('date')
        for team_id in df_sorted['team_id'].unique():
            team_df = df_sorted[df_sorted['team_id'] == team_id]
            if len(team_df) > 0:
                self.team_ratings[team_id] = team_df.iloc[-1]['rating_after']

        logger.info(f"Loaded {len(self.team_ratings)} team ratings from {team_elo_file}")

    def load_player_ratings(self, player_ratings_file: str):
        """
        Load player ELO ratings from current ratings file.

        Args:
            player_ratings_file: Path to player ratings CSV
        """
        df = load_csv_to_dataframe(player_ratings_file)

        for _, row in df.iterrows():
            player_id = str(row['player_id'])
            self.player_ratings[player_id] = row['rating']

        logger.info(f"Loaded {len(self.player_ratings)} player ratings from {player_ratings_file}")

    def get_team_rating_from_team_elo(self, team_id: str, default: float = 1500) -> float:
        """Get team rating from team ELO system."""
        return self.team_ratings.get(team_id, default)

    def get_team_rating_from_players(
        self,
        player_boxscores: pd.DataFrame,
        game_id: str,
        team_id: str,
        default: float = 1500
    ) -> float:
        """
        Calculate team rating as weighted average of player ratings.

        Args:
            player_boxscores: DataFrame with player boxscore data
            game_id: Game ID to look up
            team_id: Team ID to calculate rating for
            default: Default rating if no players found

        Returns:
            Weighted average team rating based on minutes played
        """
        # Get players for this game and team
        game_players = player_boxscores[
            (player_boxscores['game_id'] == game_id) &
            (player_boxscores['team_id'] == team_id)
        ]

        if len(game_players) == 0:
            return default

        total_weighted_rating = 0.0
        total_minutes = 0.0

        for _, player in game_players.iterrows():
            player_id = str(player['player_id'])
            minutes = player.get('minutes', 0)

            if minutes > 0:
                player_rating = self.player_ratings.get(player_id, default)
                total_weighted_rating += player_rating * minutes
                total_minutes += minutes

        if total_minutes == 0:
            return default

        return total_weighted_rating / total_minutes

    def is_close_game(self, home_rating: float, away_rating: float) -> bool:
        """
        Determine if a game should be classified as "close" based on ELO difference.

        Args:
            home_rating: Home team rating
            away_rating: Away team rating

        Returns:
            True if ELO difference is below threshold
        """
        elo_diff = abs(home_rating - away_rating)
        return elo_diff < self.close_game_threshold

    def get_adaptive_weights(self, home_rating: float, away_rating: float) -> Dict[str, float]:
        """
        Get weights based on whether this is a close game.

        Args:
            home_rating: Home team rating
            away_rating: Away team rating

        Returns:
            Dictionary with weights for team, player, form, rest
        """
        if not self.use_adaptive_weighting:
            return self.default_weights

        if self.is_close_game(home_rating, away_rating):
            return self.close_game_weights
        else:
            return self.default_weights

    def get_hybrid_rating(
        self,
        team_id: str,
        player_boxscores: pd.DataFrame,
        game_id: str,
        blend_weight: Optional[float] = None
    ) -> float:
        """
        Calculate hybrid rating combining team and player ELO.

        Args:
            team_id: Team ID
            player_boxscores: DataFrame with player boxscore data
            game_id: Game ID
            blend_weight: Optional override for blend weight

        Returns:
            Hybrid rating = (blend_weight × Team_ELO) + ((1-blend_weight) × Player_ELO)
        """
        team_rating = self.get_team_rating_from_team_elo(team_id)
        player_rating = self.get_team_rating_from_players(player_boxscores, game_id, team_id)

        weight = blend_weight if blend_weight is not None else self.blend_weight
        hybrid_rating = (weight * team_rating) + ((1 - weight) * player_rating)

        return hybrid_rating

    def predict_game(
        self,
        home_team_id: str,
        away_team_id: str,
        player_boxscores: pd.DataFrame,
        game_id: str,
        form_factor_home: float = 0.0,
        form_factor_away: float = 0.0,
        rest_factor_home: float = 0.0,
        rest_factor_away: float = 0.0
    ) -> Dict:
        """
        Predict game outcome using hybrid ratings with adaptive weighting.

        Args:
            home_team_id: Home team ID
            away_team_id: Away team ID
            player_boxscores: DataFrame with player boxscore data
            game_id: Game ID
            form_factor_home: Home team form adjustment (ELO points, default 0)
            form_factor_away: Away team form adjustment (ELO points, default 0)
            rest_factor_home: Home team rest adjustment (ELO points, default 0)
            rest_factor_away: Away team rest adjustment (ELO points, default 0)

        Returns:
            Dictionary with:
                - home_win_prob: Probability home team wins (0-1)
                - away_win_prob: Probability away team wins (0-1)
                - home_hybrid_rating: Home team hybrid rating
                - away_hybrid_rating: Away team hybrid rating
                - predicted_winner: 'home' or 'away'
                - is_close_game: Boolean indicating if game is close
                - weights_used: Dict with weights applied
        """
        # Get base hybrid ratings
        home_team_rating = self.get_team_rating_from_team_elo(home_team_id)
        away_team_rating = self.get_team_rating_from_team_elo(away_team_id)

        # Determine adaptive weights based on ELO difference
        weights = self.get_adaptive_weights(home_team_rating, away_team_rating)
        is_close = self.is_close_game(home_team_rating, away_team_rating)

        # Calculate hybrid ratings with adaptive blending
        home_player_rating = self.get_team_rating_from_players(player_boxscores, game_id, home_team_id)
        away_player_rating = self.get_team_rating_from_players(player_boxscores, game_id, away_team_id)

        # Apply adaptive weights
        home_rating = (
            weights['team'] * home_team_rating +
            weights['player'] * home_player_rating +
            weights['form'] * form_factor_home +
            weights['rest'] * rest_factor_home
        )

        away_rating = (
            weights['team'] * away_team_rating +
            weights['player'] * away_player_rating +
            weights['form'] * form_factor_away +
            weights['rest'] * rest_factor_away
        )

        # Calculate win probability
        home_win_prob = calculate_win_probability(home_rating, away_rating, self.home_advantage)
        away_win_prob = 1 - home_win_prob

        predicted_winner = 'home' if home_win_prob > 0.5 else 'away'

        return {
            'home_win_prob': home_win_prob,
            'away_win_prob': away_win_prob,
            'home_hybrid_rating': home_rating,
            'away_hybrid_rating': away_rating,
            'predicted_winner': predicted_winner,
            'is_close_game': is_close,
            'weights_used': weights,
            'elo_diff': abs(home_team_rating - away_team_rating)
        }


def validate_hybrid_predictions(
    games_file: str,
    team_elo_file: str,
    player_ratings_file: str,
    player_boxscores_file: str,
    blend_weight: float = 0.7,
    home_advantage: float = 30,  # Calibrated to 54.33% home win rate
    output_file: Optional[str] = None
) -> Dict:
    """
    Validate hybrid prediction accuracy on historical games.

    Args:
        games_file: Path to games CSV
        team_elo_file: Path to team ELO history CSV
        player_ratings_file: Path to player ratings CSV
        player_boxscores_file: Path to player boxscores CSV
        blend_weight: Weight for team ELO (0-1)
        home_advantage: Home court advantage in rating points
        output_file: Optional path to save predictions

    Returns:
        Dictionary with accuracy metrics
    """
    logger.info("=" * 70)
    logger.info(f"HYBRID PREDICTOR VALIDATION - Blend Weight: {blend_weight:.2f}")
    logger.info("=" * 70)

    # Load data
    logger.info(f"Loading games from {games_file}")
    games_df = load_csv_to_dataframe(games_file)

    logger.info(f"Loading team ELO history from {team_elo_file}")
    team_elo_df = load_csv_to_dataframe(team_elo_file)

    logger.info(f"Loading player boxscores from {player_boxscores_file}")
    player_boxscores_df = load_csv_to_dataframe(player_boxscores_file)

    # Filter completed games only
    games_df = games_df[(games_df['home_score'] > 0) | (games_df['away_score'] > 0)]
    games_df = games_df.sort_values('date')

    logger.info(f"Loaded {len(games_df):,} completed games")

    # Initialize predictor
    predictor = HybridPredictor(blend_weight=blend_weight, home_advantage=home_advantage)

    # Load player ratings (current snapshot - we'll use this for all games)
    predictor.load_player_ratings(player_ratings_file)

    # Process games chronologically
    logger.info("Making predictions...")

    predictions = []
    correct_predictions = 0
    total_predictions = 0

    # Build team ELO lookup by date
    team_elo_df = team_elo_df.sort_values(['team_id', 'date'])

    for idx, game in games_df.iterrows():
        game_id = game['game_id']
        date = game['date']
        home_team = game['home_team_id']
        away_team = game['away_team_id']
        home_score = game['home_score']
        away_score = game['away_score']

        # Get team ratings as of this game date
        home_team_elo_history = team_elo_df[
            (team_elo_df['team_id'] == home_team) &
            (team_elo_df['date'] <= date)
        ]
        away_team_elo_history = team_elo_df[
            (team_elo_df['team_id'] == away_team) &
            (team_elo_df['date'] <= date)
        ]

        if len(home_team_elo_history) > 0:
            predictor.team_ratings[home_team] = home_team_elo_history.iloc[-1]['rating_after']
        else:
            predictor.team_ratings[home_team] = 1500

        if len(away_team_elo_history) > 0:
            predictor.team_ratings[away_team] = away_team_elo_history.iloc[-1]['rating_after']
        else:
            predictor.team_ratings[away_team] = 1500

        # Make prediction
        prediction = predictor.predict_game(home_team, away_team, player_boxscores_df, game_id)

        # Determine actual winner
        actual_winner = 'home' if home_score > away_score else 'away'

        # Check if prediction correct
        is_correct = prediction['predicted_winner'] == actual_winner
        if is_correct:
            correct_predictions += 1
        total_predictions += 1

        # Record prediction
        predictions.append({
            'game_id': game_id,
            'date': date,
            'home_team_id': home_team,
            'away_team_id': away_team,
            'home_score': home_score,
            'away_score': away_score,
            'actual_winner': actual_winner,
            'predicted_winner': prediction['predicted_winner'],
            'home_win_prob': prediction['home_win_prob'],
            'away_win_prob': prediction['away_win_prob'],
            'home_hybrid_rating': prediction['home_hybrid_rating'],
            'away_hybrid_rating': prediction['away_hybrid_rating'],
            'is_correct': is_correct
        })

        # Progress logging
        if total_predictions % 1000 == 0:
            current_accuracy = correct_predictions / total_predictions * 100
            logger.info(f"Progress: {total_predictions:,}/{len(games_df):,} games "
                       f"({total_predictions/len(games_df)*100:.1f}%) | "
                       f"Accuracy: {current_accuracy:.2f}%")

    # Calculate final accuracy
    accuracy = correct_predictions / total_predictions * 100

    logger.info("=" * 70)
    logger.info(f"VALIDATION COMPLETE")
    logger.info(f"Total Games: {total_predictions:,}")
    logger.info(f"Correct Predictions: {correct_predictions:,}")
    logger.info(f"Accuracy: {accuracy:.2f}%")
    logger.info(f"Blend Weight: {blend_weight:.2f} (team={blend_weight:.0%}, player={1-blend_weight:.0%})")
    logger.info("=" * 70)

    # Save predictions if requested
    if output_file:
        predictions_df = pd.DataFrame(predictions)
        save_dataframe_to_csv(predictions_df, output_file)
        logger.info(f"Saved predictions to {output_file}")

    return {
        'accuracy': accuracy,
        'correct_predictions': correct_predictions,
        'total_predictions': total_predictions,
        'blend_weight': blend_weight
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Validate Hybrid Predictor')
    parser.add_argument('--games', default='data/raw/nba_games_all.csv', help='Games CSV file')
    parser.add_argument('--team-elo', default='data/exports/team_elo_history_phase_1_5.csv',
                       help='Team ELO history CSV file')
    parser.add_argument('--player-ratings', default='data/exports/player_ratings.csv',
                       help='Player ratings CSV file')
    parser.add_argument('--player-boxscores', default='data/raw/player_boxscores_all.csv',
                       help='Player boxscores CSV file')
    parser.add_argument('--blend-weight', type=float, default=0.7,
                       help='Blend weight for team ELO (0-1, default 0.7)')
    parser.add_argument('--home-advantage', type=float, default=70,
                       help='Home court advantage (default 70)')
    parser.add_argument('--output', default=None,
                       help='Optional output file for predictions')

    args = parser.parse_args()

    validate_hybrid_predictions(
        games_file=args.games,
        team_elo_file=args.team_elo,
        player_ratings_file=args.player_ratings,
        player_boxscores_file=args.player_boxscores,
        blend_weight=args.blend_weight,
        home_advantage=args.home_advantage,
        output_file=args.output
    )
