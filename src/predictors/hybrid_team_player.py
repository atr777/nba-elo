"""
Hybrid Team + Player ELO Predictor
Blends team chemistry (75%) with roster talent (25%) using FiveThirtyEight methodology.

Enhanced with Close Game logic for improved accuracy on close matchups.
"""

import pandas as pd
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from src.utils.elo_math import calculate_win_probability, elo_diff_to_expected_margin
from src.utils.file_io import load_yaml, get_config_path
from src.features.close_game_enhancer import CloseGameEnhancer

# ---------------------------------------------------------------------------
# Score model coefficients — loaded once at module import time
# ---------------------------------------------------------------------------
_score_model_cache = None

def _load_score_model() -> dict:
    """Load score model coefficients from config/score_model.yaml (cached)."""
    global _score_model_cache
    if _score_model_cache is None:
        try:
            cfg = load_yaml(get_config_path('score_model.yaml'))
            _score_model_cache = cfg.get('score_model', {})
            logger.info(
                "Score model loaded: intercept=%.4f coef=%.6f league_avg=%.2f",
                _score_model_cache.get('intercept', 2.84),
                _score_model_cache.get('coefficient', 0.034507),
                _score_model_cache.get('league_avg_ppg', 114.15)
            )
        except Exception as e:
            logger.warning("Could not load score_model.yaml (%s); using defaults.", e)
            _score_model_cache = {
                'intercept': 2.84,
                'coefficient': 0.034507,
                'league_avg_ppg': 114.15
            }
    return _score_model_cache


# ---------------------------------------------------------------------------
# Quarter model coefficients — loaded once at module import time (Sprint 3)
# ---------------------------------------------------------------------------
_quarter_model_cache = None

# Fallback defaults derived from league averages when YAML is unavailable
_QUARTER_MODEL_DEFAULTS = {
    'q1': {'intercept': -0.7353, 'coefficient': 0.010391, 'league_avg': 27.972},
    'q2': {'intercept':  0.3779, 'coefficient': 0.006782, 'league_avg': 28.560},
    'q3': {'intercept': -1.6465, 'coefficient': 0.004861, 'league_avg': 28.028},
    'q4': {'intercept':  1.0494, 'coefficient': 0.000163, 'league_avg': 26.620},
}

def _load_quarter_model() -> dict:
    """Load per-quarter model coefficients from config/quarter_model.yaml (cached)."""
    global _quarter_model_cache
    if _quarter_model_cache is None:
        try:
            cfg = load_yaml(get_config_path('quarter_model.yaml'))
            qm = cfg.get('quarter_model', {})
            _quarter_model_cache = {
                'q1': qm.get('q1', _QUARTER_MODEL_DEFAULTS['q1']),
                'q2': qm.get('q2', _QUARTER_MODEL_DEFAULTS['q2']),
                'q3': qm.get('q3', _QUARTER_MODEL_DEFAULTS['q3']),
                'q4': qm.get('q4', _QUARTER_MODEL_DEFAULTS['q4']),
            }
            logger.info(
                "Quarter model loaded: Q1 avg=%.2f  Q2 avg=%.2f  Q3 avg=%.2f  Q4 avg=%.2f",
                _quarter_model_cache['q1'].get('league_avg', 27.97),
                _quarter_model_cache['q2'].get('league_avg', 28.56),
                _quarter_model_cache['q3'].get('league_avg', 28.03),
                _quarter_model_cache['q4'].get('league_avg', 26.62),
            )
        except Exception as e:
            logger.warning("Could not load quarter_model.yaml (%s); using defaults.", e)
            _quarter_model_cache = dict(_QUARTER_MODEL_DEFAULTS)
    return _quarter_model_cache
from src.features.rest_fatigue_analyzer import get_rest_fatigue_analyzer
from src.features.momentum_tracker import get_momentum_tracker
from src.features.weighted_elo_tracker import get_weighted_elo_tracker
from src.features.confidence_scorer import get_confidence_scorer
from src.features.contextual_indicators import get_contextual_indicators

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


def calculate_injury_adjustment_enhanced(
    team_id: str,
    player_ratings: pd.DataFrame,
    player_team_mapping: pd.DataFrame,
    injured_players: List[str] = None,
    default_rating: float = 1500.0
) -> Dict:
    """
    Calculate enhanced injury adjustment based on player quality and role.

    Phase 2.2 Enhancement: Dynamically adjust for star vs bench player injuries.

    Research: Basketball-Reference.com BPM (Box Plus/Minus) methodology
    - Star players (top 3): Worth 15-25 ELO points each
    - Starters (rank 4-7): Worth 8-12 ELO points each
    - Rotation (rank 8-10): Worth 3-6 ELO points each
    - Bench (rank 11+): Worth 1-3 ELO points each

    Formula:
        injury_adjustment = Σ(player_impact * position_multiplier)

        Where:
        - player_impact = (player_rating - team_roster_avg) / 10
        - position_multiplier:
            - Top 3 players (stars): 1.5x
            - Players 4-7 (starters): 1.0x
            - Players 8-10 (rotation): 0.5x
            - Players 11+ (bench): 0.25x

    Args:
        team_id: Team identifier
        player_ratings: Player ratings DataFrame
        player_team_mapping: Player-team mapping DataFrame
        injured_players: List of injured player names
        default_rating: Default rating if no data available

    Returns:
        Dictionary with:
            - injury_adjustment: ELO points lost (negative value)
            - star_players_out: Count of top-3 players injured
            - starter_players_out: Count of starters (4-7) injured
            - rotation_players_out: Count of rotation (8-10) injured
            - bench_players_out: Count of bench (11+) injured
            - injured_player_details: List of dicts with player info

    Example:
        Team roster avg: 1600
        Injured: Stephen Curry (2050 rating, rank #1)

        Player impact: (2050 - 1600) / 10 = 45 points
        Position multiplier: 1.5 (star player)
        Injury adjustment: -45 * 1.5 = -67.5 ELO points
    """
    if injured_players is None or len(injured_players) == 0:
        return {
            'injury_adjustment': 0.0,
            'star_players_out': 0,
            'starter_players_out': 0,
            'rotation_players_out': 0,
            'bench_players_out': 0,
            'injured_player_details': []
        }

    # Get team's full roster
    roster = player_team_mapping[player_team_mapping['team_id'] == team_id][['player_id', 'team_id', 'position']].copy()

    if len(roster) == 0:
        return {
            'injury_adjustment': 0.0,
            'star_players_out': 0,
            'starter_players_out': 0,
            'rotation_players_out': 0,
            'bench_players_out': 0,
            'injured_player_details': []
        }

    # Merge with ratings
    roster_with_ratings = roster.merge(
        player_ratings[['player_id', 'player_name', 'rating']],
        on='player_id',
        how='left'
    )

    # Fill missing ratings with default
    roster_with_ratings['rating'] = roster_with_ratings['rating'].fillna(default_rating)

    # Rank players by rating (1 = best player)
    roster_sorted = roster_with_ratings.sort_values('rating', ascending=False).reset_index(drop=True)
    roster_sorted['rank'] = roster_sorted.index + 1

    # Calculate team roster average (top 10 players)
    top_10 = roster_sorted.head(10)
    team_avg = top_10['rating'].mean()

    # Analyze each injured player
    total_adjustment = 0.0
    star_out = 0
    starter_out = 0
    rotation_out = 0
    bench_out = 0
    injured_details = []

    for injured_name in injured_players:
        player_data = roster_sorted[roster_sorted['player_name'] == injured_name]

        if len(player_data) == 0:
            logger.debug(f"Injured player {injured_name} not found in {team_id} roster")
            continue

        player = player_data.iloc[0]
        player_rating = player['rating']
        player_rank = player['rank']

        # Calculate player impact relative to team average
        player_impact = (player_rating - team_avg) / 10.0

        # Determine position multiplier based on rank
        if player_rank <= 3:
            # Star player (top 3)
            position_multiplier = 1.5
            role = "Star"
            star_out += 1
        elif player_rank <= 7:
            # Starter (rank 4-7)
            position_multiplier = 1.0
            role = "Starter"
            starter_out += 1
        elif player_rank <= 10:
            # Rotation (rank 8-10)
            position_multiplier = 0.5
            role = "Rotation"
            rotation_out += 1
        else:
            # Bench (rank 11+)
            position_multiplier = 0.25
            role = "Bench"
            bench_out += 1

        # Calculate this player's injury adjustment (negative because losing player)
        # Negate the impact so that losing a good player = negative adjustment
        player_adjustment = -1 * player_impact * position_multiplier

        # Cap individual player adjustment at -80 ELO (superstar max)
        player_adjustment = max(player_adjustment, -80.0)

        total_adjustment += player_adjustment

        injured_details.append({
            'name': injured_name,
            'rating': player_rating,
            'rank': int(player_rank),
            'role': role,
            'impact': player_impact,
            'multiplier': position_multiplier,
            'adjustment': player_adjustment
        })

        logger.debug(
            f"Injured: {injured_name} (#{player_rank}, {role}, {player_rating:.0f} ELO) "
            f"→ {player_adjustment:+.1f} adjustment"
        )

    # Cap total injury adjustment at -150 ELO (entire starting 5 out scenario)
    total_adjustment = max(total_adjustment, -150.0)

    return {
        'injury_adjustment': total_adjustment,
        'star_players_out': star_out,
        'starter_players_out': starter_out,
        'rotation_players_out': rotation_out,
        'bench_players_out': bench_out,
        'injured_player_details': injured_details
    }


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


def calculate_upset_probability(
    home_elo: float,
    away_elo: float,
    home_win_prob: float,
    games_history: Optional[pd.DataFrame] = None,
    home_team_id: str = None,
    away_team_id: str = None
) -> float:
    """
    Calculate probability that an upset might occur.

    Phase 1.2 Optimization: Simple upset detection based on:
    - ELO difference (moderate range 50-150 most upset-prone)
    - Model confidence (<60% indicates possible upset)
    - Recent form if available (hot underdog vs cold favorite)

    Research shows upsets occur in 28-32% of NBA games.
    This indicator helps identify games where upset is more likely than average.

    Args:
        home_elo: Home team's ELO rating
        away_elo: Away team's ELO rating
        home_win_prob: Model's predicted home win probability
        games_history: Optional historical games for recent form
        home_team_id: Home team identifier
        away_team_id: Away team identifier

    Returns:
        Float between 0.0 and 1.0 representing upset probability
    """
    elo_diff = abs(home_elo - away_elo)

    # Base upset probability from ELO difference
    # Research shows moderate favorites (50-150 ELO) most vulnerable
    if elo_diff < 50:
        base_upset_prob = 0.45  # Nearly even matchup
    elif elo_diff < 100:
        base_upset_prob = 0.35  # Moderate favorite (most upsets occur here)
    elif elo_diff < 150:
        base_upset_prob = 0.28  # Clear favorite
    elif elo_diff < 200:
        base_upset_prob = 0.20  # Strong favorite
    else:
        base_upset_prob = 0.12  # Heavy favorite

    # Adjust based on model confidence
    # If model is uncertain, increase upset probability
    max_confidence = max(home_win_prob, 1 - home_win_prob)
    if max_confidence < 0.60:
        base_upset_prob += 0.10  # Model uncertainty increases upset chance

    # Optional: Adjust for recent form if data available
    if games_history is not None and home_team_id and away_team_id:
        try:
            # Get last 5 games for each team
            recent_cutoff = pd.Timestamp.now() - pd.Timedelta(days=10)
            recent_games = games_history[games_history['date'] >= recent_cutoff]

            # Calculate win rate for each team
            home_recent = recent_games[
                (recent_games['home_team_id'] == home_team_id) |
                (recent_games['away_team_id'] == home_team_id)
            ].tail(5)

            away_recent = recent_games[
                (recent_games['home_team_id'] == away_team_id) |
                (recent_games['away_team_id'] == away_team_id)
            ].tail(5)

            # Determine who's the favorite and who's the underdog
            favorite_is_home = home_win_prob > 0.5

            if favorite_is_home:
                favorite_games = home_recent
                underdog_games = away_recent
            else:
                favorite_games = away_recent
                underdog_games = home_recent

            # Count wins for each team
            if len(favorite_games) >= 3 and len(underdog_games) >= 3:
                favorite_wins = 0
                underdog_wins = 0

                for _, game in favorite_games.iterrows():
                    team_id = home_team_id if favorite_is_home else away_team_id
                    if game['home_team_id'] == team_id:
                        if game.get('home_score', 0) > game.get('away_score', 0):
                            favorite_wins += 1
                    else:
                        if game.get('away_score', 0) > game.get('home_score', 0):
                            favorite_wins += 1

                for _, game in underdog_games.iterrows():
                    team_id = away_team_id if favorite_is_home else home_team_id
                    if game['home_team_id'] == team_id:
                        if game.get('home_score', 0) > game.get('away_score', 0):
                            underdog_wins += 1
                    else:
                        if game.get('away_score', 0) > game.get('home_score', 0):
                            underdog_wins += 1

                # Hot underdog (4+ wins) vs cold favorite (≤2 wins)
                if underdog_wins >= 4 and favorite_wins <= 2:
                    base_upset_prob += 0.15
                # Warm underdog (≥3 wins) vs cold favorite
                elif underdog_wins >= 3 and favorite_wins <= 2:
                    base_upset_prob += 0.10
        except Exception as e:
            # If form calculation fails, just use base probability
            logger.debug(f"Could not calculate recent form: {e}")

    return min(base_upset_prob, 0.55)  # Cap at 55%


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
        final_home_elo, final_away_elo, home_advantage
    )

    if rest_factors['rest_fatigue_active']:
        logger.info(
            f"Rest/Fatigue adjustment: Home {rest_factors['home_total_adjustment']:+.1f} ELO, "
            f"Away {rest_factors['away_total_adjustment']:+.1f} ELO"
        )

    # Apply Weighted ELO (WElo) Form Tracking (Phase 2.1)
    # Replaces disabled momentum with research-validated approach
    welo_tracker = get_weighted_elo_tracker()
    welo_results = welo_tracker.calculate_matchup_welo(
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        games_history=games_history,
        current_date=game_date if game_date else datetime.now(),
        team_ratings=team_ratings
    )

    # Apply WElo adjustments to final ELO — dampened in tossup games.
    # When raw hybrid diff < 30, WElo form becomes noise not signal:
    # a hot team beating a cold team in a coin-flip game still wins ~50% of the time.
    # Scale WElo proportionally: 0% influence at diff=0, 100% at diff>=30.
    welo_tossup_factor = min(1.0, abs(home_hybrid - away_hybrid) / 30.0)
    effective_home_welo = welo_results['home_welo_adjustment'] * welo_tossup_factor
    effective_away_welo = welo_results['away_welo_adjustment'] * welo_tossup_factor
    final_home_elo += effective_home_welo
    final_away_elo += effective_away_welo

    if welo_results['welo_active']:
        if welo_tossup_factor < 1.0:
            logger.info(
                f"WElo dampened (tossup factor {welo_tossup_factor:.2f}): "
                f"Home {welo_results['home_welo_adjustment']:+.1f} -> {effective_home_welo:+.1f} ELO "
                f"({welo_results['home_form_description']}), "
                f"Away {welo_results['away_welo_adjustment']:+.1f} -> {effective_away_welo:+.1f} ELO "
                f"({welo_results['away_form_description']})"
            )
        else:
            logger.info(
                f"WElo adjustment: Home {effective_home_welo:+.1f} ELO "
                f"({welo_results['home_form_description']}, {welo_results['home_recent_record']}), "
                f"Away {effective_away_welo:+.1f} ELO "
                f"({welo_results['away_form_description']}, {welo_results['away_recent_record']})"
            )

    # Apply Enhanced Injury Adjustments (Phase 2.2)
    # Dynamically adjust based on star vs bench player injuries
    home_injury_data = calculate_injury_adjustment_enhanced(
        team_id=home_team_id,
        player_ratings=player_ratings,
        player_team_mapping=player_team_mapping,
        injured_players=home_injuries
    )

    away_injury_data = calculate_injury_adjustment_enhanced(
        team_id=away_team_id,
        player_ratings=player_ratings,
        player_team_mapping=player_team_mapping,
        injured_players=away_injuries
    )

    # Apply injury adjustments to final ELO
    final_home_elo += home_injury_data['injury_adjustment']
    final_away_elo += away_injury_data['injury_adjustment']

    if home_injury_data['injury_adjustment'] != 0 or away_injury_data['injury_adjustment'] != 0:
        logger.info(
            f"Injury adjustment: Home {home_injury_data['injury_adjustment']:+.1f} ELO "
            f"({home_injury_data['star_players_out']} stars out), "
            f"Away {away_injury_data['injury_adjustment']:+.1f} ELO "
            f"({away_injury_data['star_players_out']} stars out)"
        )

    # Apply Momentum/Streak Adjustments (Priority 3)
    # PHASE 1 OPTIMIZATION: Momentum feature DISABLED
    # Research shows momentum feature reduces accuracy by 5.5%
    # (72.2% without momentum vs 66.7% with momentum - see FEATURE_VALIDATION.md)
    # PHASE 2 REPLACEMENT: Now using Weighted ELO (WElo) instead
    home_momentum = 0.0
    away_momentum = 0.0

    # DISABLED - Uncomment to re-enable momentum (not recommended)
    # if games_history is not None and game_date is not None:
    #     momentum_tracker = get_momentum_tracker()
    #     home_momentum = momentum_tracker.get_streak_adjustment(
    #         home_team_id, games_history, game_date
    #     )
    #     away_momentum = momentum_tracker.get_streak_adjustment(
    #         away_team_id, games_history, game_date
    #     )
    #
    #     # Apply momentum to final ELO
    #     final_home_elo += home_momentum
    #     final_away_elo += away_momentum
    #
    #     if home_momentum != 0.0 or away_momentum != 0.0:
    #         logger.info(
    #             f"Momentum adjustment: Home {home_momentum:+.1f} ELO, "
    #             f"Away {away_momentum:+.1f} ELO"
    #         )

    # Recalculate final probability with all adjustments (close game + rest/fatigue + WElo + injury)
    final_home_prob = calculate_win_probability(
        final_home_elo, final_away_elo, home_advantage
    )

    # Toss-up game probability compression
    # Research (2026-03-08): WElo/rest adjustments can inflate predicted probability
    # on games where raw team talent is nearly equal (raw hybrid diff < 30 ELO).
    # This causes overconfidence (e.g., 75% predicted on a 6-point talent diff game).
    # Fix: compress final probability toward 50% based on the RAW hybrid ELO diff
    # (before WElo/rest/injury adjustments inflate it). Linear compression:
    # At raw_diff=0 -> 50%. At raw_diff=30 (boundary) -> no compression.
    tossup_game = False
    tossup_compression_applied = 0.0
    raw_hybrid_diff = home_hybrid - away_hybrid  # Before WElo/rest/injury adjustments
    if abs(raw_hybrid_diff) < 30:
        tossup_game = True
        compression_factor = abs(raw_hybrid_diff) / 30.0
        compressed_prob = 0.5 + (final_home_prob - 0.5) * compression_factor
        tossup_compression_applied = final_home_prob - compressed_prob
        logger.info(
            f"Toss-up compression (|raw hybrid diff| {abs(raw_hybrid_diff):.1f} < 30): "
            f"{final_home_prob:.3f} -> {compressed_prob:.3f} "
            f"(factor: {compression_factor:.2f})"
        )
        final_home_prob = compressed_prob

    # Calculate confidence: Apply confidence multiplier to win probability
    # Confidence represents how sure we are of the prediction
    # Higher probability = more confident, but reduced by confidence_multiplier for close games
    base_confidence = max(final_home_prob, 1 - final_home_prob)  # Always 0.5 to 1.0
    adjusted_confidence = base_confidence * enhancement['confidence_multiplier']

    # Phase 1.3 Optimization: Calibrate 70-80% confidence range
    # Research shows 70-80% predictions were only 60% accurate (should be ~75%)
    # Apply conservative calibration to avoid overconfidence
    if 0.70 <= adjusted_confidence < 0.80:
        # Reduce displayed confidence by 10% in this range
        # Example: 75% displayed confidence → 67.5% calibrated confidence
        calibration_factor = 0.90
        calibrated_confidence = adjusted_confidence * calibration_factor
        logger.debug(
            f"Confidence calibration: {adjusted_confidence:.1%} → {calibrated_confidence:.1%} "
            f"(70-80% range adjustment)"
        )
        adjusted_confidence = calibrated_confidence
    elif adjusted_confidence >= 0.80:
        # High confidence predictions (≥80%) are very accurate (93%+)
        # No calibration needed
        pass
    elif adjusted_confidence < 0.60:
        # Low confidence predictions need slight boost
        # These games are essentially toss-ups
        calibration_factor = 1.05
        calibrated_confidence = min(adjusted_confidence * calibration_factor, 0.65)
        if calibrated_confidence != adjusted_confidence:
            logger.debug(
                f"Confidence calibration: {adjusted_confidence:.1%} → {calibrated_confidence:.1%} "
                f"(<60% range adjustment)"
            )
        adjusted_confidence = calibrated_confidence

    # Calculate upset probability (Phase 1.2 optimization)
    upset_probability = calculate_upset_probability(
        home_elo=final_home_elo,
        away_elo=final_away_elo,
        home_win_prob=final_home_prob,
        games_history=games_history,
        home_team_id=home_team_id,
        away_team_id=away_team_id
    )

    # Flag if upset is likely (>30% chance)
    upset_alert = upset_probability > 0.30

    if upset_alert:
        logger.info(
            f"⚠️ UPSET ALERT: {home_team_id} vs {away_team_id} - "
            f"Upset probability: {upset_probability:.1%}"
        )

    # Calculate Advanced Confidence Score (Priority 1 Enhancement)
    # Analyzes multiple factors to determine prediction reliability
    confidence_scorer = get_confidence_scorer()
    contextual_indicators = get_contextual_indicators()

    # Determine games played for contextual analysis
    games_played_home = 0
    games_played_away = 0
    if games_history is not None:
        try:
            home_games = games_history[
                (games_history['home_team_id'] == home_team_id) | 
                (games_history['away_team_id'] == home_team_id)
            ]
            away_games = games_history[
                (games_history['home_team_id'] == away_team_id) | 
                (games_history['away_team_id'] == away_team_id)
            ]
            games_played_home = len(home_games)
            games_played_away = len(away_games)
        except:
            pass

    # Analyze contextual factors
    contextual_analysis = contextual_indicators.analyze_game_context(
        game_date=game_date if game_date else datetime.now(),
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        games_played_home=games_played_home,
        games_played_away=games_played_away,
        standings=None  # Can be added later
    )

    # Calculate confidence score
    confidence_analysis = confidence_scorer.calculate_confidence(
        elo_differential=abs(final_home_elo - final_away_elo),
        rest_days_home=rest_factors['home_days_rest'],
        rest_days_away=rest_factors['away_days_rest'],
        injury_impact_home=home_injury_data['injury_adjustment'],
        injury_impact_away=away_injury_data['injury_adjustment'],
        form_adjustment_home=welo_results['home_welo_adjustment'],
        form_adjustment_away=welo_results['away_welo_adjustment'],
        is_post_holiday=contextual_analysis['is_post_christmas'],
        is_season_opener=contextual_analysis['is_season_opener'],
        is_playoff_push=contextual_analysis['is_playoff_push']
    )

    # Log confidence analysis
    logger.info(
        f"Confidence Analysis: {confidence_analysis['overall_confidence']:.1f}% "
        f"({confidence_analysis['confidence_level']}) - "
        f"{confidence_analysis['recommendation']}"
    )

    if contextual_analysis['has_special_circumstances']:
        logger.info(f"Special circumstances: {contextual_analysis['context_summary']}")

    # -----------------------------------------------------------------------
    # Score Prediction (Sprint 2)
    # Convert final ELO differential to expected margin and split into scores.
    # Uses config/score_model.yaml coefficients (calibrated via OLS on 29k games).
    # -----------------------------------------------------------------------
    score_model = _load_score_model()
    _score_coef      = score_model.get('coefficient', 0.034507)
    _score_intercept = score_model.get('intercept', 2.84)
    _league_avg      = score_model.get('league_avg_ppg', 114.15)

    predicted_margin = elo_diff_to_expected_margin(
        final_home_elo - final_away_elo,
        coefficient=_score_coef,
        intercept=_score_intercept
    )
    predicted_home_score = max(70, round(_league_avg + predicted_margin / 2))
    predicted_away_score = max(70, round(_league_avg - predicted_margin / 2))

    # -----------------------------------------------------------------------
    # Quarter Predictions (Sprint 3)
    # Four separate linear models: q_margin ~ elo_diff, split symmetrically
    # around the quarter league average.  Floor of 15 prevents nonsense outputs.
    # -----------------------------------------------------------------------
    quarter_model = _load_quarter_model()
    _elo_diff_final = final_home_elo - final_away_elo
    _quarter_preds = {}
    for q_num in [1, 2, 3, 4]:
        q_cfg = quarter_model[f'q{q_num}']
        q_margin = q_cfg['intercept'] + q_cfg['coefficient'] * _elo_diff_final
        q_avg    = q_cfg['league_avg']
        _quarter_preds[f'predicted_home_q{q_num}'] = max(15, round(q_avg + q_margin / 2))
        _quarter_preds[f'predicted_away_q{q_num}'] = max(15, round(q_avg - q_margin / 2))

    return {
        'home_win_probability': final_home_prob,
        'away_win_probability': 1 - final_home_prob,
        'tossup_game': tossup_game,
        'tossup_compression_applied': tossup_compression_applied,
        'confidence': adjusted_confidence,  # Actual confidence after close game calibration
        'home_team_elo': home_team_elo,
        'home_roster_elo': home_roster,
        'home_hybrid_elo': home_hybrid,
        'away_team_elo': away_team_elo,
        'away_roster_elo': away_roster,
        'away_hybrid_elo': away_hybrid,
        'elo_difference': elo_diff,
        # Score prediction (Sprint 2)
        'predicted_home_score': predicted_home_score,
        'predicted_away_score': predicted_away_score,
        'predicted_margin': round(predicted_margin, 1),
        # Quarter predictions (Sprint 3)
        **_quarter_preds,
        'blend_weight': blend_weight,
        'home_injuries_count': len(home_injuries),
        'away_injuries_count': len(away_injuries),
        'close_game': enhancement['close_game'],
        'close_game_enhancement_active': enhancement['close_game'],
        'confidence_multiplier': enhancement['confidence_multiplier'],
        'h2h_adjustment': enhancement.get('h2h_adjustment', 0.0),
        'travel_adjustment_home': enhancement.get('travel_adjustment_home', 0.0),
        'travel_adjustment_away': enhancement.get('travel_adjustment_away', 0.0),
        # Phase 2.3 Enhanced H2H fields
        'h2h_games_analyzed': enhancement.get('h2h_games_analyzed', 0),
        'h2h_home_advantage': enhancement.get('h2h_home_advantage', 0.0),
        'h2h_recent_blowout': enhancement.get('h2h_recent_blowout', False),
        'h2h_active': enhancement.get('h2h_active', False),
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
        # Momentum/Streak fields (Priority 3 - DISABLED in Phase 1.1, replaced by WElo in Phase 2.1)
        'home_momentum_adjustment': home_momentum,
        'away_momentum_adjustment': away_momentum,
        'momentum_active': home_momentum != 0.0 or away_momentum != 0.0,
        # Weighted ELO (WElo) fields (Phase 2.1 optimization)
        'welo_active': welo_results['welo_active'],
        'welo_tossup_factor': welo_tossup_factor,
        'home_welo_adjustment': effective_home_welo,
        'away_welo_adjustment': effective_away_welo,
        'home_welo_score': welo_results['home_welo_score'],
        'away_welo_score': welo_results['away_welo_score'],
        'home_recent_record': welo_results['home_recent_record'],
        'away_recent_record': welo_results['away_recent_record'],
        'home_games_analyzed_welo': welo_results['home_games_analyzed'],
        'away_games_analyzed_welo': welo_results['away_games_analyzed'],
        'form_advantage': welo_results['form_advantage'],
        'home_form_description': welo_results['home_form_description'],
        'away_form_description': welo_results['away_form_description'],
        # Enhanced Injury Adjustment fields (Phase 2.2 optimization)
        'home_injury_adjustment': home_injury_data['injury_adjustment'],
        'away_injury_adjustment': away_injury_data['injury_adjustment'],
        'home_star_players_out': home_injury_data['star_players_out'],
        'away_star_players_out': away_injury_data['star_players_out'],
        'home_starter_players_out': home_injury_data['starter_players_out'],
        'away_starter_players_out': away_injury_data['starter_players_out'],
        'home_rotation_players_out': home_injury_data['rotation_players_out'],
        'away_rotation_players_out': away_injury_data['rotation_players_out'],
        'home_bench_players_out': home_injury_data['bench_players_out'],
        'away_bench_players_out': away_injury_data['bench_players_out'],
        # Upset Probability fields (Phase 1.2 optimization)
        'upset_probability': upset_probability,
        'upset_alert': upset_alert,
        # Advanced Confidence Scoring fields (Priority 1 Enhancement)
        'advanced_confidence': confidence_analysis['overall_confidence'],
        'confidence_level': confidence_analysis['confidence_level'],
        'elo_confidence': confidence_analysis['elo_confidence'],
        'rest_confidence': confidence_analysis['rest_confidence'],
        'injury_confidence': confidence_analysis['injury_confidence'],
        'form_confidence': confidence_analysis['form_confidence'],
        'contextual_confidence': confidence_analysis['contextual_confidence'],
        'confidence_factors_breakdown': confidence_analysis['factors_breakdown'],
        'confidence_recommendation': confidence_analysis['recommendation'],
        'is_uncertain_prediction': confidence_analysis['is_uncertain'],
        'is_high_confidence_prediction': confidence_analysis['is_high_confidence'],
        # Contextual Indicators fields (Priority 1 Enhancement)
        'is_post_christmas': contextual_analysis['is_post_christmas'],
        'is_post_allstar': contextual_analysis['is_post_allstar'],
        'is_season_opener': contextual_analysis['is_season_opener'],
        'is_playoff_push': contextual_analysis['is_playoff_push'],
        'contextual_flags': contextual_analysis['contextual_flags'],
        'context_summary': contextual_analysis['context_summary'],
        'has_special_circumstances': contextual_analysis['has_special_circumstances']
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
