"""
Weekly Validation — Roster Refresh + Data Freshness Check
==========================================================
Runs every Sunday 9AM ET via VPS cron.

What it does:
  1. Refreshes player_team_mapping.csv from live NBA API rosters
  2. Detects player trades/team changes since last refresh
  3. Writes data/exports/DATA_FRESHNESS.md with file freshness status,
     detected trades, and any data quality warnings

Usage:
    python scripts/weekly_validation.py [--dry-run]

Logs to: logs/weekly_validation.log
"""

import sys
import os
import argparse
import time
import logging
from datetime import datetime, timezone

# Project root is one level up from scripts/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

import pandas as pd
from nba_api.stats.endpoints import commonteamroster
from nba_api.stats.static import teams as nba_teams_static

# ---------------------------------------------------------------------------
# Constants (reused from update_rosters_2025_26.py)
# ---------------------------------------------------------------------------

SEASON = '2025-26'

MAPPING_PATH = os.path.join(PROJECT_ROOT, 'data', 'exports', 'player_team_mapping.csv')
FRESHNESS_PATH = os.path.join(PROJECT_ROOT, 'data', 'exports', 'DATA_FRESHNESS.md')
LOG_PATH = os.path.join(PROJECT_ROOT, 'logs', 'weekly_validation.log')

KEY_FILES = {
    'nba_games_all.csv':              os.path.join(PROJECT_ROOT, 'data', 'raw', 'nba_games_all.csv'),
    'player_boxscores_all.csv':       os.path.join(PROJECT_ROOT, 'data', 'raw', 'player_boxscores_all.csv'),
    'prediction_tracking.csv':        os.path.join(PROJECT_ROOT, 'data', 'exports', 'prediction_tracking.csv'),
    'player_ratings_bpm_adjusted.csv':os.path.join(PROJECT_ROOT, 'data', 'exports', 'player_ratings_bpm_adjusted.csv'),
    'player_team_mapping.csv':        MAPPING_PATH,
    'team_elo_history_phase_1_6.csv': os.path.join(PROJECT_ROOT, 'data', 'exports', 'team_elo_history_phase_1_6.csv'),
}

# Files older than this many days get a WARNING in the freshness report
FRESHNESS_WARNING_DAYS = 3

# NBA API team_id -> (db_id, full_team_name)
NBA_API_TO_DB = {
    1610612737: (1,  'Atlanta Hawks'),
    1610612738: (2,  'Boston Celtics'),
    1610612751: (17, 'Brooklyn Nets'),
    1610612766: (30, 'Charlotte Hornets'),
    1610612741: (4,  'Chicago Bulls'),
    1610612739: (5,  'Cleveland Cavaliers'),
    1610612742: (6,  'Dallas Mavericks'),
    1610612743: (7,  'Denver Nuggets'),
    1610612765: (8,  'Detroit Pistons'),
    1610612744: (9,  'Golden State Warriors'),
    1610612745: (10, 'Houston Rockets'),
    1610612754: (11, 'Indiana Pacers'),
    1610612746: (12, 'Los Angeles Clippers'),
    1610612747: (13, 'Los Angeles Lakers'),
    1610612763: (29, 'Memphis Grizzlies'),
    1610612748: (14, 'Miami Heat'),
    1610612749: (15, 'Milwaukee Bucks'),
    1610612750: (16, 'Minnesota Timberwolves'),
    1610612740: (3,  'New Orleans Pelicans'),
    1610612752: (18, 'New York Knicks'),
    1610612760: (25, 'Oklahoma City Thunder'),
    1610612753: (19, 'Orlando Magic'),
    1610612755: (20, 'Philadelphia 76ers'),
    1610612756: (21, 'Phoenix Suns'),
    1610612757: (22, 'Portland Trail Blazers'),
    1610612758: (23, 'Sacramento Kings'),
    1610612759: (24, 'San Antonio Spurs'),
    1610612761: (28, 'Toronto Raptors'),
    1610612762: (26, 'Utah Jazz'),
    1610612764: (27, 'Washington Wizards'),
}

POSITION_MAP = {
    'G': 'G', 'F': 'F', 'C': 'C',
    'G-F': 'G', 'F-G': 'F', 'F-C': 'F', 'C-F': 'C',
}

# 3-letter abbreviations that may appear in the existing player_team_mapping.csv.
# The new mapping always uses full team names (from NBA_API_TO_DB).
# This table lets us normalise old entries before comparing for trades.
ABBREV_TO_FULL = {
    'ATL': 'Atlanta Hawks',       'BOS': 'Boston Celtics',
    'BKN': 'Brooklyn Nets',       'CHA': 'Charlotte Hornets',
    'CHI': 'Chicago Bulls',       'CLE': 'Cleveland Cavaliers',
    'DAL': 'Dallas Mavericks',    'DEN': 'Denver Nuggets',
    'DET': 'Detroit Pistons',     'GSW': 'Golden State Warriors',
    'HOU': 'Houston Rockets',     'IND': 'Indiana Pacers',
    'LAC': 'Los Angeles Clippers','LAL': 'Los Angeles Lakers',
    'MEM': 'Memphis Grizzlies',   'MIA': 'Miami Heat',
    'MIL': 'Milwaukee Bucks',     'MIN': 'Minnesota Timberwolves',
    'NOP': 'New Orleans Pelicans','NYK': 'New York Knicks',
    'OKC': 'Oklahoma City Thunder','ORL': 'Orlando Magic',
    'PHI': 'Philadelphia 76ers',  'PHX': 'Phoenix Suns',
    'POR': 'Portland Trail Blazers','SAC': 'Sacramento Kings',
    'SAS': 'San Antonio Spurs',   'TOR': 'Toronto Raptors',
    'UTA': 'Utah Jazz',           'WAS': 'Washington Wizards',
}


def normalize_team_name(name):
    """Expand a 3-letter abbreviation to the canonical full team name, if needed."""
    if isinstance(name, str) and len(name) <= 3:
        return ABBREV_TO_FULL.get(name.upper(), name)
    return name

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging():
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    fmt = logging.Formatter('%(asctime)s  %(levelname)s  %(message)s')

    file_handler = logging.FileHandler(LOG_PATH, encoding='utf-8')
    file_handler.setFormatter(fmt)

    # On Windows the default stdout encoding is cp1252 which cannot represent
    # many NBA player names with accented characters.  Reconfigure stdout to
    # UTF-8 so logging never crashes on those names.
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Roster fetching (reused from update_rosters_2025_26.py)
# ---------------------------------------------------------------------------

def fetch_team_roster(nba_team_id, team_name, max_retries=3):
    """Fetch roster from NBA API with retry logic. Returns DataFrame or None."""
    for attempt in range(max_retries):
        try:
            time.sleep(1.0 + attempt * 0.5)   # 1 req/sec baseline; back off on retries
            roster = commonteamroster.CommonTeamRoster(team_id=nba_team_id, season=SEASON)
            df = roster.get_data_frames()[0]
            return df
        except Exception as exc:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                log.warning("  Retry %d/%d for %s (sleeping %ds): %s",
                            attempt + 1, max_retries - 1, team_name, wait, exc)
                time.sleep(wait)
            else:
                log.error("  FAILED %s after %d attempts: %s", team_name, max_retries, exc)
                return None


def build_roster_from_boxscores(team_db_id, team_name):
    """
    Fallback: infer current roster from most recent boxscore appearances.
    Mirrors the logic in update_rosters_2025_26.py.
    """
    try:
        bs = pd.read_csv(
            os.path.join(PROJECT_ROOT, 'data', 'raw', 'player_boxscores_all.csv'),
            usecols=['game_id', 'player_id', 'player_name', 'team_id', 'team_name'],
        )
        games = pd.read_csv(
            os.path.join(PROJECT_ROOT, 'data', 'raw', 'nba_games_all.csv'),
            usecols=['game_id', 'date'],
        )
        games['game_id'] = games['game_id'].astype(str)
        bs['game_id'] = bs['game_id'].astype(str)
        merged = bs.merge(games, on='game_id').copy()
        merged['date'] = pd.to_numeric(merged['date'], errors='coerce')

        szn = merged[merged['date'] >= 20251001]
        team_games = szn[szn['team_name'] == team_name]
        if len(team_games) == 0:
            log.warning("  [FALLBACK] No 2025-26 boxscore rows for %s", team_name)
            return []

        latest_date = team_games['date'].max()
        cutoff = latest_date - 30000   # roughly last 30 days of games
        recent = team_games[team_games['date'] >= cutoff]
        players = recent[['player_id', 'player_name']].drop_duplicates()

        rows = []
        for _, row in players.iterrows():
            rows.append({
                'player_id': row['player_id'],
                'player_name': row['player_name'],
                'team_id': team_db_id,
                'team_name': team_name,
                'position': 'F',   # no position data in fallback
            })
        log.info("  [FALLBACK] %d players for %s from boxscores", len(rows), team_name)
        return rows
    except Exception as exc:
        log.error("  [FALLBACK] Failed for %s: %s", team_name, exc)
        return []

# ---------------------------------------------------------------------------
# Roster refresh
# ---------------------------------------------------------------------------

def refresh_rosters(dry_run=False):
    """
    Fetch all 30 team rosters, detect trades vs. old mapping, save new mapping.

    Returns:
        new_df      — DataFrame of the refreshed mapping
        trades      — list of (player, old_team, new_team)
        new_players — list of player names not in old mapping
        removed     — list of player names no longer on any roster
        failed_teams — list of team names that fell back to boxscores
    """
    log.info("=" * 70)
    log.info(" Roster Refresh — %s Season", SEASON)
    log.info("=" * 70)

    # Load existing mapping before overwriting (for trade detection)
    if os.path.exists(MAPPING_PATH):
        old_mapping = pd.read_csv(MAPPING_PATH)
        log.info("Old mapping: %d players, %d teams",
                 len(old_mapping), old_mapping['team_name'].nunique())
    else:
        log.warning("No existing mapping found at %s — treating as fresh start", MAPPING_PATH)
        old_mapping = pd.DataFrame(columns=['player_name', 'team_name'])

    all_teams = nba_teams_static.get_teams()
    new_rows = []
    failed_teams = []

    for i, team in enumerate(all_teams, 1):
        nba_id = team['id']
        if nba_id not in NBA_API_TO_DB:
            log.warning("Unknown team id %s — skipping", nba_id)
            continue
        db_id, db_name = NBA_API_TO_DB[nba_id]
        log.info("[%2d/30] %s...", i, db_name)

        roster_df = fetch_team_roster(nba_id, db_name)
        if roster_df is not None and len(roster_df) > 0:
            for _, row in roster_df.iterrows():
                pos_raw = str(row.get('POSITION', 'F')).strip()
                pos = POSITION_MAP.get(pos_raw, 'F')
                new_rows.append({
                    'player_id':   row.get('PLAYER_ID', ''),
                    'player_name': row.get('PLAYER', ''),
                    'team_id':     db_id,
                    'team_name':   db_name,
                    'position':    pos,
                })
            log.info("       OK: %d players", len(roster_df))
        else:
            failed_teams.append(db_name)
            fallback = build_roster_from_boxscores(db_id, db_name)
            new_rows.extend(fallback)

    new_df = pd.DataFrame(new_rows)
    log.info("\nNew mapping: %d players, %d teams", len(new_df), new_df['team_name'].nunique())

    if failed_teams:
        log.warning("WARNING: %d teams used boxscore fallback: %s",
                    len(failed_teams), failed_teams)

    # ------------------------------------------------------------------
    # Trade / roster-change detection
    # ------------------------------------------------------------------
    # Use player_name as the key (consistent with the 2-column mapping).
    # Normalize old team names: the pre-existing mapping may contain 3-letter
    # abbreviations (e.g. "OKC") while the new mapping always uses full names
    # (e.g. "Oklahoma City Thunder").  Comparing without normalization would
    # produce hundreds of false-positive "trades".
    old_map = {}
    if 'player_name' in old_mapping.columns and 'team_name' in old_mapping.columns:
        old_map = {
            player: normalize_team_name(team)
            for player, team in zip(old_mapping['player_name'], old_mapping['team_name'])
        }

    new_map = dict(zip(new_df['player_name'], new_df['team_name']))

    trades = [
        (p, old_map[p], new_map[p])
        for p in new_map
        if p in old_map and old_map[p] != new_map[p]
    ]
    new_players = [p for p in new_map if p not in old_map]
    removed     = [p for p in old_map if p not in new_map]

    log.info("\n--- Change summary ---")
    log.info("  Team changes (trades/moves): %d", len(trades))
    for player, old_team, new_team in sorted(trades):
        log.info("    %s: %s -> %s", player, old_team, new_team)
    log.info("  New players (roster additions): %d", len(new_players))
    for p in sorted(new_players)[:20]:
        log.info("    + %s", p)
    if len(new_players) > 20:
        log.info("    ... and %d more", len(new_players) - 20)
    log.info("  Removed players (waived/retired): %d", len(removed))
    for p in sorted(removed)[:20]:
        log.info("    - %s", p)
    if len(removed) > 20:
        log.info("    ... and %d more", len(removed) - 20)

    if dry_run:
        log.info("\n[DRY RUN] No files written.")
        return new_df, trades, new_players, removed, failed_teams

    # ------------------------------------------------------------------
    # Save refreshed mapping (no backup suffix needed — DATA_FRESHNESS.md
    # documents every run; a dated backup is written for audit trail)
    # ------------------------------------------------------------------
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = MAPPING_PATH + f'.backup_{timestamp}'
    if os.path.exists(MAPPING_PATH):
        old_mapping.to_csv(backup_path, index=False)
        log.info("Backup saved: %s", backup_path)

    # Save with the standard 2-column format (player_name, team_name)
    # plus extra columns so the file is richer than the old version.
    new_df.to_csv(MAPPING_PATH, index=False)
    log.info("[OK] Saved %d entries to %s", len(new_df), MAPPING_PATH)

    return new_df, trades, new_players, removed, failed_teams

# ---------------------------------------------------------------------------
# Data freshness check
# ---------------------------------------------------------------------------

def check_file_freshness(run_ts):
    """
    For each key file, return a dict with:
        name, path, exists, size_mb, last_modified, age_days, status
    """
    now = run_ts.timestamp()
    results = []
    for name, path in KEY_FILES.items():
        if not os.path.exists(path):
            results.append({
                'name':          name,
                'path':          path,
                'exists':        False,
                'size_mb':       None,
                'last_modified': None,
                'age_days':      None,
                'status':        'MISSING',
            })
            continue

        stat = os.stat(path)
        size_mb = stat.st_size / (1024 * 1024)
        mtime = stat.st_mtime
        age_days = (now - mtime) / 86400
        last_modified = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        status = 'WARNING' if age_days > FRESHNESS_WARNING_DAYS else 'OK'

        results.append({
            'name':          name,
            'path':          path,
            'exists':        True,
            'size_mb':       round(size_mb, 2),
            'last_modified': last_modified,
            'age_days':      round(age_days, 1),
            'status':        status,
        })
        log.info("  %-45s  %6.1f days  %s", name, age_days, status)

    return results

# ---------------------------------------------------------------------------
# DATA_FRESHNESS.md writer
# ---------------------------------------------------------------------------

def write_freshness_report(run_ts, freshness_rows, trades, new_players,
                           removed, failed_teams, dry_run=False):
    """Write the markdown freshness report to data/exports/DATA_FRESHNESS.md."""

    warnings = [r for r in freshness_rows if r['status'] in ('WARNING', 'MISSING')]

    lines = []
    lines.append("# NBA_ELO Data Freshness Report")
    lines.append("")
    lines.append(f"**Generated:** {run_ts.strftime('%Y-%m-%d %H:%M:%S')} (local time)")
    lines.append(f"**Script:** `scripts/weekly_validation.py`")
    lines.append(f"**Season:** {SEASON}")
    lines.append("")

    # ------------------------------------------------------------------
    # Executive summary
    # ------------------------------------------------------------------
    overall_status = "WARNING" if warnings else "OK"
    lines.append(f"**Overall Status:** {overall_status}")
    lines.append("")

    # ------------------------------------------------------------------
    # File freshness table
    # ------------------------------------------------------------------
    lines.append("## Key Data File Freshness")
    lines.append("")
    lines.append("| File | Last Modified | Age (days) | Size (MB) | Status |")
    lines.append("|------|--------------|------------|-----------|--------|")

    for r in freshness_rows:
        if not r['exists']:
            lines.append(f"| `{r['name']}` | — | — | — | MISSING |")
        else:
            status_badge = f"**{r['status']}**" if r['status'] != 'OK' else r['status']
            lines.append(
                f"| `{r['name']}` | {r['last_modified']} "
                f"| {r['age_days']} "
                f"| {r['size_mb']} "
                f"| {status_badge} |"
            )
    lines.append("")

    # ------------------------------------------------------------------
    # Roster / trade changes
    # ------------------------------------------------------------------
    lines.append("## Roster Changes Detected This Run")
    lines.append("")
    lines.append(f"- **Team changes (trades/moves):** {len(trades)}")
    lines.append(f"- **New players (additions):** {len(new_players)}")
    lines.append(f"- **Removed players (waived/retired):** {len(removed)}")
    lines.append("")

    if trades:
        lines.append("### Players Who Changed Teams")
        lines.append("")
        lines.append("| Player | Old Team | New Team |")
        lines.append("|--------|----------|----------|")
        for player, old_team, new_team in sorted(trades):
            lines.append(f"| {player} | {old_team} | {new_team} |")
        lines.append("")
    else:
        lines.append("_No team changes detected since last refresh._")
        lines.append("")

    if new_players:
        lines.append("### New Players (Not in Previous Mapping)")
        lines.append("")
        for p in sorted(new_players):
            lines.append(f"- {p}")
        lines.append("")

    if removed:
        lines.append("### Removed Players (No Longer on Any Roster)")
        lines.append("")
        for p in sorted(removed):
            lines.append(f"- {p}")
        lines.append("")

    # ------------------------------------------------------------------
    # Warnings section
    # ------------------------------------------------------------------
    lines.append("## Warnings")
    lines.append("")

    if not warnings and not failed_teams:
        lines.append("_No warnings — all files are current._")
        lines.append("")
    else:
        if warnings:
            for r in warnings:
                if r['status'] == 'MISSING':
                    lines.append(f"- **MISSING:** `{r['name']}` not found at `{r['path']}`")
                else:
                    lines.append(
                        f"- **STALE:** `{r['name']}` is {r['age_days']} days old "
                        f"(threshold: {FRESHNESS_WARNING_DAYS} days). "
                        f"Last modified: {r['last_modified']}."
                    )
        if failed_teams:
            lines.append("")
            lines.append(
                f"- **API FALLBACK:** {len(failed_teams)} team(s) could not be fetched "
                f"from NBA API and used boxscore fallback: "
                + ", ".join(failed_teams)
            )
        lines.append("")

    # ------------------------------------------------------------------
    # Validation checklist (mirrors the standard SOP checklist)
    # ------------------------------------------------------------------
    lines.append("## Validation Checklist")
    lines.append("")

    games_row = next((r for r in freshness_rows if r['name'] == 'nba_games_all.csv'), None)
    pt_row    = next((r for r in freshness_rows if r['name'] == 'prediction_tracking.csv'), None)

    def check(condition, label):
        marker = "x" if condition else " "
        return f"- [{marker}] {label}"

    lines.append(check(games_row and games_row['exists'],
                        "nba_games_all.csv exists"))
    lines.append(check(games_row and games_row['exists'] and games_row['age_days'] <= 3,
                        "nba_games_all.csv updated within 3 days"))
    lines.append(check(pt_row and pt_row['exists'],
                        "prediction_tracking.csv exists"))
    lines.append(check(pt_row and pt_row['exists'] and pt_row['age_days'] <= 3,
                        "prediction_tracking.csv updated within 3 days"))
    lines.append(check(True,  # mapping just refreshed
                        "player_team_mapping.csv refreshed this run"))
    lines.append(check(not failed_teams,
                        "All 30 teams fetched from NBA API (no fallback needed)"))
    lines.append("")

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------
    lines.append("---")
    lines.append(f"_Report auto-generated by `scripts/weekly_validation.py` — "
                 f"do not edit manually._")

    content = "\n".join(lines) + "\n"

    if dry_run:
        log.info("\n[DRY RUN] DATA_FRESHNESS.md not written. Preview:\n%s", content)
        return content

    with open(FRESHNESS_PATH, 'w', encoding='utf-8') as fh:
        fh.write(content)
    log.info("[OK] DATA_FRESHNESS.md written to %s", FRESHNESS_PATH)
    return content

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Weekly roster refresh + data freshness check")
    parser.add_argument('--dry-run', action='store_true',
                        help="Fetch data but do not write any files")
    args = parser.parse_args()

    setup_logging()
    run_ts = datetime.now()

    log.info("=" * 70)
    log.info(" NBA_ELO Weekly Validation — %s", run_ts.strftime('%Y-%m-%d %H:%M:%S'))
    log.info("=" * 70)

    # Step 1 — Refresh rosters
    log.info("\n[STEP 1] Refreshing rosters from NBA API...")
    new_df, trades, new_players, removed, failed_teams = refresh_rosters(dry_run=args.dry_run)

    # Step 2 — Data freshness check
    log.info("\n[STEP 2] Checking data file freshness...")
    freshness_rows = check_file_freshness(run_ts)

    # Step 3 — Write DATA_FRESHNESS.md
    log.info("\n[STEP 3] Writing DATA_FRESHNESS.md...")
    write_freshness_report(
        run_ts=run_ts,
        freshness_rows=freshness_rows,
        trades=trades,
        new_players=new_players,
        removed=removed,
        failed_teams=failed_teams,
        dry_run=args.dry_run,
    )

    # Final summary
    log.info("\n" + "=" * 70)
    log.info(" Weekly validation complete.")
    log.info("  Roster entries:  %d", len(new_df))
    log.info("  Trades detected: %d", len(trades))
    log.info("  New players:     %d", len(new_players))
    log.info("  Removed:         %d", len(removed))
    log.info("  Fallback teams:  %d", len(failed_teams))
    warnings_count = sum(1 for r in freshness_rows if r['status'] in ('WARNING', 'MISSING'))
    log.info("  Freshness warns: %d", warnings_count)
    log.info("=" * 70)

    if warnings_count > 0:
        log.warning("ACTION REQUIRED: %d file(s) are stale or missing — "
                    "check DATA_FRESHNESS.md and re-run daily_update.py if needed.",
                    warnings_count)
        sys.exit(1)   # Non-zero exit so cron can alert on failures


if __name__ == '__main__':
    main()
