"""
NBA ELO Dashboard - Interactive Web Interface
Allows users to explore data, predict games, simulate scenarios, and visualize ratings.

Usage:
    python app.py

Then open: http://localhost:5000
"""

from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from utils.file_io import load_csv_to_dataframe
from scrapers.espn_team_injuries import get_injury_report
from scrapers.espn_scraper import get_key_injuries_for_team
from engines.team_elo_engine import TeamELOEngine
from engines.hybrid_predictor import HybridPredictor
from analytics.model_performance_tracker import get_tracker
from analytics.betting_analyzer import BettingAnalyzer
from predictors.hybrid_team_player import predict_game_hybrid
from features.head_to_head_tracker import HeadToHeadTracker
from features.season_calibrator import SeasonCalibrator

app = Flask(__name__)

# Active NBA teams (30 teams, excluding historical/exhibition teams)
ACTIVE_NBA_TEAMS = {
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10,  # Atlanta through Houston
    11, 12, 13, 14, 15, 16,          # Indiana through Minnesota
    17,                               # Brooklyn Nets (formerly New Jersey)
    18, 19, 20, 21, 22, 23, 24,      # New York through San Antonio
    25,                               # Oklahoma City Thunder (formerly Seattle SuperSonics)
    26, 27, 28,                       # Utah, Washington, Toronto
    29,                               # Memphis Grizzlies (formerly Vancouver)
    30                                # Charlotte Hornets (current)
}
# Note: Excludes All-Star teams (31-32), international exhibition (111xxx), and defunct franchises

# Global data storage
DATA = {
    'team_ratings': None,
    'player_ratings': None,
    'player_team_mapping': None,
    'games': None,
    'team_elo_history': None,
    'player_elo_history': None,
    'team_locations': None,
    'predictor': None,
    'elo_engine': None,  # TeamELOEngine with enhanced features
    # Phase 4 components
    'h2h_tracker': None,  # Head-to-head tracker
    'season_calibrator': None,  # Season calibration
    'hybrid_predictor': None,  # Hybrid predictor with adaptive weighting
    # Phase 4 settings
    'use_h2h': True,  # Enable H2H adjustments
    'use_adaptive_weighting': True,  # Enable adaptive weighting
    'use_season_calibration': True,  # Enable season calibration
    'close_game_threshold': 100.0,  # ELO diff for close games
    'h2h_lookback_games': 5,  # H2H history depth
    'h2h_max_adjustment': 50.0,  # Max H2H ELO adjustment
    'season_confidence_games': 20,  # Games for full confidence
    'season_min_confidence': 0.70,  # Min confidence early season
}

# Global update process tracker
UPDATE_PROCESS = None

def _validate_player_ratings(player_ratings):
    """
    Validate player ratings data quality.

    Note: Position scaling and scorer boost are now integrated into the player
    ELO engine (Phase 3) and applied automatically during rating calculation.
    Manual validation checks removed as they're no longer needed.
    """
    # Basic data quality checks
    if len(player_ratings) == 0:
        raise ValueError("No player ratings loaded")

    # Check for required columns
    required_cols = ['player_id', 'player_name', 'rating']
    missing_cols = [col for col in required_cols if col not in player_ratings.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    print(f"[OK] Player ratings validated ({len(player_ratings)} players)")

def load_data():
    """Load all necessary data files on startup."""
    print("Loading data...")

    # Load team ratings (latest from history - Phase 1.6 with enhanced features)
    team_history = load_csv_to_dataframe('data/exports/team_elo_history_phase_1_6.csv')
    DATA['team_elo_history'] = team_history

    # Get latest team ratings (filter to active NBA teams only)
    latest_teams = team_history.sort_values('date').groupby('team_id').last().reset_index()
    latest_teams['rating'] = latest_teams['rating_after']
    latest_teams = latest_teams[latest_teams['team_id'].isin(ACTIVE_NBA_TEAMS)]
    DATA['team_ratings'] = latest_teams[['team_id', 'team_name', 'rating']].copy()

    # Load player ratings (BPM version with position adjustments)
    DATA['player_ratings'] = load_csv_to_dataframe('data/exports/player_ratings_bpm_adjusted.csv')

    # Validate player ratings data quality
    _validate_player_ratings(DATA['player_ratings'])

    # Load player-team mapping
    DATA['player_team_mapping'] = load_csv_to_dataframe('data/exports/player_team_mapping.csv')

    # Load games (keep original with integer dates for ELO engine)
    games_raw = load_csv_to_dataframe('data/raw/nba_games_all.csv')

    # Initialize Team ELO Engine with enhanced features (needs integer dates)
    print("Initializing Team ELO Engine with enhanced features...")
    DATA['elo_engine'] = TeamELOEngine(
        k_factor=20,
        home_advantage=30,  # Calibrated to actual 2024-25 home win rate (54.33%)
        use_mov=True,
        use_enhanced_features=True  # Enable form factor + rest penalties
    )

    # Load all historical games into the engine to build form and rest state
    print("Processing historical games to build form/rest state...")
    DATA['elo_engine'].compute_season_elo(games_raw, reset=True)

    # Now convert dates to datetime for hybrid predictor and store
    DATA['games'] = games_raw.copy()
    if 'date' in DATA['games'].columns:
        DATA['games']['date'] = pd.to_datetime(DATA['games']['date'], format='%Y%m%d')

    # Load player ELO history
    DATA['player_elo_history'] = load_csv_to_dataframe('data/exports/player_elo_history_bpm.csv')

    # Load team locations for travel distance calculation (Priority 1)
    # Store as (latitude, longitude) tuples as required by close_game_enhancer
    team_locations_df = load_csv_to_dataframe('data/team_locations.csv')
    DATA['team_locations'] = {}
    for _, row in team_locations_df.iterrows():
        DATA['team_locations'][row['team_id']] = (row['latitude'], row['longitude'])

    # Store prediction parameters
    DATA['blend_weight'] = 0.7  # Optimal from Phase 4D
    DATA['home_advantage'] = 30  # Calibrated to actual 2024-25 home win rate (54.33%)

    # Initialize Phase 4 components
    print("Initializing Phase 4 accuracy features...")

    # 1. Head-to-Head Tracker
    DATA['h2h_tracker'] = HeadToHeadTracker(
        lookback_games=DATA['h2h_lookback_games'],
        max_adjustment=DATA['h2h_max_adjustment']
    )
    print(f"  [OK] H2H Tracker (lookback={DATA['h2h_lookback_games']}, max_adj={DATA['h2h_max_adjustment']})")

    # 2. Season Calibrator
    DATA['season_calibrator'] = SeasonCalibrator(
        games_for_full_confidence=DATA['season_confidence_games'],
        min_confidence=DATA['season_min_confidence']
    )
    print(f"  [OK] Season Calibrator (games={DATA['season_confidence_games']}, min_conf={DATA['season_min_confidence']})")

    # 3. Hybrid Predictor with Adaptive Weighting
    DATA['hybrid_predictor'] = HybridPredictor(
        blend_weight=DATA['blend_weight'],
        home_advantage=DATA['home_advantage'],
        use_adaptive_weighting=DATA['use_adaptive_weighting'],
        close_game_threshold=DATA['close_game_threshold']
    )

    # Load ratings into hybrid predictor
    DATA['hybrid_predictor'].load_team_ratings('data/exports/team_elo_history_phase_1_6.csv')
    DATA['hybrid_predictor'].load_player_ratings('data/exports/player_ratings_bpm_adjusted.csv')
    print(f"  [OK] Hybrid Predictor (adaptive={DATA['use_adaptive_weighting']}, threshold={DATA['close_game_threshold']})")

    print("Phase 4 features initialized!")

    print(f"Loaded {len(DATA['team_ratings'])} teams")
    print(f"Loaded {len(DATA['player_ratings'])} players")
    print(f"Loaded {len(DATA['games'])} games")
    print("Data loading complete!")


@app.route('/')
def index():
    """Home page with overview."""
    # Calculate seasons from game data (dates stored as YYYYMMDD integers)
    games = DATA['games']
    if len(games) > 0:
        # Extract years from date integers (20251130 -> 2025)
        min_year = int(str(games['date'].min())[:4])
        max_year = int(str(games['date'].max())[:4])
        seasons = f"{min_year}-{max_year}"
        # Convert date to proper string format (YYYYMMDD -> YYYY-MM-DD)
        latest_date = games['date'].max()

        # Handle different date types (int, numpy int, Timestamp, datetime)
        if isinstance(latest_date, (int, np.integer)):
            latest_date_str = str(latest_date)
        elif hasattr(latest_date, 'strftime'):
            # It's a datetime/Timestamp, format it properly
            latest_date_str = latest_date.strftime('%Y%m%d')
        else:
            # Try converting to string and cleaning
            latest_date_str = str(latest_date).replace('-', '').split()[0]

        # Ensure it's exactly 8 digits (YYYYMMDD format)
        latest_date_str = latest_date_str.strip()
        if len(latest_date_str) == 8 and latest_date_str.isdigit():
            last_updated = f"{latest_date_str[:4]}-{latest_date_str[4:6]}-{latest_date_str[6:8]}"
        else:
            last_updated = "Unknown"
    else:
        seasons = "N/A"
        last_updated = "Unknown"

    return render_template('index.html',
                         num_teams=len(DATA['team_ratings']),
                         num_players=len(DATA['player_ratings']),
                         num_games=len(DATA['games']),
                         seasons=seasons,
                         last_updated=last_updated)


@app.route('/api/teams')
def get_teams():
    """Get all teams with current ratings."""
    teams = DATA['team_ratings'].sort_values('rating', ascending=False).to_dict('records')
    return jsonify(teams)


@app.route('/api/players')
def get_players():
    """Get top players with ratings."""
    top_n = int(request.args.get('limit', 50))
    min_games = int(request.args.get('min_games', 50))

    players = DATA['player_ratings'][DATA['player_ratings']['games_played'] >= min_games]
    players = players.sort_values('rating', ascending=False).head(top_n)

    return jsonify(players.to_dict('records'))


@app.route('/api/recent-predictions')
def get_recent_predictions():
    """Get recent game predictions with results for sidebar display."""
    try:
        # Load prediction tracking CSV
        tracking_file = Path('data/exports/prediction_tracking.csv')

        if not tracking_file.exists():
            return jsonify({'games': [], 'error': 'No predictions tracked yet'})

        df = pd.read_csv(tracking_file)

        # Filter for completed games (actual_winner is not null)
        completed = df[df['actual_winner'].notna()].copy()

        if len(completed) == 0:
            return jsonify({'games': [], 'error': 'No completed games yet'})

        # Get the most recent date
        latest_date = completed['date'].max()

        # Get all games from that date
        recent_games = completed[completed['date'] == latest_date].copy()

        # Format for frontend
        games = []
        for _, game in recent_games.iterrows():
            games.append({
                'home_team_id': int(game['home_team_id']),
                'away_team_id': int(game['away_team_id']),
                'home_team_name': game['home_team_name'],
                'away_team_name': game['away_team_name'],
                'predicted_winner': game['predicted_winner'],
                'actual_winner': game['actual_winner'],
                'correct': bool(game['correct']),
                'home_score': int(game['actual_home_score']) if pd.notna(game['actual_home_score']) else None,
                'away_score': int(game['actual_away_score']) if pd.notna(game['actual_away_score']) else None,
                'confidence': float(game['confidence']) if pd.notna(game['confidence']) else 0.5,
                'date': str(game['date'])
            })

        # Calculate summary stats for the date
        correct_count = recent_games['correct'].sum()
        total_count = len(recent_games)
        accuracy = (correct_count / total_count * 100) if total_count > 0 else 0

        return jsonify({
            'games': games,
            'summary': {
                'date': str(latest_date),
                'correct': int(correct_count),
                'total': int(total_count),
                'accuracy': f"{accuracy:.1f}%"
            }
        })

    except Exception as e:
        print(f"[ERROR] Failed to load recent predictions: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'games': [], 'error': str(e)}), 500


@app.route('/api/predict', methods=['POST'])
def predict_game():
    """Predict game outcome using hybrid predictor with P1+P2+P3 enhancements."""
    data = request.json
    home_team = int(data.get('home_team'))
    away_team = int(data.get('away_team'))
    home_injuries = data.get('home_injuries', [])
    away_injuries = data.get('away_injuries', [])
    game_date = data.get('game_date', None)

    # Get team names
    home_team_name = DATA['team_ratings'][DATA['team_ratings']['team_id'] == home_team]['team_name'].iloc[0]
    away_team_name = DATA['team_ratings'][DATA['team_ratings']['team_id'] == away_team]['team_name'].iloc[0]

    try:
        # Convert game_date to datetime if needed
        if game_date:
            if isinstance(game_date, str):
                game_date_str = game_date.replace('-', '')
                game_date = datetime.strptime(game_date_str, '%Y%m%d')
        else:
            game_date = datetime.now()

        # Use hybrid predictor with all Priority 1, 2, and 3 enhancements
        prediction = predict_game_hybrid(
            home_team_id=home_team,
            away_team_id=away_team,
            team_ratings=DATA['team_ratings'],
            player_ratings=DATA['player_ratings'],
            player_team_mapping=DATA['player_team_mapping'],
            home_injuries=home_injuries,
            away_injuries=away_injuries,
            games_history=DATA['games'],
            team_locations=DATA['team_locations'],
            game_date=game_date
        )

        # Add team names to response
        prediction['home_team_name'] = home_team_name
        prediction['away_team_name'] = away_team_name

        # Convert all numpy types to Python natives for JSON serialization
        for key, value in prediction.items():
            if isinstance(value, (np.integer, np.floating)):
                prediction[key] = float(value)
            elif isinstance(value, np.bool_):
                prediction[key] = bool(value)

        return jsonify(prediction)

    except Exception as e:
        print(f"[ERROR] Hybrid prediction failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'home_team': home_team,
            'away_team': away_team,
            'home_team_name': home_team_name,
            'away_team_name': away_team_name
        }), 500


def get_recent_rating(team_id: int, num_games: int) -> float:
    """
    Calculate team rating based on recent N games.
    Uses actual rating progression from team ELO history.

    Args:
        team_id: Team ID
        num_games: Number of recent games to consider

    Returns:
        Average rating over recent N games
    """
    team_history = DATA['team_elo_history'][DATA['team_elo_history']['team_id'] == team_id]

    # Get most recent N games, sorted by date
    recent = team_history.sort_values('date', ascending=False).head(num_games)

    if len(recent) == 0:
        # Fallback to current rating if no history
        return DATA['team_ratings'][DATA['team_ratings']['team_id'] == team_id]['rating'].iloc[0]

    # Use the average of rating_after across recent games
    # This smooths out variance while capturing recent trend
    return recent['rating_after'].mean()


@app.route('/api/team/<team_id>/history')
def team_history(team_id):
    """Get ELO rating history for a team."""
    history = DATA['team_elo_history'][DATA['team_elo_history']['team_id'] == team_id]
    history = history.sort_values('date')

    return jsonify({
        'team_id': team_id,
        'team_name': history['team_name'].iloc[0] if len(history) > 0 else team_id,
        'history': history[['date', 'rating']].to_dict('records')
    })


@app.route('/api/player/<player_id>/history')
def player_history(player_id):
    """Get ELO rating history for a player."""
    history = DATA['player_elo_history'][DATA['player_elo_history']['player_id'] == player_id]
    history = history.sort_values('date')

    return jsonify({
        'player_id': player_id,
        'player_name': history['player_name'].iloc[0] if len(history) > 0 else player_id,
        'history': history[['date', 'rating_after', 'minutes', 'plus_minus']].to_dict('records')
    })


@app.route('/api/search/players')
def search_players():
    """Search for players by name."""
    query = request.args.get('q', '').lower()

    if len(query) < 2:
        return jsonify([])

    matches = DATA['player_ratings'][
        DATA['player_ratings']['player_name'].str.lower().str.contains(query)
    ].head(20)

    return jsonify(matches[['player_id', 'player_name', 'rating', 'games_played']].to_dict('records'))


@app.route('/api/compare')
def compare_players():
    """Compare multiple players or teams."""
    entity_type = request.args.get('type', 'player')  # 'player' or 'team'
    entity_ids = request.args.get('ids', '').split(',')

    if entity_type == 'player':
        data_source = DATA['player_ratings']
        id_col = 'player_id'
        name_col = 'player_name'
    else:
        data_source = DATA['team_ratings']
        id_col = 'team_id'
        name_col = 'team_name'

    results = []
    for entity_id in entity_ids:
        if not entity_id.strip():
            continue
        match = data_source[data_source[id_col] == entity_id.strip()]
        if len(match) > 0:
            results.append(match.iloc[0].to_dict())

    return jsonify(results)


@app.route('/api/stats/summary')
def stats_summary():
    """Get overall statistics summary."""
    team_ratings = DATA['team_ratings']['rating']
    player_ratings = DATA['player_ratings']['rating']

    return jsonify({
        'teams': {
            'count': len(DATA['team_ratings']),
            'mean_rating': float(team_ratings.mean()),
            'median_rating': float(team_ratings.median()),
            'std_rating': float(team_ratings.std()),
            'min_rating': float(team_ratings.min()),
            'max_rating': float(team_ratings.max())
        },
        'players': {
            'count': len(DATA['player_ratings']),
            'mean_rating': float(player_ratings.mean()),
            'median_rating': float(player_ratings.median()),
            'std_rating': float(player_ratings.std()),
            'min_rating': float(player_ratings.min()),
            'max_rating': float(player_ratings.max())
        },
        'games': {
            'total': len(DATA['games']),
            'seasons': f"{DATA['games']['date'].min() // 10000} - {DATA['games']['date'].max() // 10000}"
        }
    })


@app.route('/api/model-performance')
def model_performance():
    """Get model performance tracking data."""
    try:
        tracker = get_tracker()

        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        last_n_days = request.args.get('last_n_days', type=int)

        # Calculate date range if last_n_days specified
        if last_n_days:
            from datetime import timedelta
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=last_n_days)).strftime('%Y%m%d')

        # Get performance summary
        summary = tracker.get_performance_summary(start_date, end_date, min_games=5)

        return jsonify(summary)
    except FileNotFoundError:
        # No tracking file yet
        return jsonify({
            'error': 'No tracking data available yet',
            'message': 'Start making predictions to begin tracking'
        }), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/model-performance/daily')
def model_performance_daily():
    """Get daily performance stats."""
    try:
        tracker = get_tracker()
        date = request.args.get('date', datetime.now().strftime('%Y%m%d'))

        stats = tracker.get_daily_stats(date)
        return jsonify(stats)
    except FileNotFoundError:
        return jsonify({
            'error': 'No tracking data available',
            'date': date
        }), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/predict')
def predict_page():
    """Game prediction interface."""
    return render_template('predict.html')


@app.route('/players')
def players_page():
    """Player rankings and search."""
    return render_template('players.html')


@app.route('/teams')
def teams_page():
    """Team rankings and comparison."""
    return render_template('teams.html')


@app.route('/visualize')
def visualize_page():
    """Data visualizations."""
    return render_template('visualize.html')


@app.route('/performance')
def performance_page():
    """Model performance tracking dashboard."""
    return render_template('performance.html')


@app.route('/performance/settings')
def performance_settings_page():
    """Phase 4 model parameters and settings monitoring."""
    return render_template('performance_settings.html')


@app.route('/api/model-settings')
def get_model_settings():
    """Get current Phase 4 model parameters and settings."""
    try:
        # Get current accuracy from prediction tracking
        tracking_file = Path('data/exports/prediction_tracking.csv')
        current_accuracy = None
        total_predictions = 0

        if tracking_file.exists():
            df = pd.read_csv(tracking_file)
            completed = df[df['actual_winner'].notna()]
            if len(completed) > 0:
                correct = completed['correct'].sum()
                total_predictions = len(completed)
                current_accuracy = (correct / total_predictions * 100)

        settings = {
            'phase4_features': {
                'h2h_tracker': {
                    'enabled': DATA['use_h2h'],
                    'lookback_games': DATA['h2h_lookback_games'],
                    'max_adjustment': DATA['h2h_max_adjustment'],
                    'description': 'Tracks recent head-to-head matchups between teams'
                },
                'adaptive_weighting': {
                    'enabled': DATA['use_adaptive_weighting'],
                    'close_game_threshold': DATA['close_game_threshold'],
                    'close_weights': DATA['hybrid_predictor'].close_game_weights if DATA['hybrid_predictor'] else {},
                    'default_weights': DATA['hybrid_predictor'].default_weights if DATA['hybrid_predictor'] else {},
                    'description': 'Different weights for close vs non-close games'
                },
                'season_calibration': {
                    'enabled': DATA['use_season_calibration'],
                    'games_for_full_confidence': DATA['season_confidence_games'],
                    'min_confidence': DATA['season_min_confidence'],
                    'description': 'Reduces confidence early in season'
                }
            },
            'core_parameters': {
                'blend_weight': DATA['blend_weight'],
                'home_advantage': DATA['home_advantage'],
                'team_elo_k_factor': DATA['elo_engine'].k_factor if DATA['elo_engine'] else 20,
                'use_mov': DATA['elo_engine'].use_mov if DATA['elo_engine'] else True,
                'use_enhanced_features': DATA['elo_engine'].use_enhanced_features if DATA['elo_engine'] else True
            },
            'performance_metrics': {
                'current_accuracy': f"{current_accuracy:.2f}%" if current_accuracy else "N/A",
                'total_predictions': total_predictions,
                'target_accuracy': "68-70%",
                'industry_baseline': "68-72%"
            },
            'data_status': {
                'teams_tracked': len(DATA['team_ratings']) if DATA['team_ratings'] is not None else 0,
                'players_tracked': len(DATA['player_ratings']) if DATA['player_ratings'] is not None else 0,
                'games_in_database': len(DATA['games']) if DATA['games'] is not None else 0,
                'latest_game_date': str(DATA['games']['date'].max()) if DATA['games'] is not None and len(DATA['games']) > 0 else 'Unknown'
            }
        }

        return jsonify(settings)

    except Exception as e:
        print(f"[ERROR] Failed to get model settings: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/model-settings/update', methods=['POST'])
def update_model_settings():
    """Update Phase 4 model settings (feature toggles only, not parameters)."""
    try:
        data = request.json

        # Update feature toggles
        if 'use_h2h' in data:
            DATA['use_h2h'] = bool(data['use_h2h'])

        if 'use_adaptive_weighting' in data:
            DATA['use_adaptive_weighting'] = bool(data['use_adaptive_weighting'])
            # Update hybrid predictor
            if DATA['hybrid_predictor']:
                DATA['hybrid_predictor'].use_adaptive_weighting = DATA['use_adaptive_weighting']

        if 'use_season_calibration' in data:
            DATA['use_season_calibration'] = bool(data['use_season_calibration'])

        return jsonify({
            'success': True,
            'message': 'Settings updated successfully',
            'settings': {
                'use_h2h': DATA['use_h2h'],
                'use_adaptive_weighting': DATA['use_adaptive_weighting'],
                'use_season_calibration': DATA['use_season_calibration']
            }
        })

    except Exception as e:
        print(f"[ERROR] Failed to update settings: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/past-games')
def past_games_page():
    """View past games with predictions and results."""
    return render_template('past_games.html')


@app.route('/api/past-games')
def get_past_games():
    """Get past games with predictions and results, with optional date filter."""
    try:
        days = request.args.get('days', '7')  # Default to last 7 days

        # Load prediction tracking CSV
        tracking_file = Path('data/exports/prediction_tracking.csv')

        if not tracking_file.exists():
            return jsonify({'games': [], 'error': 'No predictions tracked yet', 'summary': {}})

        df = pd.read_csv(tracking_file)

        # Filter for completed games
        completed = df[df['actual_winner'].notna()].copy()

        if len(completed) == 0:
            return jsonify({'games': [], 'error': 'No completed games yet', 'summary': {}})

        # Convert date to datetime (format: YYYYMMDD)
        completed['date'] = pd.to_datetime(completed['date'], format='%Y%m%d')

        # Filter by days if not "all"
        if days != 'all':
            days_int = int(days)
            # For "yesterday" (days=1), we want games from yesterday specifically
            # So we look at games from the last 2 days to ensure we catch yesterday's games
            if days_int == 1:
                cutoff_date = datetime.now() - timedelta(days=2)
            else:
                cutoff_date = datetime.now() - timedelta(days=days_int)
            filtered = completed[completed['date'] >= cutoff_date].copy()
        else:
            filtered = completed.copy()

        # Sort by date descending
        filtered = filtered.sort_values('date', ascending=False)

        # Format for frontend
        games = []
        for _, game in filtered.iterrows():
            games.append({
                'home_team_id': int(game['home_team_id']),
                'away_team_id': int(game['away_team_id']),
                'home_team_name': game['home_team_name'],
                'away_team_name': game['away_team_name'],
                'predicted_winner': game['predicted_winner'],
                'actual_winner': game['actual_winner'],
                'correct': bool(game['correct']),
                'home_score': int(game['actual_home_score']) if pd.notna(game['actual_home_score']) else None,
                'away_score': int(game['actual_away_score']) if pd.notna(game['actual_away_score']) else None,
                'confidence': float(game['confidence']) if pd.notna(game['confidence']) else 0.5,
                'date': game['date'].strftime('%Y-%m-%d'),
                'predicted_home_prob': float(game['predicted_home_prob']) if pd.notna(game.get('predicted_home_prob')) else 0.5,
                'predicted_away_prob': float(game['predicted_away_prob']) if pd.notna(game.get('predicted_away_prob')) else 0.5,
            })

        # Calculate summary stats
        correct_count = filtered['correct'].sum()
        total_count = len(filtered)
        accuracy = (correct_count / total_count * 100) if total_count > 0 else 0

        return jsonify({
            'games': games,
            'summary': {
                'correct': int(correct_count),
                'total': int(total_count),
                'accuracy': f"{accuracy:.1f}%",
                'period': f"Last {days} days" if days != 'all' else "All time"
            }
        })

    except Exception as e:
        print(f"[ERROR] Failed to load past games: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'games': [], 'error': str(e), 'summary': {}}), 500


@app.route('/api/game-players')
def get_game_players():
    """Get game-specific player data including top scorers and DNP players."""
    try:
        home_team_id = int(request.args.get('home_team_id'))
        away_team_id = int(request.args.get('away_team_id'))
        game_date = request.args.get('game_date')  # Format: YYYYMMDD

        # Load games data to find the specific game_id
        games_file = Path('data/raw/nba_games_all.csv')
        if not games_file.exists():
            return jsonify({'error': 'Games data not available'}), 404

        games_df = pd.read_csv(games_file)

        # Find the game_id for this matchup on this date
        game = games_df[
            (games_df['home_team_id'] == home_team_id) &
            (games_df['away_team_id'] == away_team_id) &
            (games_df['date'].astype(str) == str(game_date))
        ]

        if game.empty:
            print(f"[WARNING] No game found for home={home_team_id}, away={away_team_id}, date={game_date}")
            return get_team_roster_fallback(home_team_id, away_team_id)

        game_id = game.iloc[0]['game_id']
        home_team_name = game.iloc[0]['home_team_name']
        away_team_name = game.iloc[0]['away_team_name']

        # Load box score data
        boxscore_file = Path('data/raw/player_boxscores_all.csv')
        if not boxscore_file.exists():
            print(f"[WARNING] Box score file not found")
            return get_team_roster_fallback(home_team_id, away_team_id)

        boxscores_df = pd.read_csv(boxscore_file, low_memory=False)

        # Filter for this specific game by game_id
        game_boxscores = boxscores_df[boxscores_df['game_id'] == game_id]

        # If not found by game_id, try matching by date and teams
        # (older games may have different game_id format)
        if game_boxscores.empty:
            print(f"[INFO] No box scores found for game_id={game_id}, trying date/team match...")

            # Load all games with dates to find matching game_id in boxscores
            # We need to find the NBA API game_id that corresponds to this date/matchup
            from nba_api.stats.endpoints import scoreboardv2
            try:
                # Try to fetch the scoreboard for this specific date
                game_date_obj = pd.to_datetime(game_date, format='%Y%m%d')
                scoreboard = scoreboardv2.ScoreboardV2(
                    game_date=game_date_obj.strftime('%m/%d/%Y'),
                    timeout=10
                )
                line_score = scoreboard.get_data_frames()[1]

                # Find the matching game in the scoreboard
                for nba_game_id in line_score['GAME_ID'].unique():
                    game_teams = line_score[line_score['GAME_ID'] == nba_game_id]
                    if len(game_teams) >= 2:
                        # Check if teams match (first row is away, second is home)
                        nba_home_team = game_teams.iloc[1]['TEAM_CITY_NAME'] + ' ' + game_teams.iloc[1]['TEAM_NAME']
                        nba_away_team = game_teams.iloc[0]['TEAM_CITY_NAME'] + ' ' + game_teams.iloc[0]['TEAM_NAME']

                        if nba_home_team == home_team_name and nba_away_team == away_team_name:
                            # Found the matching game! Use this game_id
                            print(f"[INFO] Found NBA API game_id: {nba_game_id} for {away_team_name} @ {home_team_name}")
                            game_boxscores = boxscores_df[boxscores_df['game_id'] == int(nba_game_id)]
                            break
            except Exception as e:
                print(f"[WARNING] Could not fetch live game_id: {e}")

        if game_boxscores.empty:
            print(f"[WARNING] No box scores found for {away_team_name} @ {home_team_name} on {game_date}")
            return get_team_roster_fallback(home_team_id, away_team_id)

        # Create NBA API team abbreviation to our team name mapping
        # Map team abbreviations from box scores to full team names
        team_abbr_to_name = {
            'ATL': 'Atlanta Hawks', 'BOS': 'Boston Celtics', 'BKN': 'Brooklyn Nets',
            'CHA': 'Charlotte Hornets', 'CHI': 'Chicago Bulls', 'CLE': 'Cleveland Cavaliers',
            'DAL': 'Dallas Mavericks', 'DEN': 'Denver Nuggets', 'DET': 'Detroit Pistons',
            'GSW': 'Golden State Warriors', 'HOU': 'Houston Rockets', 'IND': 'Indiana Pacers',
            'LAC': 'Los Angeles Clippers', 'LAL': 'Los Angeles Lakers', 'MEM': 'Memphis Grizzlies',
            'MIA': 'Miami Heat', 'MIL': 'Milwaukee Bucks', 'MIN': 'Minnesota Timberwolves',
            'NOP': 'New Orleans Pelicans', 'NYK': 'New York Knicks', 'OKC': 'Oklahoma City Thunder',
            'ORL': 'Orlando Magic', 'PHI': 'Philadelphia 76ers', 'PHX': 'Phoenix Suns',
            'POR': 'Portland Trail Blazers', 'SAC': 'Sacramento Kings', 'SAS': 'San Antonio Spurs',
            'TOR': 'Toronto Raptors', 'UTA': 'Utah Jazz', 'WAS': 'Washington Wizards'
        }

        # Map box score team abbreviations to our team names
        game_boxscores['mapped_team_name'] = game_boxscores['team_name'].map(team_abbr_to_name)

        # Separate home and away players by matching team names
        home_boxscores = game_boxscores[game_boxscores['mapped_team_name'] == home_team_name]
        away_boxscores = game_boxscores[game_boxscores['mapped_team_name'] == away_team_name]

        # Get top 3 scorers for each team (players who actually played)
        home_played = home_boxscores[home_boxscores['didNotPlay'] == False]
        away_played = away_boxscores[away_boxscores['didNotPlay'] == False]

        home_top_scorers = home_played.nlargest(3, 'points')
        away_top_scorers = away_played.nlargest(3, 'points')

        # Get DNP players
        home_dnp = home_boxscores[home_boxscores['didNotPlay'] == True]
        away_dnp = away_boxscores[away_boxscores['didNotPlay'] == True]

        # Calculate team records up to this game date (current season only)
        game_date_obj = pd.to_datetime(game_date, format='%Y%m%d')
        games_df['date'] = pd.to_datetime(games_df['date'], format='%Y%m%d')

        # Determine current season based on game date
        # NBA season runs Oct-June, so if month >= 10, it's the start of season (year-year+1)
        # Otherwise it's the end of season (year-1-year)
        if game_date_obj.month >= 10:
            season_start = pd.to_datetime(f"{game_date_obj.year}1001", format='%Y%m%d')
        else:
            season_start = pd.to_datetime(f"{game_date_obj.year - 1}1001", format='%Y%m%d')

        # Get games from current season before this date, regular season only
        games_before = games_df[
            (games_df['date'] >= season_start) &
            (games_df['date'] < game_date_obj) &
            (games_df['season_type'] == 'regular')
        ]

        # Calculate home team record
        home_games = games_before[
            (games_before['home_team_id'] == home_team_id) |
            (games_before['away_team_id'] == home_team_id)
        ]
        home_wins = len(home_games[home_games['winner_team_id'] == home_team_id])
        home_losses = len(home_games[home_games['winner_team_id'].notna()]) - home_wins

        # Calculate away team record
        away_games = games_before[
            (games_before['home_team_id'] == away_team_id) |
            (games_before['away_team_id'] == away_team_id)
        ]
        away_wins = len(away_games[away_games['winner_team_id'] == away_team_id])
        away_losses = len(away_games[away_games['winner_team_id'].notna()]) - away_wins

        response = {
            'home_team_record': f"{home_wins}-{home_losses}",
            'away_team_record': f"{away_wins}-{away_losses}",
            'home_top_scorers': [
                {
                    'name': row['player_name'],
                    'points': int(row['points']) if pd.notna(row['points']) else 0,
                    'rebounds': int(row['rebounds']) if pd.notna(row['rebounds']) else 0,
                    'assists': int(row['assists']) if pd.notna(row['assists']) else 0,
                    'position': row['position'] if pd.notna(row.get('position')) else ''
                }
                for _, row in home_top_scorers.iterrows()
            ],
            'away_top_scorers': [
                {
                    'name': row['player_name'],
                    'points': int(row['points']) if pd.notna(row['points']) else 0,
                    'rebounds': int(row['rebounds']) if pd.notna(row['rebounds']) else 0,
                    'assists': int(row['assists']) if pd.notna(row['assists']) else 0,
                    'position': row['position'] if pd.notna(row.get('position')) else ''
                }
                for _, row in away_top_scorers.iterrows()
            ],
            'home_injuries': [
                {
                    'name': row['player_name'],
                    'position': row['position'] if pd.notna(row.get('position')) else ''
                }
                for _, row in home_dnp.iterrows()
            ],
            'away_injuries': [
                {
                    'name': row['player_name'],
                    'position': row['position'] if pd.notna(row.get('position')) else ''
                }
                for _, row in away_dnp.iterrows()
            ]
        }

        return jsonify(response)

    except Exception as e:
        print(f"[ERROR] Failed to load game players: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def get_team_roster_fallback(home_team_id, away_team_id):
    """Fallback to team roster data when box scores aren't available."""
    try:
        player_file = Path('data/exports/player_team_mapping_with_elo.csv')
        if not player_file.exists():
            return jsonify({'error': 'Player data not available'}), 404

        players_df = pd.read_csv(player_file)

        # Get top 3 players by ELO for each team
        home_players = players_df[players_df['team_id'] == home_team_id].nlargest(3, 'rating')
        away_players = players_df[players_df['team_id'] == away_team_id].nlargest(3, 'rating')

        response = {
            'home_top_scorers': [
                {
                    'name': row['player_name'],
                    'elo': float(row['rating']),
                    'position': row['position'] if pd.notna(row.get('position')) else 'N/A'
                }
                for _, row in home_players.iterrows()
            ],
            'away_top_scorers': [
                {
                    'name': row['player_name'],
                    'elo': float(row['rating']),
                    'position': row['position'] if pd.notna(row.get('position')) else 'N/A'
                }
                for _, row in away_players.iterrows()
            ],
            'home_injuries': [],
            'away_injuries': [],
            'note': 'Box scores for this game not yet fetched. Run Quick Update to fetch recent box scores (1-2 min) or Full Update for entire season (5-10 min). Showing top 3 players by ELO rating as fallback.'
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/betting')
def betting_page():
    """Daily betting recommendations interface."""
    return render_template('betting.html')


@app.route('/api/betting/test')
def test_endpoint():
    """Test endpoint to debug routing."""
    return jsonify({'status': 'ok', 'message': 'Test endpoint works!'})


@app.route('/api/betting/daily-recommendations')
def get_daily_betting_recommendations():
    """Get daily low-risk betting recommendations using live NBA schedule data."""
    print("[BETTING ENDPOINT] Called!", flush=True)
    try:
        from nba_api.stats.endpoints import scoreboardv2

        date_str = request.args.get('date', 'today')
        print(f"[BETTING] Requested date: {date_str}", flush=True)

        # Parse date
        if date_str == 'today':
            target_date = datetime.now()
        elif date_str == 'tomorrow':
            target_date = datetime.now() + timedelta(days=1)
        else:
            target_date = datetime.strptime(date_str, '%Y-%m-%d')

        # Fetch live NBA schedule for target date with retry logic
        print(f"[BETTING] Fetching NBA schedule for {target_date.strftime('%Y-%m-%d')}...", flush=True)

        max_retries = 3
        retry_delay = 2
        line_score = None

        for attempt in range(max_retries):
            try:
                scoreboard = scoreboardv2.ScoreboardV2(
                    game_date=target_date.strftime('%m/%d/%Y'),
                    timeout=30
                )
                print("[BETTING] Scoreboard fetched, getting dataframes...", flush=True)
                line_score = scoreboard.get_data_frames()[1]  # LineScore has team details
                print(f"[BETTING] Line score has {len(line_score)} rows", flush=True)
                break  # Success!
            except Exception as e:
                print(f"[BETTING] Attempt {attempt + 1}/{max_retries} failed: {e}", flush=True)
                if attempt < max_retries - 1:
                    import time
                    print(f"[BETTING] Retrying in {retry_delay} seconds...", flush=True)
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise Exception(f"NBA API connection failed after {max_retries} attempts. The NBA API may be temporarily unavailable. Please try again in a few minutes.")

        # Create team name to ID mapping from our database
        team_name_to_id = {}
        for _, team in DATA['team_ratings'][['team_id', 'team_name']].drop_duplicates().iterrows():
            team_name_to_id[team['team_name']] = team['team_id']

        # Add team name variations (NBA API vs our database)
        team_name_variations = {
            'LA Clippers': 'Los Angeles Clippers',
        }
        for nba_name, db_name in team_name_variations.items():
            if db_name in team_name_to_id:
                team_name_to_id[nba_name] = team_name_to_id[db_name]

        # Group by game_id to get matchups (each game has 2 rows - home and away)
        games = []
        for game_id in line_score['GAME_ID'].unique():
            game_teams = line_score[line_score['GAME_ID'] == game_id]

            # Only process if game hasn't been played (PTS is None for scheduled games)
            if game_teams.iloc[0]['PTS'] is None:
                # First row is away team, second is home team in NBA API
                away_team = game_teams.iloc[0]
                home_team = game_teams.iloc[1]

                # Build team names
                home_team_name = home_team['TEAM_CITY_NAME'] + ' ' + home_team['TEAM_NAME']
                away_team_name = away_team['TEAM_CITY_NAME'] + ' ' + away_team['TEAM_NAME']

                # Map to our database team IDs
                home_team_id = team_name_to_id.get(home_team_name)
                away_team_id = team_name_to_id.get(away_team_name)

                if home_team_id is None or away_team_id is None:
                    print(f"[WARNING] Team not found in database: {home_team_name if home_team_id is None else away_team_name}", flush=True)
                    continue

                games.append({
                    'game_id': game_id,
                    'home_team_id': int(home_team_id),
                    'home_team_name': home_team_name,
                    'away_team_id': int(away_team_id),
                    'away_team_name': away_team_name,
                })

        print(f"[BETTING] Found {len(games)} scheduled games")

        # Fetch injury data once for all games
        print("[BETTING] Fetching injury data from ESPN...", flush=True)
        injury_data = get_injury_report()

        # Generate predictions for each game
        predictions = []
        for game in games:
            try:
                # Get injuries for both teams
                home_injuries = get_key_injuries_for_team(game['home_team_name'], injury_data)
                away_injuries = get_key_injuries_for_team(game['away_team_name'], injury_data)

                # Extract just player names for the prediction function
                home_injury_names = [inj['name'] for inj in home_injuries if inj.get('status') in ['Out', 'Questionable']]
                away_injury_names = [inj['name'] for inj in away_injuries if inj.get('status') in ['Out', 'Questionable']]

                prediction = predict_game_hybrid(
                    home_team_id=game['home_team_id'],
                    away_team_id=game['away_team_id'],
                    team_ratings=DATA['team_ratings'],
                    player_ratings=DATA['player_ratings'],
                    player_team_mapping=DATA['player_team_mapping'],
                    home_injuries=home_injury_names,
                    away_injuries=away_injury_names,
                    games_history=DATA['games'],
                    team_locations=DATA['team_locations'],
                    game_date=target_date
                )

                # Determine predicted winner
                predicted_winner = game['home_team_name'] if prediction['home_win_probability'] > 0.5 else game['away_team_name']

                predictions.append({
                    'game_id': game['game_id'],
                    'date': target_date.strftime('%Y-%m-%d'),
                    'home_team_id': game['home_team_id'],
                    'home_team_name': game['home_team_name'],
                    'away_team_id': game['away_team_id'],
                    'away_team_name': game['away_team_name'],
                    'predicted_home_prob': prediction['home_win_probability'],
                    'predicted_away_prob': prediction['away_win_probability'],
                    'predicted_winner': predicted_winner,
                    'confidence': prediction['confidence']
                })
                print(f"[BETTING] Predicted: {game['away_team_name']} @ {game['home_team_name']} -> {predicted_winner} ({prediction['home_win_probability']:.1%})", flush=True)
            except Exception as e:
                print(f"[ERROR] Failed to predict game {game['game_id']}: {e}")
                continue

        # Generate betting analysis
        analyzer = BettingAnalyzer()
        report = analyzer.generate_betting_report(predictions)

        return jsonify(report)

    except Exception as e:
        print(f"[ERROR] Failed to generate betting recommendations: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to generate recommendations: {str(e)}'}), 500


@app.route('/api/betting/market-odds')
def get_market_odds():
    """Fetch live market odds from The Odds API."""
    print("[MARKET ODDS] Fetching odds from The Odds API...", flush=True)
    try:
        from scrapers.odds_api_fetcher import fetch_nba_odds, get_consensus_probability

        # API key from odds_api_fetcher.py
        API_KEY = 'e1607aa8757797d0b22b442b975b781b'

        # Fetch odds
        result = fetch_nba_odds(API_KEY)

        if not result['success']:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to fetch odds')
            }), 500

        games = result['games']
        print(f"[MARKET ODDS] Found {len(games)} games with odds", flush=True)

        # Transform odds data for frontend
        odds_by_team = {}
        for game in games:
            home_team = game.get('home_team', '')
            away_team = game.get('away_team', '')

            # Get consensus probabilities
            home_consensus = get_consensus_probability(game, home_team)
            away_consensus = get_consensus_probability(game, away_team)

            if home_consensus and away_consensus:
                # Store by team name for easy lookup
                odds_by_team[home_team] = {
                    'probability': home_consensus['probability'],
                    'american_odds': home_consensus['odds'],
                    'decimal_odds': 1 / home_consensus['probability'] if home_consensus['probability'] > 0 else 0,
                    'num_bookmakers': home_consensus['num_books'],
                    'opponent': away_team
                }
                odds_by_team[away_team] = {
                    'probability': away_consensus['probability'],
                    'american_odds': away_consensus['odds'],
                    'decimal_odds': 1 / away_consensus['probability'] if away_consensus['probability'] > 0 else 0,
                    'num_bookmakers': away_consensus['num_books'],
                    'opponent': home_team
                }

        return jsonify({
            'success': True,
            'games_count': len(games),
            'odds_by_team': odds_by_team,
            'credits_used': result.get('credits_used', 'unknown'),
            'credits_remaining': result.get('credits_remaining', 'unknown')
        })

    except Exception as e:
        print(f"[ERROR] Failed to fetch market odds: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/newsletter')
def newsletter_page():
    """Newsletter generator interface."""
    return render_template('newsletter.html')


@app.route('/api/newsletter/generate', methods=['POST'])
def generate_newsletter_api():
    """Generate newsletter for specified date."""
    import subprocess
    from datetime import datetime, timedelta

    data = request.json
    date_str = data.get('date')

    # Validate date
    try:
        if date_str == 'today':
            target_date = datetime.now().strftime('%Y-%m-%d')
        elif date_str == 'tomorrow':
            target_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            # Validate custom date format
            datetime.strptime(date_str, '%Y-%m-%d')
            target_date = date_str
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    # Generate output filename
    output_file = f"newsletters/newsletter_{target_date}.md"

    # Run newsletter generation script
    try:
        result = subprocess.run(
            ['python', 'scripts/export_substack_daily.py', '--date', target_date, '--output', output_file],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return jsonify({'error': f'Generation failed: {result.stderr}'}), 500

        # Read generated newsletter
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()

        return jsonify({
            'success': True,
            'date': target_date,
            'filename': output_file,
            'content': content,
            'message': f'Newsletter generated for {target_date}'
        })

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Generation timed out'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/newsletter/list')
def list_newsletters():
    """List all generated newsletters."""
    import glob

    newsletter_files = glob.glob('newsletters/newsletter_*.md')
    newsletters = []

    for filepath in sorted(newsletter_files, reverse=True):
        filename = os.path.basename(filepath)
        date_str = filename.replace('newsletter_', '').replace('.md', '')

        # Get file size and modification time
        stat = os.stat(filepath)

        newsletters.append({
            'date': date_str,
            'filename': filename,
            'filepath': filepath,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        })

    return jsonify(newsletters)


@app.route('/api/newsletter/premium/generate', methods=['POST'])
def generate_premium_newsletter_api():
    """Generate premium newsletter for specified date."""
    import subprocess
    from datetime import datetime, timedelta

    data = request.json
    date_str = data.get('date')

    # Validate date
    try:
        if date_str == 'today':
            target_date = datetime.now().strftime('%Y-%m-%d')
        elif date_str == 'tomorrow':
            target_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            # Validate custom date format
            datetime.strptime(date_str, '%Y-%m-%d')
            target_date = date_str
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    # Generate output filename
    output_file = f"newsletters/premium_{target_date}.md"

    # Run premium newsletter generation script
    try:
        result = subprocess.run(
            ['python', 'scripts/export_substack_premium.py', '--date', target_date, '--output', output_file],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return jsonify({'error': f'Generation failed: {result.stderr}'}), 500

        # Read generated newsletter with proper encoding
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Fallback: try with different encoding
            with open(output_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

        return jsonify({
            'success': True,
            'date': target_date,
            'filename': output_file,
            'content': content,
            'message': f'Premium newsletter generated for {target_date}'
        })

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Generation timed out'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/newsletter/premium/list')
def list_premium_newsletters():
    """List all generated premium newsletters."""
    import glob

    newsletter_files = glob.glob('newsletters/premium_*.md')
    newsletters = []

    for filepath in sorted(newsletter_files, reverse=True):
        filename = os.path.basename(filepath)
        date_str = filename.replace('premium_', '').replace('.md', '')

        # Get file size and modification time
        stat = os.stat(filepath)

        newsletters.append({
            'date': date_str,
            'filename': filename,
            'filepath': filepath,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        })

    return jsonify(newsletters)




@app.route('/predict/today')
def predict_today():
    """Display today's games in styled table format."""
    return render_template('predict_today.html')


@app.route('/predict/season')
def predict_season():
    """Season predictions page with Monte Carlo simulation."""
    return render_template('season_prediction.html')


@app.route('/api/predict/today')
def api_predict_today():
    """API endpoint to get today's game predictions with injury impact analysis."""
    try:
        from datetime import datetime, timedelta
        from src.scrapers.nba_api_data_fetcher import get_todays_games

        # Get date parameter (default to 'today')
        date_str = request.args.get('date', 'today')

        # Calculate target date
        if date_str == 'today':
            target_date = datetime.now()
        elif date_str == 'tomorrow':
            target_date = datetime.now() + timedelta(days=1)
        else:
            # Custom date format (YYYY-MM-DD)
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use "today", "tomorrow", or YYYY-MM-DD'}), 400

        # Format date for NBA API (expects YYYY-MM-DD)
        formatted_date = target_date.strftime('%Y-%m-%d')

        # Helper function for injury impact using real ESPN injury data
        def get_injury_impact_analysis(team_name, player_ratings, player_team_mapping, injury_data=None):
            """
            Get actual injured players from ESPN and calculate their ELO impact.
            Falls back to top 3 players if no injury data available.
            """
            try:
                # Fetch injury data if not provided
                if injury_data is None:
                    injury_data = get_injury_report()

                # Get actual injured players for this team from ESPN
                # The new ESPN scraper directly scrapes team-specific pages, so data is already correct
                espn_injured_players = injury_data.get(team_name, [])

                # Filter to "Out" status players (most impactful)
                out_players = [p for p in espn_injured_players if p['status'].lower() in ['out', 'day to day', 'questionable']]

                if len(out_players) == 0:
                    # No injuries - fall back to top 3 players as potential impact
                    team_players = player_team_mapping[player_team_mapping['team_name'] == team_name].copy()
                    if len(team_players) == 0:
                        return []

                    team_player_ratings = player_ratings.merge(
                        team_players[['player_name', 'position']],
                        on='player_name',
                        how='inner',
                        suffixes=('', '_mapping')
                    )

                    team_player_ratings = team_player_ratings.dropna(subset=['rating'])
                    if len(team_player_ratings) == 0:
                        return []

                    top_players = team_player_ratings.nlargest(3, 'rating')
                else:
                    # Use actual injured players - show ALL significant injuries (ELO > 1550)
                    top_players = []
                    for injured in out_players:  # All injured players
                        # Look up player rating
                        player_rating = player_ratings[player_ratings['player_name'] == injured['name']]

                        if len(player_rating) > 0:
                            rating = player_rating.iloc[0]['rating']
                            # Only include players with significant impact (ELO > 1550)
                            # This filters out G-League/bench players while keeping rotation players
                            if rating > 1550:
                                top_players.append({
                                    'player_name': injured['name'],
                                    'rating': rating,
                                    'position': injured['position'],
                                    'status': injured['status']
                                })

                    # Sort by rating descending to show most impactful first
                    top_players = sorted(top_players, key=lambda x: x['rating'], reverse=True)

                # Calculate impact for each player
                analysis = []
                for player in top_players:
                    if isinstance(player, dict):
                        # From injured players
                        rating = player['rating']
                        name = player['player_name']
                        position = player['position']
                        status = player.get('status', 'Top Player')
                    else:
                        # From DataFrame (top players fallback)
                        rating = player['rating']
                        name = player['player_name']
                        position = player.get('position', 'N/A')
                        status = 'Top Player'

                    impact = (rating - 1500) * 0.3  # 30% player contribution
                    analysis.append({
                        'name': name,
                        'elo': float(rating),
                        'impact': float(impact),
                        'impact_percent': float((impact / 400) * 100),
                        'position': position,
                        'status': status
                    })

                return analysis
            except Exception as e:
                print(f"[ERROR] Injury impact analysis failed for {team_name}: {str(e)}")
                return []

        # Get games from NBA API for the specified date
        try:
            games = get_todays_games(formatted_date)
            if len(games) == 0:
                print(f"[INFO] No games scheduled for {date_str}")
        except Exception as e:
            print(f"[ERROR] Failed to fetch games from NBA API for {date_str}: {e}")
            print("[INFO] Returning empty game list")
            games = []

        # Fetch injury data once for all teams
        print("[INFO] Fetching injury data from ESPN...")
        injury_data = get_injury_report()
        print(f"[INFO] Injury data fetched for {len(injury_data)} teams")

        # Generate predictions for each game
        predictions = []

        # Get today's date in YYYYMMDD format for rest penalty calculation
        today_date = int(datetime.now().strftime('%Y%m%d'))

        for game in games:
            # Use enhanced ELO engine to get prediction with form and rest
            try:
                prediction = DATA['elo_engine'].predict_game(
                    home_team_id=game['home_id'],
                    away_team_id=game['away_id'],
                    game_date=today_date
                )

                home_rating = prediction['home_rating']
                away_rating = prediction['away_rating']
                home_win_prob = prediction['home_win_probability']

                # Extract enhanced features
                home_form_adj = prediction.get('home_form_adjustment', 0)
                away_form_adj = prediction.get('away_form_adjustment', 0)
                home_rest_penalty = prediction.get('home_rest_penalty', 0)
                away_rest_penalty = prediction.get('away_rest_penalty', 0)
                home_adjusted = prediction.get('home_adjusted_rating', home_rating)
                away_adjusted = prediction.get('away_adjusted_rating', away_rating)

            except (ValueError, KeyError):
                # Fallback to basic rating if team not in engine
                home_rating = DATA['team_ratings'][DATA['team_ratings']['team_id'] == game['home_id']]['rating'].iloc[0]
                away_rating = DATA['team_ratings'][DATA['team_ratings']['team_id'] == game['away_id']]['rating'].iloc[0]

                rating_diff = home_rating - away_rating + DATA['home_advantage']
                home_win_prob = 1 / (1 + 10 ** (-rating_diff / 400))

                home_form_adj = 0
                away_form_adj = 0
                home_rest_penalty = 0
                away_rest_penalty = 0
                home_adjusted = home_rating
                away_adjusted = away_rating

            # Get injury impact analysis with real injury data
            home_injuries = get_injury_impact_analysis(
                game['home_team'],
                DATA['player_ratings'],
                DATA['player_team_mapping'],
                injury_data
            )
            away_injuries = get_injury_impact_analysis(
                game['away_team'],
                DATA['player_ratings'],
                DATA['player_team_mapping'],
                injury_data
            )

            predictions.append({
                'time': game['time'],
                'home_team': game['home_team'],
                'away_team': game['away_team'],
                'home_win_prob': float(home_win_prob),
                'away_win_prob': float(1 - home_win_prob),
                'home_rating': float(home_rating),
                'away_rating': float(away_rating),
                'home_adjusted_rating': float(home_adjusted),
                'away_adjusted_rating': float(away_adjusted),
                'home_form_adjustment': float(home_form_adj),
                'away_form_adjustment': float(away_form_adj),
                'home_rest_penalty': float(home_rest_penalty),
                'away_rest_penalty': float(away_rest_penalty),
                'home_injuries': home_injuries,
                'away_injuries': away_injuries,
                'status': game.get('status', 'Scheduled'),
                'game_status_code': game.get('game_status_code', 1)
            })

        return jsonify({'games': predictions})

    except Exception as e:
        import traceback
        print(f"Error in api_predict_today: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/admin/update-database', methods=['POST'])
def admin_update_database():
    """Quick incremental update - fetch new games and update predictions (30-60 seconds)."""
    try:
        from datetime import datetime
        import time

        start_time = time.time()
        results = []

        # Step 1: Fetch new games from NBA API (fast)
        results.append("[STEP 1/3] Fetching new games from NBA API...")
        try:
            from src.scrapers.nba_game_fetcher import fetch_missing_games
            num_new = fetch_missing_games()
            if num_new > 0:
                results.append(f"[OK] Fetched {num_new} new games")
            else:
                results.append("[OK] No new games available")
        except Exception as e:
            results.append(f"[WARNING] Game fetch had issues: {str(e)}")

        # Step 2: Fetch box scores for recent games (fast - only missing games)
        results.append("\n[STEP 2/4] Fetching box scores for recent games...")
        try:
            import subprocess
            boxscore_result = subprocess.run(
                [sys.executable, 'scripts/fetch_recent_boxscores.py', '--days', '7'],
                capture_output=True,
                text=True,
                encoding='utf-8',  # Fix Unicode encoding on Windows
                timeout=90  # Allow up to 90 seconds for box scores
            )
            if boxscore_result.returncode == 0:
                # Extract summary line
                for line in boxscore_result.stdout.split('\n'):
                    if 'Successfully fetched' in line or 'Player records added' in line or 'already have box scores' in line:
                        results.append(f"  {line.strip()}")
            else:
                results.append("[WARNING] Box score fetch had issues")
        except Exception as e:
            results.append(f"[WARNING] Box score fetch error: {str(e)}")

        # Step 3: Update prediction tracking (fast)
        results.append("\n[STEP 3/4] Updating prediction tracking...")
        try:
            import subprocess
            tracking_result = subprocess.run(
                [sys.executable, 'scripts/auto_track_predictions.py'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if tracking_result.returncode == 0:
                # Extract summary
                for line in tracking_result.stdout.split('\n'):
                    if 'Tracked' in line or 'Accuracy' in line:
                        results.append(f"  {line.strip()}")
            else:
                results.append("[WARNING] Prediction tracking had issues")
        except Exception as e:
            results.append(f"[WARNING] Prediction tracking error: {str(e)}")

        # Step 4: Reload data into Flask (fast)
        results.append("\n[STEP 4/4] Reloading data into web interface...")
        try:
            load_data()
            latest_date = DATA['games']['date'].max()
            results.append(f"[OK] Data reloaded: {len(DATA['games'])} games, latest: {latest_date}")
        except Exception as e:
            results.append(f"[ERROR] Data reload failed: {str(e)}")

        elapsed = time.time() - start_time
        results.append(f"\n[OK] Quick update complete in {elapsed:.1f} seconds")
        results.append("\nNote: ELO ratings will be recalculated on next full update.")

        return jsonify({
            'success': True,
            'message': '\n'.join(results),
            'elapsed_seconds': round(elapsed, 1),
            'games_fetched': num_new if 'num_new' in locals() else 0
        })

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'details': error_details
        }), 500


@app.route('/admin/full-update', methods=['POST'])
def admin_full_update():
    """Trigger full database update with ELO recalc (runs in background, 5-10 min)."""
    try:
        import subprocess
        import os

        # Run daily update script in background
        process = subprocess.Popen(
            ['python', 'scripts/daily_update.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=os.path.dirname(os.path.abspath(__file__))
        )

        # Store process for status checking
        global UPDATE_PROCESS
        UPDATE_PROCESS = process

        return jsonify({
            'success': True,
            'message': 'Full update started in background. Check status for progress.',
            'pid': process.pid
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/update-status', methods=['GET'])
def admin_update_status():
    """Check the status of the background update process."""
    try:
        global UPDATE_PROCESS

        if 'UPDATE_PROCESS' not in globals() or UPDATE_PROCESS is None:
            return jsonify({
                'status': 'idle',
                'message': 'No update process running'
            })

        # Check if process is still running
        poll_result = UPDATE_PROCESS.poll()

        if poll_result is None:
            # Still running
            return jsonify({
                'status': 'running',
                'message': 'Update in progress...',
                'pid': UPDATE_PROCESS.pid
            })
        elif poll_result == 0:
            # Completed successfully
            stdout, stderr = UPDATE_PROCESS.communicate()
            UPDATE_PROCESS = None

            # Auto-reload data after successful update
            try:
                print("\n[AUTO-RELOAD] Reloading data after successful update...")
                load_data()
                latest_date = DATA['games']['date'].max()
                print(f"[AUTO-RELOAD] Data reloaded: {len(DATA['games'])} games, latest: {latest_date}")
            except Exception as reload_error:
                print(f"[AUTO-RELOAD] Warning: Failed to reload data: {reload_error}")

            return jsonify({
                'status': 'completed',
                'success': True,
                'output': stdout,
                'message': 'Update completed successfully',
                'data_reloaded': True
            })
        else:
            # Failed
            stdout, stderr = UPDATE_PROCESS.communicate()
            UPDATE_PROCESS = None
            return jsonify({
                'status': 'failed',
                'success': False,
                'output': stdout,
                'error': stderr,
                'return_code': poll_result
            })

    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500


@app.route('/admin/reload-data', methods=['POST'])
def admin_reload_data():
    """Reload all data from disk without restarting the app."""
    try:
        print("\n" + "="*80)
        print("RELOADING DATA...")
        print("="*80)

        # Reload all data
        load_data()

        # Get latest game date - handle both int and Timestamp types
        latest_date = DATA['games']['date'].max()
        try:
            # Try to convert to int (works for numpy int64)
            latest_date = int(latest_date)
        except (TypeError, ValueError):
            # If it's a Timestamp, format it as YYYYMMDD
            try:
                latest_date = int(latest_date.strftime('%Y%m%d'))
            except:
                # Fallback - just use string representation
                latest_date = str(latest_date)

        return jsonify({
            'success': True,
            'message': 'Data reloaded successfully',
            'total_games': len(DATA['games']),
            'latest_date': latest_date,
            'teams': len(DATA['team_ratings']),
            'players': len(DATA['player_ratings'])
        })

    except Exception as e:
        import traceback
        print(f"Error reloading data: {e}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/accuracy-report', methods=['POST'])
def admin_accuracy_report():
    """Generate weekly accuracy report."""
    try:
        from src.analytics.prediction_tracking import get_accuracy_stats
        from datetime import datetime, timedelta

        # Get accuracy for last 7 days
        stats = get_accuracy_stats(days_back=7)

        if not stats:
            return jsonify({'success': False, 'error': 'No prediction data available'})

        # Format report
        report = {
            'success': True,
            'period': 'Last 7 Days',
            'total_games': stats['total'],
            'correct': stats['correct'],
            'incorrect': stats['total'] - stats['correct'],
            'accuracy': f"{stats['accuracy']:.1f}%",
            'streak_type': stats.get('streak_type', 'N/A'),
            'streak_length': stats.get('current_streak', 0),
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        return jsonify(report)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# SEASON PROJECTION API ENDPOINTS (Phase 2)
# ============================================================================

def _get_season_predictor():
    """
    Get or create season predictor instance with caching.

    Cache expires after 24 hours or when new games are added.
    """
    cache_key = 'season_predictor'
    cache_expiry = 'predictor_cache_date'

    # Check if cache exists and is fresh
    current_date = int(datetime.now().strftime('%Y%m%d'))

    if cache_key in DATA and cache_expiry in DATA:
        if DATA[cache_expiry] == current_date:
            return DATA[cache_key]

    # Cache miss or expired - rebuild predictor
    print("[INFO] Building season predictor (cache miss or expired)...")

    from src.predictors.schedule_fetcher import ScheduleFetcher
    from src.predictors.season_predictor import SeasonPredictor

    # Get schedule and standings
    fetcher = ScheduleFetcher(DATA['games'])
    all_standings = fetcher.get_current_standings()
    all_remaining = fetcher.get_remaining_games(include_completed_future=True)  # For testing with full season data

    # Filter to only active NBA teams
    standings = {tid: data for tid, data in all_standings.items() if tid in ACTIVE_NBA_TEAMS}
    remaining = [g for g in all_remaining if g['home_id'] in ACTIVE_NBA_TEAMS and g['away_id'] in ACTIVE_NBA_TEAMS]

    # Create predictor
    predictor = SeasonPredictor(DATA['elo_engine'], standings, remaining)

    # Cache it
    DATA[cache_key] = predictor
    DATA[cache_expiry] = current_date

    print(f"[INFO] Season predictor ready: {len(standings)} teams, {len(remaining)} remaining games")
    return predictor


def _get_cached_projections(num_sims=10000):
    """
    Get or compute season projections with caching.

    Runs expensive Monte Carlo simulation and caches results for 24 hours.
    """
    cache_key = f'projections_{num_sims}'
    cache_expiry = 'projections_cache_date'

    current_date = int(datetime.now().strftime('%Y%m%d'))

    # Check cache
    if cache_key in DATA and cache_expiry in DATA:
        if DATA[cache_expiry] == current_date:
            print(f"[INFO] Returning cached projections ({num_sims} sims)")
            return DATA[cache_key]

    # Cache miss - run simulation
    print(f"[INFO] Running {num_sims} Monte Carlo simulations...")
    predictor = _get_season_predictor()

    results = predictor.simulate_season(num_sims=num_sims, use_enhanced=True)

    # Cache results
    DATA[cache_key] = results
    DATA[cache_expiry] = current_date

    print(f"[INFO] Projections computed and cached")
    return results


@app.route('/api/season-projection')
def api_season_projection():
    """
    Get season projections for all teams.

    Query Parameters:
        conference (optional): "East", "West", or "All" (default: "All")
        num_sims (optional): Number of simulations (default: 10000, max: 50000)

    Returns:
        JSON with metadata and team projections
    """
    try:
        # Parse query parameters
        conference = request.args.get('conference', 'All')
        num_sims = int(request.args.get('num_sims', 10000))

        # Validate parameters
        if conference not in ['East', 'West', 'All']:
            return jsonify({'error': 'Invalid conference. Must be East, West, or All'}), 400

        if num_sims < 1000 or num_sims > 50000:
            return jsonify({'error': 'num_sims must be between 1000 and 50000'}), 400

        # Get cached projections
        results = _get_cached_projections(num_sims)

        # Get standings for current records
        from src.predictors.schedule_fetcher import ScheduleFetcher
        fetcher = ScheduleFetcher(DATA['games'])
        current_standings = fetcher.get_current_standings()
        season_summary = fetcher.get_season_summary()

        # Get projections based on conference filter
        if conference == 'All':
            projections = results.get_all_projections()
        else:
            projections = results.get_conference_projections(conference)

        # Enrich projections with current records and team data
        enriched_projections = []
        for proj in projections:
            team_id = proj['team_id']

            # Skip teams not in active NBA teams (All-Star, exhibition, etc.)
            if team_id not in ACTIVE_NBA_TEAMS:
                continue

            current = current_standings.get(team_id, {})

            # Get team ELO safely
            team_elo_row = DATA['team_ratings'][DATA['team_ratings']['team_id'] == team_id]
            current_elo = float(team_elo_row['rating'].iloc[0]) if len(team_elo_row) > 0 else 1500.0

            enriched_projections.append({
                'rank': len(enriched_projections) + 1,
                'team_id': team_id,
                'team_name': proj['team_name'],
                'current_elo': current_elo,
                'current_record': f"{current.get('wins', 0)}-{current.get('losses', 0)}",
                'current_wins': current.get('wins', 0),
                'current_losses': current.get('losses', 0),
                'projected_wins': round(proj['projected_wins'], 1),
                'median_wins': proj['median_wins'],
                'win_range': list(proj['confidence_interval']),
                'playoff_probability': round(proj['playoff_probability'], 4),
                'seed_probabilities': {str(k): round(v, 4) for k, v in proj['seed_probabilities'].items()}
            })

        # Build response
        response = {
            'metadata': {
                'as_of_date': season_summary['as_of_date'],
                'num_simulations': num_sims,
                'games_played': season_summary['games_played'],
                'games_remaining': season_summary['games_remaining'],
                'season_pct_complete': round(season_summary['season_pct_complete'], 3),
                'use_enhanced_features': True,
                'conference_filter': conference
            },
            'projections': enriched_projections
        }

        return jsonify(response)

    except Exception as e:
        print(f"[ERROR] Season projection failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/season-projection/<int:team_id>')
def api_season_projection_team(team_id):
    """
    Get detailed season projection for specific team.

    Path Parameters:
        team_id: Team ID (1-30)

    Query Parameters:
        num_sims (optional): Number of simulations (default: 10000)

    Returns:
        JSON with detailed team projection including win distribution
    """
    try:
        # Validate team_id
        if team_id not in ACTIVE_NBA_TEAMS:
            return jsonify({'error': f'Invalid team_id: {team_id}. Must be 1-30 (active NBA teams)'}), 404

        # Parse query parameters
        num_sims = int(request.args.get('num_sims', 10000))

        if num_sims < 1000 or num_sims > 50000:
            return jsonify({'error': 'num_sims must be between 1000 and 50000'}), 400

        # Get cached projections
        results = _get_cached_projections(num_sims)

        # Get team projection
        proj = results.get_team_projection(team_id)

        if not proj:
            return jsonify({'error': f'No projection data for team_id: {team_id}'}), 404

        # Get current standings and schedule info
        from src.predictors.schedule_fetcher import ScheduleFetcher
        fetcher = ScheduleFetcher(DATA['games'])
        current_standings = fetcher.get_current_standings()
        team_schedule = fetcher.get_team_remaining_schedule(team_id)

        current = current_standings.get(team_id, {})

        # Get team name from current standings
        team_name = current.get('team_name', f'Team {team_id}')

        # Get team ELO
        team_elo_row = DATA['team_ratings'][DATA['team_ratings']['team_id'] == team_id]
        current_elo = float(team_elo_row['rating'].iloc[0]) if len(team_elo_row) > 0 else 1500.0

        # Get top ELO contributors (top 5 players by ELO rating)
        # Filter by team_name (not team_id) since player_team_mapping may have stale team IDs
        team_players_mapping = DATA['player_team_mapping'][
            DATA['player_team_mapping']['team_name'] == team_name
        ].copy()

        # Get those players' ratings by joining on player_name
        team_players = DATA['player_ratings'].merge(
            team_players_mapping[['player_name', 'position']],
            on='player_name',
            how='inner',
            suffixes=('', '_mapping')
        )

        top_contributors = []
        if len(team_players) > 0:
            # Sort by rating descending and take top 5
            top_players = team_players.nlargest(5, 'rating')
            for _, player in top_players.iterrows():
                top_contributors.append({
                    'player_id': int(player['player_id']) if pd.notna(player['player_id']) else 0,
                    'player_name': player['player_name'],
                    'rating': round(float(player['rating']), 1),
                    'games_played': int(player['games_played']) if 'games_played' in player and pd.notna(player['games_played']) else 0
                })

        # Build detailed response
        response = {
            'team_id': team_id,
            'team_name': team_name,
            'current_elo': current_elo,
            'current_record': {
                'wins': current.get('wins', 0),
                'losses': current.get('losses', 0),
                'games_played': current.get('games_played', 0),
                'win_pct': round(current.get('win_pct', 0.0), 3)
            },
            'projection': {
                'wins': round(proj['projected_wins'], 1),
                'losses': round(82 - proj['projected_wins'], 1),
                'win_pct': round(proj['projected_wins'] / 82, 3)
            },
            'win_distribution': {
                str(k): v for k, v in sorted(proj['win_distribution'].items())
            },
            'playoff_probability': round(proj['playoff_probability'], 4),
            'seed_probabilities': {
                str(k): round(v, 4) for k, v in sorted(proj['seed_probabilities'].items())
            },
            'confidence_interval': {
                'low': proj['confidence_interval'][0],
                'high': proj['confidence_interval'][1],
                'range': f"{proj['confidence_interval'][0]}-{proj['confidence_interval'][1]} wins"
            },
            'remaining_schedule': {
                'total_games': team_schedule['total_games'],
                'home_games': team_schedule['home_games'],
                'away_games': team_schedule['away_games']
            },
            'top_elo_contributors': top_contributors,
            'metadata': {
                'num_simulations': num_sims,
                'use_enhanced_features': True
            }
        }

        return jsonify(response)

    except Exception as e:
        print(f"[ERROR] Team projection failed for team_id {team_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/clear-cache', methods=['POST'])
def clear_cache():
    """
    Clear all cached season projections.

    Use this when season dates change or to force fresh simulations.
    """
    try:
        # Clear all projection caches
        keys_to_remove = []
        for key in DATA.keys():
            if 'projections_' in key or 'predictor' in key or 'cache' in key:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del DATA[key]

        return jsonify({
            'success': True,
            'message': f'Cleared {len(keys_to_remove)} cache entries',
            'cleared_keys': keys_to_remove
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Load data before starting server
    load_data()

    print("\n" + "="*80)
    print("NBA ELO Dashboard Starting...")
    print("="*80)
    print("\nAccess the dashboard at: http://localhost:5000")
    print("\nAvailable pages:")
    print("  - Home:        http://localhost:5000/")
    print("  - Predict:     http://localhost:5000/predict")
    print("  - Betting:     http://localhost:5000/betting  <- NEW!")
    print("  - Newsletter:  http://localhost:5000/newsletter")
    print("  - Players:     http://localhost:5000/players")
    print("  - Teams:       http://localhost:5000/teams")
    print("  - Visualize:   http://localhost:5000/visualize")
    print("  - Past Games:  http://localhost:5000/past-games")
    print("\nPress Ctrl+C to stop the server")
    print("="*80 + "\n")

    app.run(debug=True, port=5000, use_reloader=False)

