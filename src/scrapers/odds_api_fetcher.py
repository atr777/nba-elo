"""
The Odds API Integration
Fetches NBA betting odds for market validation

API Documentation: https://the-odds-api.com/sports-odds-data/nba-odds.html
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))


def convert_american_odds_to_probability(american_odds):
    """
    Convert American odds to implied win probability.

    Args:
        american_odds: Integer odds (e.g., -110, +150)

    Returns:
        float: Implied probability (0.0 to 1.0)

    Examples:
        -110 → 0.524 (52.4%)
        +150 → 0.400 (40.0%)
        -200 → 0.667 (66.7%)
        +200 → 0.333 (33.3%)
    """
    if american_odds < 0:
        # Favorite (negative odds)
        # Probability = |odds| / (|odds| + 100)
        return abs(american_odds) / (abs(american_odds) + 100)
    else:
        # Underdog (positive odds)
        # Probability = 100 / (odds + 100)
        return 100 / (american_odds + 100)


def fetch_nba_odds(api_key, date=None, regions='us', markets='h2h', odds_format='american'):
    """
    Fetch NBA odds from The Odds API.

    Args:
        api_key: The Odds API key
        date: Date to fetch odds for (defaults to today)
        regions: Regions to fetch odds for (default: 'us')
        markets: Markets to fetch (default: 'h2h' for moneyline)
        odds_format: 'american' or 'decimal'

    Returns:
        dict: {
            'games': List of games with odds,
            'credits_used': Number of API credits used,
            'credits_remaining': Remaining API credits
        }
    """
    endpoint = 'https://api.the-odds-api.com/v4/sports/basketball_nba/odds'

    params = {
        'apiKey': api_key,
        'regions': regions,
        'markets': markets,
        'oddsFormat': odds_format
    }

    try:
        response = requests.get(endpoint, params=params, timeout=10)
        response.raise_for_status()

        games = response.json()

        # Extract credit usage from headers
        credits_used = response.headers.get('x-requests-used', 'unknown')
        credits_remaining = response.headers.get('x-requests-remaining', 'unknown')

        return {
            'games': games,
            'credits_used': credits_used,
            'credits_remaining': credits_remaining,
            'success': True
        }

    except requests.exceptions.RequestException as e:
        return {
            'games': [],
            'credits_used': 0,
            'credits_remaining': 'unknown',
            'success': False,
            'error': str(e)
        }


def get_consensus_probability(game, team_name):
    """
    Calculate consensus win probability for a team from multiple bookmakers.

    Args:
        game: Game dict from The Odds API
        team_name: Team name to get probability for

    Returns:
        dict: {
            'probability': Average implied probability,
            'odds': Average American odds,
            'num_books': Number of bookmakers,
            'bookmaker_probs': List of individual bookmaker probabilities
        }
    """
    bookmaker_odds = []
    bookmaker_probs = []

    for bookmaker in game.get('bookmakers', []):
        for market in bookmaker.get('markets', []):
            if market['key'] == 'h2h':  # Moneyline
                for outcome in market['outcomes']:
                    if outcome['name'] == team_name:
                        odds = outcome['price']
                        prob = convert_american_odds_to_probability(odds)
                        bookmaker_odds.append(odds)
                        bookmaker_probs.append(prob)

    if not bookmaker_probs:
        return None

    # Calculate consensus (average)
    avg_probability = sum(bookmaker_probs) / len(bookmaker_probs)
    avg_odds = sum(bookmaker_odds) / len(bookmaker_odds)

    return {
        'probability': avg_probability,
        'odds': avg_odds,
        'num_books': len(bookmaker_probs),
        'bookmaker_probs': bookmaker_probs
    }


def get_game_odds_by_teams(api_key, home_team, away_team):
    """
    Get odds for a specific game by team names.

    Args:
        api_key: The Odds API key
        home_team: Home team name (e.g., "Los Angeles Lakers")
        away_team: Away team name (e.g., "Boston Celtics")

    Returns:
        dict: {
            'home_prob': Home team win probability,
            'away_prob': Away team win probability,
            'home_odds': Average home team odds,
            'away_odds': Average away team odds,
            'num_books': Number of bookmakers,
            'found': True/False
        }
    """
    result = fetch_nba_odds(api_key)

    if not result['success']:
        return {'found': False, 'error': result.get('error')}

    # Find the game
    for game in result['games']:
        game_home = game.get('home_team', '')
        game_away = game.get('away_team', '')

        # Match teams (case-insensitive, partial match)
        if (home_team.lower() in game_home.lower() or game_home.lower() in home_team.lower()) and \
           (away_team.lower() in game_away.lower() or game_away.lower() in away_team.lower()):

            home_consensus = get_consensus_probability(game, game_home)
            away_consensus = get_consensus_probability(game, game_away)

            if home_consensus and away_consensus:
                return {
                    'home_prob': home_consensus['probability'],
                    'away_prob': away_consensus['probability'],
                    'home_odds': home_consensus['odds'],
                    'away_odds': away_consensus['odds'],
                    'num_books': home_consensus['num_books'],
                    'found': True,
                    'credits_used': result['credits_used'],
                    'credits_remaining': result['credits_remaining']
                }

    return {'found': False, 'error': 'Game not found'}


def test_api_connection(api_key):
    """
    Test The Odds API connection and display available games.

    Args:
        api_key: The Odds API key

    Returns:
        bool: True if connection successful
    """
    print("="*80)
    print("THE ODDS API CONNECTION TEST")
    print("="*80)

    result = fetch_nba_odds(api_key)

    if not result['success']:
        print(f"\n[FAIL] API connection failed: {result.get('error')}")
        return False

    print(f"\n[OK] API connection successful")
    print(f"Credits used: {result['credits_used']}")
    print(f"Credits remaining: {result['credits_remaining']}")
    print(f"\nGames found: {len(result['games'])}")

    if result['games']:
        print("\n" + "="*80)
        print("AVAILABLE GAMES")
        print("="*80)

        for i, game in enumerate(result['games'][:5], 1):  # Show first 5
            home = game.get('home_team', 'Unknown')
            away = game.get('away_team', 'Unknown')
            commence = game.get('commence_time', 'Unknown')
            num_books = len(game.get('bookmakers', []))

            print(f"\n{i}. {away} @ {home}")
            print(f"   Start time: {commence}")
            print(f"   Bookmakers: {num_books}")

            # Get odds
            home_consensus = get_consensus_probability(game, home)
            away_consensus = get_consensus_probability(game, away)

            if home_consensus and away_consensus:
                print(f"   {home}: {home_consensus['probability']*100:.1f}% ({home_consensus['odds']:+.0f})")
                print(f"   {away}: {away_consensus['probability']*100:.1f}% ({away_consensus['odds']:+.0f})")

        if len(result['games']) > 5:
            print(f"\n... and {len(result['games']) - 5} more games")

    print("\n" + "="*80)
    return True


if __name__ == '__main__':
    # Test with API key
    API_KEY = 'e1607aa8757797d0b22b442b975b781b'

    if test_api_connection(API_KEY):
        print("\n[SUCCESS] The Odds API integration working correctly")
    else:
        print("\n[FAIL] The Odds API integration failed")
