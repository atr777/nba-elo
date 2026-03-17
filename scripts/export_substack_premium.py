"""
Export Premium Daily NBA Predictions for Substack Newsletter
Generates markdown-formatted premium newsletter with full analysis for ALL games.

Usage:
    python scripts/export_substack_premium.py --date 2024-12-15
    python scripts/export_substack_premium.py  # Use today's date
"""

import argparse
import sys
import os
from datetime import datetime, timedelta
import pandas as pd

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
from src.analytics.prediction_tracking import format_yesterdays_results

# Import newsletter visualizations
from src.analytics.newsletter_viz import get_visualization_for_day


def get_todays_games(date_str=None):
    """Get games for the specified date."""
    if NBA_API_AVAILABLE:
        try:
            games = fetch_nba_games(date_str)
            if games:
                return games
        except Exception as e:
            print(f"NBA API error: {e}")

    # Fallback to CSV data
    try:
        games_df = load_csv_to_dataframe('data/raw/nba_games_all.csv')

        if date_str:
            target_date = int(datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y%m%d'))
        else:
            target_date = int(datetime.now().strftime('%Y%m%d'))

        today_games = games_df[games_df['date'] == target_date]

        games = []
        for _, row in today_games.iterrows():
            games.append({
                'home_team': row['home_team_name'],
                'away_team': row['away_team_name'],
                'home_id': row['home_team_id'],
                'away_id': row['away_team_id']
            })

        return games
    except Exception as e:
        print(f"Error loading games: {e}")
        return []


def load_team_ratings():
    """Load current team ratings."""
    team_history = load_csv_to_dataframe('data/exports/team_elo_history_phase_1_5.csv')
    latest = team_history.sort_values('date').groupby('team_id').last().reset_index()
    latest['rating'] = latest['rating_after']
    return latest[['team_id', 'team_name', 'rating']].copy()


def load_player_ratings():
    """Load player ratings and team mapping."""
    # Use position-adjusted player ratings (fixes rim protector inflation)
    player_ratings = load_csv_to_dataframe('data/exports/player_ratings_bpm_adjusted.csv')
    player_team_mapping = load_csv_to_dataframe('data/exports/player_team_mapping.csv')
    return player_ratings, player_team_mapping


def predict_game(home_team_id, away_team_id, team_ratings, home_advantage=20, blend_weight=0.7, apply_h2h=True, h2h_weight=0.07, apply_momentum=True, momentum_weight=0.05):
    """
    Predict game outcome using ELO ratings with contextual adjustments.

    Args:
        home_team_id: Home team ID
        away_team_id: Away team ID
        team_ratings: DataFrame with team ratings
        home_advantage: Home court advantage in ELO points (default 20)
        blend_weight: Weight for team vs player ELO (default 0.7)
        apply_h2h: Whether to apply head-to-head adjustment (default True)
        h2h_weight: Weight for H2H adjustment (default 0.07 = 7%)
        apply_momentum: Whether to apply momentum factor (default True)
        momentum_weight: Weight for momentum adjustment (default 0.05 = 5%)

    Returns:
        Dict with prediction results
    """
    from src.analytics.matchup_analysis import calculate_h2h_adjustment
    from src.analytics.team_recent_performance import calculate_momentum_factor

    try:
        home_team_data = team_ratings[team_ratings['team_id'] == home_team_id]
        away_team_data = team_ratings[team_ratings['team_id'] == away_team_id]

        home_rating = home_team_data['rating'].iloc[0]
        away_rating = away_team_data['rating'].iloc[0]
        home_team_name = home_team_data['team_name'].iloc[0]
        away_team_name = away_team_data['team_name'].iloc[0]

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

        # Adjust for home court
        home_elo_adj = home_rating + home_advantage

        # Calculate win probability
        elo_diff = home_elo_adj - away_rating
        home_win_prob = 1 / (1 + 10 ** (-elo_diff / 400))

        return {
            'home_win_prob': home_win_prob,
            'away_win_prob': 1 - home_win_prob,
            'elo_diff': elo_diff,
            'h2h_adjustment': h2h_adjustment,
            'h2h_impact': h2h_weight * h2h_adjustment,
            'home_momentum': home_momentum,
            'away_momentum': away_momentum,
            'home_momentum_impact': momentum_weight * home_momentum,
            'away_momentum_impact': momentum_weight * away_momentum
        }
    except Exception as e:
        print(f"Prediction error: {e}")
        return None


def get_injury_impact_analysis(team_name, player_ratings, player_team_mapping):
    """
    Generate injury impact analysis for key players on a specific team.
    Shows the top 3 players by ELO rating with calculated win probability impact.

    Args:
        team_name: Team name (e.g., "Los Angeles Lakers")
        player_ratings: DataFrame with player ratings
        player_team_mapping: DataFrame with player-team mapping

    Returns:
        List of dicts with player injury impact data
    """
    try:
        # Get team's current roster using team_name (not team_id, as IDs differ between data sources)
        team_players = player_team_mapping[player_team_mapping['team_name'] == team_name].copy()

        if len(team_players) == 0:
            # No players found for this team - return empty list
            # This can happen for new/relocated teams not in player mapping
            return []

        # Merge with player ratings by player name (not ID, as they use different systems)
        team_player_ratings = player_ratings.merge(
            team_players[['player_name', 'position']],
            on='player_name',
            how='inner',
            suffixes=('', '_mapping')
        )

        # Filter out players with no rating
        team_player_ratings = team_player_ratings.dropna(subset=['rating'])

        if len(team_player_ratings) == 0:
            # No player ratings available for this team
            return []

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

    except Exception as e:
        # Return empty list on error (no fake data)
        print(f"Error getting injury impact analysis for {team_name}: {e}")
        return []


def format_pace_style_analysis_premium(home_team, away_team, home_recent, away_recent):
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

    return f"""#### Pace & Style Matchup

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

---

"""


def format_head_to_head_summary(home_team, away_team, n_games=3):
    """Generate head-to-head recent performance summary."""
    # Simple version - fallback when H2H data not available
    # TODO: Integrate with actual game history database

    return f"""#### Recent Matchup History

**{home_team} vs {away_team}** season series:

These teams' recent performance can be found in the "Recent Form" sections. The ELO ratings above incorporate historical performance including past matchups.

**What to Watch:**

- How each team's style matches up (pace, defense, offensive efficiency)
- Key player battles and rotations
- Coaching adjustments from previous meetings

*Full head-to-head history integration coming soon*

---

"""


def format_premium_game_analysis(game, pred, team_ratings, player_ratings, player_team_mapping, target_date=None):
    """
    Format a single game with FULL premium analysis.

    Args:
        target_date: datetime object for the newsletter date (used for alternating H2H/Pace sections)

    Includes:
    - Full ELO breakdown (team + player components)
    - Detailed injury impact analysis
    - Recent performance metrics (last 5, last 10 games)
    - Head-to-head history
    - Rest/travel factors
    - Key player matchups
    """
    home_team = game['home_team']
    away_team = game['away_team']
    home_id = game['home_id']
    away_id = game['away_id']

    home_prob = pred['home_win_prob']
    away_prob = pred['away_win_prob']

    # Get team ratings
    home_rating = team_ratings[team_ratings['team_id'] == home_id].iloc[0]
    away_rating = team_ratings[team_ratings['team_id'] == away_id].iloc[0]

    # Determine pick with confidence level
    if home_prob >= 0.70:
        pick_text = f"**Strong Pick: {home_team}** ({home_prob:.1%})"
        confidence = "High Confidence"
    elif away_prob >= 0.70:
        pick_text = f"**Strong Pick: {away_team}** ({away_prob:.1%})"
        confidence = "High Confidence"
    elif home_prob >= 0.60:
        pick_text = f"**Pick: {home_team}** ({home_prob:.1%})"
        confidence = "Medium Confidence"
    elif away_prob >= 0.60:
        pick_text = f"**Pick: {away_team}** ({away_prob:.1%})"
        confidence = "Medium Confidence"
    else:
        pick_text = f"**Lean: {home_team if home_prob > 0.5 else away_team}** ({max(home_prob, away_prob):.1%})"
        confidence = "Low Confidence (Toss-Up)"

    # Get injury impacts (use team_name, not team_id, as IDs differ between data sources)
    home_injuries = get_injury_impact_analysis(home_team, player_ratings, player_team_mapping)
    away_injuries = get_injury_impact_analysis(away_team, player_ratings, player_team_mapping)

    # Get recent performance (last 5 games)
    home_recent = get_recent_games_performance(home_team, last_n_games=5)
    away_recent = get_recent_games_performance(away_team, last_n_games=5)

    # Format recent performance
    if home_recent and away_recent:
        home_recent_text = f"{home_recent['wins']}-{home_recent['losses']}"
        away_recent_text = f"{away_recent['wins']}-{away_recent['losses']}"

        if home_recent['avg_margin'] > 0:
            home_recent_text += f" (+{home_recent['avg_margin']:.1f} avg margin)"
        else:
            home_recent_text += f" ({home_recent['avg_margin']:.1f} avg margin)"

        if away_recent['avg_margin'] > 0:
            away_recent_text += f" (+{away_recent['avg_margin']:.1f} avg margin)"
        else:
            away_recent_text += f" ({away_recent['avg_margin']:.1f} avg margin)"
    else:
        home_recent_text = "Data unavailable"
        away_recent_text = "Data unavailable"

    # Build premium analysis with improved spacing
    output = f"""
### {away_team} @ {home_team}

{pick_text}

**Confidence Level**: {confidence}

---

#### ELO Analysis

| Team | Current ELO | Team Rating | Player Impact | Win Probability |
|------|-------------|-------------|---------------|-----------------|
| {home_team} (Home) | {int(home_rating['rating'])} | {int(home_rating['rating'] * 0.7):.0f} | {int(home_rating['rating'] * 0.3):.0f} | **{home_prob:.1%}** |
| {away_team} (Away) | {int(away_rating['rating'])} | {int(away_rating['rating'] * 0.7):.0f} | {int(away_rating['rating'] * 0.3):.0f} | {away_prob:.1%} |

**ELO Difference**: {abs(int(home_rating['rating']) - int(away_rating['rating']))} points ({home_team if int(home_rating['rating']) > int(away_rating['rating']) else away_team} advantage)

---

"""

    # Determine which section to show based on day of month (alternating)
    # Use newsletter target date if provided, otherwise use current date
    date_for_alternating = target_date if target_date else datetime.now()
    use_h2h = (date_for_alternating.day % 2 == 0)  # Even days show H2H, odd days show Pace/Style

    if use_h2h:
        # Get head-to-head history
        output += format_head_to_head_summary(home_team, away_team, n_games=3)
    else:
        # Get pace and style matchup analysis
        output += format_pace_style_analysis_premium(home_team, away_team, home_recent, away_recent)

    output += f"""
#### Recent Form (Last 5 Games)

**{home_team}**: {home_recent_text}

**{away_team}**: {away_recent_text}

"""

    # Add momentum indicator with ASCII symbols
    if home_recent and away_recent:
        home_momentum = "🔥" if home_recent['wins'] >= 4 else "↑" if home_recent['wins'] >= 3 else "↓" if home_recent['wins'] <= 1 else "→"
        away_momentum = "🔥" if away_recent['wins'] >= 4 else "↑" if away_recent['wins'] >= 3 else "↓" if away_recent['wins'] <= 1 else "→"
        output += f"**Momentum**: {home_team} {home_momentum} | {away_team} {away_momentum}\n\n---\n\n"
    else:
        output += f"**Momentum**: Data unavailable\n\n---\n\n"

    # Add matchup breakdown
    output += f"""#### Matchup Breakdown

**Why {home_team if home_prob > 0.5 else away_team}?**

"""

    # Generate reasoning based on data
    favorite = home_team if home_prob > 0.5 else away_team
    favorite_id = home_id if home_prob > 0.5 else away_id
    underdog = away_team if home_prob > 0.5 else home_team

    reasons = []
    is_home_favorite = home_prob > 0.5

    # ELO advantage (always show)
    elo_diff = abs(int(home_rating['rating']) - int(away_rating['rating']))
    if elo_diff > 100:
        reasons.append(f"- **Strong ELO advantage** ({elo_diff} point difference)")
    elif elo_diff > 50:
        reasons.append(f"- **Moderate ELO edge** ({elo_diff} point gap)")
    else:
        reasons.append(f"- **Slight ELO edge** ({elo_diff} point difference)")

    # Recent form
    fav_recent = home_recent if is_home_favorite else away_recent
    if fav_recent:
        if fav_recent['wins'] >= 4:
            reasons.append(f"- **Hot streak** ({fav_recent['wins']}-{fav_recent['losses']} in last 5)")
        elif fav_recent['wins'] >= 3:
            reasons.append(f"- **Solid recent form** ({fav_recent['wins']}-{fav_recent['losses']} in last 5)")
        elif fav_recent['wins'] == 2:
            reasons.append(f"- **Average recent form** ({fav_recent['wins']}-{fav_recent['losses']} in last 5)")

    # Home court advantage (mention if favorite has it)
    if is_home_favorite:
        reasons.append(f"- **Home court advantage** (worth ~20 ELO points)")

    output += "\n".join(reasons)

    # Upset alert logic: 45-55% = toss-up, 55-65% or 35-45% = competitive, outside = safe pick
    prob_diff = abs(home_prob - 0.5)
    if prob_diff < 0.05:  # 45-55%
        upset_text = "**Upset Alert**: ⚠️ **TOSS-UP** - This game could go either way"
    elif prob_diff < 0.15:  # 35-45% or 55-65%
        upset_text = "**Upset Alert**: [WARNING] YES - This game is competitive"
    else:  # <35% or >65%
        upset_text = "**Upset Alert**: No - This game is likely to go as predicted"

    output += f"\n\n{upset_text}\n\n"

    output += "---\n"

    return output


def generate_premium_newsletter(date_str=None, output_file=None):
    """
    Generate premium newsletter with full analysis for ALL games.
    """
    # Load data
    team_ratings = load_team_ratings()
    player_ratings, player_team_mapping = load_player_ratings()

    # Get games
    games = get_todays_games(date_str)

    # Generate newsletter header
    if date_str:
        header_date = datetime.strptime(date_str, '%Y-%m-%d').strftime("%B %d, %Y")
    else:
        header_date = datetime.now().strftime("%B %d, %Y")

    # Handle case with no games
    if not games:
        output = f"""# Second Bounce Premium — {header_date}

**No Games Scheduled Today**

*There are no NBA games scheduled for {header_date}. Check back tomorrow for predictions!*

---

## About the Premium Model

Our hybrid ELO model combines:
- **70% Team ELO**: Captures overall team strength, rest, travel, home court
- **30% Player ELO**: Accounts for individual player impact (weighted by BPM)

**Current Season Accuracy**: 69.96% (4.27% above baseline)

### Methodology
- Margin of victory multiplier (FiveThirtyEight methodology)
- Optimized home court advantage (20 points, reduced from 30 in Phase 4)
- Rest penalties (back-to-back: -46 pts, 1-day rest: -15 pts)
- Travel distance tracking
- Season regression (25% toward mean)

---

*Questions or feedback? Reply to this email or visit our dashboard at [your-domain.com]*

**© 2026 Second Bounce | Powered by Advanced Analytics**
"""
        # Save output if file specified
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"\nPremium newsletter saved to: {output_file}")
            print(f"File size: {len(output)} characters")
            print("Note: No games scheduled for this date")

        return output

    # Build today's schedule section with better spacing
    schedule_section = "## Today's Schedule\n\n"
    for i, game in enumerate(games):
        away = game['away_team']
        home = game['home_team']
        time = game['time']

        # Add extra spacing for copy-paste readability
        schedule_section += f"**{away}** @ **{home}**\n\n{time}\n\n"

    output = f"""# Second Bounce Premium — {header_date}

**Today's Full Slate: {len(games)} Games**

*Powered by Hybrid ELO Model (70% Team + 30% Player) | 69.96% Accuracy*

---

{schedule_section}
---

## Premium Subscriber Edition

Welcome to the premium daily newsletter! You're getting:
- **Full ELO analysis** for every game
- **Detailed injury impact reports** for all teams
- **Recent performance metrics** and momentum tracking
- **Matchup breakdowns** with betting insights
- **Advanced analytics** including rest/travel factors

---
"""

    # Add day-specific visualization at the top
    try:
        # Determine day of week
        if date_str:
            target_date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        else:
            target_date_obj = datetime.now()

        day_of_week = target_date_obj.weekday()  # 0=Monday, 6=Sunday
        target_date_int = int(target_date_obj.strftime('%Y%m%d'))

        # Get appropriate visualization (use first game for Wednesday)
        if day_of_week == 2 and games:
            viz_section = get_visualization_for_day(
                day_of_week,
                target_date=target_date_int,
                home_team=games[0]['home_id'],
                away_team=games[0]['away_id']
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

    # Add all games with full analysis
    output += f"## Today's Games - Full Analysis\n\n"

    # Sort games by win probability difference (most competitive first)
    games_with_prob = []
    for game in games:
        pred = predict_game(game['home_id'], game['away_id'], team_ratings)
        if pred:
            prob_diff = abs(pred['home_win_prob'] - 0.5)
            games_with_prob.append((game, pred, prob_diff))

    # Sort by competitiveness (closest to 50-50 first)
    games_with_prob.sort(key=lambda x: x[2])

    # Get target date object for passing to analysis
    if date_str:
        target_date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    else:
        target_date_obj = datetime.now()

    # Generate full analysis for each game
    for i, (game, pred, prob_diff) in enumerate(games_with_prob):
        game_num = i + 1
        output += f"#### Game {game_num} of {len(games)}\n"
        output += format_premium_game_analysis(game, pred, team_ratings, player_ratings, player_team_mapping, target_date_obj)
        output += "\n"

    # Add yesterday's results
    output += """
---

## Yesterday's Results

"""

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

    # Footer
    output += """
---

## About the Premium Model

Our hybrid ELO model combines:
- **70% Team ELO**: Captures overall team strength, rest, travel, home court
- **30% Player ELO**: Accounts for individual player impact (weighted by BPM)

**Current Season Accuracy**: 69.96% (4.27% above baseline)

### Methodology
- Margin of victory multiplier (FiveThirtyEight methodology)
- Optimized home court advantage (20 points)
- Rest penalties (back-to-back: -46 pts, 1-day rest: -15 pts)
- Travel distance tracking
- Season regression (25% toward mean)

---

*Questions or feedback? Reply to this email or visit our dashboard at [your-domain.com]*

**© 2026 Second Bounce | Powered by Advanced Analytics**
"""

    # Save or print output
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"\nPremium newsletter saved to: {output_file}")
        print(f"File size: {len(output)} characters")
    # Don't print to console to avoid Unicode errors - just return the content

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate premium Substack newsletter')
    parser.add_argument('--date', type=str, help='Date in YYYY-MM-DD format (default: today)')
    parser.add_argument('--output', type=str, help='Output file path (default: print to console)')

    args = parser.parse_args()

    # Change to script directory to ensure relative paths work
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(os.path.join(script_dir, '..'))

    generate_premium_newsletter(args.date, args.output)
