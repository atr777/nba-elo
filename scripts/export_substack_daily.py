"""
Export Daily NBA Predictions for Substack Newsletter
Generates markdown-formatted predictions ready to paste into Substack.

Usage:
    python scripts/export_substack_daily.py --date 2024-12-15 --featured-game "Lakers vs Warriors"
    python scripts/export_substack_daily.py --all-games  # Generate all games for today
"""

import argparse
import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import random

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.utils.file_io import load_csv_to_dataframe

# Import NBA API data fetcher
try:
    from src.scrapers.nba_api_data_fetcher import get_todays_games as fetch_nba_games
    NBA_API_AVAILABLE = True
except ImportError:
    NBA_API_AVAILABLE = False
    print("Warning: NBA API not available. Using sample data.")

# Import recent performance analytics
from src.analytics.team_recent_performance import get_recent_games_performance

# Import prediction tracking
from src.analytics.prediction_tracking import (
    format_yesterdays_results,
    format_yesterdays_results_with_predictions,
    get_accuracy_stats
)

# Import matchup analysis
from src.analytics.matchup_analysis import (
    format_head_to_head_summary,
    identify_upset_candidates,
    format_upset_watch,
    generate_game_storyline
)

# Import game summary for quick-glance predictions view
from src.analytics.game_summary import generate_games_summary, generate_featured_games_summary, format_featured_games

# Import newsletter visualizations
from src.analytics.newsletter_viz import get_visualization_for_day

def get_todays_games(date_str=None):
    """
    Get games scheduled for today from NBA API.
    Falls back to sample data if API is unavailable.
    """
    if NBA_API_AVAILABLE:
        try:
            games = fetch_nba_games(date_str)
            if games:
                print(f"Fetched {len(games)} games from NBA API")
                return games
            else:
                print("No games found from NBA API, using sample data")
        except Exception as e:
            print(f"Error fetching from NBA API: {e}")
            print("Falling back to sample data")

    # Fallback: sample games using actual team IDs from our database (1-30)
    sample_games = [
        {'home_team': 'Los Angeles Lakers', 'home_id': 14, 'away_team': 'Golden State Warriors', 'away_id': 10, 'time': '7:00 PM ET'},
        {'home_team': 'Boston Celtics', 'home_id': 2, 'away_team': 'Miami Heat', 'away_id': 16, 'time': '7:30 PM ET'},
        {'home_team': 'Milwaukee Bucks', 'home_id': 17, 'away_team': 'Brooklyn Nets', 'away_id': 3, 'time': '8:00 PM ET'},
        {'home_team': 'Denver Nuggets', 'home_id': 8, 'away_team': 'Phoenix Suns', 'away_id': 24, 'time': '9:00 PM ET'},
        {'home_team': 'Dallas Mavericks', 'home_id': 7, 'away_team': 'LA Clippers', 'away_id': 13, 'time': '10:00 PM ET'},
    ]

    return sample_games

def predict_game(home_id, away_id, team_ratings, apply_h2h=True, h2h_weight=0.07, apply_momentum=True, momentum_weight=0.05):
    """
    Make a prediction for a single game with contextual adjustments.

    Args:
        home_id: Home team ID
        away_id: Away team ID
        team_ratings: DataFrame with team ratings
        apply_h2h: Whether to apply head-to-head adjustment (default True)
        h2h_weight: Weight for H2H adjustment (default 0.07 = 7%)
        apply_momentum: Whether to apply momentum factor (default True)
        momentum_weight: Weight for momentum adjustment (default 0.05 = 5%)

    Returns:
        Dict with prediction results
    """
    from src.analytics.matchup_analysis import calculate_h2h_adjustment
    from src.analytics.team_recent_performance import calculate_momentum_factor

    home_team_data = team_ratings[team_ratings['team_id'] == home_id]
    away_team_data = team_ratings[team_ratings['team_id'] == away_id]

    if len(home_team_data) == 0 or len(away_team_data) == 0:
        print(f"Warning: Could not find team data for home_id={home_id} or away_id={away_id}")
        return None

    home_rating = home_team_data['rating'].iloc[0]
    away_rating = away_team_data['rating'].iloc[0]
    home_team_name = home_team_data['team_name'].iloc[0]
    away_team_name = away_team_data['team_name'].iloc[0]

    # Track base ratings for display
    base_home_rating = home_rating
    base_away_rating = away_rating

    # Apply H2H adjustment if enabled
    h2h_adjustment = 0
    if apply_h2h:
        h2h_adjustment = calculate_h2h_adjustment(home_team_name, away_team_name, lookback_games=5)
        # Apply weight to adjustment
        home_rating = home_rating + (h2h_weight * h2h_adjustment)

    # Apply Momentum adjustment if enabled
    home_momentum = 0
    away_momentum = 0
    if apply_momentum:
        home_momentum = calculate_momentum_factor(home_team_name, lookback_games=5)
        away_momentum = calculate_momentum_factor(away_team_name, lookback_games=5)

        # Apply weighted momentum to ratings
        home_rating = home_rating + (momentum_weight * home_momentum)
        away_rating = away_rating + (momentum_weight * away_momentum)

    # Sprint 5A: Aligned with hybrid_team_player default (60 pts)
    home_advantage = 60
    rating_diff = home_rating - away_rating + home_advantage
    home_win_prob = 1 / (1 + 10 ** (-rating_diff / 400))

    return {
        'home_rating': home_rating,
        'away_rating': away_rating,
        'base_home_rating': base_home_rating,
        'base_away_rating': base_away_rating,
        'home_win_prob': home_win_prob,
        'away_win_prob': 1 - home_win_prob,
        'predicted_winner': 'home' if home_win_prob > 0.5 else 'away',
        'h2h_adjustment': h2h_adjustment,
        'h2h_impact': h2h_weight * h2h_adjustment,
        'home_momentum': home_momentum,
        'away_momentum': away_momentum,
        'home_momentum_impact': momentum_weight * home_momentum,
        'away_momentum_impact': momentum_weight * away_momentum
    }

def get_injury_impact_analysis(team_name, player_ratings, player_team_mapping=None):
    """
    Generate injury impact analysis for key players on a specific team.
    Shows the top 3 players by ELO rating for injury monitoring.
    """
    # Load player-team mapping if not provided
    if player_team_mapping is None:
        try:
            player_team_mapping = load_csv_to_dataframe('data/exports/player_team_mapping.csv')
        except:
            # Fallback: use top 3 players overall (placeholder)
            top_players = player_ratings.nlargest(3, 'rating')
            analysis = []
            for _, player in top_players.iterrows():
                impact = (player['rating'] - 1500) * 0.3
                analysis.append({
                    'name': player['player_name'],
                    'elo': player['rating'],
                    'impact': impact,
                    'impact_percent': (impact / 400) * 100
                })
            return analysis

    # Filter players by team
    team_players = player_team_mapping[player_team_mapping['team_name'] == team_name]

    if team_players.empty:
        # No players found for this team - return empty list
        # This can happen for new/relocated teams not in player mapping
        return []

    # Merge with player ratings by player name (fuzzy match)
    # Since player IDs are from different sources, we'll match by name
    team_player_ratings = player_ratings.merge(
        team_players[['player_name']],
        on='player_name',
        how='inner',
        suffixes=('', '_mapping')
    )

    # Get top 3 players by ELO rating
    top_players = team_player_ratings.nlargest(3, 'rating')

    analysis = []
    for _, player in top_players.iterrows():
        impact = (player['rating'] - 1500) * 0.3  # 30% player contribution
        analysis.append({
            'name': player['player_name'],
            'elo': player['rating'],
            'impact': impact,
            'impact_percent': (impact / 400) * 100,  # Convert to probability %
            'position': player.get('position', 'N/A')
        })

    # Return analysis (may be empty if no matching players found)
    return analysis

def interpret_probability(prob):
    """Return human-readable interpretation of win probability."""
    if prob < 0.52:
        return "Pick'em"
    elif prob < 0.60:
        return "Slight favorite"
    elif prob < 0.70:
        return "Moderate favorite"
    elif prob < 0.80:
        return "Strong favorite"
    else:
        return "Heavy favorite"

def format_pace_style_analysis(home_team, away_team, home_recent, away_recent):
    """Generate pace and style matchup analysis - key predictive factors for betting."""
    # Use last 10 games for more stable trends
    # Points per game serves as a strong proxy for pace until we integrate possession data

    home_avg_pts = home_recent.get('avg_points', 0) if home_recent else 0
    away_avg_pts = away_recent.get('avg_points', 0) if away_recent else 0
    home_avg_against = home_recent.get('avg_points_allowed', 0) if home_recent else 0
    away_avg_against = away_recent.get('avg_points_allowed', 0) if away_recent else 0

    # Determine pace styles (using points as proxy)
    home_style = "Fast-paced" if home_avg_pts > 115 else "Moderate" if home_avg_pts > 108 else "Slow-paced"
    away_style = "Fast-paced" if away_avg_pts > 115 else "Moderate" if away_avg_pts > 108 else "Slow-paced"

    # Determine defensive styles (based on 2024-25 NBA defensive rating thresholds)
    # Elite: <111 PPG, Average: 111-116 PPG, Weak: >116 PPG
    home_defense = "Elite defense" if home_avg_against < 111 else "Average defense" if home_avg_against < 116 else "Weak defense"
    away_defense = "Elite defense" if away_avg_against < 111 else "Average defense" if away_avg_against < 116 else "Weak defense"

    # Generate matchup insight
    if home_avg_pts > 115 and away_avg_pts > 115:
        tempo_note = "HIGH-SCORING POTENTIAL: Both teams play at fast pace - expect high total"
    elif home_avg_pts < 108 and away_avg_pts < 108:
        tempo_note = "LOW-SCORING GAME: Both teams play slow, methodical basketball"
    elif abs(home_avg_pts - away_avg_pts) > 10:
        tempo_note = "PACE CLASH: Different tempo styles - game flow will be contested"
    else:
        tempo_note = "BALANCED MATCHUP: Similar pace and scoring tendencies"

    return f"""### Pace & Style Matchup

| Team | Style | Recent PPG | Def. Efficiency |
|------|-------|-----------|-----------------|
| **{home_team}** | {home_style} | {home_avg_pts:.1f} | {home_defense} ({home_avg_against:.1f} allowed) |
| **{away_team}** | {away_style} | {away_avg_pts:.1f} | {away_defense} ({away_avg_against:.1f} allowed) |

**Matchup Dynamics:**
{tempo_note}

**Betting Implications:**
- Projected total range: {home_avg_pts + away_avg_pts - 5:.0f}-{home_avg_pts + away_avg_pts + 5:.0f} points
- Style advantage favors the team that can control pace
- Watch first quarter tempo - sets tone for total scoring

*Analysis based on last 10 games*
"""

def format_head_to_head_summary(home_team, away_team, n_games=3):
    """Generate head-to-head recent performance summary."""
    # Simple version - fallback when H2H data not available
    # TODO: Integrate with actual game history database

    return f"""### Recent Matchup History

**{home_team} vs {away_team}** season series:

These teams' recent performance can be found in the "Recent Form" sections. The ELO ratings above incorporate historical performance including past matchups.

**What to Watch:**
- How each team's style matchesup (pace, defense, offensive efficiency)
- Key player battles and rotations
- Coaching adjustments from previous meetings

*Full head-to-head history integration coming soon*
"""

def format_featured_game(game, prediction, team_ratings, player_ratings, player_team_mapping=None):
    """Format the featured game with full analysis (for free tier)."""
    home_team = game['home_team']
    away_team = game['away_team']
    home_prob = prediction['home_win_prob']
    away_prob = prediction['away_win_prob']

    winner = home_team if prediction['predicted_winner'] == 'home' else away_team
    winner_prob = max(home_prob, away_prob)

    # Get injury impact for both teams
    home_injuries = get_injury_impact_analysis(home_team, player_ratings, player_team_mapping)
    away_injuries = get_injury_impact_analysis(away_team, player_ratings, player_team_mapping)

    # Get recent performance for both teams
    home_recent = get_recent_games_performance(home_team, last_n_games=10)
    away_recent = get_recent_games_performance(away_team, last_n_games=10)

    # Format recent form string
    if home_recent and winner == home_team:
        winner_record = f"{home_recent['wins']}-{home_recent['losses']}"
        if home_recent['current_streak_type'] == 'W':
            streak_text = f"Won {home_recent['current_streak_length']}"
        else:
            streak_text = f"Lost {home_recent['current_streak_length']}"
    elif away_recent and winner == away_team:
        winner_record = f"{away_recent['wins']}-{away_recent['losses']}"
        if away_recent['current_streak_type'] == 'W':
            streak_text = f"Won {away_recent['current_streak_length']}"
        else:
            streak_text = f"Lost {away_recent['current_streak_length']}"
    else:
        winner_record = "N/A"
        streak_text = "N/A"

    # Generate storyline
    storyline = generate_game_storyline(home_team, away_team, prediction, home_recent, away_recent)

    # Determine which section to show based on day of month (alternating)
    today = datetime.now()
    use_h2h = (today.day % 2 == 0)  # Even days show H2H, odd days show Pace/Style

    if use_h2h:
        # Get head-to-head history
        dynamic_section = format_head_to_head_summary(home_team, away_team, n_games=3)
    else:
        # Get pace and style matchup analysis
        dynamic_section = format_pace_style_analysis(home_team, away_team, home_recent, away_recent)

    output = f"""
## FEATURED GAME: {away_team} @ {home_team}
**{game['time']}**

### The Storyline
{storyline}

### The Prediction
**{winner} {winner_prob*100:.1f}%** ({interpret_probability(winner_prob)})

| Team | ELO Rating | Win Probability |
|------|-----------|----------------|
| **{home_team}** (Home) | {prediction['home_rating']:.0f} | **{home_prob*100:.1f}%** |
| **{away_team}** (Away) | {prediction['away_rating']:.0f} | {away_prob*100:.1f}% |

*Home court advantage: +20 ELO points*

{dynamic_section}

### The Analysis

The model gives **{winner}** a **{winner_prob*100:.1f}%** chance to win this matchup.

**Why {winner}?**
- ELO Rating: {prediction['home_rating']:.0f} vs {prediction['away_rating']:.0f} ({abs(prediction['home_rating'] - prediction['away_rating']):.0f} point advantage)
- Home court edge: Worth approximately {(20/400)*100:.1f}% in win probability
- Recent form: {winner_record} in last 10 games (current streak: {streak_text})

---
"""

    return output

def format_quick_pick(game, prediction):
    """Format a quick prediction (for paid tier preview)."""
    home_team = game['home_team']
    away_team = game['away_team']
    home_prob = prediction['home_win_prob']

    winner = home_team if prediction['predicted_winner'] == 'home' else away_team
    winner_prob = max(home_prob, 1-home_prob)

    output = f"""
### {away_team} @ {home_team}
**{game['time']}** | **Prediction: {winner} {winner_prob*100:.1f}%**
ELO: {away_team} {prediction['away_rating']:.0f} vs {home_team} {prediction['home_rating']:.0f}
"""

    return output

def generate_newsletter(featured_game_name=None, all_games=False, date_str=None):
    """Generate the full newsletter content."""

    # Load data
    print("Loading ELO ratings...")
    team_history = load_csv_to_dataframe('data/exports/team_elo_history_phase_1_5.csv')
    latest_teams = team_history.sort_values('date').groupby('team_id').last().reset_index()
    latest_teams['rating'] = latest_teams['rating_after']
    team_ratings = latest_teams[['team_id', 'team_name', 'rating']].copy()

    # Use position-adjusted player ratings (fixes rim protector inflation)
    player_ratings = load_csv_to_dataframe('data/exports/player_ratings_bpm_adjusted.csv')

    # Load player-team mapping
    try:
        player_team_mapping = load_csv_to_dataframe('data/exports/player_team_mapping.csv')
        print("Player-team mapping loaded successfully")
    except Exception as e:
        print(f"Warning: Could not load player-team mapping: {e}")
        player_team_mapping = None

    # Get games for specified date (or today)
    games = get_todays_games(date_str)

    # Generate newsletter header
    if date_str:
        header_date = datetime.strptime(date_str, '%Y-%m-%d').strftime("%B %d, %Y")
    else:
        header_date = datetime.now().strftime("%B %d, %Y")

    # Get accuracy stats for header
    accuracy_stats = get_accuracy_stats(days_back=7)
    if accuracy_stats:
        week_record = f"{accuracy_stats['correct']}-{accuracy_stats['total'] - accuracy_stats['correct']}"
        week_pct = f"{accuracy_stats['accuracy']:.1f}%"
        if accuracy_stats['streak_type'] == 'W':
            streak_text = f"| Win Streak: {accuracy_stats['current_streak']} games"
        elif accuracy_stats['streak_type'] == 'L':
            streak_text = f"| Losing Streak: {accuracy_stats['current_streak']} games"
        else:
            streak_text = ""
        accuracy_header = f"**Season: 69.96%** | **This Week: {week_record} ({week_pct})** {streak_text}"
    else:
        accuracy_header = "**Season Accuracy: 69.96%** (4.27% above baseline)"

    # Build today's schedule section
    schedule_section = "## Today's Schedule\n\n"
    for i, game in enumerate(games):
        away = game['away_team']
        home = game['home_team']
        time = game['time']

        # Format as side-by-side matchups (2 per row for better formatting)
        if i % 2 == 0:
            schedule_section += f"**{away}** @ **{home}**  \n{time}\n\n"
        else:
            schedule_section += f"**{away}** @ **{home}**  \n{time}\n\n"

    output = f"""# Second Bounce — {header_date}

**Today's Slate: {len(games)} Games**

---

{schedule_section}
---

## Model Performance Tracker
{accuracy_header}

*Powered by Hybrid ELO Model (70% Team + 30% Player)*

---
"""

    # Add yesterday's results with prediction tracking
    try:
        yesterday_results = format_yesterdays_results_with_predictions()
        if yesterday_results and "No completed games" not in yesterday_results:
            output += f"""
## Yesterday's Results
{yesterday_results}

---

"""
    except Exception as e:
        print(f"Warning: Could not get yesterday's results: {e}")

    # Determine featured game first (needed for Wednesday visualization)
    if featured_game_name:
        featured = next((g for g in games if featured_game_name.lower() in f"{g['home_team']} {g['away_team']}".lower()), games[0])
    else:
        featured = games[0]  # Default to first game

    # Generate predictions for all games (needed for upset watch)
    all_predictions = []
    for game in games:
        pred = predict_game(game['home_id'], game['away_id'], team_ratings)
        if pred:
            all_predictions.append(pred)

    # Add upset watch section
    try:
        upset_candidates = identify_upset_candidates(games, all_predictions, team_ratings)
        if upset_candidates:
            upset_watch_text = format_upset_watch(upset_candidates, max_games=2)
            output += f"""
## Upset Watch
{upset_watch_text}

---

"""
    except Exception as e:
        print(f"Warning: Could not generate upset watch: {e}")

    # Add summarized games view (at-a-glance predictions)
    try:
        # Prepare predictions in the format game_summary expects
        predictions_for_summary = []
        for game in games:
            pred = predict_game(game['home_id'], game['away_id'], team_ratings)
            if pred:
                predictions_for_summary.append({
                    'game_time': game.get('time', 'TBD'),
                    'home_team': game['home_team'],
                    'away_team': game['away_team'],
                    'home_win_prob': pred['home_win_prob']
                })
        
        if predictions_for_summary:
            games_summary = generate_games_summary(predictions_for_summary, format='markdown')
            output += f"""
## Today's Games at a Glance
{games_summary}

---

"""
    except Exception as e:
        print(f"Warning: Could not generate games summary: {e}")

    # Add day-specific visualization BEFORE featured game
    try:
        # Determine day of week
        if date_str:
            target_date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        else:
            target_date_obj = datetime.now()

        day_of_week = target_date_obj.weekday()  # 0=Monday, 6=Sunday
        target_date_int = int(target_date_obj.strftime('%Y%m%d'))

        # Get appropriate visualization
        # For Wednesday (day 2), pass featured game teams
        if day_of_week == 2 and featured:
            viz_section = get_visualization_for_day(
                day_of_week,
                target_date=target_date_int,
                home_team=featured['home_id'],
                away_team=featured['away_id']
            )
        else:
            viz_section = get_visualization_for_day(
                day_of_week,
                target_date=target_date_int
            )

        output += viz_section
        output += "\n\n---\n\n"
    except Exception as e:
        print(f"Warning: Could not generate visualization: {e}")
        # Continue without visualization

    # Featured game (free tier content)
    pred = predict_game(featured['home_id'], featured['away_id'], team_ratings)
    if pred:
        output += format_featured_game(featured, pred, team_ratings, player_ratings, player_team_mapping)
    else:
        print(f"ERROR: Could not generate prediction for featured game")

    # Other games preview
    output += f"""
## Today's Other Games

*Premium subscribers get full analysis + injury reports for all games below*

"""

    for game in games:
        if game == featured:
            continue

        pred = predict_game(game['home_id'], game['away_id'], team_ratings)
        if pred:
            output += format_quick_pick(game, pred)

    output += """
---

## Upgrade to Premium

Get the full breakdown for **ALL games** every day:
- Detailed ELO analysis for every matchup
- Injury impact reports (key player swings)
- Advanced team performance analytics
- Historical head-to-head data
- Weekly accuracy tracking

**Only $9.99/month** | [Upgrade Now]

---

## Yesterday's Results

"""

    # Add yesterday's results
    try:
        # Calculate yesterday's date from the target date
        if date_str:
            target_date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            yesterday_date_obj = target_date_obj - timedelta(days=1)
            yesterday_date_int = int(yesterday_date_obj.strftime('%Y%m%d'))
            yesterdays_results = format_yesterdays_results(yesterday_date_int)
        else:
            yesterdays_results = format_yesterdays_results()

        output += yesterdays_results + "\n"
    except Exception as e:
        print(f"Warning: Could not load yesterday's results: {e}")
        output += "*Yesterday's results unavailable*\n"

    output += """
---

**Questions?** Reply to this email
**Model details:** Hybrid Team (70%) + Player ELO (30%) using Box Plus/Minus
**Data:** 31,163 games analyzed (2000-2025 seasons)

"""

    return output

def main():
    parser = argparse.ArgumentParser(description='Export NBA predictions for Substack')
    parser.add_argument('--date', type=str, help='Date for predictions (YYYY-MM-DD)')
    parser.add_argument('--featured-game', type=str, help='Featured game (e.g., "Lakers Warriors")')
    parser.add_argument('--all-games', action='store_true', help='Generate full analysis for all games (premium)')
    parser.add_argument('--output', type=str, default='substack_newsletter.md', help='Output file')

    args = parser.parse_args()

    print("Generating Substack newsletter...")
    newsletter = generate_newsletter(
        featured_game_name=args.featured_game,
        all_games=args.all_games,
        date_str=args.date
    )

    # Save to file
    output_path = args.output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(newsletter)

    print(f"\nNewsletter saved to: {output_path}")
    print(f"\nCopy this content into Substack:")
    print("="*80)
    # Don't print newsletter content to avoid Unicode errors on Windows
    print(f"Newsletter preview available in: {output_path}")
    print(f"Ready to paste into Substack!")

if __name__ == '__main__':
    main()
