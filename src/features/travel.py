"""
Travel Distance Analytics Module
================================
Calculates travel distances between NBA arenas and analyzes impact on performance.

Key Functions:
- haversine_distance: Calculate distance between two lat/lon coordinates
- load_arena_coordinates: Load arena location data
- calculate_travel_distance: Get distance between two teams
- add_travel_to_games: Enhance game data with travel distances
- analyze_travel_impact: Measure correlation between travel and performance
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, Dict
import math


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth.
    
    Args:
        lat1, lon1: Latitude and longitude of first point (degrees)
        lat2, lon2: Latitude and longitude of second point (degrees)
    
    Returns:
        Distance in kilometers
    
    Formula:
        Uses the Haversine formula to calculate distance on a sphere.
        https://en.wikipedia.org/wiki/Haversine_formula
    """
    # Convert decimal degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of Earth in kilometers
    r = 6371
    
    return c * r


def load_arena_coordinates(filepath: str = "config/arena_coordinates.csv") -> pd.DataFrame:
    """
    Load NBA arena coordinates from CSV.
    
    Args:
        filepath: Path to arena coordinates CSV
    
    Returns:
        DataFrame with columns: team_id, team_name, arena_name, city, state, latitude, longitude
    """
    df = pd.read_csv(filepath)
    return df


def calculate_travel_distance(
    team_id: int, 
    prev_opponent_id: int, 
    is_home: bool,
    arena_coords: pd.DataFrame
) -> float:
    """
    Calculate travel distance for a team between consecutive games.
    
    Args:
        team_id: Current team's ID
        prev_opponent_id: Previous game's opponent ID
        is_home: Whether current game is at home
        arena_coords: DataFrame with arena coordinates
    
    Returns:
        Travel distance in kilometers (0 if insufficient data)
    
    Logic:
        - If previous game was home and current is away: home -> opponent arena
        - If previous game was away and current is home: opponent arena -> home
        - If previous game was away and current is away: opponent1 -> opponent2
        - If both home: 0 (no travel)
    """
    try:
        # Get team's home arena coordinates
        team_coords = arena_coords[arena_coords['team_id'] == team_id].iloc[0]
        team_lat = team_coords['latitude']
        team_lon = team_coords['longitude']
        
        # Get previous opponent's arena coordinates
        opp_coords = arena_coords[arena_coords['team_id'] == prev_opponent_id].iloc[0]
        opp_lat = opp_coords['latitude']
        opp_lon = opp_coords['longitude']
        
        # Determine start and end locations based on home/away status
        # (This is simplified - in reality, teams might not travel directly)
        if is_home:
            # Coming home from previous opponent's arena
            distance = haversine_distance(opp_lat, opp_lon, team_lat, team_lon)
        else:
            # Traveling from home to opponent's arena
            distance = haversine_distance(team_lat, team_lon, opp_lat, opp_lon)
        
        return distance
        
    except (IndexError, KeyError):
        return 0.0


def add_travel_to_elo_history(
    elo_history_path: str,
    arena_coords_path: str = "config/arena_coordinates.csv",
    output_path: str = "data/exports/team_elo_with_travel.csv"
) -> pd.DataFrame:
    """
    Enhance ELO history with travel distance calculations.
    
    Args:
        elo_history_path: Path to team_elo_history.csv
        arena_coords_path: Path to arena_coordinates.csv
        output_path: Where to save enhanced data
    
    Returns:
        Enhanced DataFrame with travel_distance_km and long_travel columns
    """
    print("Loading ELO history...")
    elo_df = pd.read_csv(elo_history_path)
    
    print("Loading arena coordinates...")
    arena_coords = load_arena_coordinates(arena_coords_path)
    
    print("Calculating travel distances...")
    
    # Sort by team and date to get consecutive games
    elo_df = elo_df.sort_values(['team_id', 'date'])
    
    # Initialize travel columns
    elo_df['travel_distance_km'] = 0.0
    elo_df['long_travel'] = False
    
    # Calculate travel for each team
    for team_id in elo_df['team_id'].unique():
        team_games = elo_df[elo_df['team_id'] == team_id].copy()
        
        for i in range(1, len(team_games)):
            current_idx = team_games.index[i]
            prev_idx = team_games.index[i-1]
            
            prev_opponent = elo_df.loc[prev_idx, 'opponent_id']
            is_home = elo_df.loc[current_idx, 'is_home']
            
            # Calculate distance
            distance = calculate_travel_distance(
                team_id=team_id,
                prev_opponent_id=prev_opponent,
                is_home=is_home,
                arena_coords=arena_coords
            )
            
            elo_df.loc[current_idx, 'travel_distance_km'] = distance
            elo_df.loc[current_idx, 'long_travel'] = (distance > 1500)
    
    print(f"Travel distances calculated for {len(elo_df)} games")
    
    # Summary statistics
    avg_travel = elo_df[elo_df['travel_distance_km'] > 0]['travel_distance_km'].mean()
    long_travel_games = elo_df['long_travel'].sum()
    
    print(f"\nTravel Statistics:")
    print(f"  Average travel distance: {avg_travel:.1f} km")
    print(f"  Long travel games (>1500km): {long_travel_games:,}")
    
    # Save enhanced data
    elo_df.to_csv(output_path, index=False)
    print(f"\n✓ Enhanced data saved to: {output_path}")
    
    return elo_df


def analyze_travel_impact(elo_with_travel_path: str) -> Dict:
    """
    Analyze correlation between travel distance and performance.
    
    Args:
        elo_with_travel_path: Path to ELO data with travel distances
    
    Returns:
        Dictionary with analysis results
    """
    print("Analyzing travel impact on performance...")
    
    df = pd.read_csv(elo_with_travel_path)
    
    # Calculate win rate by travel distance bins
    df['travel_bin'] = pd.cut(
        df['travel_distance_km'],
        bins=[0, 500, 1000, 1500, 2000, 5000],
        labels=['0-500km', '500-1000km', '1000-1500km', '1500-2000km', '2000+km']
    )
    
    travel_analysis = df.groupby('travel_bin').agg({
        'won': ['mean', 'count'],
        'rating_change': 'mean',
        'expected_score': 'mean'
    }).round(4)
    
    print("\nWin Rate by Travel Distance:")
    print(travel_analysis)
    
    # Long travel impact
    long_travel = df[df['long_travel'] == True]
    short_travel = df[df['long_travel'] == False]
    
    long_win_rate = long_travel['won'].mean()
    short_win_rate = short_travel['won'].mean()
    
    print(f"\nLong Travel (>1500km) Win Rate: {long_win_rate:.3f}")
    print(f"Normal Travel Win Rate: {short_win_rate:.3f}")
    print(f"Impact: {(long_win_rate - short_win_rate):.3f} ({(long_win_rate - short_win_rate)*100:.1f}%)")
    
    # Correlation with ELO change
    correlation = df['travel_distance_km'].corr(df['rating_change'])
    print(f"\nCorrelation (travel distance vs ELO change): {correlation:.4f}")
    
    results = {
        'long_travel_win_rate': long_win_rate,
        'normal_travel_win_rate': short_win_rate,
        'impact': long_win_rate - short_win_rate,
        'correlation': correlation,
        'avg_travel': df['travel_distance_km'].mean()
    }
    
    return results


def main():
    """
    Main execution: Add travel distances to ELO history and analyze impact.
    """
    print("=" * 70)
    print("NBA ELO - TRAVEL DISTANCE ANALYTICS")
    print("=" * 70)
    print()
    
    # Step 1: Add travel distances
    elo_with_travel = add_travel_to_elo_history(
        elo_history_path="data/exports/team_elo_history_phase_1_5.csv",
        arena_coords_path="config/arena_coordinates.csv",
        output_path="data/exports/team_elo_with_travel.csv"
    )
    
    print("\n" + "=" * 70)
    
    # Step 2: Analyze impact
    results = analyze_travel_impact("data/exports/team_elo_with_travel.csv")
    
    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"\nNext steps:")
    print(f"1. Review travel impact on win rates")
    print(f"2. Consider adding travel penalty to ELO engine")
    print(f"3. Create visualizations showing travel vs performance")
    
    return results


if __name__ == "__main__":
    results = main()
