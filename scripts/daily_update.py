"""
Daily NBA ELO Update Script
Automatically fetches new games, recalculates ELO ratings, and validates accuracy.

Usage:
    python scripts/daily_update.py [--dry-run]
"""

import subprocess
import sys
import os
from datetime import datetime
import pandas as pd

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.utils.file_io import load_csv_to_dataframe

def log(message):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def run_command(cmd, description, timeout=1800):
    """Run a command and log the output.

    Args:
        cmd: Command to run
        description: Description for logging
        timeout: Timeout in seconds (default: 1800 = 30 minutes)
    """
    log(f"Starting: {description}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            log(f"ERROR in {description}:")
            log(result.stderr)
            return False
        log(f"Completed: {description}")
        return True
    except subprocess.TimeoutExpired:
        log(f"TIMEOUT in {description} (exceeded {timeout/60:.1f} minutes)")
        return False
    except Exception as e:
        log(f"EXCEPTION in {description}: {str(e)}")
        return False

def get_data_stats():
    """Get current data statistics."""
    try:
        games = load_csv_to_dataframe('data/raw/nba_games_all.csv')
        team_elo = load_csv_to_dataframe('data/exports/team_elo_history_phase_1_6.csv')
        player_elo = load_csv_to_dataframe('data/exports/player_ratings_bpm_adjusted.csv')

        return {
            'total_games': len(games),
            'latest_game_date': games['date'].max(),
            'teams_tracked': team_elo['team_id'].nunique(),
            'players_tracked': len(player_elo)
        }
    except Exception as e:
        log(f"Error getting stats: {str(e)}")
        return None

def check_for_new_games():
    """Check if there are new games to process."""
    try:
        # Load the raw games data
        games = load_csv_to_dataframe('data/raw/nba_games_all.csv')

        # Load the processed ELO history to find last processed date (Phase 1.6 with enhanced features)
        team_elo = load_csv_to_dataframe('data/exports/team_elo_history_phase_1_6.csv')

        latest_game = pd.to_datetime(games['date'], format='%Y%m%d').max()
        latest_processed = pd.to_datetime(team_elo['date'], format='%Y%m%d').max()

        log(f"Latest game in database: {latest_game.strftime('%Y-%m-%d')}")
        log(f"Latest processed game: {latest_processed.strftime('%Y-%m-%d')}")

        # Check if there's a gap
        if latest_game > latest_processed:
            gap_days = (latest_game - latest_processed).days
            log(f"GAP DETECTED: {gap_days} day(s) of unprocessed games")
            return True
        else:
            log("No new games to process - database is up to date")
            return False

    except Exception as e:
        log(f"Error checking for new games: {str(e)}")
        log("Proceeding with update to be safe...")
        return True  # Default to updating if we can't determine

def main():
    """Main daily update workflow."""
    dry_run = '--dry-run' in sys.argv

    log("="*80)
    log("NBA ELO DAILY UPDATE STARTING")
    log("="*80)

    if dry_run:
        log("DRY RUN MODE - No changes will be made")

    # Get initial stats
    log("\n--- Initial Statistics ---")
    initial_stats = get_data_stats()
    if initial_stats:
        log(f"Total games: {initial_stats['total_games']}")
        log(f"Latest game: {initial_stats['latest_game_date']}")
        log(f"Teams tracked: {initial_stats['teams_tracked']}")
        log(f"Players tracked: {initial_stats['players_tracked']}")

    # Step 1: ALWAYS fetch new games from NBA API first
    log("\n--- Step 1: Fetching New Games from NBA API ---")
    num_new_games_fetched = 0
    if not dry_run:
        try:
            from src.scrapers.nba_game_fetcher import fetch_missing_games
            num_new_games_fetched = fetch_missing_games()
            if num_new_games_fetched > 0:
                log(f"[OK] Fetched {num_new_games_fetched} new games from NBA API")
            else:
                log("[OK] No new games available from NBA API")
        except Exception as e:
            log(f"[ERROR] Game fetch failed: {str(e)}")
            log("Continuing to check if existing games need processing...")
    else:
        log("[DRY RUN] Skipping game fetch")

    # Check if there are unprocessed games (after fetching)
    log("\n--- Checking for Unprocessed Games ---")
    has_new_games = check_for_new_games()

    if not has_new_games and not dry_run:
        log("\n[OK] Database is fully up to date. No processing needed.")
        log("\n" + "="*80)
        log("DAILY UPDATE COMPLETE (NO CHANGES)")
        log("="*80)
        return

    if dry_run:
        log("\nDry run complete. No updates performed.")
        return

    # Use the count of fetched games for boxscore scraping decision
    num_new_games = num_new_games_fetched

    # Step 1.5: Only scrape boxscores if there are NEW games
    if num_new_games > 0:
        log("\n--- Step 1.5: Scraping Boxscores for New Games ONLY ---")
        # CRITICAL FIX: Only process games that don't have boxscores yet
        # The scraper will skip games already in the output file
        success = run_command(
            'python scripts/nba_box_scraper.py --input data/raw/nba_games_all.csv --output data/raw/player_boxscores_all.csv --rate-limit 0.5 --checkpoint 100',
            "Scraping new game data (incremental)"
        )
        if not success:
            log("WARNING: Boxscore scraping had issues. Continuing with existing data...")
    else:
        log("\n[SKIP] No boxscore scraping needed (database up to date)")

    # Step 2: Recalculate team ELO (Phase 1.6 with enhanced features)
    log("\n--- Step 2: Recalculating Team ELO (Enhanced Features) ---")
    success = run_command(
        'python src/engines/team_elo_engine.py --output data/exports/team_elo_history_phase_1_6.csv',
        "Team ELO calculation (Phase 1.6 with form + rest)"
    )
    if not success:
        log("WARNING: Team ELO calculation had issues. Continuing...")

    # Step 3: Recalculate player ELO
    log("\n--- Step 3: Recalculating Player ELO ---")
    success = run_command(
        'python src/engines/player_elo_engine.py --metric bpm --output-ratings data/exports/player_ratings_bpm_adjusted.csv --output-history data/exports/player_elo_history_bpm.csv',
        "Player ELO calculation (BPM)"
    )
    if not success:
        log("WARNING: Player ELO calculation had issues. Continuing...")

    # Step 4: Track predictions for recent games
    log("\n--- Step 4: Tracking Recent Predictions ---")
    success = run_command(
        'python scripts/auto_track_predictions.py --days-back 7',
        "Auto-tracking predictions for last 7 days"
    )
    if not success:
        log("WARNING: Prediction tracking had issues. Continuing...")

    # Get final stats
    log("\n--- Final Statistics ---")
    final_stats = get_data_stats()
    if final_stats and initial_stats:
        new_games = final_stats['total_games'] - initial_stats['total_games']
        log(f"New games added: {new_games}")
        log(f"Total games: {final_stats['total_games']}")
        log(f"Latest game: {final_stats['latest_game_date']}")
        log(f"Players tracked: {final_stats['players_tracked']}")

    log("\n" + "="*80)
    log("DAILY UPDATE COMPLETE")
    log("="*80)

if __name__ == '__main__':
    main()
