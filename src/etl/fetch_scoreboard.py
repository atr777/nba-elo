"""
ESPN Scoreboard Scraper
Fetches NBA game data from ESPN's API for specified date ranges.
"""

import requests
import pandas as pd
import time
from datetime import datetime
from typing import List, Dict, Optional
from tqdm import tqdm
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.utils.file_io import save_dataframe_to_csv, load_settings, get_data_path
from src.utils.date_utils import generate_date_range
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ESPNScoreboardScraper:
    """Scraper for ESPN NBA scoreboard data."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the scraper.
        
        Args:
            config: Configuration dictionary (loads from settings.yaml if None)
        """
        if config is None:
            config = load_settings()
        
        self.base_url = config['api']['espn_scoreboard']
        self.timeout = config['api']['request_timeout']
        self.retry_attempts = config['api']['retry_attempts']
        self.rate_limit_delay = config['api']['rate_limit_delay']
        
        logger.info("ESPN Scoreboard Scraper initialized")
    
    def fetch_games_for_date(self, date: str) -> List[Dict]:
        """
        Fetch all NBA games for a specific date.
        
        Args:
            date: Date string in YYYYMMDD format
            
        Returns:
            List of game dictionaries
        """
        url = f"{self.base_url}?dates={date}"
        
        for attempt in range(self.retry_attempts):
            try:
                response = requests.get(url, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                
                games = []
                events = data.get('events', [])
                
                for event in events:
                    game_data = self._parse_game_event(event, date)
                    if game_data:
                        games.append(game_data)
                
                return games
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed for date {date}: {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed to fetch data for date {date} after {self.retry_attempts} attempts")
                    return []
        
        return []
    
    def _parse_game_event(self, event: Dict, date: str) -> Optional[Dict]:
        """
        Parse a single game event from ESPN API response.
        
        Args:
            event: Game event dictionary from API
            date: Date string
            
        Returns:
            Parsed game dictionary or None if parsing fails
        """
        try:
            game_id = event['id']
            competitions = event.get('competitions', [])
            
            if not competitions:
                return None
            
            competition = competitions[0]
            competitors = competition.get('competitors', [])
            
            if len(competitors) != 2:
                return None
            
            # ESPN API has home team first, away team second
            home_team = next((c for c in competitors if c.get('homeAway') == 'home'), None)
            away_team = next((c for c in competitors if c.get('homeAway') == 'away'), None)
            
            if not home_team or not away_team:
                return None
            
            # Extract scores
            home_score = int(home_team.get('score', 0))
            away_score = int(away_team.get('score', 0))
            
            # Determine winner
            if home_score > away_score:
                winner_team_id = home_team['team']['id']
            elif away_score > home_score:
                winner_team_id = away_team['team']['id']
            else:
                # Tie - shouldn't happen in NBA but handle it
                winner_team_id = None
            
            return {
                'game_id': game_id,
                'date': date,
                'home_team_id': home_team['team']['id'],
                'home_team_name': home_team['team']['displayName'],
                'away_team_id': away_team['team']['id'],
                'away_team_name': away_team['team']['displayName'],
                'home_score': home_score,
                'away_score': away_score,
                'winner_team_id': winner_team_id
            }
            
        except (KeyError, ValueError) as e:
            logger.warning(f"Failed to parse game event: {e}")
            return None
    
    def scrape_season(self, start_date: str, end_date: str, output_path: Optional[str] = None) -> pd.DataFrame:
        """
        Scrape all games between start and end dates.
        
        Args:
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            output_path: Optional path to save CSV (defaults to data/raw/nba_games_raw.csv)
            
        Returns:
            DataFrame with all games
        """
        logger.info(f"Starting scrape from {start_date} to {end_date}")
        
        dates = generate_date_range(start_date, end_date)
        all_games = []
        
        for date in tqdm(dates, desc="Fetching games"):
            games = self.fetch_games_for_date(date)
            all_games.extend(games)
            time.sleep(self.rate_limit_delay)  # Rate limiting
        
        df = pd.DataFrame(all_games)
        
        if len(df) == 0:
            logger.warning("No games found in date range")
            return df
        
        # Sort by date and game_id
        df = df.sort_values(['date', 'game_id']).reset_index(drop=True)
        
        logger.info(f"Successfully scraped {len(df)} games")
        
        # Save to file
        if output_path is None:
            output_path = get_data_path('raw', 'nba_games_raw.csv')
        
        save_dataframe_to_csv(df, output_path)
        
        return df


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape NBA games from ESPN API')
    parser.add_argument('--start-date', type=str, required=True, help='Start date (YYYYMMDD)')
    parser.add_argument('--end-date', type=str, required=True, help='End date (YYYYMMDD)')
    parser.add_argument('--output', type=str, help='Output CSV path (optional)')
    
    args = parser.parse_args()
    
    scraper = ESPNScoreboardScraper()
    df = scraper.scrape_season(args.start_date, args.end_date, args.output)
    
    print(f"\n✓ Scraping complete!")
    print(f"  Total games: {len(df)}")
    print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"  Teams found: {df['home_team_name'].nunique()}")


if __name__ == "__main__":
    main()
