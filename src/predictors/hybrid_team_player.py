"""
Hybrid Team + Player ELO Predictor
Blends team chemistry (75%) with roster talent (25%) using FiveThirtyEight methodology.

Enhanced with Close Game logic for improved accuracy on close matchups.
"""

import pandas as pd
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from utils.elo_math import calculate_win_probability
from features.close_game_enhancer import CloseGameEnhancer
from features.rest_fatigue_analyzer import get_rest_fatigue_analyzer
from features.momentum_tracker import get_momentum_tracker

logger = logging.getLogger(__name__)

# Initialize Close Game Enhancer (singleton)
_close_game_enhancer = None

def get_close_game_enhancer() -> CloseGameEnhancer:
    """Get or create the Close Game Enhancer singleton."""
    global _close_game_enhancer
    if _close_game_enhancer is None:
        _close_game_enhancer = CloseGameEnhancer()
        logger.info("Close Game Enhancer initialized")
    return _close_game_enhancer


def calculate_roster_elo(
    team_id: str,
    player_ratings: pd.DataFrame,
    player_team_mapping: pd.DataFrame,
    injured_players: List[str] = None,
    default_rating: float = 1500.0
) -> float:
    """
    Calculate team's roster ELO from player ratings.

    Uses FiveThirtyEight methodology:
    - Take top 10 players by rating
    - Weight by expected minutes (estimated from rating rank)
    - Remove injured players from calculation

    Args:
        team_id: Team identifier
        player_ratings: DataFrame with columns ['player_id', 'player_name', 'rating']
        player_team_mapping: DataFrame with columns ['player_id', 'team_id', 'position']
        injured_players: List of player names who are out
        default_rating: Default rating if no data available

    Returns:
        Weighted average ELO of healthy roster
    """
    if injured_players is None:
        injured_players = []

    # Get team's roster (drop player_name to avoid merge conflicts)
    roster = player_team_mapping[player_team_mapping['team_id'] == team_id][['player_id', 'team_id', 'position']].copy()

    if len(roster) == 0:
        logger.warning(f"No roster found for team {team_id}, using default rating")
        return default_rating

    # Merge with ratings
    roster_with_ratings = roster.merge(
        player_ratings[['player_id', 'player_name', 'rating']],
        on='player_id',
        how='left'
    )

    # Remove injured players
    if injured_players:
        healthy_roster = roster_with_ratings[
            ~roster_with_ratings['player_name'].isin(injured_players)
        ].copy()
    else:
        healthy_roster = roster_with_ratings.copy()

    # Fill missing ratings with default
    healthy_roster['rating'] = healthy_roster['rating'].fillna(default_rating)

    if len(healthy_roster) == 0:
        logger.warning(f"No healthy players for team {team_id}, using default rating")
        return default_rating

    # Take top 10 players by rating (rotation players)
    top_players = healthy_roster.nlargest(10, 'rating')

    if len(top_players) == 0:
        return default_rating

    # Weight by expected minutes
    # Top player = 100% weight, decreasing by 5% per rank
    # This approximates: starters ~30-35 min, bench ~15-20 min
    weights = [1.0 - (i * 0.05) for i in range(len(top_players))]

    # Calculate weighted average
    weighted_sum = sum(
        rating * weight
        for rating, weight in zip(top_players['rating'], weights)
    )
    total_weight = sum(weights)

    roster_elo = weighted_sum / total_weight

    logger.debug(
        f"Team {team_id} roster ELO: {roster_elo:.1f} "
        f"(top player: {top_players.iloc[0]['rating']:.1f}, "
        f"injured: {len(injured_players)})"
    )

    return roster_elo


def get_hybrid_rating(
    team_id: str,
    team_elo: float,
    player_ratings: pd.DataFrame,
    player_team_mapping: pd.DataFrame,
    injured_players: List[str] = None,
    blend_weight: float = 0.75
) -> Tuple[float, float]:
    """
    Calculate hybrid rating: blend of team ELO and roster ELO.

    Calibrated 75/25 split (adjusted from FiveThirtyEight's 70/30):
    - 75% team ELO (captures chemistry, coaching, system, home court)
    - 25% roster ELO (captures individual talent)

    Args:
        team_id: Team identifier
        team_elo: Team's current ELO rating
        player_ratings: Player ratings DataFrame
        player_team_mapping: Player-team mapping DataFrame
        injured_players: List of injured player names
        blend_weight: Weight for team ELO (0.75 = 75% team, 25% roster)

    Returns:
        Tuple of (hybrid_rating, roster_elo)
    """
    roster_elo = calculate_roster_elo(
        team_id,
        player_ratings,
        player_team_mapping,
        injured_players
    )

    # Blend team and roster ELO
    hybrid = (team_elo * blend_weight) + (roster_elo * (1 - blend_weight))

    logger.debug(
        f"Team {team_id} hybrid: {hybrid:.1f} "
        f"(team: {team_elo:.1f}, roster: {roster_elo:.1f}, "
        f"blend: {blend_weight:.1%})"
    )

    return hybrid, roster_elo


def predict_game_hybrid(
    home_team_id: str,
    away_team_id: str,
    team_ratings: pd.DataFrame,
    player_ratings: pd.DataFrame,
    player_team_mapping: pd.DataFrame,
    home_injuries: List[str] = None,
    away_injuries: List[str] = None,
    blend_weight: float = 0.75,
    home_advantage: float = 60.0,  # Calibrated for 54.3% home win rate (P2 optimization)
    games_history: Optional[pd.DataFrame] = None,
    team_locations: Optional[Dict] = None,
    game_date: Optional[datetime] = None
) -> Dict:
    """
    Predict game outcome using hybrid team+player ELO.

    Enhanced with Close Game logic for improved accuracy on close matchups.

    Args:
        home_team_id: Home team identifier
        away_team_id: Away team identifier
        team_ratings: Team ratings DataFrame with columns ['team_id', 'rating']
        player_ratings: Player ratings DataFrame
        player_team_mapping: Player-team mapping DataFrame
        home_injuries: List of home team injured player names
        away_injuries: List of away team injured player names
        blend_weight: Weight for team ELO in blend (default 0.75)
        home_advantage: Home court advantage in ELO points (default 50)
        games_history: Optional historical games data for H2H analysis
        team_locations: Optional team location data for travel fatigue
        game_date: Optional game date for travel fatigue calculation

    Returns:
        Dictionary with prediction details:
        - home_win_probability: Probability of home team winning
        - away_win_probability: Probability of away team winning
        - home_team_elo: Home team's base ELO
        - home_roster_elo: Home roster ELO
        - home_hybrid_elo: Home hybrid rating
        - away_team_elo: Away team's base ELO
        - away_roster_elo: Away roster ELO
        - away_hybrid_elo: Away hybrid rating
        - elo_difference: Home hybrid - away hybrid (with home advantage)
        - close_game: Boolean indicating if close game enhancement was applied
        - confidence_multiplier: Confidence adjustment (1.0 = full confidence)
    """
    if home_injuries is None:
        home_injuries = []
    if away_injuries is None:
        away_injuries = []

    # Get base team ELO
    home_team_rating = team_ratings[team_ratings['team_id'] == home_team_id]
    away_team_rating = team_ratings[team_ratings['team_id'] == away_team_id]

    if len(home_team_rating) == 0:
        raise ValueError(f"Home team {home_team_id} not found in ratings")
    if len(away_team_rating) == 0:
        raise ValueError(f"Away team {away_team_id} not found in ratings")

    home_team_elo = home_team_rating.iloc[0]['rating']
    away_team_elo = away_team_rating.iloc[0]['rating']

    # Calculate hybrid ratings
    home_hybrid, home_roster = get_hybrid_rating(
        home_team_id,
        home_team_elo,
        player_ratings,
        player_team_mapping,
        home_injuries,
        blend_weight
    )

    away_hybrid, away_roster = get_hybrid_rating(
        away_team_id,
        away_team_elo,
        player_ratings,
        player_team_mapping,
        away_injuries,
        blend_weight
    )

    # Calculate base win probability with hybrid ratings
    home_win_prob = calculate_win_probability(
        home_hybrid,
        away_hybrid,
        home_advantage
    )

    elo_diff = home_hybrid - away_hybrid + home_advantage

    logger.info(
        f"Base hybrid prediction: {home_team_id} vs {away_team_id}: "
        f"{home_win_prob:.1%} (ELO diff: {elo_diff:+.1f})"
    )

    # Apply Close Game Enhancement for improved accuracy on close matchups
    enhancer = get_close_game_enhancer()
    enhancement = enhancer.enhance_prediction(
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        home_hybrid_elo=home_hybrid,
        away_hybrid_elo=away_hybrid,
        home_injuries=home_injuries,
        away_injuries=away_injuries,
        home_win_probability=home_win_prob,
        games_history=games_history,
        team_locations=team_locations,
        game_date=game_date
    )

    # Use enhanced values if close game
    final_home_elo = enhancement['adjusted_home_elo']
    final_away_elo = enhancement['adjusted_away_elo']

    if enhancement['close_game']:
        logger.info(
            f"Enhanced prediction: {home_team_id} vs {away_team_id}: "
            f"{enhancement['adjusted_home_win_probability']:.1%} (was {home_win_prob:.1%}), "
            f"confidence: {enhancement['confidence_multiplier']:.0%}"
        )

    # Apply Rest/Fatigue Analysis (Priority 3)
    rest_analyzer = get_rest_fatigue_analyzer()
    rest_factors = rest_analyzer.analyze(
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        game_date=game_date,
        games_history=games_history
    )

    # Apply rest/fatigue adjustments to ELO
    final_home_elo += rest_factors['home_total_adjustment']
    final_away_elo += rest_factors['away_total_adjustment']

    # Recalculate probability with rest/fatigue
    final_home_prob = calculate_win_probability(
        final_home_elo, final_away_elo, 0  # Home advantage already applied
    )

    if rest_factors['rest_fatigue_active']:
        logger.info(
            f"Rest/Fatigue adjustment: Home {rest_factors['home_total_adjustment']:+.1f} ELO, "
            f"Away {rest_factors['away_total_adjustment']:+.1f} ELO"
        )

    # Apply Momentum/Streak Adjustments (Priority 3)
    home_momentum = 0.0
    away_momentum = 0.0
    if games_history is not None and game_date is not None:
        momentum_tracker = get_momentum_tracker()
        home_momentum = momentum_tracker.get_streak_adjustment(
            home_team_id, games_history, game_date
        )
        away_momentum = momentum_tracker.get_streak_adjustment(
            away_team_id, games_history, game_date
        )

        # Apply momentum to final ELO
        final_home_elo += home_momentum
        final_away_elo += away_momentum

        if home_momentum != 0.0 or away_momentum != 0.0:
            logger.info(
                f"Momentum adjustment: Home {home_momentum:+.1f} ELO, "
                f"Away {away_momentum:+.1f} ELO"
            )

    # Recalculate final probability with all adjustments (close game + rest/fatigue + momentum)
    final_home_prob = calculate_win_probability(
        final_home_elo, final_away_elo, 0  # Home advantage already applied
    )

    # Calculate confidence: Apply confidence multiplier to win probability
    # Confidence represents how sure we are of the prediction
    # Higher probability = more confident, but reduced by confidence_multiplier for close games
    base_confidence = max(final_home_prob, 1 - final_home_prob)  # Always 0.5 to 1.0
    adjusted_confidence = base_confidence * enhancement['confidence_multiplier']

    return {
        'home_win_probability': final_home_prob,
        'away_win_probability': 1 - final_home_prob,
        'confidence': adjusted_confidence,  # Actual confidence after close game calibration
        'home_team_elo': home_team_elo,
        'home_roster_elo': home_roster,
        'home_hybrid_elo': home_hybrid,
        'away_team_elo': away_team_elo,
        'away_roster_elo': away_roster,
        'away_hybrid_elo': away_hybrid,
        'elo_difference': elo_diff,
        'blend_weight': blend_weight,
        'home_injuries_count': len(home_injuries),
        'away_injuries_count': len(away_injuries),
        'close_game': enhancement['close_game'],
        'close_game_enhancement_active': enhancement['close_game'],
        'confidence_multiplier': enhancement['confidence_multiplier'],
        'h2h_adjustment': enhancement.get('h2h_adjustment', 0.0),
        'travel_adjustment_home': enhancement.get('travel_adjustment_home', 0.0),
        'travel_adjustment_away': enhancement.get('travel_adjustment_away', 0.0),
        'final_home_elo': final_home_elo,
        'final_away_elo': final_away_elo,
        # Rest/Fatigue fields
        'home_back_to_back': rest_factors['home_back_to_back'],
        'away_back_to_back': rest_factors['away_back_to_back'],
        'home_days_rest': rest_factors['home_days_rest'],
        'away_days_rest': rest_factors['away_days_rest'],
        'home_games_in_4_days': rest_factors['home_games_in_4_days'],
        'away_games_in_4_days': rest_factors['away_games_in_4_days'],
        'home_b2b_penalty': rest_factors['home_b2b_penalty'],
        'away_b2b_penalty': rest_factors['away_b2b_penalty'],
        'home_density_penalty': rest_factors['home_density_penalty'],
        'away_density_penalty': rest_factors['away_density_penalty'],
        'home_rest_advantage': rest_factors['home_rest_advantage'],
        'away_rest_advantage': rest_factors['away_rest_advantage'],
        'rest_fatigue_active': rest_factors['rest_fatigue_active'],
        'rest_fatigue_net_adjustment': rest_factors['net_adjustment'],
        # Momentum/Streak fields (Priority 3)
        'home_momentum_adjustment': home_momentum,
        'away_momentum_adjustment': away_momentum,
        'momentum_active': home_momentum != 0.0 or away_momentum != 0.0
    }


def calculate_injury_impact(
    team_id: str,
    injured_players: List[str],
    player_ratings: pd.DataFrame,
    player_team_mapping: pd.DataFrame
) -> Dict:
    """
    Calculate the impact of injuries on team strength.

    Args:
        team_id: Team identifier
        injured_players: List of injured player names
        player_ratings: Player ratings DataFrame
        player_team_mapping: Player-team mapping DataFrame

    Returns:
        Dictionary with injury impact details:
        - roster_elo_full: Roster ELO with all players
        - roster_elo_injured: Roster ELO without injured players
        - elo_loss: ELO points lost due to injuries
        - injured_player_ratings: List of injured players and their ratings
    """
    # Calculate full roster ELO
    roster_elo_full = calculate_roster_elo(
        team_id,
        player_ratings,
        player_team_mapping,
        injured_players=[]
    )

    # Calculate injured roster ELO
    roster_elo_injured = calculate_roster_elo(
        team_id,
        player_ratings,
        player_team_mapping,
        injured_players=injured_players
    )

    elo_loss = roster_elo_full - roster_elo_injured

    # Get ratings for injured players
    injured_ratings = []
    for player_name in injured_players:
        player_data = player_ratings[player_ratings['player_name'] == player_name]
        if len(player_data) > 0:
            injured_ratings.append({
                'name': player_name,
                'rating': player_data.iloc[0]['rating']
            })

    # Sort by rating descending
    injured_ratings = sorted(injured_ratings, key=lambda x: x['rating'], reverse=True)

    return {
        'roster_elo_full': roster_elo_full,
        'roster_elo_injured': roster_elo_injured,
        'elo_loss': elo_loss,
        'injured_player_ratings': injured_ratings
    }
