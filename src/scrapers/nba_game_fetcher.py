"""
NBA Game Fetcher - Fetch completed games from NBA API
Uses nba_api to retrieve game results and append to nba_games_all.csv
"""

from nba_api.stats.endpoints import leaguegamefinder
from datetime import datetime, timedelta
import pandas as pd
import time

# Team ID mapping from NBA API to our database IDs
NBA_API_TO_DB_ID = {
    1610612737: 1,   # Atlanta Hawks
    1610612738: 2,   # Boston Celtics
    1610612751: 17,  # Brooklyn Nets
    1610612766: 30,  # Charlotte Hornets
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
    1610612763: 29,  # Memphis Grizzlies
    1610612748: 14,  # Miami Heat
    1610612749: 15,  # Milwaukee Bucks
    1610612750: 16,  # Minnesota Timberwolves
    1610612740: 3,   # New Orleans Pelicans
    1610612752: 18,  # New York Knicks
    1610612760: 25,  # Oklahoma City Thunder
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

DB_ID_TO_NAME = {
    1: 'Atlanta Hawks', 2: 'Boston Celtics', 17: 'Brooklyn Nets', 30: 'Charlotte Hornets',
    4: 'Chicago Bulls', 5: 'Cleveland Cavaliers', 6: 'Dallas Mavericks', 7: 'Denver Nuggets',
    8: 'Detroit Pistons', 9: 'Golden State Warriors', 10: 'Houston Rockets', 11: 'Indiana Pacers',
    12: 'Los Angeles Clippers', 13: 'Los Angeles Lakers', 29: 'Memphis Grizzlies', 14: 'Miami Heat',
    15: 'Milwaukee Bucks', 16: 'Minnesota Timberwolves', 3: 'New Orleans Pelicans', 18: 'New York Knicks',
    25: 'Oklahoma City Thunder', 19: 'Orlando Magic', 20: 'Philadelphia 76ers', 21: 'Phoenix Suns',
    22: 'Portland Trail Blazers', 23: 'Sacramento Kings', 24: 'San Antonio Spurs', 28: 'Toronto Raptors',
    26: 'Utah Jazz', 27: 'Washington Wizards'
}


def fetch_games_between_dates(start_date_str, end_date_str):
    """
    Fetch all NBA games between two dates.

    Args:
        start_date_str: Start date in 'YYYY-MM-DD' format
        end_date_str: End date in 'YYYY-MM-DD' format

    Returns:
        List of game dictionaries with our database format
    """
    print(f"\n[NBA API] Fetching games from {start_date_str} to {end_date_str}...")

    try:
        # Use leaguegamefinder to get all games in date range
        game_finder = leaguegamefinder.LeagueGameFinder(
            date_from_nullable=start_date_str,
            date_to_nullable=end_date_str,
            league_id_nullable='00',  # NBA
            season_type_nullable='Regular Season',
            timeout=15  # Fail fast — CDN fallback is reliable
        )

        games_df = game_finder.get_data_frames()[0]

        if len(games_df) == 0:
            print("[NBA API] No games found in date range")
            return []

        print(f"[NBA API] Retrieved {len(games_df)} game records")

        # Group by GAME_ID to get both teams for each game
        games_by_id = {}

        for idx, row in games_df.iterrows():
            game_id = str(row['GAME_ID'])
            team_api_id = row['TEAM_ID']
            team_db_id = NBA_API_TO_DB_ID.get(team_api_id)

            if team_db_id is None:
                continue

            is_home = row['MATCHUP'].find('@') == -1  # No '@' means home game

            if game_id not in games_by_id:
                games_by_id[game_id] = {
                    'game_id': int(game_id),
                    'date': int(row['GAME_DATE'].replace('-', '')),  # YYYYMMDD format
                    'season_type': 'regular'
                }

            if is_home:
                games_by_id[game_id]['home_team_id'] = team_db_id
                games_by_id[game_id]['home_team_name'] = DB_ID_TO_NAME[team_db_id]
                games_by_id[game_id]['home_score'] = row['PTS']
            else:
                games_by_id[game_id]['away_team_id'] = team_db_id
                games_by_id[game_id]['away_team_name'] = DB_ID_TO_NAME[team_db_id]
                games_by_id[game_id]['away_score'] = row['PTS']

        # Filter complete games (have both home and away data)
        complete_games = []
        for game_id, game_data in games_by_id.items():
            if all(key in game_data for key in ['home_team_id', 'away_team_id', 'home_score', 'away_score']):
                # Determine winner
                if game_data['home_score'] > game_data['away_score']:
                    game_data['winner_team_id'] = game_data['home_team_id']
                else:
                    game_data['winner_team_id'] = game_data['away_team_id']

                complete_games.append(game_data)

        print(f"[NBA API] Processed {len(complete_games)} complete games")
        return complete_games

    except Exception as e:
        print(f"[ERROR] NBA API fetch failed: {str(e)}")
        return []


def _confirmed_finals(games):
    """Keep the games ESPN reports as final with an identical score.

    Unverifiable dates (ESPN unreachable) are kept only when at least two days
    old, by which point every game on them has long finished.
    """
    if not games:
        return games
    from src.scrapers.nba_api_data_fetcher import fetch_games_from_espn
    kept = []
    for d in sorted({g['date'] for g in games}):
        day = [g for g in games if g['date'] == d]
        ds = str(d)
        espn = fetch_games_from_espn(f"{ds[:4]}-{ds[4:6]}-{ds[6:]}")
        if not espn:
            old = (datetime.now() - datetime.strptime(ds, '%Y%m%d')).days >= 2
            print(f"[GUARD] ESPN had nothing for {ds}; {'trusting' if old else 'holding'} {len(day)} game(s)")
            if old:
                kept += day
            continue
        finals = {(e['home_id'], e['away_id']): (e['home_score'], e['away_score'])
                  for e in espn if e['game_status_code'] == 3}
        for g in day:
            got = finals.get((g['home_team_id'], g['away_team_id']))
            if got == (g['home_score'], g['away_score']):
                kept.append(g)
            else:
                print(f"[GUARD] holding {g['away_team_name']} at {g['home_team_name']} {ds}: "
                      f"API {g['away_score']}-{g['home_score']}, ESPN final {got}")
    return kept


def fetch_missing_games(csv_path='data/raw/nba_games_all.csv'):
    """
    Fetch games missing from the database.
    Looks at the latest date in CSV and fetches up to today.

    Args:
        csv_path: Path to nba_games_all.csv

    Returns:
        Number of new games added
    """
    print("\n" + "=" * 80)
    print("FETCHING MISSING GAMES FROM NBA API")
    print("=" * 80)

    # Load existing games
    try:
        existing_games = pd.read_csv(csv_path)
        latest_date_int = existing_games['date'].max()
        latest_date = datetime.strptime(str(latest_date_int), '%Y%m%d')
    except Exception as e:
        print(f"[ERROR] Could not read existing games: {e}")
        return 0

    # Calculate date range
    today = datetime.now()
    yesterday = today - timedelta(days=1)  # Fetch up to yesterday (today's games might not be complete)

    # Re-check the latest stored date too. A date can be partly ingested (a late
    # game still running when we fetched); starting the day after would skip its
    # missing games forever. Duplicates are dropped below on (date, home, away).
    start_date = latest_date

    if start_date > yesterday:
        print(f"\n[OK] Database is up to date (latest: {latest_date.strftime('%Y-%m-%d')})")
        return 0

    print(f"\nLatest game in database: {latest_date.strftime('%Y-%m-%d')}")
    print(f"Fetching games from: {start_date.strftime('%Y-%m-%d')} to {yesterday.strftime('%Y-%m-%d')}")
    print(f"Gap: {(yesterday - latest_date).days} days\n")

    # Fetch new games
    new_games = fetch_games_between_dates(
        start_date.strftime('%Y-%m-%d'),
        yesterday.strftime('%Y-%m-%d')
    )

    # Only games ESPN confirms as finished, with the same score. The stats API has
    # returned games still in progress as complete, with stale partial scores
    # (2026-11-18 00:20 ET: CHA-LAL 34-30 and UTA-LAC 58-62 were stored as finals,
    # graded, and fed into the ratings).
    new_games = _confirmed_finals(new_games)

    # Already stored? Identity is (date, home, away): our rows carry ids from more
    # than one source, so game_id alone cannot detect a duplicate.
    have = set(zip(existing_games['date'], existing_games['home_team_id'], existing_games['away_team_id']))
    new_games = [g for g in new_games if (g['date'], g['home_team_id'], g['away_team_id']) not in have]

    if len(new_games) == 0:
        print("\n[OK] No new games to add")
        return 0

    # Convert to DataFrame
    new_games_df = pd.DataFrame(new_games)

    # Ensure column order matches existing
    column_order = list(existing_games.columns)
    new_games_df = new_games_df[column_order]

    # Append to existing
    updated_games = pd.concat([existing_games, new_games_df], ignore_index=True)

    # Remove duplicates based on game_id
    updated_games = updated_games.drop_duplicates(subset=['game_id'], keep='first')

    # Sort by date
    updated_games = updated_games.sort_values('date')

    # Save
    updated_games.to_csv(csv_path, index=False)

    print(f"\n[OK] Added {len(new_games)} new games")
    print(f"[OK] Total games in database: {len(updated_games)}")
    print(f"[OK] Saved to {csv_path}")

    return len(new_games)


if __name__ == '__main__':
    # Test fetching
    num_added = fetch_missing_games()
    print(f"\nFetch complete: {num_added} games added")
