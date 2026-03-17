"""
NBA Injury Scraper
Scrapes daily injury reports from NBA official sources and ESPN.

Priority 2 Enhancement: Automated injury tracking with status parsing

Features:
- Daily scraping from NBA official injury reports
- Parse injury status: Out, Questionable, Doubtful, Probable
- Track expected return dates
- Store in structured JSON format
- Integration with prediction system

Data Format:
{
    "date": "2024-12-29",
    "teams": {
        "LAL": {
            "injuries": [
                {
                    "player_name": "LeBron James",
                    "status": "Out",
                    "injury": "Ankle",
                    "expected_return": "2024-12-31"
                }
            ]
        }
    }
}
"""

import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import time

logger = logging.getLogger(__name__)


class InjuryScraper:
    """
    Scrape and parse NBA injury reports.

    Sources:
    1. NBA official injury report
    2. ESPN injury data (backup)
    3. Basketball Reference (tertiary)
    """

    def __init__(self, data_dir: str = "data/raw"):
        """
        Initialize injury scraper.

        Args:
            data_dir: Directory to store injury data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Injury status mapping
        self.status_map = {
            'out': 'Out',
            'doubtful': 'Doubtful',
            'questionable': 'Questionable',
            'probable': 'Probable',
            'available': 'Available',
            'gtd': 'Questionable',  # Game-Time Decision
        }

        # Team abbreviation mapping (ESPN to standard)
        self.team_abbrev_map = {
            'PHX': 'PHO',  # Phoenix
            'GS': 'GSW',   # Golden State
            'NY': 'NYK',   # New York
            'SA': 'SAS',   # San Antonio
            'NO': 'NOP',   # New Orleans
        }

        logger.info(f"Injury Scraper initialized, data dir: {self.data_dir}")

    def scrape_daily_injuries(self, date: Optional[datetime] = None) -> Dict:
        """
        Scrape injury data for a given date.

        Args:
            date: Date to scrape (default: today)

        Returns:
            Dictionary with injury data:
            {
                'date': '2024-12-29',
                'teams': {
                    'LAL': {
                        'injuries': [...]
                    }
                }
            }
        """
        if date is None:
            date = datetime.now()

        date_str = date.strftime('%Y-%m-%d')

        logger.info(f"Scraping injury data for {date_str}")

        # Try NBA official first
        injuries = self._scrape_nba_official(date)

        if not injuries or len(injuries.get('teams', {})) == 0:
            # Fallback to ESPN
            logger.warning("NBA official source failed, trying ESPN")
            injuries = self._scrape_espn_injuries(date)

        # Save to file
        if injuries:
            self._save_injury_data(injuries, date)

        return injuries

    def _scrape_nba_official(self, date: datetime) -> Dict:
        """
        Scrape from NBA official injury report API.

        NBA API endpoint: https://www.nba.com/stats/...
        Note: This is a placeholder - actual NBA API may require authentication

        Args:
            date: Date to scrape

        Returns:
            Injury data dictionary
        """
        try:
            # NBA Stats API endpoint (example)
            # This may need adjustment based on actual API availability
            url = "https://stats.nba.com/stats/leaguedashplayerstats"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Referer': 'https://www.nba.com/',
            }

            # Note: This is a simplified example
            # Real implementation would need proper API parameters
            params = {
                'Season': '2024-25',
                'SeasonType': 'Regular Season',
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Parse response (format depends on actual API)
            injuries = self._parse_nba_official_response(data, date)

            logger.info(f"Scraped {len(injuries.get('teams', {}))} teams from NBA official")

            return injuries

        except Exception as e:
            logger.error(f"Error scraping NBA official: {e}")
            return {}

    def _scrape_espn_injuries(self, date: datetime) -> Dict:
        """
        Scrape from ESPN injury data.

        ESPN has team-specific injury pages:
        https://www.espn.com/nba/team/injuries/_/name/lal

        Args:
            date: Date to scrape

        Returns:
            Injury data dictionary
        """
        injuries_data = {
            'date': date.strftime('%Y-%m-%d'),
            'teams': {},
            'source': 'ESPN'
        }

        # List of NBA teams (abbreviations)
        teams = [
            'ATL', 'BOS', 'BKN', 'CHA', 'CHI', 'CLE', 'DAL', 'DEN', 'DET', 'GSW',
            'HOU', 'IND', 'LAC', 'LAL', 'MEM', 'MIA', 'MIL', 'MIN', 'NOP', 'NYK',
            'OKC', 'ORL', 'PHI', 'PHO', 'POR', 'SAC', 'SAS', 'TOR', 'UTA', 'WAS'
        ]

        for team in teams:
            try:
                # ESPN uses lowercase team names
                espn_team = team.lower()

                url = f"https://www.espn.com/nba/team/injuries/_/name/{espn_team}"

                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }

                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()

                # Parse HTML to extract injury data
                team_injuries = self._parse_espn_html(response.text, team)

                if team_injuries:
                    injuries_data['teams'][team] = {
                        'injuries': team_injuries
                    }

                # Rate limiting
                time.sleep(0.5)

            except Exception as e:
                logger.debug(f"Error scraping {team} injuries from ESPN: {e}")
                continue

        logger.info(f"Scraped {len(injuries_data['teams'])} teams from ESPN")

        return injuries_data

    def _parse_espn_html(self, html: str, team: str) -> List[Dict]:
        """
        Parse ESPN injury HTML to extract injury data.

        This is a simplified version - real implementation would use
        BeautifulSoup or similar HTML parser.

        Args:
            html: HTML content
            team: Team abbreviation

        Returns:
            List of injury dicts
        """
        injuries = []

        try:
            # This is a placeholder - real implementation would parse HTML properly
            # For now, return empty list
            # In production, would use BeautifulSoup:
            # from bs4 import BeautifulSoup
            # soup = BeautifulSoup(html, 'html.parser')
            # table = soup.find('table', class_='Table')
            # ... parse table rows ...

            logger.debug(f"ESPN HTML parsing not fully implemented for {team}")

        except Exception as e:
            logger.error(f"Error parsing ESPN HTML for {team}: {e}")

        return injuries

    def _parse_nba_official_response(self, data: Dict, date: datetime) -> Dict:
        """
        Parse NBA official API response.

        Args:
            data: API response data
            date: Date of data

        Returns:
            Standardized injury data dict
        """
        injuries = {
            'date': date.strftime('%Y-%m-%d'),
            'teams': {},
            'source': 'NBA Official'
        }

        # Parse based on actual API structure
        # This is a placeholder

        return injuries

    def _save_injury_data(self, injuries: Dict, date: datetime):
        """
        Save injury data to JSON file.

        Args:
            injuries: Injury data dictionary
            date: Date of data
        """
        date_str = date.strftime('%Y%m%d')
        filename = self.data_dir / f"injury_reports_{date_str}.json"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(injuries, f, indent=2)

            logger.info(f"Saved injury data to {filename}")

        except Exception as e:
            logger.error(f"Error saving injury data: {e}")

    def load_injury_data(self, date: Optional[datetime] = None) -> Dict:
        """
        Load injury data from file.

        Args:
            date: Date to load (default: today)

        Returns:
            Injury data dictionary
        """
        if date is None:
            date = datetime.now()

        date_str = date.strftime('%Y%m%d')
        filename = self.data_dir / f"injury_reports_{date_str}.json"

        if not filename.exists():
            logger.warning(f"Injury data file not found: {filename}")
            return {}

        try:
            with open(filename, 'r', encoding='utf-8') as f:
                injuries = json.load(f)

            logger.info(f"Loaded injury data from {filename}")

            return injuries

        except Exception as e:
            logger.error(f"Error loading injury data: {e}")
            return {}

    def get_team_injuries(
        self,
        team_id: str,
        date: Optional[datetime] = None,
        include_questionable: bool = False
    ) -> List[str]:
        """
        Get injured players for a team.

        Args:
            team_id: Team abbreviation (e.g., 'LAL')
            date: Date to check (default: today)
            include_questionable: Include questionable players (default: False)

        Returns:
            List of injured player names
        """
        injuries = self.load_injury_data(date)

        if not injuries or 'teams' not in injuries:
            return []

        team_data = injuries.get('teams', {}).get(team_id, {})
        team_injuries = team_data.get('injuries', [])

        injured_players = []

        for injury in team_injuries:
            status = injury.get('status', '').lower()

            # Always include 'Out' and 'Doubtful'
            if status in ['out', 'doubtful']:
                injured_players.append(injury['player_name'])

            # Optionally include 'Questionable'
            elif include_questionable and status == 'questionable':
                injured_players.append(injury['player_name'])

        return injured_players

    def get_injury_severity_score(
        self,
        status: str,
        days_since_injury: int = 0
    ) -> float:
        """
        Calculate injury severity score (0.0 to 1.0).

        Higher score = more severe impact

        Args:
            status: Injury status (Out, Doubtful, Questionable, Probable)
            days_since_injury: Days since injury occurred

        Returns:
            Severity score (0.0 to 1.0)
        """
        status_lower = status.lower()

        # Base severity by status
        status_severity = {
            'out': 1.0,
            'doubtful': 0.8,
            'questionable': 0.5,
            'probable': 0.2,
            'available': 0.0,
        }

        base_severity = status_severity.get(status_lower, 0.5)

        # Adjust for long-term injuries (more than 7 days)
        if days_since_injury > 7:
            # Long-term injuries may have replacement adjustments
            base_severity *= 0.9

        return base_severity


# Singleton instance
_injury_scraper = None

def get_injury_scraper() -> InjuryScraper:
    """Get or create the InjuryScraper singleton."""
    global _injury_scraper
    if _injury_scraper is None:
        _injury_scraper = InjuryScraper()
        logger.info("Injury Scraper initialized")
    return _injury_scraper
