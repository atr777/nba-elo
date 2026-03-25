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


def elo_diff_to_expected_margin(elo_diff: float, coefficient: float, intercept: float) -> float:
    """
    Convert ELO point differential to expected margin of victory (home - away).

    Args:
        elo_diff: Home team ELO minus away team ELO (after all adjustments)
        coefficient: Points per ELO point (from linear regression calibration)
        intercept: Baseline home margin when teams are equal (home court PPG advantage)

    Returns:
        Expected point margin from the home team's perspective (positive = home wins)
    """
    return intercept + coefficient * elo_diff


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


def calculate_mov_multiplier(point_diff: int, scale: float = 15.0) -> float:
    """
    Calculate margin-of-victory multiplier using FiveThirtyEight formula.

    This logarithmic scaling prevents overreacting to blowouts while still
    rewarding quality wins and penalizing bad losses.

    Args:
        point_diff: Absolute point differential (positive integer)
        scale: Scaling constant (default 15, typical NBA winning margin)

    Returns:
        Multiplier for K-factor (typically 0.2 to 1.5)

    Examples:
        1-point win:  ln(2)/ln(15) ≈ 0.26  (K reduced to ~5)
        5-point win:  ln(6)/ln(15) ≈ 0.66  (K reduced to ~13)
        15-point win: ln(16)/ln(15) ≈ 1.02 (K stays ~20)
        30-point win: ln(31)/ln(15) ≈ 1.26 (K increased to ~25)

    Reference: FiveThirtyEight NBA ELO methodology
    """
    return math.log(abs(point_diff) + 1) / math.log(scale)


def process_game_elo_update(
    home_rating: float,
    away_rating: float,
    home_score: int,
    away_score: int,
    k_factor: float = 20,
    home_advantage: float = 30,  # Calibrated
    use_mov: bool = True
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
        use_mov: If True, apply margin-of-victory multiplier (FiveThirtyEight style)

    Returns:
        Dictionary with new ratings and metadata:
        {
            'home_new_rating': float,
            'away_new_rating': float,
            'home_expected': float,
            'away_expected': float,
            'home_change': float,
            'away_change': float,
            'mov_multiplier': float  (only if use_mov=True)
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

    # Apply margin-of-victory multiplier to K-factor
    mov_multiplier = 1.0
    if use_mov:
        point_diff = abs(home_score - away_score)
        mov_multiplier = calculate_mov_multiplier(point_diff)
        adjusted_k = k_factor * mov_multiplier
    else:
        adjusted_k = k_factor

    # Calculate rating changes with adjusted K
    home_change = calculate_elo_change(adjusted_k, home_actual, home_expected)
    away_change = calculate_elo_change(adjusted_k, away_actual, away_expected)

    # Calculate new ratings
    home_new_rating = home_rating + home_change
    away_new_rating = away_rating + away_change

    result = {
        'home_new_rating': home_new_rating,
        'away_new_rating': away_new_rating,
        'home_expected': home_expected,
        'away_expected': away_expected,
        'home_change': home_change,
        'away_change': away_change
    }

    if use_mov:
        result['mov_multiplier'] = mov_multiplier

    return result


def rating_to_win_percentage(rating_diff: float) -> float:
    """
    Convert ELO rating difference to approximate win percentage.
    
    Args:
        rating_diff: Difference between team rating and league average (1500)
        
    Returns:
        Expected win percentage against average team
    """
    return calculate_expected_score(1500 + rating_diff, 1500, 0)
