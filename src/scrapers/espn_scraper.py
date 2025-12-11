"""
ESPN Data Scraper for NBA Schedule and Injury Reports
Fetches real-time game schedules and injury data from ESPN.com
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time

# Team name mappings from ESPN to our database
ESPN_TO_DB_TEAMS = {
    'Atlanta Hawks': 'Atlanta Hawks',
    'Boston Celtics': 'Boston Celtics',
    'Brooklyn Nets': 'Brooklyn Nets',
    'Charlotte Hornets': 'Charlotte Hornets',
    'Chicago Bulls': 'Chicago Bulls',
    'Cleveland Cavaliers': 'Cleveland Cavaliers',
    'Dallas Mavericks': 'Dallas Mavericks',
    'Denver Nuggets': 'Denver Nuggets',
    'Detroit Pistons': 'Detroit Pistons',
    'Golden State Warriors': 'Golden State Warriors',
    'Houston Rockets': 'Houston Rockets',
    'Indiana Pacers': 'Indiana Pacers',
    'LA Clippers': 'Los Angeles Clippers',
    'Los Angeles Lakers': 'Los Angeles Lakers',
    'Memphis Grizzlies': 'Memphis Grizzlies',
    'Miami Heat': 'Miami Heat',
    'Milwaukee Bucks': 'Milwaukee Bucks',
    'Minnesota Timberwolves': 'Minnesota Timberwolves',
    'New Orleans Pelicans': 'New Orleans Pelicans',
    'New York Knicks': 'New York Knicks',
    'Oklahoma City Thunder': 'Oklahoma City Thunder',
    'Orlando Magic': 'Orlando Magic',
    'Philadelphia 76ers': 'Philadelphia 76ers',
    'Phoenix Suns': 'Phoenix Suns',
    'Portland Trail Blazers': 'Portland Trail Blazers',
    'Sacramento Kings': 'Sacramento Kings',
    'San Antonio Spurs': 'San Antonio Spurs',
    'Toronto Raptors': 'Toronto Raptors',
    'Utah Jazz': 'Utah Jazz',
    'Washington Wizards': 'Washington Wizards'
}

# Short abbreviations used in ESPN URLs
ESPN_ABBREV = {
    'atl': 'Atlanta Hawks', 'bos': 'Boston Celtics', 'bkn': 'Brooklyn Nets',
    'cha': 'Charlotte Hornets', 'chi': 'Chicago Bulls', 'cle': 'Cleveland Cavaliers',
    'dal': 'Dallas Mavericks', 'den': 'Denver Nuggets', 'det': 'Detroit Pistons',
    'gs': 'Golden State Warriors', 'hou': 'Houston Rockets', 'ind': 'Indiana Pacers',
    'lac': 'LA Clippers', 'lal': 'Los Angeles Lakers', 'mem': 'Memphis Grizzlies',
    'mia': 'Miami Heat', 'mil': 'Milwaukee Bucks', 'min': 'Minnesota Timberwolves',
    'no': 'New Orleans Pelicans', 'ny': 'New York Knicks', 'okc': 'Oklahoma City Thunder',
    'orl': 'Orlando Magic', 'phi': 'Philadelphia 76ers', 'phx': 'Phoenix Suns',
    'por': 'Portland Trail Blazers', 'sac': 'Sacramento Kings', 'sa': 'San Antonio Spurs',
    'tor': 'Toronto Raptors', 'utah': 'Utah Jazz', 'wsh': 'Washington Wizards'
}


def get_todays_schedule(date_str=None):
    """
    Scrape ESPN for today's NBA schedule.

    Args:
        date_str: Optional date string in YYYY-MM-DD format. Uses today if not provided.

    Returns:
        List of game dictionaries with home_team, away_team, time, status, etc.
    """
    if date_str:
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
        url = f"https://www.espn.com/nba/schedule/_/date/{target_date.strftime('%Y%m%d')}"
    else:
        url = "https://www.espn.com/nba/schedule"

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        games = []

        # Find all game rows in the schedule table
        game_rows = soup.find_all('tr', class_=lambda x: x and 'Table__TR' in x)

        for row in game_rows:
            try:
                # Extract team links
                team_links = row.find_all('a', href=lambda x: x and '/nba/team/' in x)
                if len(team_links) < 2:
                    continue

                # Extract team names from links
                away_team_link = team_links[0]['href']
                home_team_link = team_links[1]['href']

                # Parse team abbreviations from URL
                away_abbrev = away_team_link.split('/name/')[1].split('/')[0] if '/name/' in away_team_link else None
                home_abbrev = home_team_link.split('/name/')[1].split('/')[0] if '/name/' in home_team_link else None

                if not away_abbrev or not home_abbrev:
                    continue

                away_team = ESPN_ABBREV.get(away_abbrev, team_links[0].text.strip())
                home_team = ESPN_ABBREV.get(home_abbrev, team_links[1].text.strip())

                # Extract time/status
                time_cell = row.find('td', class_=lambda x: x and 'date__col' in x)
                game_time = time_cell.text.strip() if time_cell else 'TBD'

                # Check if game is live
                status = 'Scheduled'
                if 'LIVE' in game_time.upper() or 'PM' not in game_time:
                    status = 'Live' if 'LIVE' in game_time.upper() else 'Final'

                # Extract TV channel if available
                tv_cell = row.find('td', class_=lambda x: x and 'tv__col' in x)
                tv_channel = tv_cell.text.strip() if tv_cell else None

                games.append({
                    'home_team': home_team,
                    'away_team': away_team,
                    'time': game_time,
                    'status': status,
                    'tv': tv_channel
                })
            except Exception as e:
                print(f"Error parsing game row: {e}")
                continue

        return games

    except requests.RequestException as e:
        print(f"Error fetching ESPN schedule: {e}")
        return []


def get_injury_report():
    """
    Scrape ESPN for current NBA injury reports.

    Returns:
        Dictionary mapping team names to lists of injured players.
        Each player dict contains: name, position, status, return_date, comment
    """
    url = "https://www.espn.com/nba/injuries"

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        injury_data = {}

        # Find all team title divs
        team_titles = soup.find_all('div', class_='Table__Title')

        for title in team_titles:
            try:
                # Extract team name
                team_name = title.get_text(strip=True)

                # Normalize team name
                team_name = ESPN_TO_DB_TEAMS.get(team_name, team_name)

                # Find the next ResponsiveTable after this title
                next_table = title.find_next('div', class_='ResponsiveTable')
                if not next_table:
                    continue

                # Find tbody
                tbody = next_table.find('tbody')
                if not tbody:
                    continue

                injuries = []
                rows = tbody.find_all('tr')

                for row in rows:
                    try:
                        cells = row.find_all('td')
                        if len(cells) < 5:
                            continue

                        # Extract player data
                        player_name = cells[0].get_text(strip=True)
                        position = cells[1].get_text(strip=True)
                        return_date = cells[2].get_text(strip=True) if cells[2].get_text(strip=True) else 'Unknown'
                        status = cells[3].get_text(strip=True)
                        comment = cells[4].get_text(strip=True)

                        injuries.append({
                            'name': player_name,
                            'position': position,
                            'return_date': return_date,
                            'status': status,
                            'comment': comment
                        })
                    except Exception as e:
                        print(f"Error parsing injury row: {e}")
                        continue

                if injuries:
                    injury_data[team_name] = injuries

            except Exception as e:
                print(f"Error parsing team section: {e}")
                continue

        return injury_data

    except requests.RequestException as e:
        print(f"Error fetching ESPN injury report: {e}")
        return {}


def get_key_injuries_for_team(team_name, injury_data=None):
    """
    Get key injuries for a specific team (players marked as Out or Questionable).

    Args:
        team_name: Full team name (e.g., "Los Angeles Lakers")
        injury_data: Pre-fetched injury data dict. If None, will fetch fresh data.

    Returns:
        List of injured players for that team
    """
    if injury_data is None:
        injury_data = get_injury_report()

    # Normalize team name
    team_name = ESPN_TO_DB_TEAMS.get(team_name, team_name)

    return injury_data.get(team_name, [])


# Test function
if __name__ == '__main__':
    print("Testing ESPN Scraper...")
    print("=" * 80)

    print("\n--- TODAY'S SCHEDULE ---")
    schedule = get_todays_schedule()
    for game in schedule:
        print(f"{game['away_team']} @ {game['home_team']} - {game['time']} ({game['status']})")
        if game['tv']:
            print(f"  TV: {game['tv']}")

    print(f"\nTotal games: {len(schedule)}")

    print("\n--- INJURY REPORT ---")
    injuries = get_injury_report()
    for team, players in injuries.items():
        print(f"\n{team}:")
        for player in players:
            print(f"  - {player['name']} ({player['position']}): {player['status']} - {player['comment'][:60]}...")

    print(f"\nTotal teams with injuries: {len(injuries)}")
