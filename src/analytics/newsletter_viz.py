"""
Newsletter Visualization Module
Generates day-specific visualizations for daily newsletters with injury consideration
"""

import pandas as pd
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.utils.file_io import load_csv_to_dataframe


def get_injury_adjusted_team_elo(team_id, date, team_elo):
    """
    Calculate injury-adjusted team ELO by subtracting missing players' impact.

    Args:
        team_id: Team identifier
        date: Date to check injuries for (YYYYMMDD int)
        team_elo: Base team ELO rating

    Returns:
        Adjusted ELO rating accounting for injuries
    """
    try:
        # Load player ratings (position-adjusted) and team mapping
        player_ratings = load_csv_to_dataframe('data/exports/player_ratings_bpm_adjusted.csv')
        team_mapping = load_csv_to_dataframe('data/exports/player_team_mapping.csv')

        # Get current roster
        roster = team_mapping[team_mapping['team_id'] == team_id]

        # NOTE: Injury data integration is a future enhancement (not implemented yet)
        # Would require: Daily scraping from NBA.com injury report or ESPN API
        # See: nba_api_data_fetcher.py get_injury_status_for_game() for placeholder
        # For now, return base ELO without injury adjustment
        return team_elo

    except Exception as e:
        return team_elo


def get_monday_viz(target_date=None):
    """
    Monday: Top 20 Player ELO Rankings
    Shows highest-rated players with injury status

    Args:
        target_date: Date for rankings (YYYYMMDD int or None for today)

    Returns:
        Formatted string visualization
    """
    try:
        # Load player ratings
        player_ratings = load_csv_to_dataframe('data/exports/player_ratings_bpm_adjusted.csv')
        team_mapping = load_csv_to_dataframe('data/exports/player_team_mapping.csv')

        # Merge to get team names (use player_name since player_id systems differ)
        player_data = player_ratings.merge(
            team_mapping[['player_name', 'team_name', 'position']],
            on='player_name',
            how='left'
        )

        # Sort by ELO rating and get top 20
        top_20 = player_data.nlargest(20, 'rating')[
            ['player_name', 'team_name', 'rating', 'games_played']
        ].reset_index(drop=True)

        # Format output
        output = "## Top 20 Player ELO Rankings\n\n"
        output += "```\n"
        output += f"{'Rank':<5} {'Player':<25} {'Team':<5} {'ELO':<6} {'Games':<6}\n"
        output += "-" * 55 + "\n"

        for idx, row in top_20.iterrows():
            rank = idx + 1
            player = row['player_name'][:24]  # Truncate long names
            team = row['team_name'] if pd.notna(row['team_name']) else 'FA'
            elo = int(row['rating'])
            games = int(row['games_played'])

            output += f"{rank:<5} {player:<25} {team:<5} {elo:<6} {games:<6}\n"

        output += "```\n\n"
        output += "*Rankings based on current player ELO ratings*\n"

        return output

    except Exception as e:
        return f"*Top 20 Player Rankings unavailable: {e}*\n"


def get_tuesday_viz(target_date=None):
    """
    Tuesday: Hottest and Coldest Teams (Last 5 Games)
    Shows top 5 teams with biggest ELO gains and losses

    Args:
        target_date: Date to calculate from (YYYYMMDD int or None for today)

    Returns:
        Formatted string visualization
    """
    try:
        # Load team ELO history
        team_history = load_csv_to_dataframe('data/exports/team_elo_history_phase_1_5.csv')

        # Determine target date
        if target_date is None:
            target_date = int(datetime.now().strftime('%Y%m%d'))

        # Get latest ratings for each team
        latest = team_history.sort_values('date').groupby('team_id').last().reset_index()

        # Get ratings from 5 games ago for each team
        team_changes = []

        for team_id in latest['team_id'].unique():
            team_data = team_history[team_history['team_id'] == team_id].sort_values('date')

            if len(team_data) < 5:
                continue

            # Skip All-Star teams
            team_name = str(team_data.iloc[-1]['team_name'])
            if 'Team LeBron' in team_name or 'Team Giannis' in team_name or 'Team Durant' in team_name:
                continue

            current_elo = float(team_data.iloc[-1]['rating_after'])

            if len(team_data) >= 6:
                five_games_ago_elo = float(team_data.iloc[-6]['rating_after'])  # -6 because we want the rating BEFORE the last 5 games
            else:
                # Not enough games, use first game rating
                five_games_ago_elo = float(team_data.iloc[0]['rating_before'])

            elo_change = current_elo - five_games_ago_elo

            # Calculate W-L record for last 5 games
            last_5_games = team_data.tail(5)
            wins = int(last_5_games['won'].sum())
            losses = len(last_5_games) - wins

            team_changes.append({
                'team_id': team_id,
                'team_name': str(team_data.iloc[-1]['team_name']),
                'current_elo': current_elo,
                'elo_change': elo_change,
                'record': f"{wins}-{losses}"
            })

        df_changes = pd.DataFrame(team_changes)

        # Get top 5 hottest and coldest
        hottest = df_changes.nlargest(5, 'elo_change')
        coldest = df_changes.nsmallest(5, 'elo_change')

        # Format output
        output = "## Hottest & Coldest Teams (Last 5 Games)\n\n"

        output += "### Hottest Teams\n```\n"
        output += f"{'Rank':<5} {'Team':<20} {'ELO Change':<12} {'Record':<8}\n"
        output += "-" * 50 + "\n"

        for idx, row in hottest.iterrows():
            rank = hottest.index.get_loc(idx) + 1
            team = row['team_name'][:19]
            change = f"+{int(row['elo_change'])}"
            record = row['record']
            output += f"{rank:<5} {team:<20} {change:<12} {record:<8}\n"

        output += "```\n\n"

        output += "### Coldest Teams\n```\n"
        output += f"{'Rank':<5} {'Team':<20} {'ELO Change':<12} {'Record':<8}\n"
        output += "-" * 50 + "\n"

        for idx, row in coldest.iterrows():
            rank = coldest.index.get_loc(idx) + 1
            team = row['team_name'][:19]
            change = f"{int(row['elo_change'])}"
            record = row['record']
            output += f"{rank:<5} {team:<20} {change:<12} {record:<8}\n"

        output += "```\n\n"
        output += "*ELO changes calculated over last 5 games*\n"

        return output

    except Exception as e:
        return f"*Hottest/Coldest Teams unavailable: {e}*\n"


def get_wednesday_viz(home_team, away_team, target_date=None):
    """
    Wednesday: Featured Game Teams' Track Record (Last 10 Games)
    Shows actual W-L records for both teams

    Args:
        home_team: Home team ID
        away_team: Away team ID
        target_date: Date to calculate from (YYYYMMDD int or None for today)

    Returns:
        Formatted string visualization
    """
    try:
        # Load team ELO history
        team_history = load_csv_to_dataframe('data/exports/team_elo_history_phase_1_5.csv')

        def get_last_10_record(team_id):
            team_data = team_history[team_history['team_id'] == team_id].sort_values('date').tail(10)

            if len(team_data) == 0:
                return "N/A", 0, [], None

            wins = int(team_data['won'].sum())
            losses = len(team_data) - wins
            win_pct = wins / len(team_data)

            # Get game-by-game results (W or L)
            results = ['W' if int(r) == 1 else 'L' for r in team_data['won'].tolist()]

            # Get team name from the data
            team_name = str(team_data.iloc[-1]['team_name'])

            return f"{wins}-{losses}", win_pct, results, team_name

        home_record, home_pct, home_results, home_team_name = get_last_10_record(home_team)
        away_record, away_pct, away_results, away_team_name = get_last_10_record(away_team)

        # Format output
        output = "## Featured Teams' Track Record (Last 10 Games)\n\n"

        output += f"### {home_team_name}\n"
        output += f"**Record:** {home_record} ({home_pct:.1%})\n"
        output += f"**Game Log:** {' '.join(home_results)}\n\n"

        output += f"### {away_team_name}\n"
        output += f"**Record:** {away_record} ({away_pct:.1%})\n"
        output += f"**Game Log:** {' '.join(away_results)}\n\n"

        # Visual comparison
        output += "### Head-to-Head Momentum\n```\n"
        home_bar = '#' * int(home_pct * 20)
        home_empty = '-' * (20 - int(home_pct * 20))
        away_bar = '#' * int(away_pct * 20)
        away_empty = '-' * (20 - int(away_pct * 20))

        output += f"{home_team_name:<25} {home_bar}{home_empty} {home_pct:.1%}\n"
        output += f"{away_team_name:<25} {away_bar}{away_empty} {away_pct:.1%}\n"
        output += "```\n\n"

        return output

    except Exception as e:
        return f"*Featured Teams Track Record unavailable: {e}*\n"


def get_thursday_viz(target_date=None):
    """
    Thursday: Closest Games Today
    Shows games with tightest win probabilities

    Args:
        target_date: Date to get games for (YYYYMMDD int or None for today)

    Returns:
        Formatted string visualization
    """
    try:
        # Load games and team ratings
        games = load_csv_to_dataframe('data/raw/nba_games_all.csv')
        team_history = load_csv_to_dataframe('data/exports/team_elo_history_phase_1_5.csv')

        # Determine target date
        if target_date is None:
            target_date = int(datetime.now().strftime('%Y%m%d'))

        # Get today's games
        todays_games = games[games['date'] == target_date].copy()

        if len(todays_games) == 0:
            # Return empty string instead of error message
            # (Games may exist but not yet in CSV - coming from API/CDN)
            return ""

        # Get latest team ratings
        latest_ratings = team_history.sort_values('date').groupby('team_id').last().reset_index()
        latest_ratings['rating'] = latest_ratings['rating_after']

        game_predictions = []

        for _, game in todays_games.iterrows():
            home_rating_data = latest_ratings[latest_ratings['team_id'] == game['home_team_id']]
            away_rating_data = latest_ratings[latest_ratings['team_id'] == game['away_team_id']]

            if len(home_rating_data) == 0 or len(away_rating_data) == 0:
                continue

            home_rating = home_rating_data['rating'].iloc[0]
            away_rating = away_rating_data['rating'].iloc[0]

            # Calculate win probability
            home_advantage = 30  # Calibrated
            rating_diff = home_rating - away_rating + home_advantage
            home_win_prob = 1 / (1 + 10 ** (-rating_diff / 400))

            # Calculate closeness (distance from 50-50)
            closeness = abs(home_win_prob - 0.5)

            game_predictions.append({
                'home_team': game['home_team_name'],
                'away_team': game['away_team_name'],
                'home_prob': home_win_prob,
                'away_prob': 1 - home_win_prob,
                'closeness': closeness
            })

        # Sort by closeness (smallest = closest games)
        df_predictions = pd.DataFrame(game_predictions).sort_values('closeness')

        # Get top 5 closest games
        closest_5 = df_predictions.head(5)

        # Format output
        output = "## Closest Games Today\n\n"
        output += "*Games with tightest win probabilities*\n\n"
        output += "```\n"
        output += f"{'Matchup':<35} {'Home':<8} {'Away':<8}\n"
        output += "-" * 55 + "\n"

        for idx, game in closest_5.iterrows():
            matchup = f"{game['away_team']} @ {game['home_team']}"[:34]
            home_prob = f"{game['home_prob']:.1%}"
            away_prob = f"{game['away_prob']:.1%}"

            output += f"{matchup:<35} {home_prob:<8} {away_prob:<8}\n"

        output += "```\n\n"

        return output

    except Exception as e:
        return f"*Closest Games unavailable: {e}*\n"


def get_friday_viz(target_date=None):
    """
    Friday: Biggest Player ELO Gains (This Week)
    Shows players with largest ELO increases over last 7 days

    Args:
        target_date: End date for week (YYYYMMDD int or None for today)

    Returns:
        Formatted string visualization
    """
    try:
        from datetime import datetime, timedelta

        # Load player ELO history
        player_history = load_csv_to_dataframe('data/exports/player_elo_history_bpm.csv')

        # Determine target date (end of week)
        if target_date is None:
            target_date = int(datetime.now().strftime('%Y%m%d'))

        # Calculate date 7 days ago
        target_datetime = datetime.strptime(str(target_date), '%Y%m%d')
        week_ago = target_datetime - timedelta(days=7)
        week_ago_int = int(week_ago.strftime('%Y%m%d'))

        # Get most recent rating for each player (today)
        recent_ratings = player_history[player_history['date'] <= target_date].sort_values('date').groupby('player_id').last()

        # Get ratings from 7 days ago
        old_ratings = player_history[player_history['date'] <= week_ago_int].sort_values('date').groupby('player_id').last()

        # Calculate gains
        gains = []
        for player_id in recent_ratings.index:
            if player_id in old_ratings.index:
                recent_elo = recent_ratings.loc[player_id, 'rating_after']
                old_elo = old_ratings.loc[player_id, 'rating_after']
                elo_gain = recent_elo - old_elo

                # Only include players with positive gains
                if elo_gain > 0:
                    gains.append({
                        'player_id': player_id,
                        'player_name': recent_ratings.loc[player_id, 'player_name'],
                        'current_elo': recent_elo,
                        'elo_gain': elo_gain,
                        'games_played': recent_ratings.loc[player_id, 'games_played']
                    })

        if not gains:
            return "*No player ELO gains data available for this week*\n"

        # Sort by ELO gain (descending) and take top 10
        gains_df = pd.DataFrame(gains)
        top_gainers = gains_df.nlargest(10, 'elo_gain').reset_index(drop=True)

        # Format output
        output = "## Biggest Player ELO Gains This Week\n\n"
        output += "```\n"
        output += f"{'Rank':<5} {'Player':<25} {'+ELO':<8} {'ELO':<6} {'Games':<6}\n"
        output += "-" * 55 + "\n"

        for idx, row in top_gainers.iterrows():
            rank = idx + 1
            player = row['player_name'][:24]
            elo_gain = f"+{int(row['elo_gain'])}"
            elo = int(row['current_elo'])
            games = int(row['games_played'])

            output += f"{rank:<5} {player:<25} {elo_gain:<8} {elo:<6} {games:<6}\n"

        output += "```\n\n"
        output += "*ELO gains calculated from last 7 days*\n\n"

        return output

    except Exception as e:
        return f"*Player ELO Gains unavailable: {e}*\n"



def get_saturday_viz(target_date=None):
    """
    Saturday: Biggest Team ELO Gains (This Week)
    Shows teams with largest ELO increases over last 7 days

    Args:
        target_date: End date for week (YYYYMMDD int or None for today)

    Returns:
        Formatted string visualization
    """
    try:
        # Load team ELO history
        team_history = load_csv_to_dataframe('data/exports/team_elo_history_phase_1_5.csv')

        # Determine target date
        if target_date is None:
            target_date = int(datetime.now().strftime('%Y%m%d'))

        # Calculate date 7 days ago
        target_datetime = datetime.strptime(str(target_date), '%Y%m%d')
        week_ago = int((target_datetime - timedelta(days=7)).strftime('%Y%m%d'))

        # Get team changes over the week
        team_changes = []

        for team_id in team_history['team_id'].unique():
            team_data = team_history[team_history['team_id'] == team_id].sort_values('date')

            # Get current ELO
            current_data = team_data[team_data['date'] <= target_date]
            if len(current_data) == 0:
                continue

            # Skip All-Star teams
            team_name_check = str(current_data.iloc[-1]['team_name'])
            if 'Team LeBron' in team_name_check or 'Team Giannis' in team_name_check or 'Team Durant' in team_name_check:
                continue

            current_elo = float(current_data.iloc[-1]['rating_after'])

            # Get ELO from 7 days ago
            week_ago_data = team_data[team_data['date'] <= week_ago]
            if len(week_ago_data) == 0:
                # If no data from a week ago, use first available rating
                week_ago_elo = float(team_data.iloc[0]['rating_before'])
            else:
                week_ago_elo = float(week_ago_data.iloc[-1]['rating_after'])

            elo_change = current_elo - week_ago_elo

            # Get games played this week
            week_games = team_data[(team_data['date'] > week_ago) & (team_data['date'] <= target_date)]
            wins = int(week_games['won'].sum())
            games = len(week_games)
            losses = games - wins

            team_changes.append({
                'team_id': str(team_data.iloc[-1]['team_name']),
                'current_elo': current_elo,
                'elo_change': elo_change,
                'record': f"{wins}-{losses}",
                'games': games
            })

        df_changes = pd.DataFrame(team_changes)

        # Get top 10 biggest gainers
        top_gainers = df_changes.nlargest(10, 'elo_change')

        # Format output
        output = "## Biggest Team ELO Gains This Week\n\n"
        output += "```\n"
        output += f"{'Rank':<5} {'Team':<20} {'ELO Change':<12} {'Record':<8} {'Current ELO':<12}\n"
        output += "-" * 65 + "\n"

        for idx, row in top_gainers.iterrows():
            rank = top_gainers.index.get_loc(idx) + 1
            team = row['team_id'][:19]
            change = f"+{int(row['elo_change'])}"
            record = row['record']
            current = int(row['current_elo'])

            output += f"{rank:<5} {team:<20} {change:<12} {record:<8} {current:<12}\n"

        output += "```\n\n"
        output += f"*Based on ELO changes over last 7 days*\n\n"

        return output

    except Exception as e:
        return f"*Team ELO Gains unavailable: {e}*\n"


def get_sunday_viz(target_date=None):
    """
    Sunday: Model vs Reality (Weekly Accuracy)
    Shows how the model performed over the past week

    Args:
        target_date: End date for week (YYYYMMDD int or None for today)

    Returns:
        Formatted string visualization
    """
    try:
        # Load games and team ratings
        games = load_csv_to_dataframe('data/raw/nba_games_all.csv')
        team_history = load_csv_to_dataframe('data/exports/team_elo_history_phase_1_5.csv')

        # Determine target date and week range
        if target_date is None:
            target_date = int(datetime.now().strftime('%Y%m%d'))

        target_datetime = datetime.strptime(str(target_date), '%Y%m%d')
        week_ago = int((target_datetime - timedelta(days=7)).strftime('%Y%m%d'))

        # Get week's games with completed scores
        week_games = games[
            (games['date'] > week_ago) &
            (games['date'] <= target_date) &
            (games['home_score'] > 0) &
            (games['away_score'] > 0)
        ].copy()

        if len(week_games) == 0:
            return "*No completed games this week*\n"

        # Get latest team ratings
        latest_ratings = team_history.sort_values('date').groupby('team_id').last().reset_index()
        latest_ratings['rating'] = latest_ratings['rating_after']

        correct_predictions = 0
        total_games = 0
        upsets = []

        for _, game in week_games.iterrows():
            home_rating_data = latest_ratings[latest_ratings['team_id'] == game['home_team_id']]
            away_rating_data = latest_ratings[latest_ratings['team_id'] == game['away_team_id']]

            if len(home_rating_data) == 0 or len(away_rating_data) == 0:
                continue

            home_rating = home_rating_data['rating'].iloc[0]
            away_rating = away_rating_data['rating'].iloc[0]

            # Calculate prediction
            home_advantage = 30  # Calibrated
            rating_diff = home_rating - away_rating + home_advantage
            home_win_prob = 1 / (1 + 10 ** (-rating_diff / 400))

            predicted_winner = game['home_team_name'] if home_win_prob > 0.5 else game['away_team_name']
            actual_winner = game['home_team_name'] if game['home_score'] > game['away_score'] else game['away_team_name']

            if predicted_winner == actual_winner:
                correct_predictions += 1
            elif max(home_win_prob, 1 - home_win_prob) > 0.65:
                # Mark as upset if favorite (>65% prob) lost
                upsets.append({
                    'date': game['date'],
                    'favorite': predicted_winner,
                    'underdog': actual_winner,
                    'prob': max(home_win_prob, 1 - home_win_prob)
                })

            total_games += 1

        accuracy = correct_predictions / total_games if total_games > 0 else 0

        # Format output
        output = "## Model vs Reality: This Week's Performance\n\n"

        output += f"### Weekly Accuracy\n"
        output += f"**Correct Predictions:** {correct_predictions} / {total_games} ({accuracy:.1%})\n"
        output += f"**Model Baseline:** 65.69%\n"

        if accuracy > 0.6569:
            output += f"**Status:** **Above baseline** (+{(accuracy - 0.6569):.1%})\n\n"
        else:
            output += f"**Status:** **Below baseline** ({(accuracy - 0.6569):.1%})\n\n"

        # Visual accuracy bar
        output += "```\n"
        acc_bar = '#' * int(accuracy * 50)
        acc_empty = '-' * (50 - int(accuracy * 50))
        output += f"This Week: {acc_bar}{acc_empty} {accuracy:.1%}\n"

        baseline_bar = '#' * int(0.6569 * 50)
        baseline_empty = '-' * (50 - int(0.6569 * 50))
        output += f"Baseline:  {baseline_bar}{baseline_empty} 65.69%\n"
        output += "```\n\n"

        # Show upsets if any
        if len(upsets) > 0:
            output += f"### Notable Upsets ({len(upsets)})\n"
            for upset in upsets[:5]:  # Show top 5
                date_str = datetime.strptime(str(upset['date']), '%Y%m%d').strftime('%b %d')
                output += f"- **{date_str}:** {upset['underdog']} upset {upset['favorite']} ({upset['prob']:.1%} favorite)\n"
            output += "\n"

        return output

    except Exception as e:
        return f"*Weekly Performance unavailable: {e}*\n"


def get_visualization_for_day(day_of_week, target_date=None, home_team=None, away_team=None):
    """
    Get the appropriate visualization based on day of week.

    Args:
        day_of_week: 0=Monday, 1=Tuesday, ..., 6=Sunday
        target_date: Date for data (YYYYMMDD int or None for today)
        home_team: Home team ID (for Wednesday)
        away_team: Away team ID (for Wednesday)

    Returns:
        Formatted visualization string
    """
    if day_of_week == 0:  # Monday
        return get_monday_viz(target_date)
    elif day_of_week == 1:  # Tuesday
        return get_tuesday_viz(target_date)
    elif day_of_week == 2:  # Wednesday
        if home_team and away_team:
            return get_wednesday_viz(home_team, away_team, target_date)
        else:
            return "*Wednesday visualization requires featured game teams*\n"
    elif day_of_week == 3:  # Thursday
        return get_thursday_viz(target_date)
    elif day_of_week == 4:  # Friday
        return get_friday_viz(target_date)
    elif day_of_week == 5:  # Saturday
        return get_saturday_viz(target_date)
    elif day_of_week == 6:  # Sunday
        return get_sunday_viz(target_date)
    else:
        return "*Invalid day of week*\n"


# Validation Test - Generate visualizations for last 7 days
if __name__ == '__main__':
    print("=" * 80)
    print("NEWSLETTER VISUALIZATION VALIDATION")
    print("Generating visualizations for Nov 18-24, 2025")
    print("=" * 80)

    # Define test dates (Nov 18-24, 2025)
    test_dates = [
        (20251118, 0, "Monday"),
        (20251119, 1, "Tuesday"),
        (20251120, 2, "Wednesday"),
        (20251121, 3, "Thursday"),
        (20251122, 4, "Friday"),
        (20251123, 5, "Saturday"),
        (20251124, 6, "Sunday")
    ]

    for date, day_num, day_name in test_dates:
        print(f"\n{'=' * 80}")
        print(f"{day_name.upper()} - {datetime.strptime(str(date), '%Y%m%d').strftime('%B %d, %Y')}")
        print("=" * 80)

        if day_num == 2:  # Wednesday needs teams
            viz = get_visualization_for_day(day_num, date, 'BOS', 'DET')
        else:
            viz = get_visualization_for_day(day_num, date)

        print(viz)
