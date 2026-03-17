"""
Fetch Missing Games from NBA CDN (Jan 13 - Mar 7, 2026)
=========================================================
One-time recovery script using the NBA CDN schedule fallback.
The official stats.nba.com API is unreliable; the CDN schedule
has full scores for all completed games.

Usage:
    python scripts/fetch_missing_from_cdn.py [--start YYYY-MM-DD] [--end YYYY-MM-DD]
"""

import sys, os, argparse
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import requests
import pandas as pd
from datetime import datetime, timedelta

# ── Team ID mapping: NBA API teamId → our DB ID ──────────────────────────────
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
    1610612746: 12,  # Los Angeles Clippers
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
    1: 'Atlanta Hawks', 2: 'Boston Celtics', 3: 'New Orleans Pelicans', 4: 'Chicago Bulls',
    5: 'Cleveland Cavaliers', 6: 'Dallas Mavericks', 7: 'Denver Nuggets', 8: 'Detroit Pistons',
    9: 'Golden State Warriors', 10: 'Houston Rockets', 11: 'Indiana Pacers',
    12: 'Los Angeles Clippers', 13: 'Los Angeles Lakers', 14: 'Miami Heat',
    15: 'Milwaukee Bucks', 16: 'Minnesota Timberwolves', 17: 'Brooklyn Nets',
    18: 'New York Knicks', 19: 'Orlando Magic', 20: 'Philadelphia 76ers',
    21: 'Phoenix Suns', 22: 'Portland Trail Blazers', 23: 'Sacramento Kings',
    24: 'San Antonio Spurs', 25: 'Oklahoma City Thunder', 26: 'Utah Jazz',
    27: 'Washington Wizards', 28: 'Toronto Raptors', 29: 'Memphis Grizzlies',
    30: 'Charlotte Hornets',
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', default='2026-01-13', help='Start date YYYY-MM-DD')
    parser.add_argument('--end', default='2026-03-07', help='End date YYYY-MM-DD (inclusive)')
    parser.add_argument('--dry-run', action='store_true', help='Print results without writing')
    return parser.parse_args()


def fetch_cdn_schedule():
    url = 'https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json'
    print(f"[CDN] Fetching full schedule from NBA CDN...")
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.json().get('leagueSchedule', {}).get('gameDates', [])


def extract_completed_games(game_dates, start_str, end_str):
    """Extract completed games (gameStatus=3) within the date range."""
    start = datetime.strptime(start_str, '%Y-%m-%d').date()
    end = datetime.strptime(end_str, '%Y-%m-%d').date()

    results = []
    skipped = 0

    for gd in game_dates:
        raw_date = gd.get('gameDate', '')
        # CDN format: 'MM/DD/YYYY HH:MM:SS'
        try:
            game_date = datetime.strptime(raw_date.split(' ')[0], '%m/%d/%Y').date()
        except ValueError:
            continue

        if not (start <= game_date <= end):
            continue

        for game in gd.get('games', []):
            if game.get('gameStatus') != 3:  # 3 = Final
                continue

            home = game.get('homeTeam', {})
            away = game.get('awayTeam', {})

            home_nba_id = home.get('teamId', 0)
            away_nba_id = away.get('teamId', 0)
            home_db_id = NBA_API_TO_DB_ID.get(home_nba_id)
            away_db_id = NBA_API_TO_DB_ID.get(away_nba_id)

            if home_db_id is None or away_db_id is None:
                skipped += 1
                continue

            home_score = home.get('score', 0) or 0
            away_score = away.get('score', 0) or 0

            if home_score == 0 and away_score == 0:
                skipped += 1
                continue

            winner_id = home_db_id if home_score > away_score else away_db_id
            date_int = int(game_date.strftime('%Y%m%d'))
            game_id = game.get('gameId', f"{date_int}_{home_db_id}_{away_db_id}")

            results.append({
                'game_id': game_id,
                'date': date_int,
                'home_team_id': home_db_id,
                'home_team_name': DB_ID_TO_NAME.get(home_db_id, home.get('teamName', '')),
                'away_team_id': away_db_id,
                'away_team_name': DB_ID_TO_NAME.get(away_db_id, away.get('teamName', '')),
                'home_score': int(home_score),
                'away_score': int(away_score),
                'winner_team_id': float(winner_id),
                'season_type': 'regular',
            })

    print(f"[CDN] Extracted {len(results)} completed games, skipped {skipped} (unmapped teams or no score)")
    return results


def main():
    args = parse_args()
    print("=" * 70)
    print(f" NBA CDN Missing Game Recovery: {args.start} -> {args.end}")
    print("=" * 70)

    # Load existing data
    games_path = 'data/raw/nba_games_all.csv'
    existing = pd.read_csv(games_path)
    existing_ids = set(existing['game_id'].astype(str))
    print(f"[CSV] Existing games: {len(existing)} | Latest: {existing['date'].max()}")

    # Fetch from CDN
    game_dates = fetch_cdn_schedule()
    new_games = extract_completed_games(game_dates, args.start, args.end)

    if not new_games:
        print("[WARN] No completed games found in range. Nothing to add.")
        return

    # Deduplicate against existing
    new_df = pd.DataFrame(new_games)
    new_df['game_id'] = new_df['game_id'].astype(str)
    truly_new = new_df[~new_df['game_id'].isin(existing_ids)]
    dupes = len(new_df) - len(truly_new)

    print(f"[DEDUP] {len(new_df)} fetched, {dupes} already in CSV, {len(truly_new)} new to add")

    if len(truly_new) == 0:
        print("[OK] All fetched games already in database. Nothing to add.")
        return

    if args.dry_run:
        print("\n[DRY RUN] Would add these games:")
        print(truly_new[['date', 'home_team_name', 'away_team_name', 'home_score', 'away_score']].to_string())
        return

    # Append and sort
    updated = pd.concat([existing, truly_new], ignore_index=True)
    updated = updated.sort_values('date').reset_index(drop=True)
    updated.to_csv(games_path, index=False)

    print(f"\n[OK] Added {len(truly_new)} games. New total: {len(updated)}")
    print(f"[OK] Date range now: {updated['date'].min()} -> {updated['date'].max()}")

    # Quick validation
    print("\n[VALIDATION]")
    print(f"  No NaN in home_score: {updated['home_score'].notna().all()}")
    print(f"  No NaN in away_score: {updated['away_score'].notna().all()}")
    print(f"  Score range plausible: {(updated['home_score'] > 50).mean():.1%} home, {(updated['away_score'] > 50).mean():.1%} away")


if __name__ == '__main__':
    main()
