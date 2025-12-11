"""
Top Player Concentration Analysis
Dynamically calculates team dependency on star players without manual tracking.
"""

import pandas as pd
import numpy as np
import unicodedata
import re
from typing import Dict, Tuple


def normalize_name(name: str) -> str:
    """
    Normalize player name for matching.
    Handles special characters, accents, punctuation.

    Examples:
    - "Nikola Jokić" -> "nikola jokic"
    - "Luka Dončić" -> "luka doncic"
    - "Giannis Antetokounmpo" -> "giannis antetokounmpo"
    - "Jose Alvarado" -> "jose alvarado"
    """
    if pd.isna(name):
        return ""

    # Convert to string and lowercase
    name = str(name).lower().strip()

    # Remove accents/diacritics (ć -> c, č -> c, etc.)
    name = unicodedata.normalize('NFKD', name)
    name = ''.join([c for c in name if not unicodedata.combining(c)])

    # Remove punctuation except spaces
    name = re.sub(r'[^\w\s]', '', name)

    # Normalize whitespace
    name = ' '.join(name.split())

    return name


def calculate_top_player_metrics(
    team_id: str,
    player_ratings: pd.DataFrame,
    player_team_mapping: pd.DataFrame,
    team_base_elo: float
) -> Dict:
    """
    Calculate top player concentration metrics for a team.

    This dynamically adapts to roster changes (trades, injuries) without manual updates.

    Args:
        team_id: Team ID to analyze
        player_ratings: DataFrame with columns: player_id, rating
        player_team_mapping: DataFrame with columns: player_id, team_id
        team_base_elo: Team's base ELO rating

    Returns:
        Dictionary with:
        - top_player_bonus: ELO boost from having elite players
        - concentration_risk: Volatility factor (0-1, higher = more dependent on star)
        - top_5_depth: Quality of rotation (positive = good depth)
        - top_player_elo: Rating of best player
        - second_player_elo: Rating of second best player
        - concentration_ratio: Numeric measure of star dependency
    """

    # Get team's players (ensure type matching for team_id)
    team_id_str = str(team_id)
    player_team_mapping_copy = player_team_mapping.copy()
    player_team_mapping_copy['team_id'] = player_team_mapping_copy['team_id'].astype(str)

    team_players_mapping = player_team_mapping_copy[player_team_mapping_copy['team_id'] == team_id_str]

    if len(team_players_mapping) == 0:
        # No players mapped - return neutral values
        return {
            'top_player_bonus': 0.0,
            'concentration_risk': 0.0,
            'top_5_depth': 0.0,
            'top_player_elo': 1500.0,
            'second_player_elo': 1500.0,
            'concentration_ratio': 0.0,
            'team_has_superstar': False
        }

    # Join ratings with mapping by normalized player_name (IDs don't match between datasets)
    # Create normalized name columns for matching
    player_ratings_copy = player_ratings.copy()
    player_ratings_copy['name_normalized'] = player_ratings_copy['player_name'].apply(normalize_name)

    team_players_mapping_copy = team_players_mapping.copy()
    team_players_mapping_copy['name_normalized'] = team_players_mapping_copy['player_name'].apply(normalize_name)

    # Join on normalized names
    team_player_ratings = player_ratings_copy.merge(
        team_players_mapping_copy[['name_normalized']],
        on='name_normalized',
        how='inner'
    )

    if len(team_player_ratings) == 0:
        return {
            'top_player_bonus': 0.0,
            'concentration_risk': 0.0,
            'top_5_depth': 0.0,
            'top_player_elo': 1500.0,
            'second_player_elo': 1500.0,
            'concentration_ratio': 0.0,
            'team_has_superstar': False
        }

    # Sort by rating descending
    team_player_ratings = team_player_ratings.sort_values('rating', ascending=False).reset_index(drop=True)

    # Get top players
    top_player_elo = team_player_ratings.iloc[0]['rating'] if len(team_player_ratings) > 0 else 1500
    second_player_elo = team_player_ratings.iloc[1]['rating'] if len(team_player_ratings) > 1 else 1500
    top_5_players = team_player_ratings.head(5)

    # Calculate metrics
    team_avg_elo = team_player_ratings['rating'].mean()
    top_5_avg_elo = top_5_players['rating'].mean()

    # 1. Top Player Bonus
    # How much better is the top player than team average?
    # Elite players (2000+ ELO) provide significant boost
    if top_player_elo >= 2000:
        # Superstar - provides large bonus
        top_player_bonus = (top_player_elo - team_avg_elo) * 0.4
    elif top_player_elo >= 1900:
        # All-star - moderate bonus
        top_player_bonus = (top_player_elo - team_avg_elo) * 0.3
    else:
        # Good player - small bonus
        top_player_bonus = (top_player_elo - team_avg_elo) * 0.2

    # 2. Concentration Risk
    # Measures gap between top and second player (team dependency on star)
    concentration_gap = top_player_elo - second_player_elo

    # Normalize to 0-1 scale (gap of 200+ = max risk of 1.0)
    concentration_risk = min(concentration_gap / 200, 1.0)

    # 3. Concentration Ratio
    # Alternative metric: (Top ELO - Team Avg) / Team Avg
    if team_avg_elo > 0:
        concentration_ratio = (top_player_elo - team_avg_elo) / team_avg_elo
    else:
        concentration_ratio = 0.0

    # 4. Top 5 Depth Score
    # How good is the rotation compared to league average (1500)?
    top_5_depth = top_5_avg_elo - 1500

    # 5. Superstar flag
    team_has_superstar = top_player_elo >= 2000

    return {
        'top_player_bonus': float(top_player_bonus),
        'concentration_risk': float(concentration_risk),
        'top_5_depth': float(top_5_depth),
        'top_player_elo': float(top_player_elo),
        'second_player_elo': float(second_player_elo),
        'concentration_ratio': float(concentration_ratio),
        'team_has_superstar': bool(team_has_superstar)
    }


def apply_concentration_adjustments(
    home_metrics: Dict,
    away_metrics: Dict,
    home_base_elo: float,
    away_base_elo: float
) -> Tuple[float, float, Dict]:
    """
    Apply top player concentration adjustments to team ELO ratings.

    Args:
        home_metrics: Home team concentration metrics
        away_metrics: Away team concentration metrics
        home_base_elo: Home team base ELO
        away_base_elo: Away team base ELO

    Returns:
        Tuple of (adjusted_home_elo, adjusted_away_elo, adjustment_details)
    """

    # Apply top player bonuses
    home_adjusted = home_base_elo + home_metrics['top_player_bonus']
    away_adjusted = away_base_elo + away_metrics['top_player_bonus']

    # Depth adjustments (small impact, 10% of depth score)
    home_depth_adj = home_metrics['top_5_depth'] * 0.1
    away_depth_adj = away_metrics['top_5_depth'] * 0.1

    home_adjusted += home_depth_adj
    away_adjusted += away_depth_adj

    adjustment_details = {
        'home_top_player_bonus': home_metrics['top_player_bonus'],
        'away_top_player_bonus': away_metrics['top_player_bonus'],
        'home_depth_adjustment': home_depth_adj,
        'away_depth_adjustment': away_depth_adj,
        'home_concentration_risk': home_metrics['concentration_risk'],
        'away_concentration_risk': away_metrics['concentration_risk'],
        'home_has_superstar': home_metrics['team_has_superstar'],
        'away_has_superstar': away_metrics['team_has_superstar']
    }

    return home_adjusted, away_adjusted, adjustment_details


def get_confidence_adjustment_for_concentration(
    predicted_winner: str,
    home_metrics: Dict,
    away_metrics: Dict,
    base_confidence: float
) -> float:
    """
    Reduce confidence for teams with high concentration risk.

    High concentration = high variance = lower confidence in predictions.

    Args:
        predicted_winner: 'home' or 'away'
        home_metrics: Home team concentration metrics
        away_metrics: Away team concentration metrics
        base_confidence: Base confidence before adjustment

    Returns:
        Adjusted confidence (reduced for high concentration teams)
    """

    # Get predicted winner's concentration risk
    if predicted_winner == 'home':
        winner_risk = home_metrics['concentration_risk']
    else:
        winner_risk = away_metrics['concentration_risk']

    # Reduce confidence based on concentration risk
    # High risk (0.8+) = reduce confidence by up to 20%
    # Low risk (0.2-) = minimal reduction
    confidence_penalty = winner_risk * 0.20  # Max 20% reduction

    adjusted_confidence = base_confidence * (1 - confidence_penalty)

    return adjusted_confidence


def analyze_team_construction(
    team_id: str,
    player_ratings: pd.DataFrame,
    player_team_mapping: pd.DataFrame,
    team_base_elo: float
) -> Dict:
    """
    Full analysis of team construction and star dependency.

    Returns detailed breakdown for debugging/analysis.
    """

    metrics = calculate_top_player_metrics(
        team_id, player_ratings, player_team_mapping, team_base_elo
    )

    # Classify team construction
    if metrics['concentration_risk'] > 0.6:
        construction_type = "Star-Dependent"
        description = "Team heavily relies on top player. High variance."
    elif metrics['concentration_risk'] > 0.3:
        construction_type = "Top-Heavy"
        description = "Strong top player but some depth. Moderate variance."
    else:
        construction_type = "Balanced"
        description = "Well-distributed talent. More consistent."

    # Classify depth
    if metrics['top_5_depth'] > 200:
        depth_rating = "Elite"
    elif metrics['top_5_depth'] > 100:
        depth_rating = "Good"
    elif metrics['top_5_depth'] > 0:
        depth_rating = "Average"
    else:
        depth_rating = "Poor"

    analysis = {
        **metrics,
        'construction_type': construction_type,
        'construction_description': description,
        'depth_rating': depth_rating,
        'expected_elo_boost': metrics['top_player_bonus'],
        'volatility_level': 'High' if metrics['concentration_risk'] > 0.5 else 'Medium' if metrics['concentration_risk'] > 0.3 else 'Low'
    }

    return analysis
