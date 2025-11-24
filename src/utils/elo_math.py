"""
ELO rating mathematical utilities.
Core formulas for expected score, rating updates, and win probability.
"""

import math
from typing import Dict, Tuple


def calculate_expected_score(team_rating: float, opponent_rating: float, home_advantage: float = 0) -> float:
    """
    Calculate expected score for a team using ELO formula.
    
    Args:
        team_rating: Current ELO rating of the team
        opponent_rating: Current ELO rating of the opponent
        home_advantage: Rating bonus if team is at home (default 0)
        
    Returns:
        Expected score between 0 and 1
        
    Formula: 1 / (1 + 10^((opponent_rating - (team_rating + home_advantage)) / 400))
    """
    adjusted_rating = team_rating + home_advantage
    rating_diff = opponent_rating - adjusted_rating
    return 1 / (1 + math.pow(10, rating_diff / 400))


def calculate_win_probability(team_rating: float, opponent_rating: float, home_advantage: float = 0) -> float:
    """
    Calculate win probability (same as expected score).
    Alias for calculate_expected_score for clarity in prediction contexts.
    """
    return calculate_expected_score(team_rating, opponent_rating, home_advantage)


def update_elo_rating(current_rating: float, k_factor: float, actual_score: float, expected_score: float) -> float:
    """
    Update ELO rating based on game result.
    
    Args:
        current_rating: Current ELO rating
        k_factor: K-factor (sensitivity parameter)
        actual_score: Actual game result (1 for win, 0 for loss)
        expected_score: Expected score from ELO calculation
        
    Returns:
        New ELO rating
        
    Formula: new_rating = old_rating + K * (actual - expected)
    """
    return current_rating + k_factor * (actual_score - expected_score)


def calculate_elo_change(k_factor: float, actual_score: float, expected_score: float) -> float:
    """
    Calculate the change in ELO rating.
    
    Returns:
        The delta (change) in rating points
    """
    return k_factor * (actual_score - expected_score)


def process_game_elo_update(
    home_rating: float,
    away_rating: float,
    home_score: int,
    away_score: int,
    k_factor: float = 20,
    home_advantage: float = 100
) -> Dict[str, float]:
    """
    Process a complete game and return updated ratings for both teams.
    
    Args:
        home_rating: Current home team ELO
        away_rating: Current away team ELO
        home_score: Home team final score
        away_score: Away team final score
        k_factor: K-factor for rating updates
        home_advantage: Home court advantage bonus
        
    Returns:
        Dictionary with new ratings and metadata:
        {
            'home_new_rating': float,
            'away_new_rating': float,
            'home_expected': float,
            'away_expected': float,
            'home_change': float,
            'away_change': float
        }
    """
    # Determine actual scores (1 for win, 0 for loss)
    if home_score > away_score:
        home_actual = 1.0
        away_actual = 0.0
    else:
        home_actual = 0.0
        away_actual = 1.0
    
    # Calculate expected scores
    home_expected = calculate_expected_score(home_rating, away_rating, home_advantage)
    away_expected = 1 - home_expected  # Expected scores sum to 1
    
    # Calculate rating changes
    home_change = calculate_elo_change(k_factor, home_actual, home_expected)
    away_change = calculate_elo_change(k_factor, away_actual, away_expected)
    
    # Calculate new ratings
    home_new_rating = home_rating + home_change
    away_new_rating = away_rating + away_change
    
    return {
        'home_new_rating': home_new_rating,
        'away_new_rating': away_new_rating,
        'home_expected': home_expected,
        'away_expected': away_expected,
        'home_change': home_change,
        'away_change': away_change
    }


def rating_to_win_percentage(rating_diff: float) -> float:
    """
    Convert ELO rating difference to approximate win percentage.
    
    Args:
        rating_diff: Difference between team rating and league average (1500)
        
    Returns:
        Expected win percentage against average team
    """
    return calculate_expected_score(1500 + rating_diff, 1500, 0)
