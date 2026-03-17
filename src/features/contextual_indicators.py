"""
Contextual Indicators
Identifies special circumstances that affect prediction reliability.

Special scenarios tracked:
- Post-holiday games (Christmas, All-Star break)
- Season opener games (first 5 games)
- Playoff push games (last 15 games, teams in contention)
- Back-to-back situations
- Long road trips

Research: These scenarios have historically lower prediction accuracy due to
irregular rest patterns, motivation shifts, and lineup uncertainties.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class ContextualIndicators:
    """
    Identify special game circumstances that affect prediction reliability.

    Use cases:
    - Flag post-holiday games for reduced confidence
    - Identify playoff race implications
    - Track season opener uncertainty
    - Monitor travel/rest irregularities
    """

    def __init__(
        self,
        post_holiday_days: int = 3,
        season_opener_games: int = 5,
        playoff_push_games: int = 15,
        playoff_spot_proximity: float = 3.0
    ):
        """
        Initialize contextual indicators.

        Args:
            post_holiday_days: Days after holiday to flag (default: 3)
            season_opener_games: Number of games to flag at season start (default: 5)
            playoff_push_games: Games before season end to check playoff race (default: 15)
            playoff_spot_proximity: Games within playoff spot to flag (default: 3.0)
        """
        self.post_holiday_days = post_holiday_days
        self.season_opener_games = season_opener_games
        self.playoff_push_games = playoff_push_games
        self.playoff_spot_proximity = playoff_spot_proximity

        # NBA season structure (typical schedule)
        self.regular_season_games = 82
        self.season_start_month = 10  # October
        self.season_end_month = 4  # April

        # Key holiday dates (MM-DD format, year-agnostic)
        self.holidays = {
            'christmas': (12, 25),
            'all_star': None,  # Variable date, set dynamically
            'thanksgiving': (11, 23),  # Approximate (4th Thursday)
        }

        logger.info(
            f"Contextual Indicators initialized: "
            f"post_holiday={post_holiday_days}d, "
            f"season_opener={season_opener_games}g, "
            f"playoff_push={playoff_push_games}g"
        )

    def analyze_game_context(
        self,
        game_date: datetime,
        home_team_id: str,
        away_team_id: str,
        games_played_home: int = 0,
        games_played_away: int = 0,
        standings: Optional[Dict] = None,
        **kwargs
    ) -> Dict:
        """
        Analyze contextual factors for a game.

        Args:
            game_date: Date of the game
            home_team_id: Home team identifier
            away_team_id: Away team identifier
            games_played_home: Games played by home team this season
            games_played_away: Games played by away team this season
            standings: Optional dict with team standings {team_id: {'rank': int, 'games_back': float}}
            **kwargs: Additional context

        Returns:
            Dictionary with:
                - is_post_christmas: Within 3 days of Dec 25
                - is_post_allstar: Within 3 days of All-Star break
                - is_post_thanksgiving: Within 3 days of Thanksgiving
                - is_season_opener: First 5 games of season
                - is_playoff_push: Last 15 games + team in playoff race
                - contextual_flags: List of active flags
                - context_summary: Human-readable summary
                - confidence_penalty: Suggested confidence reduction (0-30%)
        """
        flags = []
        penalty = 0.0

        # Check post-holiday status
        is_post_christmas = self._is_post_holiday(game_date, 'christmas')
        is_post_allstar = self._is_post_allstar_break(game_date)
        is_post_thanksgiving = self._is_post_holiday(game_date, 'thanksgiving')

        if is_post_christmas:
            flags.append("Post-Christmas")
            penalty += 30.0  # Biggest penalty (Dec 27 was very unpredictable)
            logger.debug(f"Post-Christmas game detected: {game_date.strftime('%Y-%m-%d')}")

        if is_post_allstar:
            flags.append("Post-All-Star")
            penalty += 15.0
            logger.debug(f"Post-All-Star game detected: {game_date.strftime('%Y-%m-%d')}")

        if is_post_thanksgiving:
            flags.append("Post-Thanksgiving")
            penalty += 10.0

        # Check season opener status (either team)
        is_season_opener = (
            games_played_home < self.season_opener_games or
            games_played_away < self.season_opener_games
        )

        if is_season_opener:
            flags.append("Season Opener")
            penalty += 20.0
            logger.debug(
                f"Season opener detected: Home={games_played_home}g, Away={games_played_away}g"
            )

        # Check playoff push status
        is_playoff_push = self._is_playoff_push(
            game_date,
            home_team_id,
            away_team_id,
            games_played_home,
            games_played_away,
            standings
        )

        if is_playoff_push:
            flags.append("Playoff Push")
            penalty += 10.0
            logger.debug(f"Playoff push game detected")

        # Generate summary
        if len(flags) == 0:
            context_summary = "Normal game conditions"
        else:
            context_summary = "Special circumstances: " + ", ".join(flags)

        # Cap penalty at 50% (always keep some signal)
        penalty = min(penalty, 50.0)

        result = {
            'is_post_christmas': is_post_christmas,
            'is_post_allstar': is_post_allstar,
            'is_post_thanksgiving': is_post_thanksgiving,
            'is_season_opener': is_season_opener,
            'is_playoff_push': is_playoff_push,
            'contextual_flags': flags,
            'context_summary': context_summary,
            'confidence_penalty': penalty,
            'has_special_circumstances': len(flags) > 0
        }

        if len(flags) > 0:
            logger.info(
                f"Game context: {context_summary} (penalty: {penalty:.1f}%)"
            )

        return result

    def _is_post_holiday(self, game_date: datetime, holiday_name: str) -> bool:
        """
        Check if game is within N days after a holiday.

        Args:
            game_date: Game date
            holiday_name: Holiday identifier ('christmas', 'thanksgiving', etc.)

        Returns:
            True if game is within post_holiday_days of the holiday
        """
        if holiday_name not in self.holidays:
            return False

        holiday_date = self.holidays[holiday_name]
        if holiday_date is None:
            return False

        month, day = holiday_date

        # Create holiday date for this year
        holiday_this_year = datetime(game_date.year, month, day)

        # Check if game is 1-3 days after holiday
        days_after = (game_date - holiday_this_year).days

        return 1 <= days_after <= self.post_holiday_days

    def _is_post_allstar_break(self, game_date: datetime) -> bool:
        """
        Check if game is within N days after All-Star break.

        All-Star break is typically mid-February (around Feb 15-20).
        This is approximate - ideally would use actual All-Star dates.

        Args:
            game_date: Game date

        Returns:
            True if game is within post_holiday_days of All-Star break
        """
        # All-Star break is typically around Feb 17-19
        # We'll check for games Feb 20-23
        if game_date.month == 2 and 20 <= game_date.day <= 23:
            logger.debug(f"Post-All-Star break detected: {game_date.strftime('%Y-%m-%d')}")
            return True

        return False

    def _is_playoff_push(
        self,
        game_date: datetime,
        home_team_id: str,
        away_team_id: str,
        games_played_home: int,
        games_played_away: int,
        standings: Optional[Dict] = None
    ) -> bool:
        """
        Check if game is in playoff push period.

        Criteria:
        1. Within last 15 games of regular season, AND
        2. Either team is within 3 games of playoff spot

        Args:
            game_date: Game date
            home_team_id: Home team ID
            away_team_id: Away team ID
            games_played_home: Games played by home team
            games_played_away: Games played by away team
            standings: Optional standings data

        Returns:
            True if game is in playoff push for either team
        """
        # Check if in last 15 games of season
        max_games_played = max(games_played_home, games_played_away)
        games_remaining = self.regular_season_games - max_games_played

        if games_remaining > self.playoff_push_games:
            return False

        # If no standings provided, assume yes (conservative approach)
        if standings is None:
            logger.debug("No standings data, assuming playoff push")
            return True

        # Check if either team is in playoff race
        home_in_race = self._is_team_in_playoff_race(home_team_id, standings)
        away_in_race = self._is_team_in_playoff_race(away_team_id, standings)

        return home_in_race or away_in_race

    def _is_team_in_playoff_race(
        self,
        team_id: str,
        standings: Dict
    ) -> bool:
        """
        Check if team is in playoff race (within N games of playoff spot).

        Args:
            team_id: Team identifier
            standings: Standings dict {team_id: {'rank': int, 'games_back': float}}

        Returns:
            True if team is in playoff contention
        """
        if team_id not in standings:
            return False

        team_data = standings[team_id]

        # Check rank (top 10 teams per conference make play-in/playoffs)
        rank = team_data.get('rank', 99)
        if rank <= 10:
            return True

        # Check games back from playoff spot
        games_back = team_data.get('games_back', 99.0)
        if games_back <= self.playoff_spot_proximity:
            return True

        return False

    def get_holiday_schedule(self, year: int) -> List[Dict]:
        """
        Get full holiday schedule for a season.

        Args:
            year: Season year

        Returns:
            List of dicts with holiday info
        """
        schedule = []

        # Christmas
        christmas = datetime(year, 12, 25)
        schedule.append({
            'name': 'Christmas',
            'date': christmas,
            'post_period_start': christmas + timedelta(days=1),
            'post_period_end': christmas + timedelta(days=self.post_holiday_days),
            'penalty': 30.0
        })

        # Thanksgiving (4th Thursday of November - approximate)
        thanksgiving = datetime(year, 11, 23)  # Approximate
        schedule.append({
            'name': 'Thanksgiving',
            'date': thanksgiving,
            'post_period_start': thanksgiving + timedelta(days=1),
            'post_period_end': thanksgiving + timedelta(days=self.post_holiday_days),
            'penalty': 10.0
        })

        # All-Star (mid-February - approximate)
        allstar = datetime(year, 2, 18)  # Approximate
        schedule.append({
            'name': 'All-Star Break',
            'date': allstar,
            'post_period_start': allstar + timedelta(days=1),
            'post_period_end': allstar + timedelta(days=self.post_holiday_days),
            'penalty': 15.0
        })

        return schedule


# Singleton instance
_contextual_indicators = None

def get_contextual_indicators() -> ContextualIndicators:
    """Get or create the ContextualIndicators singleton."""
    global _contextual_indicators
    if _contextual_indicators is None:
        _contextual_indicators = ContextualIndicators()
        logger.info("Contextual Indicators initialized")
    return _contextual_indicators
