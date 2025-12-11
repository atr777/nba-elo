"""
Team ELO Engine
Computes and tracks team-level ELO ratings across NBA seasons.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from collections import defaultdict
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.utils.file_io import load_csv_to_dataframe, save_dataframe_to_csv, load_settings, get_data_path
from src.utils.elo_math import process_game_elo_update
from src.utils.logging_utils import get_logger
from src.features.form_factor import FormTracker
from src.features.rest_penalties import RestTracker

logger = get_logger(__name__)


class TeamELOEngine:
    """Engine for computing team-level ELO ratings."""

    def __init__(
        self,
        base_rating: float = 1500,
        k_factor: float = 20,
        home_advantage: float = 20,  # Phase 4: Reduced from 30 to 20 (modern NBA has lower HCA)
        use_mov: bool = True,
        use_enhanced_features: bool = True,
        use_top_player_concentration: bool = True,
        player_ratings: pd.DataFrame = None,
        player_team_mapping: pd.DataFrame = None
    ):
        """
        Initialize the Team ELO Engine.

        Args:
            base_rating: Starting ELO rating for all teams
            k_factor: K-factor for rating updates (sensitivity parameter)
            home_advantage: Home court advantage rating bonus
            use_mov: If True, apply margin-of-victory multiplier (default: True)
            use_enhanced_features: If True, apply form factor and rest penalties (default: True)
            use_top_player_concentration: If True, apply top player concentration adjustments (default: True)
            player_ratings: DataFrame with player ratings for concentration calculations
            player_team_mapping: DataFrame mapping players to teams
        """
        self.base_rating = base_rating
        self.k_factor = k_factor
        self.home_advantage = home_advantage
        self.use_mov = use_mov
        self.use_enhanced_features = use_enhanced_features
        self.use_top_player_concentration = use_top_player_concentration

        # Current ratings dictionary {team_id: rating}
        self.current_ratings = {}

        # History tracking
        self.rating_history = []

        # Player data for top player concentration
        self.player_ratings = player_ratings if player_ratings is not None else pd.DataFrame()
        self.player_team_mapping = player_team_mapping if player_team_mapping is not None else pd.DataFrame()

        # Enhanced features trackers
        if use_enhanced_features:
            self.form_tracker = FormTracker(lookback_games=5, form_weight=0.1)
            self.rest_tracker = RestTracker(b2b_penalty=46, one_day_penalty=15)
        else:
            self.form_tracker = None
            self.rest_tracker = None

        mov_status = "enabled" if use_mov else "disabled"
        enhanced_status = "enabled" if use_enhanced_features else "disabled"
        concentration_status = "enabled" if use_top_player_concentration else "disabled"
        logger.info(
            f"Team ELO Engine initialized: base={base_rating}, K={k_factor}, "
            f"home_adv={home_advantage}, MOV={mov_status}, Enhanced={enhanced_status}, "
            f"TopPlayerConcentration={concentration_status}"
        )
    
    def reset_ratings(self):
        """Reset all team ratings to base rating."""
        self.current_ratings = {}
        self.rating_history = []
        logger.info("Ratings reset to base")
    
    def _ensure_team_exists(self, team_id: str, team_name: str):
        """Ensure a team has an initialized rating."""
        if team_id not in self.current_ratings:
            self.current_ratings[team_id] = self.base_rating
            logger.debug(f"Initialized {team_name} (ID: {team_id}) at {self.base_rating}")
    
    def process_game(self, game: Dict) -> Dict:
        """
        Process a single game and update team ratings.
        
        Args:
            game: Dictionary with keys: game_id, date, home_team_id, home_team_name,
                  away_team_id, away_team_name, home_score, away_score
                  
        Returns:
            Dictionary with game results and rating changes
        """
        # Ensure teams exist
        self._ensure_team_exists(game['home_team_id'], game['home_team_name'])
        self._ensure_team_exists(game['away_team_id'], game['away_team_name'])
        
        # Get current ratings
        home_rating = self.current_ratings[game['home_team_id']]
        away_rating = self.current_ratings[game['away_team_id']]
        
        # Calculate new ratings
        result = process_game_elo_update(
            home_rating=home_rating,
            away_rating=away_rating,
            home_score=game['home_score'],
            away_score=game['away_score'],
            k_factor=self.k_factor,
            home_advantage=self.home_advantage,
            use_mov=self.use_mov
        )
        
        # Update current ratings
        self.current_ratings[game['home_team_id']] = result['home_new_rating']
        self.current_ratings[game['away_team_id']] = result['away_new_rating']

        # Update enhanced features trackers
        if self.use_enhanced_features:
            # Update form tracker with point differentials
            home_diff = game['home_score'] - game['away_score']
            away_diff = game['away_score'] - game['home_score']
            self.form_tracker.add_game_result(game['home_team_id'], home_diff)
            self.form_tracker.add_game_result(game['away_team_id'], away_diff)

            # Update rest tracker with game dates
            self.rest_tracker.update_last_game(game['home_team_id'], game['date'])
            self.rest_tracker.update_last_game(game['away_team_id'], game['date'])

        # Record history
        self._record_history(game, result)

        return result
    
    def _record_history(self, game: Dict, result: Dict):
        """Record rating changes in history."""
        # Home team record
        self.rating_history.append({
            'game_id': game['game_id'],
            'date': game['date'],
            'team_id': game['home_team_id'],
            'team_name': game['home_team_name'],
            'is_home': True,
            'opponent_id': game['away_team_id'],
            'opponent_name': game['away_team_name'],
            'team_score': game['home_score'],
            'opponent_score': game['away_score'],
            'won': game['home_score'] > game['away_score'],
            'rating_before': result['home_new_rating'] - result['home_change'],
            'rating_after': result['home_new_rating'],
            'rating_change': result['home_change'],
            'expected_score': result['home_expected']
        })
        
        # Away team record
        self.rating_history.append({
            'game_id': game['game_id'],
            'date': game['date'],
            'team_id': game['away_team_id'],
            'team_name': game['away_team_name'],
            'is_home': False,
            'opponent_id': game['home_team_id'],
            'opponent_name': game['home_team_name'],
            'team_score': game['away_score'],
            'opponent_score': game['home_score'],
            'won': game['away_score'] > game['home_score'],
            'rating_before': result['away_new_rating'] - result['away_change'],
            'rating_after': result['away_new_rating'],
            'rating_change': result['away_change'],
            'expected_score': result['away_expected']
        })
    
    def compute_season_elo(self, games_df: pd.DataFrame, reset: bool = True) -> pd.DataFrame:
        """
        Compute ELO ratings for all games in a season.

        Args:
            games_df: DataFrame with game data (must be sorted by date)
            reset: Whether to reset ratings before computation

        Returns:
            DataFrame with rating history
        """
        if reset:
            self.reset_ratings()

        # Filter out scheduled/incomplete games (0-0 scores)
        # Keep scheduled games in raw data but exclude from ELO calculations
        original_count = len(games_df)
        games_df = games_df[
            (games_df['home_score'].astype(int) > 0) |
            (games_df['away_score'].astype(int) > 0)
        ].copy()

        filtered_count = original_count - len(games_df)
        if filtered_count > 0:
            logger.info(f"Filtered out {filtered_count} scheduled/incomplete games (0-0 scores)")

        logger.info(f"Computing ELO for {len(games_df)} completed games")

        # Ensure games are sorted by date
        games_df = games_df.sort_values('date').reset_index(drop=True)

        # Process each game
        for _, game in games_df.iterrows():
            self.process_game(game.to_dict())

        # Convert history to DataFrame
        history_df = pd.DataFrame(self.rating_history)

        logger.info(f"[OK] Computed {len(history_df)} rating updates")

        return history_df
    
    def get_current_ratings(self) -> pd.DataFrame:
        """
        Get current ratings as a DataFrame.
        
        Returns:
            DataFrame with columns: team_id, team_name, rating
        """
        ratings_list = [
            {'team_id': team_id, 'rating': rating}
            for team_id, rating in self.current_ratings.items()
        ]
        return pd.DataFrame(ratings_list).sort_values('rating', ascending=False)
    
    def predict_game(self, home_team_id: str, away_team_id: str, game_date: int = None) -> Dict:
        """
        Predict outcome of a game between two teams.

        Args:
            home_team_id: Home team ID
            away_team_id: Away team ID
            game_date: Game date (YYYYMMDD format) for rest penalty calculation (optional)

        Returns:
            Dictionary with prediction details including enhanced features
        """
        if home_team_id not in self.current_ratings or away_team_id not in self.current_ratings:
            raise ValueError("One or both teams not found in current ratings")

        home_rating = self.current_ratings[home_team_id]
        away_rating = self.current_ratings[away_team_id]

        # Apply enhanced features if enabled
        home_form_adj = 0.0
        away_form_adj = 0.0
        home_rest_penalty = 0.0
        away_rest_penalty = 0.0

        if self.use_enhanced_features:
            # Form factor adjustments
            home_form_adj = self.form_tracker.get_form_adjustment(home_team_id)
            away_form_adj = self.form_tracker.get_form_adjustment(away_team_id)

            # Rest penalties (only if game_date provided)
            if game_date is not None:
                home_rest_penalty = self.rest_tracker.get_rest_penalty(home_team_id, game_date)
                away_rest_penalty = self.rest_tracker.get_rest_penalty(away_team_id, game_date)

        # Calculate adjusted ratings (before top player concentration)
        home_adjusted = home_rating + home_form_adj + home_rest_penalty
        away_adjusted = away_rating + away_form_adj + away_rest_penalty

        # Apply top player concentration if enabled
        home_concentration_bonus = 0.0
        away_concentration_bonus = 0.0
        home_concentration_risk = 0.0
        away_concentration_risk = 0.0
        concentration_confidence_penalty = 0.0

        if self.use_top_player_concentration and not self.player_ratings.empty and not self.player_team_mapping.empty:
            from src.utils.top_player_concentration import (
                calculate_top_player_metrics,
                apply_concentration_adjustments,
                get_confidence_adjustment_for_concentration
            )

            # Calculate concentration metrics for both teams
            home_metrics = calculate_top_player_metrics(
                home_team_id, self.player_ratings, self.player_team_mapping, home_adjusted
            )
            away_metrics = calculate_top_player_metrics(
                away_team_id, self.player_ratings, self.player_team_mapping, away_adjusted
            )

            # Apply concentration adjustments to ELO
            home_adjusted, away_adjusted, adj_details = apply_concentration_adjustments(
                home_metrics, away_metrics, home_adjusted, away_adjusted
            )

            home_concentration_bonus = adj_details['home_top_player_bonus'] + adj_details['home_depth_adjustment']
            away_concentration_bonus = adj_details['away_top_player_bonus'] + adj_details['away_depth_adjustment']
            home_concentration_risk = adj_details['home_concentration_risk']
            away_concentration_risk = adj_details['away_concentration_risk']

        # Calculate win probability with all adjustments
        from src.utils.elo_math import calculate_win_probability
        from src.utils.confidence_adjuster import get_confidence_with_cap

        home_win_prob = calculate_win_probability(home_adjusted, away_adjusted, self.home_advantage)

        # Apply confidence caps to prevent overconfidence
        confidence_info = get_confidence_with_cap(home_win_prob, home_adjusted, away_adjusted)

        # Further reduce confidence for high concentration risk teams
        final_confidence = confidence_info['confidence']
        if self.use_top_player_concentration and not self.player_ratings.empty:
            from src.utils.top_player_concentration import get_confidence_adjustment_for_concentration

            final_confidence = get_confidence_adjustment_for_concentration(
                confidence_info['predicted_winner'],
                {'concentration_risk': home_concentration_risk},
                {'concentration_risk': away_concentration_risk},
                final_confidence
            )
            concentration_confidence_penalty = confidence_info['confidence'] - final_confidence

        result = {
            'home_team_id': home_team_id,
            'away_team_id': away_team_id,
            'home_rating': home_rating,
            'away_rating': away_rating,
            'home_win_probability': confidence_info['home_win_prob_capped'] if confidence_info['predicted_winner'] == 'home' else 1 - final_confidence,
            'away_win_probability': confidence_info['away_win_prob_capped'] if confidence_info['predicted_winner'] == 'away' else 1 - final_confidence,
            'confidence': final_confidence,
            'predicted_winner': confidence_info['predicted_winner'],
            'confidence_capped': confidence_info['confidence_reduced'],
            'original_home_win_probability': home_win_prob,
            'original_away_win_probability': 1 - home_win_prob
        }

        # Include enhanced features info if enabled
        if self.use_enhanced_features:
            result['home_form_adjustment'] = home_form_adj
            result['away_form_adjustment'] = away_form_adj
            result['home_rest_penalty'] = home_rest_penalty
            result['away_rest_penalty'] = away_rest_penalty
            result['home_adjusted_rating'] = home_adjusted
            result['away_adjusted_rating'] = away_adjusted

        # Include top player concentration info if enabled
        if self.use_top_player_concentration:
            result['home_concentration_bonus'] = home_concentration_bonus
            result['away_concentration_bonus'] = away_concentration_bonus
            result['home_concentration_risk'] = home_concentration_risk
            result['away_concentration_risk'] = away_concentration_risk
            result['concentration_confidence_penalty'] = concentration_confidence_penalty

        return result


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Compute team ELO ratings')
    parser.add_argument('--input', type=str, help='Input games CSV path')
    parser.add_argument('--output', type=str, help='Output ELO history CSV path')
    parser.add_argument('--k-factor', type=float, default=20, help='K-factor (default: 20)')
    parser.add_argument('--home-advantage', type=float, default=100, help='Home advantage (default: 100)')
    parser.add_argument('--use-mov', action='store_true', default=True, help='Use margin-of-victory multiplier (default: True)')
    parser.add_argument('--no-mov', action='store_false', dest='use_mov', help='Disable margin-of-victory multiplier')

    args = parser.parse_args()

    # Load games
    input_path = args.input or get_data_path('raw', 'nba_games_all.csv')
    output_path = args.output or get_data_path('exports', 'team_elo_history.csv')

    logger.info(f"Loading games from: {input_path}")
    games_df = load_csv_to_dataframe(input_path)

    # Initialize engine
    engine = TeamELOEngine(
        k_factor=args.k_factor,
        home_advantage=args.home_advantage,
        use_mov=args.use_mov
    )
    
    # Compute ELO
    history_df = engine.compute_season_elo(games_df)
    
    # Save results
    save_dataframe_to_csv(history_df, output_path)
    
    # Print summary
    print(f"\n[OK] ELO computation complete!")
    print(f"  Total updates: {len(history_df)}")
    print(f"  Teams tracked: {history_df['team_id'].nunique()}")
    print(f"\nTop 5 teams (final ratings):")
    
    current_ratings = engine.get_current_ratings()
    # Merge with team names from history
    team_names = history_df.groupby('team_id')['team_name'].first()
    current_ratings = current_ratings.merge(
        team_names.reset_index(),
        on='team_id',
        how='left'
    )
    print(current_ratings.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
