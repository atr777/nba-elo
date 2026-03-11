"""
NBA Box Score Scraper - Production Version with Parallel Processing
===================================================================
Scrape player-level box score data from ESPN API for Phase 3 Player ELO

FEATURES:
    - PARALLEL PROCESSING: 8 workers for 4-5x faster scraping
    - Thread-safe progress tracking and checkpointing
    - Handles rate limiting per worker
    - Comprehensive error logging
    - Resume capability for failed runs

USAGE:
    python nba_box_scraper.py --input nba_games_all.csv --output player_boxscores_all.csv
    python nba_box_scraper.py --input games.csv --output boxscores.csv --workers 8
    python nba_box_scraper.py --input games.csv --workers 1  # Serial mode (legacy)
"""

import requests
import pandas as pd
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('box_scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class NBABoxScraper:
    """Scrape player box scores from ESPN API with parallel processing"""

    def __init__(self, rate_limit_delay=0.5, retry_attempts=3, workers=8):
        """
        Initialize scraper

        Args:
            rate_limit_delay: Seconds to wait between requests per worker
            retry_attempts: Number of retry attempts for failed requests
            workers: Number of parallel workers (default: 8, set to 1 for serial)
        """
        self.base_url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary"
        self.rate_limit_delay = rate_limit_delay
        self.retry_attempts = retry_attempts
        self.workers = workers
        self.session = requests.Session()

        # Thread-safe tracking
        self.lock = threading.Lock()
        self.progress_count = 0
        self.all_players = []
        self.failed_games = []

    def fetch_boxscore(self, game_id):
        """
        Fetch boxscore for a single game

        Args:
            game_id: ESPN game ID

        Returns:
            List of player dictionaries or None on failure
        """
        params = {'event': game_id}

        for attempt in range(self.retry_attempts):
            try:
                response = self.session.get(
                    self.base_url,
                    params=params,
                    timeout=15
                )

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_boxscore(data, game_id)
                elif response.status_code == 404:
                    logger.warning(f"Game {game_id}: Not found (404)")
                    return None
                else:
                    logger.warning(f"Game {game_id}: Status {response.status_code}")
                    if attempt < self.retry_attempts - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff

            except requests.exceptions.RequestException as e:
                logger.warning(f"Game {game_id} attempt {attempt + 1}: {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(2 ** attempt)

        logger.error(f"Game {game_id}: All retry attempts failed")
        return None

    def _parse_boxscore(self, data, game_id):
        """
        Parse ESPN API response to extract player data INCLUDING FULL STATS

        Args:
            data: JSON response from ESPN API
            game_id: Game ID for reference

        Returns:
            List of player dictionaries with complete box score stats
        """
        players = []

        try:
            if 'boxscore' not in data or 'players' not in data['boxscore']:
                logger.warning(f"Game {game_id}: No boxscore data")
                return None

            for team_data in data['boxscore']['players']:
                team_id = team_data.get('team', {}).get('id', '')
                team_name = team_data.get('team', {}).get('displayName', '')

                for player_stats in team_data.get('statistics', []):
                    # Get stat labels (column headers)
                    labels = player_stats.get('labels', [])

                    for athlete in player_stats.get('athletes', []):
                        athlete_info = athlete.get('athlete', {})
                        stats_list = athlete.get('stats', [])

                        # Create base player record
                        player_record = {
                            'game_id': game_id,
                            'player_id': athlete_info.get('id', ''),
                            'player_name': athlete_info.get('displayName', ''),
                            'team_id': team_id,
                            'team_name': team_name,
                            'starter': athlete.get('starter', False),
                            'position': athlete_info.get('position', {}).get('abbreviation', ''),
                            'jersey': athlete_info.get('jersey', ''),
                            'didNotPlay': athlete.get('didNotPlay', False)
                        }

                        # Parse all stats using labels
                        for i, label in enumerate(labels):
                            stat_value = stats_list[i] if i < len(stats_list) else ''

                            if label == 'MIN':
                                player_record['minutes'] = self._parse_minutes(stat_value)
                            elif label == 'PTS':
                                player_record['points'] = self._parse_int(stat_value)
                            elif label == 'FG':
                                fg_made, fg_att = self._parse_made_attempted(stat_value)
                                player_record['fg_made'] = fg_made
                                player_record['fg_attempted'] = fg_att
                            elif label == '3PT':
                                fg3_made, fg3_att = self._parse_made_attempted(stat_value)
                                player_record['fg3_made'] = fg3_made
                                player_record['fg3_attempted'] = fg3_att
                            elif label == 'FT':
                                ft_made, ft_att = self._parse_made_attempted(stat_value)
                                player_record['ft_made'] = ft_made
                                player_record['ft_attempted'] = ft_att
                            elif label == 'REB':
                                player_record['rebounds'] = self._parse_int(stat_value)
                            elif label == 'OREB':
                                player_record['offensive_rebounds'] = self._parse_int(stat_value)
                            elif label == 'DREB':
                                player_record['defensive_rebounds'] = self._parse_int(stat_value)
                            elif label == 'AST':
                                player_record['assists'] = self._parse_int(stat_value)
                            elif label == 'STL':
                                player_record['steals'] = self._parse_int(stat_value)
                            elif label == 'BLK':
                                player_record['blocks'] = self._parse_int(stat_value)
                            elif label == 'TO':
                                player_record['turnovers'] = self._parse_int(stat_value)
                            elif label == 'PF':
                                player_record['fouls'] = self._parse_int(stat_value)
                            elif label == '+/-':
                                player_record['plus_minus'] = self._parse_int(stat_value)

                        players.append(player_record)

        except Exception as e:
            logger.error(f"Game {game_id}: Parse error - {e}")
            return None

        return players

    def _parse_minutes(self, minutes_str):
        """Parse minutes (MM:SS or MM format) to float"""
        try:
            if not minutes_str or minutes_str == '--':
                return 0.0
            if ':' in minutes_str:
                parts = minutes_str.split(':')
                return int(parts[0]) + int(parts[1]) / 60.0
            else:
                return float(minutes_str)
        except ValueError:
            return 0.0

    def _parse_int(self, value_str):
        """Parse integer value, handling '--' and empty strings"""
        try:
            if not value_str or value_str == '--':
                return 0
            return int(value_str)
        except ValueError:
            return 0

    def _parse_made_attempted(self, value_str):
        """
        Parse 'made-attempted' format (e.g., '6-18' for field goals)

        Returns:
            Tuple of (made, attempted)
        """
        try:
            if not value_str or value_str == '--':
                return (0, 0)
            parts = value_str.split('-')
            if len(parts) == 2:
                return (int(parts[0]), int(parts[1]))
            return (0, 0)
        except ValueError:
            return (0, 0)

    def _process_game_wrapper(self, game_id):
        """
        Wrapper for processing a single game (thread-safe)

        Args:
            game_id: Game ID to process

        Returns:
            Tuple of (success, game_id, players)
        """
        # Rate limiting per worker
        time.sleep(self.rate_limit_delay)

        # Fetch boxscore
        players = self.fetch_boxscore(game_id)

        # Update progress (thread-safe)
        with self.lock:
            self.progress_count += 1

            if players:
                self.all_players.extend(players)
                success = True
            else:
                self.failed_games.append(game_id)
                success = False

        return (success, game_id, len(players) if players else 0)

    def scrape_season_parallel(self, game_ids, output_file, checkpoint_interval=100):
        """
        Scrape box scores for a list of game IDs using parallel workers

        Args:
            game_ids: List of ESPN game IDs
            output_file: Path to save results
            checkpoint_interval: Save progress every N games
        """
        logger.info(f"Starting PARALLEL scrape with {self.workers} workers")
        logger.info(f"Total games: {len(game_ids)}")
        logger.info(f"Output file: {output_file}")

        # Reset progress tracking
        self.progress_count = 0
        self.all_players = []
        self.failed_games = []

        # Check for existing progress
        output_path = Path(output_file)
        if output_path.exists():
            logger.info(f"Found existing output file, loading...")
            existing_df = pd.read_csv(output_file, low_memory=False)
            completed_games = set(existing_df['game_id'].unique())
            logger.info(f"Already completed: {len(completed_games)} games")
            game_ids = [gid for gid in game_ids if gid not in completed_games]
            logger.info(f"Remaining to scrape: {len(game_ids)} games")
            self.all_players.extend(existing_df.to_dict('records'))

        if len(game_ids) == 0:
            logger.info("No games to scrape!")
            return pd.DataFrame(self.all_players)

        start_time = time.time()
        total_games = len(game_ids)
        last_checkpoint = 0

        # Parallel processing with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            # Submit all tasks
            future_to_game = {
                executor.submit(self._process_game_wrapper, game_id): game_id
                for game_id in game_ids
            }

            # Process completed tasks as they finish
            for future in as_completed(future_to_game):
                game_id = future_to_game[future]

                try:
                    success, gid, player_count = future.result()

                    # Progress logging (every 10 games)
                    if self.progress_count % 10 == 0:
                        elapsed = time.time() - start_time
                        rate = self.progress_count / elapsed if elapsed > 0 else 0
                        remaining = (total_games - self.progress_count) / rate if rate > 0 else 0
                        logger.info(
                            f"Progress: {self.progress_count}/{total_games} "
                            f"({self.progress_count/total_games*100:.1f}%) - "
                            f"Rate: {rate:.1f} games/sec - "
                            f"ETA: {remaining/60:.1f} min"
                        )

                    # Checkpoint save
                    if self.progress_count - last_checkpoint >= checkpoint_interval:
                        with self.lock:
                            self._save_checkpoint(self.all_players, output_file)
                            logger.info(f"Checkpoint saved: {len(self.all_players)} records")
                            last_checkpoint = self.progress_count

                except Exception as e:
                    logger.error(f"Error processing game {game_id}: {e}")
                    with self.lock:
                        self.failed_games.append(game_id)

        # Final save
        self._save_checkpoint(self.all_players, output_file)

        # Summary
        elapsed = time.time() - start_time
        logger.info(f"\n{'='*70}")
        logger.info(f"SCRAPING COMPLETE")
        logger.info(f"{'='*70}")
        logger.info(f"Total games attempted: {total_games}")
        logger.info(f"Successful: {total_games - len(self.failed_games)}")
        logger.info(f"Failed: {len(self.failed_games)}")
        logger.info(f"Total player records: {len(self.all_players)}")
        logger.info(f"Time elapsed: {elapsed/60:.1f} minutes")
        logger.info(f"Average rate: {total_games/elapsed:.1f} games/sec")
        logger.info(f"Output saved to: {output_file}")

        if self.failed_games:
            failed_file = output_path.parent / 'failed_game_ids.txt'
            with open(failed_file, 'w') as f:
                f.write('\n'.join(map(str, self.failed_games)))
            logger.info(f"Failed game IDs saved to: {failed_file}")

        return pd.DataFrame(self.all_players)

    def scrape_season_serial(self, game_ids, output_file, checkpoint_interval=100):
        """
        Legacy serial scraping method (for compatibility)

        Args:
            game_ids: List of ESPN game IDs
            output_file: Path to save results
            checkpoint_interval: Save progress every N games
        """
        logger.info(f"Starting SERIAL scrape (1 worker)")
        logger.info(f"Total games: {len(game_ids)}")
        logger.info(f"Output file: {output_file}")

        all_players = []
        failed_games = []

        # Check for existing progress
        output_path = Path(output_file)
        if output_path.exists():
            logger.info(f"Found existing output file, loading...")
            existing_df = pd.read_csv(output_file, low_memory=False)
            completed_games = set(existing_df['game_id'].unique())
            logger.info(f"Already completed: {len(completed_games)} games")
            game_ids = [gid for gid in game_ids if gid not in completed_games]
            logger.info(f"Remaining to scrape: {len(game_ids)} games")
            all_players.extend(existing_df.to_dict('records'))

        start_time = time.time()

        for i, game_id in enumerate(game_ids, 1):
            # Progress logging
            if i % 10 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                remaining = (len(game_ids) - i) / rate if rate > 0 else 0
                logger.info(
                    f"Progress: {i}/{len(game_ids)} "
                    f"({i/len(game_ids)*100:.1f}%) - "
                    f"Rate: {rate:.1f} games/sec - "
                    f"ETA: {remaining/60:.1f} min"
                )

            # Fetch boxscore
            players = self.fetch_boxscore(game_id)

            if players:
                all_players.extend(players)
                logger.debug(f"Game {game_id}: {len(players)} players")
            else:
                failed_games.append(game_id)

            # Checkpoint save
            if i % checkpoint_interval == 0:
                self._save_checkpoint(all_players, output_file)
                logger.info(f"Checkpoint saved: {len(all_players)} records")

            # Rate limiting
            time.sleep(self.rate_limit_delay)

        # Final save
        self._save_checkpoint(all_players, output_file)

        # Summary
        elapsed = time.time() - start_time
        logger.info(f"\n{'='*70}")
        logger.info(f"SCRAPING COMPLETE")
        logger.info(f"{'='*70}")
        logger.info(f"Total games attempted: {len(game_ids)}")
        logger.info(f"Successful: {len(game_ids) - len(failed_games)}")
        logger.info(f"Failed: {len(failed_games)}")
        logger.info(f"Total player records: {len(all_players)}")
        logger.info(f"Time elapsed: {elapsed/60:.1f} minutes")
        logger.info(f"Output saved to: {output_file}")

        if failed_games:
            failed_file = output_path.parent / 'failed_game_ids.txt'
            with open(failed_file, 'w') as f:
                f.write('\n'.join(map(str, failed_games)))
            logger.info(f"Failed game IDs saved to: {failed_file}")

        return pd.DataFrame(all_players)

    def _save_checkpoint(self, players, output_file):
        """Save progress to CSV (thread-safe when called with lock)"""
        if players:
            df = pd.DataFrame(players)
            df.to_csv(output_file, index=False)


def load_game_ids(games_file):
    """Load game IDs from the games CSV"""
    try:
        df = pd.read_csv(games_file)

        # Find game_id column
        game_id_col = None
        for col in ['game_id', 'gameId', 'id', 'Game_ID']:
            if col in df.columns:
                game_id_col = col
                break

        if game_id_col is None:
            raise ValueError("Could not find game_id column in CSV")

        # Sort by date for chronological processing
        if 'date' in df.columns:
            df = df.sort_values('date')

        game_ids = df[game_id_col].unique().tolist()
        logger.info(f"Loaded {len(game_ids)} unique game IDs from {games_file}")

        return game_ids

    except Exception as e:
        logger.error(f"Failed to load game IDs: {e}")
        sys.exit(1)


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(
        description='Scrape NBA player box scores from ESPN API (Parallel Processing)'
    )
    parser.add_argument(
        '--input',
        required=True,
        help='Input CSV file with game IDs (e.g., nba_games_all.csv)'
    )
    parser.add_argument(
        '--output',
        default='player_boxscores_all.csv',
        help='Output CSV file for player data'
    )
    parser.add_argument(
        '--rate-limit',
        type=float,
        default=0.5,
        help='Delay between requests per worker in seconds (default: 0.5)'
    )
    parser.add_argument(
        '--checkpoint',
        type=int,
        default=100,
        help='Save progress every N games (default: 100)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=8,
        help='Number of parallel workers (default: 8, use 1 for serial)'
    )

    args = parser.parse_args()

    # Load game IDs
    game_ids = load_game_ids(args.input)

    # Initialize scraper
    scraper = NBABoxScraper(
        rate_limit_delay=args.rate_limit,
        workers=args.workers
    )

    # Run scraping (parallel or serial based on workers)
    if args.workers > 1:
        df = scraper.scrape_season_parallel(
            game_ids,
            args.output,
            checkpoint_interval=args.checkpoint
        )
    else:
        df = scraper.scrape_season_serial(
            game_ids,
            args.output,
            checkpoint_interval=args.checkpoint
        )

    # Final statistics
    if not df.empty:
        logger.info(f"\n{'='*70}")
        logger.info(f"FINAL STATISTICS")
        logger.info(f"{'='*70}")
        logger.info(f"Total player records: {len(df)}")
        logger.info(f"Unique players: {df['player_id'].nunique()}")
        logger.info(f"Unique teams: {df['team_id'].nunique()}")
        logger.info(f"Unique games: {df['game_id'].nunique()}")
        logger.info(f"Average minutes per player: {pd.to_numeric(df['minutes'], errors='coerce').mean():.1f}")
        logger.info(f"Total starters: {df['starter'].sum()}")
        logger.info(f"\n[OK] Box score scraping complete!")


if __name__ == "__main__":
    main()
