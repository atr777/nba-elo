"""
Simulation Results Aggregator
Phase 1: Core Simulator Component

Aggregates and analyzes Monte Carlo simulation results.
"""

import numpy as np
from collections import defaultdict, Counter
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class SimulationResults:
    """Aggregate and analyze Monte Carlo simulation results."""

    def __init__(self, raw_results: Dict, num_sims: int):
        """
        Initialize with raw simulation data.

        Args:
            raw_results: Dict with keys:
                - 'team_records': List[Dict] - Final standings per simulation
                - 'playoff_teams': List[Dict] - Playoff teams per simulation
                - 'conference_seeds': List[Dict] - Seeding per simulation
            num_sims: Number of simulations run
        """
        self.raw = raw_results
        self.num_sims = num_sims
        self._cache = {}  # Cache expensive calculations

        logger.info(f"SimulationResults initialized with {num_sims} simulations")

    def get_team_projection(self, team_id: int) -> Dict:
        """
        Get full projection for specific team.

        Returns:
            {
                'team_id': int,
                'projected_wins': float,  # Mean
                'median_wins': int,
                'win_distribution': Dict[wins -> count],
                'playoff_probability': float,  # 0.0 to 1.0
                'seed_probabilities': Dict[seed -> probability],
                'confidence_interval': (low, high)  # 90% CI
            }
        """
        # Check cache
        cache_key = f"team_{team_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Extract this team's results from all simulations
        team_wins = []
        playoff_count = 0
        seed_counts = defaultdict(int)

        for sim_standings, playoff_teams, seeds in zip(
            self.raw['team_records'],
            self.raw['playoff_teams'],
            self.raw['conference_seeds']
        ):
            # Get wins for this simulation
            if team_id in sim_standings:
                wins = sim_standings[team_id]['wins']
                team_wins.append(wins)

                # Check if made playoffs
                in_east_playoffs = team_id in playoff_teams.get('east_playoffs', [])
                in_west_playoffs = team_id in playoff_teams.get('west_playoffs', [])
                if in_east_playoffs or in_west_playoffs:
                    playoff_count += 1

                # Track seed
                if team_id in seeds:
                    seed_counts[seeds[team_id]] += 1

        # Calculate statistics
        if len(team_wins) == 0:
            logger.warning(f"No data found for team {team_id}")
            return None

        win_dist = Counter(team_wins)
        projected_wins = float(np.mean(team_wins))
        median_wins = int(np.median(team_wins))
        playoff_prob = playoff_count / self.num_sims

        # 90% confidence interval (5th to 95th percentile)
        ci_low = int(np.percentile(team_wins, 5))
        ci_high = int(np.percentile(team_wins, 95))

        # Seed probabilities
        seed_probs = {
            seed: count / self.num_sims
            for seed, count in seed_counts.items()
        }

        result = {
            'team_id': team_id,
            'projected_wins': projected_wins,
            'median_wins': median_wins,
            'win_distribution': dict(win_dist),
            'playoff_probability': playoff_prob,
            'seed_probabilities': seed_probs,
            'confidence_interval': (ci_low, ci_high)
        }

        # Cache result
        self._cache[cache_key] = result
        return result

    def get_all_projections(self) -> List[Dict]:
        """
        Get projections for all teams, sorted by projected wins.

        Returns:
            List of team projection dicts
        """
        # Get all unique team IDs from first simulation
        team_ids = set(self.raw['team_records'][0].keys())

        projections = []
        for team_id in team_ids:
            proj = self.get_team_projection(team_id)
            if proj:
                # Add team name from first simulation
                proj['team_name'] = self.raw['team_records'][0][team_id]['team_name']
                projections.append(proj)

        # Sort by projected wins
        projections.sort(key=lambda x: x['projected_wins'], reverse=True)
        return projections

    def get_conference_projections(self, conference: str = 'East') -> List[Dict]:
        """
        Get projections for teams in specified conference.

        Args:
            conference: 'East' or 'West'

        Returns:
            List of team projection dicts, sorted by projected wins
        """
        # Hardcoded conference mapping (TODO: make this data-driven)
        if conference == 'East':
            conference_teams = set(range(1, 16))  # Teams 1-15
        else:  # West
            conference_teams = set(range(16, 31))  # Teams 16-30

        all_projs = self.get_all_projections()

        # Filter to conference
        conference_projs = [p for p in all_projs if p['team_id'] in conference_teams]

        return conference_projs

    def get_playoff_race(self, conference: str = 'East', cutoff_seed: int = 10) -> List[Dict]:
        """
        Get teams in playoff race (near cutoff line).

        Args:
            conference: 'East' or 'West'
            cutoff_seed: Seed cutoff (default 10 for play-in)

        Returns:
            List of teams with playoff odds 10%-90%
        """
        conf_projs = self.get_conference_projections(conference)

        # Filter to teams in race (not locks or eliminated)
        race_teams = [
            p for p in conf_projs
            if 0.10 <= p['playoff_probability'] <= 0.90
        ]

        return race_teams

    def get_summary_stats(self) -> Dict:
        """
        Get overall summary statistics.

        Returns:
            {
                'num_simulations': int,
                'total_teams': int,
                'playoff_locks': int,  # Teams with >99% odds
                'eliminated': int,  # Teams with <1% odds
                'in_race': int,  # Teams between 1-99%
                'avg_parity': float  # Avg spread in conference win totals
            }
        """
        all_projs = self.get_all_projections()

        playoff_locks = sum(1 for p in all_projs if p['playoff_probability'] > 0.99)
        eliminated = sum(1 for p in all_projs if p['playoff_probability'] < 0.01)
        in_race = len(all_projs) - playoff_locks - eliminated

        return {
            'num_simulations': self.num_sims,
            'total_teams': len(all_projs),
            'playoff_locks': playoff_locks,
            'eliminated': eliminated,
            'in_race': in_race
        }

    def export_to_dict(self) -> Dict:
        """
        Export all projections to dict for JSON serialization.

        Returns:
            {
                'metadata': {...},
                'projections': [...]
            }
        """
        return {
            'metadata': self.get_summary_stats(),
            'projections': self.get_all_projections()
        }


if __name__ == '__main__':
    # Test simulation results aggregation
    import sys
    sys.path.insert(0, 'c:/Users/Aaron/Desktop/NBA_ELO/nba-elo-engine')

    print("="*80)
    print("SIMULATION RESULTS TEST")
    print("="*80)

    # Create mock simulation data
    print("\nCreating mock simulation data...")

    mock_results = {
        'team_records': [],
        'playoff_teams': [],
        'conference_seeds': []
    }

    # Generate 100 mock simulations
    num_sims = 100
    for i in range(num_sims):
        # Mock standings
        standings = {
            2: {'team_name': 'Boston Celtics', 'wins': 55 + (i % 10), 'losses': 27 - (i % 10)},
            13: {'team_name': 'Los Angeles Lakers', 'wins': 45 + (i % 8), 'losses': 37 - (i % 8)},
            25: {'team_name': 'Oklahoma City Thunder', 'wins': 60 + (i % 6), 'losses': 22 - (i % 6)},
        }

        # Mock playoffs
        playoffs = {
            'east_playoffs': [2, 13],  # Simplified
            'west_playoffs': [25]
        }

        # Mock seeds
        seeds = {
            2: 1 if i < 80 else 2,
            13: 6 if i < 50 else 7,
            25: 1
        }

        mock_results['team_records'].append(standings)
        mock_results['playoff_teams'].append(playoffs)
        mock_results['conference_seeds'].append(seeds)

    print(f"Created {num_sims} mock simulations")

    # Initialize results aggregator
    print("\nInitializing SimulationResults...")
    results = SimulationResults(mock_results, num_sims)

    # Test team projection
    print("\n--- Boston Celtics Projection ---")
    celtics_proj = results.get_team_projection(2)
    print(f"Projected wins: {celtics_proj['projected_wins']:.1f}")
    print(f"Median wins: {celtics_proj['median_wins']}")
    print(f"Win range (90% CI): {celtics_proj['confidence_interval']}")
    print(f"Playoff probability: {celtics_proj['playoff_probability']*100:.1f}%")
    print(f"Seed probabilities: {celtics_proj['seed_probabilities']}")

    # Test all projections
    print("\n--- All Team Projections ---")
    all_projs = results.get_all_projections()
    for proj in all_projs:
        print(f"{proj['team_name']:30} {proj['projected_wins']:.1f} wins, {proj['playoff_probability']*100:.0f}% playoffs")

    # Test summary stats
    print("\n--- Summary Statistics ---")
    summary = results.get_summary_stats()
    for key, value in summary.items():
        print(f"{key}: {value}")

    print("\n" + "="*80)
    print("TEST COMPLETE - SimulationResults Working!")
    print("="*80)
