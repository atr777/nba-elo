"""
Enhanced Travel Analyzer
Analyzes travel impact on game predictions with timezone and streak tracking.

Priority 3 Enhancement: Comprehensive travel fatigue modeling

Features:
- Distance traveled calculation (haversine formula)
- Timezone crossings impact
- Road/home streak tracking
- Travel fatigue penalties
- Integration with prediction system

Research:
- Teams traveling 2+ time zones have 5-10% lower win rates
- Long road trips (5+ games) create cumulative fatigue
- Cross-country travel (>2000 miles) significantly impacts performance
"""

import math
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)


class TravelAnalyzer:
    """
    Analyze travel fatigue and its impact on game performance.

    Factors analyzed:
    - Distance traveled from last game
    - Time zones crossed
    - Road/home streak length
    - Days since last game (rest)
    """

    def __init__(
        self,
        team_locations: Optional[Dict] = None,
        long_travel_threshold: float = 2000.0,  # miles
        timezone_penalty_per_zone: float = 8.0,  # ELO points
        road_streak_threshold: int = 4,  # games
        road_streak_penalty: float = 10.0  # ELO points per game over threshold
    ):
        """
        Initialize travel analyzer.

        Args:
            team_locations: Dict with team location data (lat, lon, timezone)
            long_travel_threshold: Miles threshold for long travel (default: 2000)
            timezone_penalty_per_zone: ELO penalty per timezone crossed (default: 8)
            road_streak_threshold: Games before road fatigue kicks in (default: 4)
            road_streak_penalty: ELO penalty per game over threshold (default: 10)
        """
        self.team_locations = team_locations or self._load_default_locations()
        self.long_travel_threshold = long_travel_threshold
        self.tz_penalty_per_zone = timezone_penalty_per_zone
        self.road_streak_threshold = road_streak_threshold
        self.road_streak_penalty = road_streak_penalty

        # Track team streaks: {team_id: {'type': 'home'/'road', 'count': int}}
        self.team_streaks = {}

        logger.info(
            f"Travel Analyzer initialized: "
            f"long_travel={long_travel_threshold}mi, "
            f"tz_penalty={timezone_penalty_per_zone}/zone"
        )

    def _load_default_locations(self) -> Dict:
        """Load default team locations if not provided."""
        # Try to load from team_locations.json
        locations_file = Path("data/team_locations.json")

        if locations_file.exists():
            import json
            with open(locations_file, 'r') as f:
                return json.load(f)

        # Return empty dict if not found (will need to be populated)
        logger.warning("Team locations file not found, using empty dict")
        return {}

    def analyze_travel_impact(
        self,
        home_team_id: str,
        away_team_id: str,
        home_last_game_location: Optional[str] = None,
        away_last_game_location: Optional[str] = None,
        home_is_home_streak: bool = True,
        away_is_road_streak: bool = True,
        home_streak_count: int = 0,
        away_streak_count: int = 0
    ) -> Dict:
        """
        Analyze travel impact for both teams.

        Args:
            home_team_id: Home team abbreviation
            away_team_id: Away team abbreviation
            home_last_game_location: Last game location for home team
            away_last_game_location: Last game location for away team
            home_is_home_streak: Is home team on home streak?
            away_is_road_streak: Is away team on road trip?
            home_streak_count: Length of home team's streak
            away_streak_count: Length of away team's road trip

        Returns:
            Dictionary with:
                - home_travel_distance: Miles traveled by home team
                - away_travel_distance: Miles traveled by away team
                - home_timezones_crossed: Timezones crossed by home team
                - away_timezones_crossed: Timezones crossed by away team
                - home_travel_penalty: ELO penalty for home team
                - away_travel_penalty: ELO penalty for away team
                - travel_advantage: Net travel advantage (positive = home advantage)
        """
        # Calculate travel distances
        home_travel = self._calculate_travel_distance(
            team_id=home_team_id,
            from_location=home_last_game_location,
            to_location=home_team_id,  # Going home
            is_home_game=True
        )

        away_travel = self._calculate_travel_distance(
            team_id=away_team_id,
            from_location=away_last_game_location,
            to_location=home_team_id,  # Going to opponent's arena
            is_home_game=False
        )

        # Calculate timezone crossings
        home_tz_crossed = self._calculate_timezone_crossings(
            from_team=home_last_game_location or home_team_id,
            to_team=home_team_id
        )

        away_tz_crossed = self._calculate_timezone_crossings(
            from_team=away_last_game_location or away_team_id,
            to_team=home_team_id
        )

        # Calculate travel penalties
        home_penalty = self._calculate_travel_penalty(
            distance=home_travel['distance'],
            timezones_crossed=home_tz_crossed,
            is_road_streak=not home_is_home_streak,
            streak_count=home_streak_count
        )

        away_penalty = self._calculate_travel_penalty(
            distance=away_travel['distance'],
            timezones_crossed=away_tz_crossed,
            is_road_streak=away_is_road_streak,
            streak_count=away_streak_count
        )

        # Net advantage (positive = home team benefits)
        travel_advantage = away_penalty - home_penalty

        logger.info(
            f"Travel analysis: Home={home_travel['distance']:.0f}mi, "
            f"Away={away_travel['distance']:.0f}mi, "
            f"Advantage={travel_advantage:+.1f} ELO (home)"
        )

        return {
            'home_travel_distance': home_travel['distance'],
            'away_travel_distance': away_travel['distance'],
            'home_timezones_crossed': home_tz_crossed,
            'away_timezones_crossed': away_tz_crossed,
            'home_travel_penalty': home_penalty,
            'away_travel_penalty': away_penalty,
            'home_road_streak': not home_is_home_streak,
            'away_road_streak': away_is_road_streak,
            'home_streak_count': home_streak_count,
            'away_streak_count': away_streak_count,
            'travel_advantage': travel_advantage,
            'significant_travel_difference': abs(travel_advantage) > 15
        }

    def _calculate_travel_distance(
        self,
        team_id: str,
        from_location: Optional[str],
        to_location: str,
        is_home_game: bool
    ) -> Dict:
        """
        Calculate travel distance for a team.

        Args:
            team_id: Team abbreviation
            from_location: Previous game location (team abbrev)
            to_location: Current game location (team abbrev)
            is_home_game: Is this a home game?

        Returns:
            Dict with distance and details
        """
        if from_location is None or from_location == to_location:
            # No travel needed
            return {'distance': 0.0, 'from': from_location, 'to': to_location}

        # Get coordinates
        from_coords = self.team_locations.get(from_location, {})
        to_coords = self.team_locations.get(to_location, {})

        if not from_coords or not to_coords:
            logger.debug(f"Missing location data for {from_location} or {to_location}")
            return {'distance': 0.0, 'from': from_location, 'to': to_location}

        # Calculate haversine distance
        distance_km = self._haversine_distance(
            from_coords['lat'],
            from_coords['lon'],
            to_coords['lat'],
            to_coords['lon']
        )

        # Convert to miles
        distance_mi = distance_km * 0.621371

        return {
            'distance': distance_mi,
            'from': from_location,
            'to': to_location,
            'is_long_travel': distance_mi > self.long_travel_threshold
        }

    def _haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculate great-circle distance between two points.

        Args:
            lat1, lon1: First point coordinates
            lat2, lon2: Second point coordinates

        Returns:
            Distance in kilometers
        """
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = (math.sin(dlat/2)**2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2)
        c = 2 * math.asin(math.sqrt(a))

        # Earth radius in km
        r = 6371

        return c * r

    def _calculate_timezone_crossings(
        self,
        from_team: str,
        to_team: str
    ) -> int:
        """
        Calculate number of time zones crossed.

        Args:
            from_team: Origin team abbreviation
            to_team: Destination team abbreviation

        Returns:
            Number of time zones crossed (0-3)
        """
        from_location = self.team_locations.get(from_team, {})
        to_location = self.team_locations.get(to_team, {})

        if not from_location or not to_location:
            return 0

        from_tz = from_location.get('timezone', '')
        to_tz = to_location.get('timezone', '')

        # Map timezones to numeric values (US timezones)
        tz_map = {
            'America/New_York': 0,      # Eastern
            'America/Chicago': 1,        # Central
            'America/Denver': 2,         # Mountain
            'America/Phoenix': 2,        # Arizona (no DST)
            'America/Los_Angeles': 3,    # Pacific
            'America/Toronto': 0,        # Eastern (Canada)
        }

        from_tz_num = tz_map.get(from_tz, 0)
        to_tz_num = tz_map.get(to_tz, 0)

        zones_crossed = abs(to_tz_num - from_tz_num)

        return zones_crossed

    def _calculate_travel_penalty(
        self,
        distance: float,
        timezones_crossed: int,
        is_road_streak: bool,
        streak_count: int
    ) -> float:
        """
        Calculate total travel penalty in ELO points.

        Args:
            distance: Miles traveled
            timezones_crossed: Number of timezones crossed
            is_road_streak: Is team on road trip?
            streak_count: Length of road trip

        Returns:
            Total ELO penalty (negative number)
        """
        penalty = 0.0

        # Distance penalty (long travel)
        if distance > self.long_travel_threshold:
            # -5 to -15 ELO based on distance
            excess_distance = distance - self.long_travel_threshold
            distance_penalty = min(15.0, 5.0 + (excess_distance / 500.0))
            penalty -= distance_penalty

        # Timezone penalty
        if timezones_crossed > 0:
            tz_penalty = timezones_crossed * self.tz_penalty_per_zone
            penalty -= tz_penalty

        # Road streak penalty
        if is_road_streak and streak_count > self.road_streak_threshold:
            games_over = streak_count - self.road_streak_threshold
            streak_penalty = games_over * self.road_streak_penalty
            penalty -= min(streak_penalty, 30.0)  # Cap at -30 ELO

        return penalty


# Singleton instance
_travel_analyzer = None

def get_travel_analyzer() -> TravelAnalyzer:
    """Get or create the TravelAnalyzer singleton."""
    global _travel_analyzer
    if _travel_analyzer is None:
        _travel_analyzer = TravelAnalyzer()
        logger.info("Travel Analyzer initialized")
    return _travel_analyzer
