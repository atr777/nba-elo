"""
NBA API Data Fetcher for Schedule and Player Information
Uses official nba_api library for reliable, structured data
"""

from nba_api.live.nba.endpoints import scoreboard
from nba_api.stats.endpoints import commonplayerinfo, commonteamroster, leaguegamefinder, scoreboardv2
from nba_api.stats.static import teams, players
from datetime import datetime, timedelta
import pandas as pd
import time

# Team ID mapping (NBA API uses 1610612XXX format, we use 1-30)
# Database IDs: 1=Hawks, 2=Celtics, 3=Hornets, 4=Bulls, 5=Cavs, 6=Mavs, 7=Nuggets, 8=Pistons
# 9=Warriors, 10=Rockets, 11=Pacers, 12=Clippers, 13=Lakers, 14=Heat, 15=Bucks, 16=Wolves
# 17=Nets, 18=Knicks, 19=Magic, 20=76ers, 21=Suns, 22=Blazers, 23=Kings, 24=Spurs
# 25=Thunder, 26=Jazz, 27=Wizards, 28=Raptors, 29=Grizzlies, 30=Charlotte (current)
NBA_API_TO_DB_ID = {
    1610612737: 1,   # Atlanta Hawks
    1610612738: 2,   # Boston Celtics
    1610612751: 17,  # Brooklyn Nets (was New Jersey Nets, DB ID 17)
    1610612766: 30,  # Charlotte Hornets (current, DB ID 30)
    1610612741: 4,   # Chicago Bulls
    1610612739: 5,   # Cleveland Cavaliers
    1610612742: 6,   # Dallas Mavericks
    1610612743: 7,   # Denver Nuggets
    1610612765: 8,   # Detroit Pistons
    1610612744: 9,   # Golden State Warriors
    1610612745: 10,  # Houston Rockets
    1610612754: 11,  # Indiana Pacers
    1610612746: 12,  # LA Clippers
    1610612747: 13,  # Los Angeles Lakers
    1610612763: 29,  # Memphis Grizzlies (was Vancouver, DB ID 29)
    1610612748: 14,  # Miami Heat
    1610612749: 15,  # Milwaukee Bucks
    1610612750: 16,  # Minnesota Timberwolves
    1610612740: 3,   # New Orleans Pelicans (was Hornets, DB ID 3)
    1610612752: 18,  # New York Knicks
    1610612760: 25,  # Oklahoma City Thunder (was Seattle, DB ID 25)
    1610612753: 19,  # Orlando Magic
    1610612755: 20,  # Philadelphia 76ers
    1610612756: 21,  # Phoenix Suns
    1610612757: 22,  # Portland Trail Blazers
    1610612758: 23,  # Sacramento Kings
    1610612759: 24,  # San Antonio Spurs
    1610612761: 28,  # Toronto Raptors
    1610612762: 26,  # Utah Jazz
    1610612764: 27,  # Washington Wizards
}


def fetch_games_from_nba_cdn(date_str):
    """
    Fallback: Fetch games from NBA CDN schedule when API doesn't have data.

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        List of game dictionaries or empty list if unavailable
    """
    try:
        import requests

        url = 'https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json'
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return []

        data = response.json()
        game_dates = data.get('leagueSchedule', {}).get('gameDates', [])

        # Convert YYYY-MM-DD to MM/DD/YYYY for matching
        target_date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        target_date_cdn = target_date_obj.strftime('%m/%d/%Y')

        # Find matching date
        for game_date in game_dates:
            gd = game_date.get('gameDate', '')
            if gd.startswith(target_date_cdn):
                games = game_date.get('games', [])

                # Convert to our format
                result_games = []
                for game in games:
                    home_team = game.get('homeTeam', {})
                    away_team = game.get('awayTeam', {})

                    result_games.append({
                        'gameId': game.get('gameId', ''),
                        'gameStatus': 1,  # Scheduled
                        'gameStatusText': game.get('gameStatusText', 'Scheduled'),
                        'gameCode': f"{target_date_obj.strftime('%Y%m%d')}/{away_team.get('teamTricode', '')}{home_team.get('teamTricode', '')}",
                        'homeTeam': {
                            'teamId': home_team.get('teamId', 0),
                            'teamCity': home_team.get('teamCity', ''),
                            'teamName': home_team.get('teamName', ''),
                            'teamTricode': home_team.get('teamTricode', '')
                        },
                        'awayTeam': {
                            'teamId': away_team.get('teamId', 0),
                            'teamCity': away_team.get('teamCity', ''),
                            'teamName': away_team.get('teamName', ''),
                            'teamTricode': away_team.get('teamTricode', '')
                        },
                        'gameTimeUTC': game.get('gameTimeUTC', ''),
                        'gameEt': game.get('gameEt', '')
                    })

                return result_games

        return []

    except Exception as e:
        print(f"[WARNING] NBA CDN fallback failed: {e}")
        return []


def get_todays_games(date_str=None):
    """
    Fetch today's NBA schedule using the official NBA API.

    Args:
        date_str: Optional date string in YYYY-MM-DD format. Uses today if not provided.

    Returns:
        List of game dictionaries with home_team, away_team, time, status, home_id, away_id
    """
    import time
    from nba_api.stats.endpoints import scoreboardv2

    # Determine if we're requesting today or a future/past date
    if date_str:
        target_date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    else:
        target_date_obj = datetime.now()

    today = datetime.now().date()
    target = target_date_obj.date()

    # Calculate days difference
    days_diff = (target - today).days

    # For today or tomorrow, use live scoreboard (has next-day schedule)
    # For dates 2+ days away or in the past, use scoreboardv2
    if -1 <= days_diff <= 1:
        # Retry logic for NBA API connection issues
        max_retries = 3
        retry_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                # Use live scoreboard API for today/tomorrow (has near-future schedule)
                board = scoreboard.ScoreBoard()
                games_data = board.games.get_dict()
                break  # Success, exit retry loop
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"[WARNING] NBA API connection failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                    print(f"[INFO] Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    # Final attempt failed, re-raise the exception
                    raise
    else:
        # Use scoreboardv2 for dates 2+ days in future or past dates
        game_date_formatted = target_date_obj.strftime('%m/%d/%Y')
        board = scoreboardv2.ScoreboardV2(game_date=game_date_formatted)

        # scoreboardv2 returns DataFrames, get the GameHeader frame
        games_df = board.get_data_frames()[0]

        # Get team data for name mapping
        all_teams = teams.get_teams()
        team_map = {t['id']: t for t in all_teams}

        # Convert DataFrame to list of dicts to match live API format
        games_data = []
        for _, row in games_df.iterrows():
            home_team_id = row['HOME_TEAM_ID']
            away_team_id = row['VISITOR_TEAM_ID']

            # Get team info
            home_team_info = team_map.get(home_team_id, {})
            away_team_info = team_map.get(away_team_id, {})

            # Map scoreboardv2 fields to live API format
            games_data.append({
                'gameId': row['GAME_ID'],
                'gameStatus': row['GAME_STATUS_ID'],  # 1=scheduled, 2=live, 3=final
                'gameStatusText': row['GAME_STATUS_TEXT'],
                'homeTeam': {
                    'teamId': home_team_id,
                    'teamCity': home_team_info.get('city', ''),
                    'teamName': home_team_info.get('nickname', '')
                },
                'awayTeam': {
                    'teamId': away_team_id,
                    'teamCity': away_team_info.get('city', ''),
                    'teamName': away_team_info.get('nickname', '')
                },
                'gameTimeUTC': row['GAME_DATE_EST'],  # This is EST time in scoreboardv2
                'gameEt': row['GAME_DATE_EST']
            })

    try:
        from pytz import timezone

        # Determine target date
        if date_str:
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
        else:
            target_date = datetime.now()

        target_date_str = target_date.strftime('%Y%m%d')

        # Eastern timezone for NBA games
        eastern = timezone('US/Eastern')

        games = []
        for game in games_data:
            # gameStatus: 1=scheduled, 2=live, 3=final
            game_status = game.get('gameStatus', 0)

            # Include all games: scheduled (1), live (2), and final (3)

            # Filter by date using appropriate method for each API
            # Live API: use gameCode (format: YYYYMMDD/AWYHOME)
            # scoreboardv2 API: use gameTimeUTC converted to ET
            game_code = game.get('gameCode', '')
            if game_code and '/' in game_code:
                # Live API format: "20251210/PHXOKC"
                game_date_str = game_code.split('/')[0]
            else:
                # scoreboardv2 API: parse time and convert to ET
                game_time_utc = game.get('gameTimeUTC', '')
                if game_time_utc:
                    # Parse UTC time - handle both formats (with and without 'Z')
                    try:
                        # Try format with 'Z' (live API)
                        game_date_obj_utc = datetime.strptime(game_time_utc, '%Y-%m-%dT%H:%M:%SZ')
                        # Convert to Eastern time for date comparison
                        game_date_obj_utc = game_date_obj_utc.replace(tzinfo=timezone('UTC'))
                        game_date_obj_et = game_date_obj_utc.astimezone(eastern)
                    except ValueError:
                        # Try format without 'Z' (scoreboardv2 API)
                        game_date_obj_et = datetime.strptime(game_time_utc, '%Y-%m-%dT%H:%M:%S')
                        # scoreboardv2 GAME_DATE_EST is already in ET, just parse it
                        game_date_obj_et = game_date_obj_et.replace(tzinfo=eastern)

                    game_date_str = game_date_obj_et.strftime('%Y%m%d')
                else:
                    # No date info available, skip
                    continue

            # Only include games from target date
            if game_date_str != target_date_str:
                continue

            # Get team info
            home_team_data = game.get('homeTeam', {})
            away_team_data = game.get('awayTeam', {})

            home_team_id_nba = home_team_data.get('teamId')
            away_team_id_nba = away_team_data.get('teamId')

            # Convert to our database format (1-30)
            home_id = NBA_API_TO_DB_ID.get(home_team_id_nba, None)
            away_id = NBA_API_TO_DB_ID.get(away_team_id_nba, None)

            if home_id is None or away_id is None:
                continue

            # Build team names
            home_team = f"{home_team_data.get('teamCity', '')} {home_team_data.get('teamName', '')}".strip()
            away_team = f"{away_team_data.get('teamCity', '')} {away_team_data.get('teamName', '')}".strip()

            # Parse game time from gameEt (Eastern Time) or use gameStatusText
            game_et = game.get('gameEt', '')
            game_status_text = game.get('gameStatusText', '')

            # Live games always use the clock/quarter text (e.g. "Q4 4:54")
            # Final games use 'Final'; scheduled games parse the scheduled time
            if game_status == 2:
                time_str = game_status_text if game_status_text else 'LIVE'
            elif game_status == 3:
                time_str = 'Final'
            elif game_status_text and ('pm et' in game_status_text.lower() or 'am et' in game_status_text.lower()):
                time_str = game_status_text
            elif game_et:
                try:
                    game_time_obj = datetime.strptime(game_et, '%Y-%m-%dT%H:%M:%SZ')
                    time_str = game_time_obj.strftime('%I:%M %p ET')
                except ValueError:
                    try:
                        game_time_obj = datetime.strptime(game_et, '%Y-%m-%dT%H:%M:%S')
                        time_str = game_time_obj.strftime('%I:%M %p ET')
                    except:
                        time_str = 'TBD'
            else:
                time_str = 'TBD'

            # Determine game status text
            if game_status == 1:
                status_text = 'Scheduled'
            elif game_status == 2:
                status_text = game_status_text if game_status_text else 'LIVE'
            else:
                status_text = 'Final'

            games.append({
                'home_team': home_team,
                'away_team': away_team,
                'home_id': home_id,
                'away_id': away_id,
                'time': time_str,
                'status': status_text,
                'game_status_code': game_status,
                'game_id': game.get('gameId', '')
            })

        # If no games found, try CDN fallback
        if len(games) == 0:
            # Use provided date or today's date
            fallback_date = date_str if date_str else target_date.strftime('%Y-%m-%d')
            print(f"[INFO] No games found from API for {fallback_date}, trying NBA CDN fallback...")
            cdn_games = fetch_games_from_nba_cdn(fallback_date)

            if len(cdn_games) > 0:
                print(f"[SUCCESS] Found {len(cdn_games)} games from NBA CDN")
                # Re-process CDN games through the same filtering logic
                games_data = cdn_games
                games = []

                for game in games_data:
                    game_code = game.get('gameCode', '')
                    if game_code and '/' in game_code:
                        game_date_str = game_code.split('/')[0]

                        if game_date_str != target_date_str:
                            continue

                        home_team_data = game.get('homeTeam', {})
                        away_team_data = game.get('awayTeam', {})

                        home_team_id_nba = home_team_data.get('teamId')
                        away_team_id_nba = away_team_data.get('teamId')

                        home_team_id = NBA_API_TO_DB_ID.get(home_team_id_nba, home_team_id_nba)
                        away_team_id = NBA_API_TO_DB_ID.get(away_team_id_nba, away_team_id_nba)

                        home_team = f"{home_team_data.get('teamCity', '')} {home_team_data.get('teamName', '')}".strip()
                        away_team = f"{away_team_data.get('teamCity', '')} {away_team_data.get('teamName', '')}".strip()

                        # Use gameStatusText which contains the ET time (e.g., "8:00 pm ET")
                        time_str = game.get('gameStatusText', 'TBD')

                        games.append({
                            'home_team': home_team,
                            'away_team': away_team,
                            'time': time_str,
                            'home_id': home_team_id,
                            'away_id': away_team_id,
                            'status': 'Scheduled',
                            'game_status_code': 1,
                            'game_id': game.get('gameId', '')
                        })

        return games

    except Exception as e:
        print(f"Error fetching NBA schedule: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_team_roster(team_name):
    """
    Get current roster for a team.

    Args:
        team_name: Full team name (e.g., "Los Angeles Lakers")

    Returns:
        List of player dictionaries with player_id, name, position
    """
    try:
        # Find team ID
        all_teams = teams.get_teams()
        team_dict = next((t for t in all_teams if t['full_name'] == team_name), None)

        if not team_dict:
            print(f"Team not found: {team_name}")
            return []

        team_id = team_dict['id']

        # Get roster
        roster = commonteamroster.CommonTeamRoster(team_id=team_id)
        roster_df = roster.common_team_roster.get_data_frame()

        players_list = []
        for _, row in roster_df.iterrows():
            players_list.append({
                'player_id': row['PLAYER_ID'],
                'name': row['PLAYER'],
                'position': row['POSITION'],
                'number': row['NUM']
            })

        return players_list

    except Exception as e:
        print(f"Error fetching roster for {team_name}: {e}")
        return []


def build_player_to_team_mapping():
    """
    Build a mapping of all active players to their current teams.

    Returns:
        DataFrame with columns: player_id, player_name, team_name, position
    """
    try:
        all_teams = teams.get_teams()
        player_team_map = []

        for team in all_teams:
            team_name = team['full_name']
            print(f"Fetching roster for {team_name}...")

            roster = get_team_roster(team_name)
            for player in roster:
                player_team_map.append({
                    'player_id': player['player_id'],
                    'player_name': player['name'],
                    'team_name': team_name,
                    'position': player['position'],
                    'team_id': NBA_API_TO_DB_ID.get(team['id'], None)
                })

            # Rate limiting to avoid overwhelming the API
            time.sleep(0.6)

        return pd.DataFrame(player_team_map)

    except Exception as e:
        print(f"Error building player-team mapping: {e}")
        return pd.DataFrame()


def get_injury_status_for_game(game_id):
    """
    Get injury status for players in a specific game.

    FUTURE ENHANCEMENT: This function is not currently implemented.
    NBA API doesn't provide injury reports directly.

    Implementation options:
    1. Scrape ESPN injury report page (https://www.espn.com/nba/injuries)
    2. Use RapidAPI NBA Injury Report endpoint (requires paid subscription)
    3. Parse official NBA.com injury/inactive list (requires auth)

    Current workaround: Manual injury updates can be provided through
    the injury impact analysis in export_substack_premium.py

    Args:
        game_id: NBA game ID

    Returns:
        Dictionary with team names as keys, injured players as values
        Currently returns empty dict (no data available)
    """
    # Not implemented - return empty dict
    return {}


# Test function
if __name__ == '__main__':
    print("Testing NBA API Data Fetcher...")
    print("=" * 80)

    print("\n--- TODAY'S SCHEDULE ---")
    schedule = get_todays_games()
    print(f"Found {len(schedule)} games:\n")

    for game in schedule:
        print(f"{game['away_team']} (ID: {game['away_id']}) @ {game['home_team']} (ID: {game['home_id']})")
        print(f"  Time: {game['time']}")
        print(f"  Status: {game['status']}")
        print()

    if schedule:
        print("\n--- TESTING ROSTER FETCH ---")
        # Test with first game's home team
        test_team = schedule[0]['home_team']
        print(f"Fetching roster for {test_team}...")
        roster = get_team_roster(test_team)
        print(f"Found {len(roster)} players:\n")
        for player in roster[:5]:  # Show first 5
            print(f"  - {player['name']} ({player['position']})")

    print("\n--- BUILDING PLAYER-TEAM MAPPING ---")
    print("This will take ~30 seconds due to API rate limiting...")
    mapping = build_player_to_team_mapping()

    if not mapping.empty:
        print(f"\nMapping complete! {len(mapping)} players found")

        # Save to file (do this first to avoid Unicode errors)
        output_path = 'data/exports/player_team_mapping.csv'
        mapping.to_csv(output_path, index=False, encoding='utf-8')
        print(f"\nSaved to: {output_path}")

        print("\nSample data (first 10 players):")
        try:
            print(mapping.head(10).to_string())
        except UnicodeEncodeError:
            # Fallback for Windows console
            print("(Sample data contains special characters - check the CSV file)")
