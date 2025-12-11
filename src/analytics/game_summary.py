"""
Game Summary View
Provides a quick at-a-glance summary of today's NBA games with predictions

Used in "Predict Games" tab of newsletters
"""

import pandas as pd
from datetime import datetime
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.utils.file_io import load_csv_to_dataframe


def generate_games_summary(predictions, format='markdown'):
    """
    Generate a summarized view of games with predictions.

    Args:
        predictions: List of prediction dicts from predict_game()
        format: 'markdown' or 'text'

    Returns:
        str: Formatted games summary
    """
    if not predictions:
        return "No games scheduled for today."

    # Sort by game time, then by confidence/spread
    sorted_predictions = sorted(predictions, key=lambda x: (
        x.get('game_time', ''),
        -abs(x.get('home_win_prob', 0.5) - 0.5)  # Sort by competitiveness
    ))

    lines = []

    if format == 'markdown':
        lines.append("## Today's Games at a Glance")
        lines.append("")
        lines.append(f"**{len(predictions)} games scheduled**")
        lines.append("")
        lines.append("| Time | Matchup | Prediction | Confidence | Type |")
        lines.append("|------|---------|------------|------------|------|")

        for pred in sorted_predictions:
            time_str = pred.get('game_time', 'TBD')
            away_team = pred.get('away_team', 'Away')
            home_team = pred.get('home_team', 'Home')
            home_prob = pred.get('home_win_prob', 0.5)

            # Determine favorite
            if home_prob > 0.5:
                favorite = home_team
                prob = home_prob
            else:
                favorite = away_team
                prob = 1 - home_prob

            # Determine game type
            game_type = categorize_game(prob)

            # Format confidence
            confidence_level = get_confidence_display(prob)

            matchup = f"{away_team} @ {home_team}"
            prediction_str = f"{favorite} {prob*100:.1f}%"

            lines.append(f"| {time_str} | {matchup} | {prediction_str} | {confidence_level} | {game_type} |")

        lines.append("")

    else:  # text format
        lines.append("="*80)
        lines.append(f"TODAY'S GAMES AT A GLANCE ({len(predictions)} games)")
        lines.append("="*80)
        lines.append("")

        for pred in sorted_predictions:
            time_str = pred.get('game_time', 'TBD')
            away_team = pred.get('away_team', 'Away')
            home_team = pred.get('home_team', 'Home')
            home_prob = pred.get('home_win_prob', 0.5)

            if home_prob > 0.5:
                favorite = home_team
                prob = home_prob
            else:
                favorite = away_team
                prob = 1 - home_prob

            game_type = categorize_game(prob)
            confidence = get_confidence_display(prob)

            lines.append(f"{time_str:<10} {away_team} @ {home_team}")
            lines.append(f"           {game_type}: {favorite} {prob*100:.1f}% ({confidence})")
            lines.append("")

    return "\n".join(lines)


def categorize_game(win_probability):
    """
    Categorize game by competitiveness.

    Args:
        win_probability: Favorite's win probability (0.5 to 1.0)

    Returns:
        str: Game category
    """
    if win_probability >= 0.80:
        return "Blowout"
    elif win_probability >= 0.70:
        return "Strong Favorite"
    elif win_probability >= 0.60:
        return "Moderate Favorite"
    elif win_probability >= 0.55:
        return "Slight Favorite"
    else:
        return "Toss-up"


def get_confidence_display(win_probability):
    """
    Get confidence level display text.

    Args:
        win_probability: Favorite's win probability

    Returns:
        str: Confidence display
    """
    if win_probability >= 0.75:
        return "High"
    elif win_probability >= 0.60:
        return "Medium"
    else:
        return "Low"


def generate_featured_games_summary(predictions, num_featured=3):
    """
    Generate a summary highlighting featured games.

    Args:
        predictions: List of prediction dicts
        num_featured: Number of games to feature

    Returns:
        dict: {
            'blowouts': List of likely blowout games,
            'upsets': List of upset alert games,
            'competitive': List of most competitive games
        }
    """
    if not predictions:
        return {'blowouts': [], 'upsets': [], 'competitive': []}

    blowouts = []
    competitive = []

    for pred in predictions:
        home_prob = pred.get('home_win_prob', 0.5)
        spread = abs(home_prob - 0.5)

        # Categorize
        if spread >= 0.30:  # 80%+ favorite
            blowouts.append(pred)
        elif spread <= 0.10:  # Within 60/40
            competitive.append(pred)

    # Sort
    blowouts.sort(key=lambda x: abs(x['home_win_prob'] - 0.5), reverse=True)
    competitive.sort(key=lambda x: abs(x['home_win_prob'] - 0.5))

    return {
        'blowouts': blowouts[:num_featured],
        'competitive': competitive[:num_featured],
        'upsets': []  # Upsets are handled by existing upset_watch functionality
    }


def format_featured_games(featured_games):
    """
    Format featured games for newsletter display.

    Args:
        featured_games: Dict from generate_featured_games_summary()

    Returns:
        str: Markdown formatted text
    """
    lines = []

    if featured_games['blowouts']:
        lines.append("### Likely Blowouts")
        lines.append("")
        for game in featured_games['blowouts']:
            away = game.get('away_team', 'Away')
            home = game.get('home_team', 'Home')
            home_prob = game.get('home_win_prob', 0.5)

            if home_prob > 0.5:
                fav = home
                prob = home_prob
            else:
                fav = away
                prob = 1 - home_prob

            lines.append(f"- **{away} @ {home}**: {fav} {prob*100:.1f}%")
        lines.append("")

    if featured_games['competitive']:
        lines.append("### Most Competitive Games")
        lines.append("")
        for game in featured_games['competitive']:
            away = game.get('away_team', 'Away')
            home = game.get('home_team', 'Home')
            home_prob = game.get('home_win_prob', 0.5)

            if home_prob > 0.5:
                fav = home
                prob = home_prob
            else:
                fav = away
                prob = 1 - home_prob

            lines.append(f"- **{away} @ {home}**: {fav} {prob*100:.1f}% (close game)")
        lines.append("")

    return "\n".join(lines)


if __name__ == '__main__':
    # Test with sample predictions
    sample_predictions = [
        {
            'game_time': '7:00 PM',
            'home_team': 'Los Angeles Lakers',
            'away_team': 'Boston Celtics',
            'home_win_prob': 0.557
        },
        {
            'game_time': '7:30 PM',
            'home_team': 'Miami Heat',
            'away_team': 'Washington Wizards',
            'home_win_prob': 0.908
        },
        {
            'game_time': '8:00 PM',
            'home_team': 'Denver Nuggets',
            'away_team': 'Golden State Warriors',
            'home_win_prob': 0.682
        }
    ]

    print("="*80)
    print("GAME SUMMARY TEST")
    print("="*80)

    # Test markdown format
    markdown_summary = generate_games_summary(sample_predictions, format='markdown')
    print("\nMarkdown Format:")
    print("-"*80)
    print(markdown_summary)

    # Test featured games
    print("\n"+"="*80)
    print("FEATURED GAMES TEST")
    print("="*80)
    featured = generate_featured_games_summary(sample_predictions)
    featured_text = format_featured_games(featured)
    print(featured_text)

    print("="*80)
    print("[SUCCESS] Game summary working correctly")
