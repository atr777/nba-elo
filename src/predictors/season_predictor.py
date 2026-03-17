"""
Season Predictor - Monte Carlo Simulator
Phase 2: Enhanced with Hybrid Predictor

Runs Monte Carlo simulations to project season outcomes using Phase 2 hybrid predictor.
"""

import random
import copy
import logging
from typing import Dict, List, Optional
from collections import defaultdict, Counter
import numpy as np
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)


class SeasonPredictor:
    """Monte Carlo season simulator using Phase 2 hybrid predictor."""

    def __init__(self, team_ratings, player_ratings, player_team_mapping, games_history,
                 current_standings: Dict, remaining_schedule: List[Dict]):
        """
        Initialize season predictor with Phase 2 data.

        Args:
            team_ratings: Team ratings DataFrame
            player_ratings: Player ratings DataFrame
            player_team_mapping: Player-team mapping DataFrame
            games_history: Historical games DataFrame for WElo and H2H
            current_standings: Dict[team_id] -> {'wins': int, 'losses': int, 'team_name': str}
            remaining_schedule: List of remaining games from ScheduleFetcher
        """
        self.team_ratings = team_ratings
        self.player_ratings = player_ratings
        self.player_team_mapping = player_team_mapping
        self.games_history = games_history
        self.standings = current_standings
        self.schedule = remaining_schedule

        logger.info(f"SeasonPredictor initialized (Phase 2): {len(current_standings)} teams, {len(remaining_schedule)} remaining games")

    def simulate_season(self, num_sims: int = 10000, use_enhanced: bool = True, seed: Optional[int] = None) -> 'SimulationResults':
        """
        Run Monte Carlo simulations of remaining season.

        Args:
            num_sims: Number of simulations (default 10,000)
            use_enhanced: Use form factor + rest penalties (default True)
            seed: Random seed for reproducibility (optional)

        Returns:
            SimulationResults object with aggregated projections
        """
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        logger.info(f"Starting {num_sims} Monte Carlo simulations (enhanced={use_enhanced})")

        # Storage for all simulation results
        all_team_records = []  # List of final standings per sim
        all_playoff_teams = []  # Which teams made playoffs per sim
        all_conference_seeds = []  # Final seeding per sim

        for sim_num in range(num_sims):
            # Progress logging
            if (sim_num + 1) % 1000 == 0:
                logger.info(f"Completed {sim_num + 1}/{num_sims} simulations")

            # Copy current standings for this simulation
            sim_standings = copy.deepcopy(self.standings)

            # Simulate each remaining game
            for game in self.schedule:
                # Skip games with teams not in standings (All-Star, exhibition, etc.)
                if game['home_id'] not in sim_standings or game['away_id'] not in sim_standings:
                    continue

                # Get win probability using Phase 2 hybrid predictor
                try:
                    from src.predictors.hybrid_team_player import predict_game_hybrid

                    # Parse game date
                    game_date = game.get('date')
                    if game_date:
                        if isinstance(game_date, int):
                            game_date = datetime.strptime(str(game_date), '%Y%m%d')
                        elif isinstance(game_date, str):
                            game_date = datetime.strptime(game_date, '%Y-%m-%d')

                    prediction = predict_game_hybrid(
                        home_team_id=game['home_id'],
                        away_team_id=game['away_id'],
                        team_ratings=self.team_ratings,
                        player_ratings=self.player_ratings,
                        player_team_mapping=self.player_team_mapping,
                        home_injuries=[],
                        away_injuries=[],
                        games_history=self.games_history,
                        game_date=game_date
                    )
                    home_win_prob = prediction['home_win_probability']
                except (ValueError, KeyError, Exception) as e:
                    # Fallback if prediction fails
                    logger.warning(f"Phase 2 prediction failed for game {game['home_id']} vs {game['away_id']}: {e}")
                    home_win_prob = 0.5  # Coin flip

                # Random draw to determine winner
                home_wins = random.random() < home_win_prob

                # Update standings
                if home_wins:
                    sim_standings[game['home_id']]['wins'] += 1
                    sim_standings[game['away_id']]['losses'] += 1
                else:
                    sim_standings[game['away_id']]['wins'] += 1
                    sim_standings[game['home_id']]['losses'] += 1

            # Record final standings for this simulation
            all_team_records.append(sim_standings)

            # Determine playoff teams (top 10 per conference)
            playoff_teams = self._get_playoff_teams(sim_standings)
            all_playoff_teams.append(playoff_teams)

            # Get conference seeding
            seeds = self._get_conference_seeds(sim_standings)
            all_conference_seeds.append(seeds)

        logger.info(f"Completed all {num_sims} simulations")

        # Return aggregated results
        from src.predictors.simulation_results import SimulationResults
        return SimulationResults(
            raw_results={
                'team_records': all_team_records,
                'playoff_teams': all_playoff_teams,
                'conference_seeds': all_conference_seeds
            },
            num_sims=num_sims
        )

    def _get_playoff_teams(self, standings: Dict) -> Dict[str, List[int]]:
        """
        Determine which teams make playoffs based on standings.

        Top 6 seeds get direct playoff berth.
        Seeds 7-10 go to play-in tournament.

        Args:
            standings: Final standings for this simulation

        Returns:
            {
                'east_playoffs': [team_ids for top 10 East teams],
                'west_playoffs': [team_ids for top 10 West teams]
            }
        """
        # TODO: Need conference mapping - for now use hardcoded
        # East: Teams 1-15 (approximately)
        # West: Teams 16-30 (approximately)

        # This is a simplified version - will need actual conference data
        east_team_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
        west_team_ids = [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]

        # Filter standings to each conference
        east_teams = [(tid, standings[tid]) for tid in standings if tid in east_team_ids]
        west_teams = [(tid, standings[tid]) for tid in standings if tid in west_team_ids]

        # Sort by wins (with tiebreaker using team_id for consistency)
        east_sorted = sorted(east_teams, key=lambda x: (x[1]['wins'], -x[0]), reverse=True)
        west_sorted = sorted(west_teams, key=lambda x: (x[1]['wins'], -x[0]), reverse=True)

        # Top 10 per conference
        east_playoffs = [team_id for team_id, _ in east_sorted[:10]]
        west_playoffs = [team_id for team_id, _ in west_sorted[:10]]

        return {
            'east_playoffs': east_playoffs,
            'west_playoffs': west_playoffs
        }

    def _get_conference_seeds(self, standings: Dict) -> Dict[int, int]:
        """
        Get 1-10 seeding for each conference.

        Args:
            standings: Final standings for this simulation

        Returns:
            Dict mapping team_id -> seed (1-10 per conference)
        """
        # Same conference mapping as above
        east_team_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
        west_team_ids = [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]

        east_teams = [(tid, standings[tid]) for tid in standings if tid in east_team_ids]
        west_teams = [(tid, standings[tid]) for tid in standings if tid in west_team_ids]

        east_sorted = sorted(east_teams, key=lambda x: (x[1]['wins'], -x[0]), reverse=True)
        west_sorted = sorted(west_teams, key=lambda x: (x[1]['wins'], -x[0]), reverse=True)

        seeds = {}

        # Assign seeds 1-10 for East
        for seed, (team_id, _) in enumerate(east_sorted[:10], 1):
            seeds[team_id] = seed

        # Assign seeds 1-10 for West
        for seed, (team_id, _) in enumerate(west_sorted[:10], 1):
            seeds[team_id] = seed

        return seeds


if __name__ == '__main__':
    # Test the season predictor
    import sys
    sys.path.insert(0, 'c:/Users/Aaron/Desktop/NBA_ELO/nba-elo-engine')

    from src.utils.file_io import load_csv_to_dataframe
    from src.predictors.schedule_fetcher import ScheduleFetcher
    from src.engines.team_elo_engine import TeamELOEngine
    import pandas as pd

    print("="*80)
    print("SEASON PREDICTOR TEST")
    print("="*80)

    # Load data
    print("\nLoading data...")
    games = load_csv_to_dataframe('data/raw/nba_games_all.csv')

    # Initialize ELO engine with enhanced features
    print("Initializing ELO engine...")
    elo_engine = TeamELOEngine(
        k_factor=20,
        home_advantage=30,  # Calibrated
        use_mov=True,
        use_enhanced_features=True
    )

    # Process games up to Dec 1, 2024
    test_date = 20241201
    completed_games = games[(games['date'] >= 20241022) & (games['date'] <= test_date)]
    print(f"Processing {len(completed_games)} completed games through {test_date}...")

    for _, game in completed_games.iterrows():
        try:
            elo_engine.process_game(game.to_dict())
        except Exception as e:
            pass  # Skip games with missing data

    print(f"ELO engine ready with {len(elo_engine.current_ratings)} teams")

    # Get schedule and standings
    print("\nFetching schedule and standings...")
    fetcher = ScheduleFetcher(games)
    standings = fetcher.get_current_standings(test_date)
    remaining = fetcher.get_remaining_games(test_date, include_completed_future=True)

    print(f"Current standings: {len(standings)} teams")
    print(f"Remaining games: {len(remaining)}")

    # Run small simulation for testing
    print("\n--- Running 100 Simulations (Test) ---")
    predictor = SeasonPredictor(elo_engine, standings, remaining)
    results = predictor.simulate_season(num_sims=100, use_enhanced=True, seed=42)

    print("\nSimulation complete!")
    print(f"Ran {results.num_sims} simulations")

    # Show sample projection for Celtics
    celtics_id = 2
    celtics_proj = results.get_team_projection(celtics_id)
    print(f"\n--- Boston Celtics Projection ---")
    print(f"Current record: {standings[celtics_id]['wins']}-{standings[celtics_id]['losses']}")
    print(f"Projected wins: {celtics_proj['projected_wins']:.1f}")
    print(f"Win range (90% CI): {celtics_proj['confidence_interval']}")
    print(f"Playoff probability: {celtics_proj['playoff_probability']*100:.1f}%")

    print("\n" + "="*80)
    print("TEST COMPLETE - Phase 1 Monte Carlo Engine Working!")
    print("="*80)
    print("\nNext: Create simulation_results.py for advanced aggregation")
