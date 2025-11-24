"""
Test ESPN Boxscore API
======================
Quick test to verify ESPN's boxscore endpoint works and see what data we get.
"""

import requests
import json
import pandas as pd
from datetime import datetime


def test_boxscore_api(game_id: str):
    """
    Test fetching boxscore for a single game.
    
    Args:
        game_id: ESPN game ID (e.g., "401585601")
    
    Returns:
        Dict with boxscore data
    """
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
    
    print(f"Testing game ID: {game_id}")
    print(f"URL: {url}")
    print()
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        
        # Check if boxscore exists
        if 'boxscore' not in data:
            print("❌ No boxscore found in response")
            return None
        
        boxscore = data['boxscore']
        
        # Extract team info
        teams = boxscore.get('teams', [])
        
        print(f"✅ Boxscore found!")
        print(f"   Teams: {len(teams)}")
        
        players_data = []
        
        for team in teams:
            team_name = team['team']['displayName']
            team_id = team['team']['id']
            
            print(f"\n📊 {team_name} (ID: {team_id}):")
            
            # Get statistics (players)
            statistics = team.get('statistics', [])
            
            for stat_group in statistics:
                if stat_group.get('name') == 'minutes':
                    continue
                
                athletes = stat_group.get('athletes', [])
                
                print(f"   Players found: {len(athletes)}")
                
                for athlete in athletes:
                    player_id = athlete.get('athlete', {}).get('id')
                    player_name = athlete.get('athlete', {}).get('displayName')
                    
                    # Get stats
                    stats = athlete.get('stats', [])
                    minutes = None
                    
                    # Find minutes played
                    for stat_value in stats:
                        # Minutes is usually the first stat
                        if stat_value and ':' in str(stat_value):
                            minutes = stat_value
                            break
                    
                    if player_name:
                        players_data.append({
                            'player_id': player_id,
                            'player_name': player_name,
                            'team_id': team_id,
                            'team_name': team_name,
                            'minutes': minutes,
                        })
                        
                        print(f"      • {player_name}: {minutes} min")
        
        return players_data
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None


def test_multiple_games():
    """Test on a few recent games."""
    print("=" * 70)
    print("ESPN BOXSCORE API TEST")
    print("=" * 70)
    print()
    
    # Test with a few recent game IDs
    # You can get these from your nba_games_all.csv file
    test_game_ids = [
        "401585601",  # Example game ID
        "401585602",
        "401585603",
    ]
    
    print("📋 Testing with sample game IDs...")
    print("   (These might not work if they're too old or invalid)")
    print()
    
    all_players = []
    
    for game_id in test_game_ids:
        print("-" * 70)
        players = test_boxscore_api(game_id)
        
        if players:
            all_players.extend(players)
            print(f"   ✅ Success: {len(players)} player records")
        else:
            print(f"   ❌ Failed to get boxscore")
        
        print()
    
    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Total player records: {len(all_players)}")
    
    if all_players:
        print("\n✅ API is working!")
        print("\nSample data:")
        df = pd.DataFrame(all_players)
        print(df.head(10).to_string(index=False))
        
        # Save sample
        df.to_csv("test_boxscore_sample.csv", index=False)
        print(f"\n💾 Saved sample to: test_boxscore_sample.csv")
    else:
        print("\n⚠️  No data retrieved. Game IDs might be invalid.")
        print("    We'll need to extract actual game IDs from your nba_games_all.csv")
    
    return all_players


def get_sample_game_ids_from_data():
    """Get real game IDs from your actual data."""
    print("=" * 70)
    print("EXTRACTING REAL GAME IDs FROM YOUR DATA")
    print("=" * 70)
    print()
    
    # Try to load your games file
    possible_paths = [
        "data/raw/nba_games_all_clean.csv",
        "data/raw/nba_games_all.csv",
    ]
    
    for path in possible_paths:
        try:
            print(f"Trying: {path}")
            df = pd.read_csv(path)
            
            # Get recent games (2024-25 season)
            if df['date'].dtype == 'int64':
                recent = df[df['date'] >= 20241101].head(5)
            else:
                recent = df.tail(5)
            
            game_ids = recent['game_id'].tolist()
            
            print(f"✅ Found {len(game_ids)} recent game IDs:")
            for gid in game_ids:
                print(f"   • {gid}")
            
            print("\nTesting these game IDs...")
            print()
            
            all_players = []
            for game_id in game_ids:
                print("-" * 70)
                players = test_boxscore_api(str(game_id))
                if players:
                    all_players.extend(players)
                    print(f"   ✅ Success: {len(players)} players")
                else:
                    print(f"   ❌ Failed")
                print()
            
            if all_players:
                print("=" * 70)
                print("✅ API TEST SUCCESSFUL!")
                print("=" * 70)
                print(f"\nRetrieved {len(all_players)} player records")
                
                df = pd.DataFrame(all_players)
                print("\nSample data:")
                print(df.head(15).to_string(index=False))
                
                df.to_csv("test_boxscore_sample.csv", index=False)
                print(f"\n💾 Saved to: test_boxscore_sample.csv")
            
            return all_players
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            continue
    
    print("\n❌ Could not load game data files")
    return []


if __name__ == "__main__":
    # First try with real game IDs from your data
    players = get_sample_game_ids_from_data()
    
    if not players:
        # Fallback to test IDs
        print("\nFalling back to test game IDs...")
        players = test_multiple_games()
