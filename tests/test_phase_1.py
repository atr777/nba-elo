"""
Phase 1 Test Script
Tests the complete Team ELO pipeline: scrape → compute → analyze
"""

import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.etl.fetch_scoreboard import ESPNScoreboardScraper
from src.engines.team_elo_engine import TeamELOEngine
from src.utils.file_io import get_data_path
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


def test_phase_1(start_date='20231024', end_date='20231031'):
    """
    Test Phase 1 functionality with a small date range.
    
    Args:
        start_date: Start date (YYYYMMDD)
        end_date: End date (YYYYMMDD)
    """
    print("="*60)
    print("NBA ELO Intelligence Engine - Phase 1 Test")
    print("="*60)
    
    # Step 1: Scrape games
    print("\n[1/3] Scraping games...")
    scraper = ESPNScoreboardScraper()
    games_df = scraper.scrape_season(
        start_date=start_date,
        end_date=end_date,
        output_path=get_data_path('raw', 'test_games.csv')
    )
    
    if len(games_df) == 0:
        print("⚠ No games found in date range. Try a different date range.")
        return
    
    print(f"✓ Scraped {len(games_df)} games")
    print(f"  Date range: {games_df['date'].min()} - {games_df['date'].max()}")
    
    # Step 2: Compute ELO
    print("\n[2/3] Computing team ELO ratings...")
    engine = TeamELOEngine(k_factor=20, home_advantage=100)
    history_df = engine.compute_season_elo(games_df)
    
    print(f"✓ Computed {len(history_df)} rating updates")
    
    # Step 3: Analyze results
    print("\n[3/3] Analyzing results...")
    
    # Get current ratings
    current_ratings = engine.get_current_ratings()
    
    # Add team names
    team_names = history_df.groupby('team_id')['team_name'].first()
    current_ratings = current_ratings.merge(
        team_names.reset_index(),
        on='team_id',
        how='left'
    )
    
    print("\nTop 10 Teams by ELO Rating:")
    print("-" * 60)
    for i, row in current_ratings.head(10).iterrows():
        print(f"{i+1:2d}. {row['team_name']:25s} {row['rating']:.1f}")
    
    # Sample game analysis
    print("\nSample Game Analysis:")
    print("-" * 60)
    sample_game = history_df[history_df['is_home'] == True].iloc[0]
    print(f"Game: {sample_game['team_name']} vs {sample_game['opponent_name']}")
    print(f"Score: {sample_game['team_score']}-{sample_game['opponent_score']}")
    print(f"Result: {'WIN' if sample_game['won'] else 'LOSS'}")
    print(f"Expected Win Prob: {sample_game['expected_score']:.1%}")
    print(f"Rating Change: {sample_game['rating_change']:+.1f}")
    print(f"Rating: {sample_game['rating_before']:.1f} → {sample_game['rating_after']:.1f}")
    
    # Prediction example
    print("\nSample Prediction:")
    print("-" * 60)
    if len(current_ratings) >= 2:
        team1_id = current_ratings.iloc[0]['team_id']
        team2_id = current_ratings.iloc[1]['team_id']
        
        prediction = engine.predict_game(team1_id, team2_id)
        team1_name = current_ratings[current_ratings['team_id'] == team1_id]['team_name'].iloc[0]
        team2_name = current_ratings[current_ratings['team_id'] == team2_id]['team_name'].iloc[0]
        
        print(f"{team1_name} (home) vs {team2_name}")
        print(f"  {team1_name} rating: {prediction['home_rating']:.1f}")
        print(f"  {team2_name} rating: {prediction['away_rating']:.1f}")
        print(f"  {team1_name} win probability: {prediction['home_win_probability']:.1%}")
        print(f"  {team2_name} win probability: {prediction['away_win_probability']:.1%}")
    
    print("\n" + "="*60)
    print("✓ Phase 1 test complete!")
    print("="*60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Phase 1 Team ELO system')
    parser.add_argument('--start', type=str, default='20231024', help='Start date (YYYYMMDD)')
    parser.add_argument('--end', type=str, default='20231031', help='End date (YYYYMMDD)')
    
    args = parser.parse_args()
    
    test_phase_1(args.start, args.end)
