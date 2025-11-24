"""
NBA Box Score Scraper - Production Version
==========================================
Scrape player-level box score data from ESPN API for Phase 3 Player ELO

USAGE:
    python nba_box_scraper.py --input nba_games_all.csv --output player_boxscores_all.csv

FEATURES:
    - Scrapes from ESPN's box score API
    - Handles rate limiting and retries
    - Saves incremental progress
    - Resume capability for failed runs
    - Comprehensive error logging
"""

import requests
import pandas as pd
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path
import sys

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
    """Scrape player box scores from ESPN API"""
    
    def __init__(self, rate_limit_delay=0.5, retry_attempts=3):
        """
        Initialize scraper
        
        Args:
            rate_limit_delay: Seconds to wait between requests
            retry_attempts: Number of retry attempts for failed requests
        """
        self.base_url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary"
        self.rate_limit_delay = rate_limit_delay
        self.retry_attempts = retry_attempts
        self.session = requests.Session()
        
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
        Parse ESPN API response to extract player data
        
        Args:
            data: JSON response from ESPN API
            game_id: Game ID for reference
            
        Returns:
            List of player dictionaries
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
                    for athlete in player_stats.get('athletes', []):
                        athlete_info = athlete.get('athlete', {})
                        stats_list = athlete.get('stats', [])
                        
                        # Parse minutes (format: "MM:SS" or "MM")
                        minutes_played = self._parse_minutes(
                            stats_list[0] if stats_list else '0'
                        )
                        
                        player_record = {
                            'game_id': game_id,
                            'player_id': athlete_info.get('id', ''),
                            'player_name': athlete_info.get('displayName', ''),
                            'team_id': team_id,
                            'team_name': team_name,
                            'minutes': minutes_played,
                            'starter': athlete.get('starter', False),
                            'position': athlete_info.get('position', {}).get('abbreviation', ''),
                            'jersey': athlete_info.get('jersey', ''),
                            'didNotPlay': athlete.get('didNotPlay', False)
                        }
                        
                        players.append(player_record)
            
            return players if players else None
            
        except Exception as e:
            logger.error(f"Game {game_id}: Parsing error - {e}")
            return None
    
    def _parse_minutes(self, minutes_str):
        """Convert minutes string to decimal"""
        try:
            if ':' in minutes_str:
                parts = minutes_str.split(':')
                return int(parts[0]) + int(parts[1]) / 60
            return float(minutes_str) if minutes_str else 0.0
        except:
            return 0.0
    
    def scrape_season(self, game_ids, output_file, checkpoint_interval=100):
        """
        Scrape box scores for a list of game IDs
        
        Args:
            game_ids: List of ESPN game IDs
            output_file: Path to save results
            checkpoint_interval: Save progress every N games
        """
        logger.info(f"Starting scrape of {len(game_ids)} games")
        logger.info(f"Output file: {output_file}")
        
        all_players = []
        failed_games = []
        
        # Check for existing progress
        output_path = Path(output_file)
        if output_path.exists():
            logger.info(f"Found existing output file, loading...")
            existing_df = pd.read_csv(output_file)
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
        """Save progress to CSV"""
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
        description='Scrape NBA player box scores from ESPN API'
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
        help='Delay between requests in seconds (default: 0.5)'
    )
    parser.add_argument(
        '--checkpoint',
        type=int,
        default=100,
        help='Save progress every N games (default: 100)'
    )
    
    args = parser.parse_args()
    
    # Load game IDs
    game_ids = load_game_ids(args.input)
    
    # Initialize scraper
    scraper = NBABoxScraper(rate_limit_delay=args.rate_limit)
    
    # Run scraping
    df = scraper.scrape_season(
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
        logger.info(f"Average minutes per player: {df['minutes'].mean():.1f}")
        logger.info(f"Total starters: {df['starter'].sum()}")
        logger.info(f"\n✅ Box score scraping complete!")


if __name__ == "__main__":
    main()
