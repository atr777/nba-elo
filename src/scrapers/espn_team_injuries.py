"""
ESPN Team Injury Scraper - JSON Extraction Approach
Scrapes individual team injury pages like: https://www.espn.com/nba/team/injuries/_/name/hou
Extracts injury data from embedded JSON in the page source.
"""

import requests
import json
import time
from datetime import datetime, timedelta

# Cache for injury data (refreshes every 4 hours)
_injury_cache = {
    'data': None,
    'last_updated': None
}
CACHE_DURATION_HOURS = 4

# ESPN team abbreviations to our team names
ESPN_TEAM_ABBREVS = {
    'atl': 'Atlanta Hawks',
    'bos': 'Boston Celtics',
    'bkn': 'Brooklyn Nets',
    'cha': 'Charlotte Hornets',
    'chi': 'Chicago Bulls',
    'cle': 'Cleveland Cavaliers',
    'dal': 'Dallas Mavericks',
    'den': 'Denver Nuggets',
    'det': 'Detroit Pistons',
    'gs': 'Golden State Warriors',
    'hou': 'Houston Rockets',
    'ind': 'Indiana Pacers',
    'lac': 'Los Angeles Clippers',
    'lal': 'Los Angeles Lakers',
    'mem': 'Memphis Grizzlies',
    'mia': 'Miami Heat',
    'mil': 'Milwaukee Bucks',
    'min': 'Minnesota Timberwolves',
    'no': 'New Orleans Pelicans',
    'ny': 'New York Knicks',
    'okc': 'Oklahoma City Thunder',
    'orl': 'Orlando Magic',
    'phi': 'Philadelphia 76ers',
    'phx': 'Phoenix Suns',
    'por': 'Portland Trail Blazers',
    'sac': 'Sacramento Kings',
    'sa': 'San Antonio Spurs',
    'tor': 'Toronto Raptors',
    'utah': 'Utah Jazz',
    'wsh': 'Washington Wizards'
}


def scrape_team_injuries(team_abbrev):
    """
    Scrape injuries for a single team using embedded JSON extraction.

    Args:
        team_abbrev: ESPN team abbreviation (e.g., 'hou' for Houston)

    Returns:
        List of injury dicts with keys: name, position, date, status, comment
    """
    url = f"https://www.espn.com/nba/team/injuries/_/name/{team_abbrev}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        text = response.text

        # Find the "injuries":[ JSON structure embedded in the page
        pattern = '"injuries":['
        idx = text.find(pattern)

        if idx == -1:
            # No injuries found (team might have zero injuries)
            return []

        # Extract the JSON array using bracket counting
        start = idx + len('"injuries":')

        bracket_count = 0
        in_string = False
        escape_next = False

        for i in range(start, min(start + 50000, len(text))):
            char = text[i]

            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if char == '"':
                in_string = not in_string
                continue

            if not in_string:
                if char == '[' or char == '{':
                    bracket_count += 1
                elif char == ']' or char == '}':
                    bracket_count -= 1

                    if bracket_count == 0:
                        end = i + 1
                        json_str = text[start:end]

                        # Parse the JSON
                        injuries_data = json.loads(json_str)

                        # Extract injury information
                        all_injuries = []

                        for date_group in injuries_data:
                            date = date_group.get('date', 'Unknown')
                            items = date_group.get('items', [])

                            for item in items:
                                athlete = item.get('athlete', {})
                                name = athlete.get('name', 'Unknown')
                                position = athlete.get('position', 'N/A')
                                status_type = item.get('type', {})
                                status = status_type.get('description', 'Unknown')
                                description = item.get('description', 'No details')

                                all_injuries.append({
                                    'name': name,
                                    'position': position,
                                    'date': date,
                                    'status': status,
                                    'comment': description
                                })

                        return all_injuries

        # If we couldn't parse the JSON, return empty
        return []

    except Exception as e:
        print(f"Error scraping {team_abbrev}: {str(e)}")
        return []


def get_all_injuries(force_refresh=False):
    """
    Scrape injuries for all NBA teams with caching.

    Args:
        force_refresh: If True, bypass cache and fetch fresh data

    Returns:
        Dict mapping team name -> list of injury dicts
    """
    global _injury_cache

    # Check if cache is valid
    if not force_refresh and _injury_cache['data'] is not None:
        if _injury_cache['last_updated'] is not None:
            cache_age = datetime.now() - _injury_cache['last_updated']
            if cache_age < timedelta(hours=CACHE_DURATION_HOURS):
                print(f"[CACHE] Using cached injury data (age: {cache_age})")
                return _injury_cache['data']

    # Cache is stale or doesn't exist - fetch fresh data
    print(f"[FETCH] Scraping fresh injury data for all 30 teams...")
    all_injuries = {}

    for abbrev, team_name in ESPN_TEAM_ABBREVS.items():
        print(f"  Scraping {team_name} ({abbrev})...")
        injuries = scrape_team_injuries(abbrev)

        if injuries:
            all_injuries[team_name] = injuries
            print(f"    Found {len(injuries)} injured players")

        time.sleep(0.5)  # Rate limiting

    # Update cache
    _injury_cache['data'] = all_injuries
    _injury_cache['last_updated'] = datetime.now()

    print(f"[CACHE] Cached {len(all_injuries)} teams with injuries")
    return all_injuries


# Alias for compatibility with existing code
get_injury_report = get_all_injuries


if __name__ == '__main__':
    print("=" * 80)
    print("ESPN TEAM INJURY SCRAPER - DIRECT APPROACH")
    print("=" * 80)

    injuries = get_all_injuries()

    print(f"\n{'=' * 80}")
    print(f"SUMMARY: Found injuries for {len(injuries)} teams")
    print(f"{'=' * 80}")

    # Sample output
    if 'Houston Rockets' in injuries:
        print(f"\nHouston Rockets injuries:")
        for inj in injuries['Houston Rockets']:
            print(f"  - {inj['name']} ({inj['position']}): {inj['status']}")
