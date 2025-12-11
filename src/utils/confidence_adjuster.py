"""
Confidence Adjustment Utilities
Applies smart confidence caps based on ELO differentials to prevent overconfidence.
"""


def apply_confidence_cap(home_elo: float, away_elo: float, base_confidence: float) -> float:
    """
    Apply confidence cap based on ELO differential to prevent overconfidence.

    Analysis from 100 games showed we were overconfident on close matchups:
    - 11 of 19 upsets were high-confidence predictions (>65%) that failed
    - Average confidence on these misses: 72.7%
    - Many had ELO differentials < 150

    Args:
        home_elo: Home team's ELO rating (after adjustments)
        away_elo: Away team's ELO rating (after adjustments)
        base_confidence: Initial confidence (0.0 to 1.0)

    Returns:
        Capped confidence (0.0 to 1.0)

    Confidence Caps by ELO Differential:
        < 50 ELO:   Max 55% (Toss-up - essentially 50/50)
        50-100 ELO:  Max 65% (Slight edge - still very competitive)
        100-150 ELO: Max 75% (Clear favorite - but not dominant)
        150-200 ELO: Max 82% (Heavy favorite)
        200+ ELO:    Max 90% (Overwhelming favorite)

    Examples from our data:
    - Wolves (+98 ELO) vs Suns: Was 73.5% → Should be 65% max
    - Rockets (+294 ELO) vs Jazz: Was 84.4% → Should be 90% max (still lost due to injury)
    """
    elo_diff = abs(home_elo - away_elo)

    # Determine maximum allowed confidence based on ELO gap
    if elo_diff < 50:
        # Toss-up territory - essentially a coin flip
        max_confidence = 0.55
    elif elo_diff < 100:
        # Slight edge - close game, high variance
        max_confidence = 0.65
    elif elo_diff < 150:
        # Clear favorite - but upsets still common
        max_confidence = 0.75
    elif elo_diff < 200:
        # Heavy favorite
        max_confidence = 0.82
    else:
        # Overwhelming favorite (200+ ELO gap)
        max_confidence = 0.90

    # Return the minimum of base confidence and the cap
    # This ensures we never exceed the cap, but can be less confident if appropriate
    capped_confidence = min(base_confidence, max_confidence)

    return capped_confidence


def get_confidence_with_cap(home_win_prob: float, home_elo: float, away_elo: float) -> dict:
    """
    Get confidence values with caps applied.

    Args:
        home_win_prob: Home team win probability (0.0 to 1.0)
        home_elo: Home team ELO
        away_elo: Away team ELO

    Returns:
        Dictionary with:
        - home_win_prob_capped: Home win probability after cap
        - away_win_prob_capped: Away win probability after cap
        - confidence: Confidence in predicted winner (after cap)
        - predicted_winner: 'home' or 'away'
        - confidence_reduced: Boolean - was confidence reduced by cap?
        - elo_diff: ELO differential used for capping
    """
    # Determine which team is favored
    if home_win_prob > 0.5:
        predicted_winner = 'home'
        base_confidence = home_win_prob
    else:
        predicted_winner = 'away'
        base_confidence = 1 - home_win_prob

    # Apply confidence cap
    capped_confidence = apply_confidence_cap(home_elo, away_elo, base_confidence)

    # Calculate capped probabilities
    if predicted_winner == 'home':
        home_win_prob_capped = capped_confidence
        away_win_prob_capped = 1 - capped_confidence
    else:
        away_win_prob_capped = capped_confidence
        home_win_prob_capped = 1 - capped_confidence

    return {
        'home_win_prob_capped': home_win_prob_capped,
        'away_win_prob_capped': away_win_prob_capped,
        'confidence': capped_confidence,
        'predicted_winner': predicted_winner,
        'confidence_reduced': capped_confidence < base_confidence,
        'elo_diff': abs(home_elo - away_elo),
        'original_confidence': base_confidence
    }
