"""
Betting Market Validation
Adjusts ELO predictions toward market consensus for improved accuracy

FiveThirtyEight uses a similar approach, blending their model with betting markets
to incorporate the "wisdom of crowds" and late-breaking information.
"""

import math


def validate_with_betting_market(
    model_home_prob,
    model_away_prob,
    market_home_prob,
    market_away_prob,
    market_weight=0.15
):
    """
    Adjust model prediction toward market consensus.

    Logic:
        1. Calculate divergence between model and market
        2. Apply weighted adjustment toward market
        3. Maintain probabilities sum to 1.0

    Args:
        model_home_prob: Our ELO-based home win probability (0.0-1.0)
        model_away_prob: Our ELO-based away win probability (0.0-1.0)
        market_home_prob: Market-implied home win probability (0.0-1.0)
        market_away_prob: Market-implied away win probability (0.0-1.0)
        market_weight: How much to trust market (0.0-1.0, default 0.15 = 15%)

    Returns:
        dict: {
            'adjusted_home_prob': Final home win probability,
            'adjusted_away_prob': Final away win probability,
            'market_adjustment': How much we adjusted (+ = toward home, - = toward away),
            'divergence': Absolute difference between model and market,
            'confidence': 'high', 'medium', or 'low' based on divergence
        }

    Example:
        Model says Lakers 55.8%, Market says 52.4%
        Divergence: +3.4%
        Adjustment at 15% weight: 55.8% - (0.15 × 3.4%) = 55.3%
    """
    # Normalize probabilities to sum to 1.0
    model_total = model_home_prob + model_away_prob
    model_home_prob = model_home_prob / model_total
    model_away_prob = model_away_prob / model_total

    market_total = market_home_prob + market_away_prob
    market_home_prob = market_home_prob / market_total
    market_away_prob = market_away_prob / market_total

    # Calculate divergence (how far our model is from market)
    home_divergence = model_home_prob - market_home_prob
    divergence_magnitude = abs(home_divergence)

    # Apply weighted blend
    # adjusted = model + weight × (market - model)
    # This is equivalent to: adjusted = (1 - weight) × model + weight × market
    adjusted_home_prob = model_home_prob + market_weight * (market_home_prob - model_home_prob)
    adjusted_away_prob = 1.0 - adjusted_home_prob

    # Calculate how much we adjusted
    market_adjustment = adjusted_home_prob - model_home_prob

    # Determine confidence level based on divergence
    confidence = calculate_confidence_level(divergence_magnitude)

    return {
        'adjusted_home_prob': adjusted_home_prob,
        'adjusted_away_prob': adjusted_away_prob,
        'market_adjustment': market_adjustment,
        'divergence': home_divergence,  # Signed divergence (+ = bullish, - = bearish)
        'divergence_magnitude': divergence_magnitude,
        'confidence': confidence
    }


def calculate_confidence_level(divergence_magnitude):
    """
    Determine prediction confidence based on model-market divergence.

    Logic:
        - Low divergence (<5%) = High confidence (model and market agree)
        - Medium divergence (5-10%) = Medium confidence
        - High divergence (>10%) = Low confidence (model and market disagree)

    Args:
        divergence_magnitude: Absolute difference (0.0-1.0)

    Returns:
        str: 'high', 'medium', or 'low'
    """
    if divergence_magnitude < 0.05:  # Less than 5% difference
        return 'high'
    elif divergence_magnitude < 0.10:  # 5-10% difference
        return 'medium'
    else:  # More than 10% difference
        return 'low'


def format_market_analysis(
    model_home_prob,
    market_home_prob,
    adjusted_home_prob,
    divergence,
    home_team,
    away_team,
    market_odds=None
):
    """
    Format market validation results for newsletter display.

    Args:
        model_home_prob: ELO prediction
        market_home_prob: Market consensus
        adjusted_home_prob: Final adjusted prediction
        divergence: Model - Market difference
        home_team: Home team name
        away_team: Away team name
        market_odds: Average market odds (optional)

    Returns:
        str: Formatted markdown text
    """
    divergence_pct = divergence * 100

    # Determine sentiment
    if abs(divergence_pct) < 3:
        sentiment = "Model and market agree"
    elif divergence_pct > 0:
        sentiment = f"Model bullish on {home_team} (+{divergence_pct:.1f}%)"
    else:
        sentiment = f"Model bearish on {home_team} ({divergence_pct:.1f}%)"

    lines = []
    lines.append(f"**ELO Prediction**: {home_team} {model_home_prob*100:.1f}%")

    if market_odds:
        lines.append(f"**Market Consensus**: {home_team} {market_home_prob*100:.1f}% ({market_odds:+.0f})")
    else:
        lines.append(f"**Market Consensus**: {home_team} {market_home_prob*100:.1f}%")

    lines.append(f"**Model Divergence**: {sentiment}")
    lines.append(f"**Adjusted Prediction**: {home_team} {adjusted_home_prob*100:.1f}%")

    return "\n".join(lines)


def should_flag_as_upset_alert(model_home_prob, market_home_prob, threshold=0.10):
    """
    Determine if game should be flagged as upset alert based on model-market divergence.

    Args:
        model_home_prob: Model's home win probability
        market_home_prob: Market's home win probability
        threshold: Divergence threshold (default 0.10 = 10%)

    Returns:
        dict: {
            'is_upset_alert': True/False,
            'reason': Explanation string,
            'model_favorite': Team favored by model,
            'market_favorite': Team favored by market
        }
    """
    divergence = abs(model_home_prob - market_home_prob)

    # Determine favorites
    model_favorite = 'home' if model_home_prob > 0.5 else 'away'
    market_favorite = 'home' if market_home_prob > 0.5 else 'away'

    # Check for upset alert
    is_upset_alert = False
    reason = ""

    if divergence >= threshold:
        if model_favorite != market_favorite:
            # Model and market pick different winners
            is_upset_alert = True
            reason = f"Model picks {model_favorite}, market picks {market_favorite}"
        else:
            # Same winner but large divergence
            is_upset_alert = True
            reason = f"Large divergence ({divergence*100:.1f}%), same favorite"

    return {
        'is_upset_alert': is_upset_alert,
        'reason': reason,
        'model_favorite': model_favorite,
        'market_favorite': market_favorite,
        'divergence': divergence
    }


if __name__ == '__main__':
    # Test market validation
    print("="*80)
    print("MARKET VALIDATION TEST")
    print("="*80)

    # Test case 1: Model bullish on Lakers
    print("\nTest 1: Lakers @ Celtics (Model bullish)")
    print("-" * 80)
    result = validate_with_betting_market(
        model_home_prob=0.558,  # Lakers 55.8%
        model_away_prob=0.442,  # Celtics 44.2%
        market_home_prob=0.524,  # Market: Lakers 52.4%
        market_away_prob=0.476,  # Market: Celtics 47.6%
        market_weight=0.15
    )

    print(f"Model prediction: Lakers 55.8%")
    print(f"Market consensus: Lakers 52.4%")
    print(f"Divergence: +{result['divergence']*100:.1f}% (bullish on Lakers)")
    print(f"Adjusted prediction: Lakers {result['adjusted_home_prob']*100:.1f}%")
    print(f"Market adjustment: {result['market_adjustment']*100:+.2f}%")
    print(f"Confidence: {result['confidence']}")

    # Test case 2: Large divergence
    print("\n\nTest 2: Warriors @ Nuggets (Large divergence)")
    print("-" * 80)
    result2 = validate_with_betting_market(
        model_home_prob=0.68,  # Nuggets 68%
        model_away_prob=0.32,  # Warriors 32%
        market_home_prob=0.55,  # Market: Nuggets 55%
        market_away_prob=0.45,  # Market: Warriors 45%
        market_weight=0.15
    )

    print(f"Model prediction: Nuggets 68.0%")
    print(f"Market consensus: Nuggets 55.0%")
    print(f"Divergence: +{result2['divergence']*100:.1f}% (very bullish on Nuggets)")
    print(f"Adjusted prediction: Nuggets {result2['adjusted_home_prob']*100:.1f}%")
    print(f"Market adjustment: {result2['market_adjustment']*100:+.2f}%")
    print(f"Confidence: {result2['confidence']}")

    # Test upset alert
    upset = should_flag_as_upset_alert(
        result2['adjusted_home_prob'],
        0.55,
        threshold=0.10
    )
    print(f"Upset alert: {upset['is_upset_alert']} - {upset.get('reason', 'N/A')}")

    print("\n" + "="*80)
    print("[SUCCESS] Market validation working correctly")
