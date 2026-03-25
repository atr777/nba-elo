"""
Model Performance Tracking Module

Tracks predictions vs actual results to monitor model accuracy in real-time.
Supports detailed analytics by game type, date range, and enhancement features.
"""

import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class ModelPerformanceTracker:
    """Tracks and analyzes model prediction performance."""

    def __init__(self, tracking_file: str = 'data/exports/prediction_tracking.csv'):
        """
        Initialize the Model Performance Tracker.

        Args:
            tracking_file: Path to CSV file for storing prediction logs
        """
        self.tracking_file = tracking_file
        self._ensure_tracking_file_exists()
        logger.info(f"ModelPerformanceTracker initialized with file: {tracking_file}")

    def _ensure_tracking_file_exists(self):
        """Create tracking file with headers if it doesn't exist."""
        tracking_path = Path(self.tracking_file)

        if not tracking_path.exists():
            # Create directory if needed
            tracking_path.parent.mkdir(parents=True, exist_ok=True)

            # Create empty DataFrame with schema
            df = pd.DataFrame(columns=[
                'game_id',
                'date',
                'timestamp',
                'home_team_id',
                'away_team_id',
                'home_team_name',
                'away_team_name',
                'predicted_winner',
                'predicted_home_prob',
                'predicted_away_prob',
                'confidence',
                'actual_winner',
                'actual_home_score',
                'actual_away_score',
                'correct',
                'elo_diff',
                'is_close_game',
                'is_toss_up',
                'home_back_to_back',
                'away_back_to_back',
                'rest_fatigue_active',
                'close_game_enhancement_active',
                'momentum_active',
                'home_momentum_adjustment',
                'away_momentum_adjustment',
                'home_elo',
                'away_elo',
                'margin_of_victory',
                'upset'
            ])
            df.to_csv(self.tracking_file, index=False)
            logger.info(f"Created new tracking file: {self.tracking_file}")

    def log_prediction(self,
                      game_id: str,
                      game_date: str,
                      home_team_id: int,
                      away_team_id: int,
                      home_team_name: str,
                      away_team_name: str,
                      prediction: Dict,
                      actual_winner: Optional[str] = None,
                      actual_home_score: Optional[int] = None,
                      actual_away_score: Optional[int] = None) -> None:
        """
        Log a prediction to the tracking file.

        Args:
            game_id: Unique game identifier
            game_date: Game date (YYYYMMDD format)
            home_team_id: Home team ID
            away_team_id: Away team ID
            home_team_name: Home team name
            away_team_name: Away team name
            prediction: Prediction dict from predict_game_hybrid()
            actual_winner: 'home' or 'away' (if game completed)
            actual_home_score: Home team final score (if game completed)
            actual_away_score: Away team final score (if game completed)
        """

        # Determine predicted winner
        predicted_home_prob = prediction.get('home_win_probability', 0.5)
        predicted_winner = 'home' if predicted_home_prob >= 0.5 else 'away'

        # Calculate if correct (if actual result available)
        correct = None
        if actual_winner is not None:
            correct = (predicted_winner == actual_winner)

        # Extract enhancement flags
        close_game_active = prediction.get('close_game_enhancement_active', False)
        rest_fatigue_active = prediction.get('rest_fatigue_active', False)

        # Calculate ELO difference
        home_elo = prediction.get('final_home_elo', prediction.get('home_elo', 1500))
        away_elo = prediction.get('final_away_elo', prediction.get('away_elo', 1500))
        elo_diff = abs(home_elo - away_elo)

        # Determine game type
        is_close_game = elo_diff < 100
        is_toss_up = elo_diff < 50

        # Calculate margin of victory
        margin = None
        if actual_home_score is not None and actual_away_score is not None:
            margin = abs(actual_home_score - actual_away_score)

        # Determine if upset
        upset = None
        if actual_winner is not None:
            upset = (predicted_winner != actual_winner)

        # Create log entry
        log_entry = {
            'game_id': game_id,
            'date': game_date,
            'timestamp': datetime.now().isoformat(),
            'home_team_id': home_team_id,
            'away_team_id': away_team_id,
            'home_team_name': home_team_name,
            'away_team_name': away_team_name,
            'predicted_winner': predicted_winner,
            'predicted_home_prob': predicted_home_prob,
            'predicted_away_prob': 1 - predicted_home_prob,
            'confidence': prediction.get('confidence', predicted_home_prob),
            'actual_winner': actual_winner,
            'actual_home_score': actual_home_score,
            'actual_away_score': actual_away_score,
            'correct': correct,
            'elo_diff': elo_diff,
            'is_close_game': is_close_game,
            'is_toss_up': is_toss_up,
            'home_back_to_back': prediction.get('home_back_to_back', False),
            'away_back_to_back': prediction.get('away_back_to_back', False),
            'rest_fatigue_active': rest_fatigue_active,
            'close_game_enhancement_active': close_game_active,
            'momentum_active': prediction.get('momentum_active', False),
            'home_momentum_adjustment': prediction.get('home_momentum_adjustment', 0.0),
            'away_momentum_adjustment': prediction.get('away_momentum_adjustment', 0.0),
            'home_elo': home_elo,
            'away_elo': away_elo,
            'margin_of_victory': margin,
            'upset': upset,
            'predicted_home_score': prediction.get('predicted_home_score'),
            'predicted_away_score': prediction.get('predicted_away_score'),
            'predicted_margin': prediction.get('predicted_margin'),
            'predicted_home_q1': prediction.get('predicted_home_q1'),
            'predicted_home_q2': prediction.get('predicted_home_q2'),
            'predicted_home_q3': prediction.get('predicted_home_q3'),
            'predicted_home_q4': prediction.get('predicted_home_q4'),
            'predicted_away_q1': prediction.get('predicted_away_q1'),
            'predicted_away_q2': prediction.get('predicted_away_q2'),
            'predicted_away_q3': prediction.get('predicted_away_q3'),
            'predicted_away_q4': prediction.get('predicted_away_q4'),
        }

        # Append to CSV
        df = pd.DataFrame([log_entry])
        df.to_csv(self.tracking_file, mode='a', header=False, index=False)

        logger.info(f"Logged prediction for game {game_id}: {predicted_winner} ({predicted_home_prob:.1%})")

    def get_performance_summary(self,
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None,
                               min_games: int = 10) -> Dict:
        """
        Get comprehensive performance summary.

        Args:
            start_date: Start date filter (YYYYMMDD)
            end_date: End date filter (YYYYMMDD)
            min_games: Minimum games required for category stats

        Returns:
            Dictionary with performance metrics
        """

        df = pd.read_csv(self.tracking_file)

        # Filter by date range (convert strings to integers)
        if start_date:
            start_date_int = int(start_date) if isinstance(start_date, str) else start_date
            df = df[df['date'] >= start_date_int]
        if end_date:
            end_date_int = int(end_date) if isinstance(end_date, str) else end_date
            df = df[df['date'] <= end_date_int]

        # Only completed games (have actual results)
        completed = df[df['actual_winner'].notna()].copy()

        if len(completed) == 0:
            return {
                'error': 'No completed games in date range',
                'total_predictions': len(df),
                'completed_games': 0
            }

        # Overall accuracy
        overall_accuracy = completed['correct'].mean()
        total_games = len(completed)
        correct_predictions = completed['correct'].sum()

        # Home/Away accuracy
        home_games = completed[completed['actual_winner'] == 'home']
        away_games = completed[completed['actual_winner'] == 'away']
        home_win_rate = len(home_games) / len(completed) if len(completed) > 0 else 0

        home_predicted_correctly = completed[
            (completed['predicted_winner'] == 'home') &
            (completed['actual_winner'] == 'home')
        ]
        away_predicted_correctly = completed[
            (completed['predicted_winner'] == 'away') &
            (completed['actual_winner'] == 'away')
        ]

        # Close game performance
        close_games = completed[completed['is_close_game'] == True]
        close_game_accuracy = close_games['correct'].mean() if len(close_games) >= min_games else None

        toss_ups = completed[completed['is_toss_up'] == True]
        toss_up_accuracy = toss_ups['correct'].mean() if len(toss_ups) >= min_games else None

        # Enhancement impact
        enhanced_games = completed[completed['close_game_enhancement_active'] == True]
        enhanced_accuracy = enhanced_games['correct'].mean() if len(enhanced_games) >= min_games else None

        rest_fatigue_games = completed[completed['rest_fatigue_active'] == True]
        rest_fatigue_accuracy = rest_fatigue_games['correct'].mean() if len(rest_fatigue_games) >= min_games else None

        # Back-to-back performance
        home_b2b = completed[completed['home_back_to_back'] == True]
        away_b2b = completed[completed['away_back_to_back'] == True]

        # Upset analysis
        upsets = completed[completed['upset'] == True]
        upset_rate = len(upsets) / len(completed) if len(completed) > 0 else 0

        # Confidence calibration
        avg_confidence = completed['confidence'].mean()
        high_conf = completed[completed['confidence'] >= 0.70]
        high_conf_accuracy = high_conf['correct'].mean() if len(high_conf) >= min_games else None

        low_conf = completed[completed['confidence'] < 0.60]
        low_conf_accuracy = low_conf['correct'].mean() if len(low_conf) >= min_games else None

        # Recent performance (last 7 days)
        recent_date = int((datetime.now() - timedelta(days=7)).strftime('%Y%m%d'))
        recent = completed[completed['date'] >= recent_date]
        recent_accuracy = recent['correct'].mean() if len(recent) > 0 else None

        return {
            'summary': {
                'total_games': total_games,
                'correct_predictions': int(correct_predictions),
                'overall_accuracy': overall_accuracy,
                'date_range': f"{completed['date'].min()} to {completed['date'].max()}"
            },
            'home_away': {
                'home_win_rate': home_win_rate,
                'home_games': len(home_games),
                'away_games': len(away_games),
                'home_predicted_correct': len(home_predicted_correctly),
                'away_predicted_correct': len(away_predicted_correctly)
            },
            'by_game_type': {
                'close_games': {
                    'count': len(close_games),
                    'accuracy': close_game_accuracy
                },
                'toss_ups': {
                    'count': len(toss_ups),
                    'accuracy': toss_up_accuracy
                },
                'large_diff': {
                    'count': len(completed[completed['is_close_game'] == False]),
                    'accuracy': completed[completed['is_close_game'] == False]['correct'].mean()
                }
            },
            'enhancements': {
                'close_game_enhancement': {
                    'games': len(enhanced_games),
                    'accuracy': enhanced_accuracy
                },
                'rest_fatigue': {
                    'games': len(rest_fatigue_games),
                    'accuracy': rest_fatigue_accuracy
                }
            },
            'back_to_back': {
                'home_b2b_games': len(home_b2b),
                'away_b2b_games': len(away_b2b),
                'home_b2b_accuracy': home_b2b['correct'].mean() if len(home_b2b) >= min_games else None,
                'away_b2b_accuracy': away_b2b['correct'].mean() if len(away_b2b) >= min_games else None
            },
            'confidence': {
                'average_confidence': avg_confidence,
                'high_confidence_games': len(high_conf),
                'high_confidence_accuracy': high_conf_accuracy,
                'low_confidence_games': len(low_conf),
                'low_confidence_accuracy': low_conf_accuracy
            },
            'upsets': {
                'total_upsets': len(upsets),
                'upset_rate': upset_rate
            },
            'recent_performance': {
                'last_7_days_games': len(recent),
                'last_7_days_accuracy': recent_accuracy
            }
        }

    def get_daily_stats(self, date: Optional[str] = None) -> Dict:
        """
        Get statistics for a specific date.

        Args:
            date: Date in YYYYMMDD format (default: today)

        Returns:
            Dictionary with daily statistics
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')

        # Convert to integer for comparison
        date_int = int(date) if isinstance(date, str) else date

        df = pd.read_csv(self.tracking_file)
        daily = df[df['date'] == date_int]

        if len(daily) == 0:
            return {
                'date': date,
                'total_predictions': 0,
                'message': 'No predictions for this date'
            }

        completed = daily[daily['actual_winner'].notna()]

        return {
            'date': date,
            'total_predictions': len(daily),
            'completed_games': len(completed),
            'correct': int(completed['correct'].sum()) if len(completed) > 0 else 0,
            'accuracy': completed['correct'].mean() if len(completed) > 0 else None,
            'close_games': len(daily[daily['is_close_game'] == True]),
            'enhancements_active': len(daily[daily['close_game_enhancement_active'] == True]),
            'avg_confidence': daily['confidence'].mean()
        }

    def generate_report(self,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       output_file: Optional[str] = None) -> str:
        """
        Generate a formatted performance report.

        Args:
            start_date: Start date filter (YYYYMMDD)
            end_date: End date filter (YYYYMMDD)
            output_file: Optional file to save report

        Returns:
            Formatted report string
        """

        stats = self.get_performance_summary(start_date, end_date)

        if 'error' in stats:
            return f"Error: {stats['error']}"

        report_lines = [
            "=" * 80,
            "MODEL PERFORMANCE REPORT",
            "=" * 80,
            "",
            f"Date Range: {stats['summary']['date_range']}",
            f"Total Games: {stats['summary']['total_games']}",
            f"Overall Accuracy: {stats['summary']['overall_accuracy']:.2%} ({stats['summary']['correct_predictions']}/{stats['summary']['total_games']})",
            "",
            "HOME/AWAY ANALYSIS",
            "-" * 80,
            f"Home Win Rate: {stats['home_away']['home_win_rate']:.2%} ({stats['home_away']['home_games']} games)",
            f"Home Predicted Correctly: {stats['home_away']['home_predicted_correct']} games",
            f"Away Predicted Correctly: {stats['home_away']['away_predicted_correct']} games",
            "",
            "GAME TYPE BREAKDOWN",
            "-" * 80,
        ]

        # Close games
        close_acc = stats['by_game_type']['close_games']['accuracy']
        if close_acc is not None:
            report_lines.append(
                f"Close Games (<100 ELO): {close_acc:.2%} ({stats['by_game_type']['close_games']['count']} games)"
            )
        else:
            report_lines.append(
                f"Close Games (<100 ELO): N/A (only {stats['by_game_type']['close_games']['count']} games)"
            )

        # Toss-ups
        toss_acc = stats['by_game_type']['toss_ups']['accuracy']
        if toss_acc is not None:
            report_lines.append(
                f"Toss-ups (<50 ELO): {toss_acc:.2%} ({stats['by_game_type']['toss_ups']['count']} games)"
            )
        else:
            report_lines.append(
                f"Toss-ups (<50 ELO): N/A (only {stats['by_game_type']['toss_ups']['count']} games)"
            )

        # Large differences
        large_acc = stats['by_game_type']['large_diff']['accuracy']
        report_lines.append(
            f"Large Difference (>=100 ELO): {large_acc:.2%} ({stats['by_game_type']['large_diff']['count']} games)"
        )

        report_lines.extend([
            "",
            "ENHANCEMENT IMPACT",
            "-" * 80,
        ])

        # Close game enhancement
        cge_acc = stats['enhancements']['close_game_enhancement']['accuracy']
        if cge_acc is not None:
            report_lines.append(
                f"Close Game Enhancement: {cge_acc:.2%} ({stats['enhancements']['close_game_enhancement']['games']} games)"
            )
        else:
            report_lines.append(
                f"Close Game Enhancement: N/A ({stats['enhancements']['close_game_enhancement']['games']} games)"
            )

        # Rest/Fatigue
        rf_acc = stats['enhancements']['rest_fatigue']['accuracy']
        if rf_acc is not None:
            report_lines.append(
                f"Rest/Fatigue Analysis: {rf_acc:.2%} ({stats['enhancements']['rest_fatigue']['games']} games)"
            )
        else:
            report_lines.append(
                f"Rest/Fatigue Analysis: N/A ({stats['enhancements']['rest_fatigue']['games']} games)"
            )

        report_lines.extend([
            "",
            "CONFIDENCE CALIBRATION",
            "-" * 80,
            f"Average Confidence: {stats['confidence']['average_confidence']:.2%}",
        ])

        if stats['confidence']['high_confidence_accuracy'] is not None:
            report_lines.append(
                f"High Confidence (>=70%): {stats['confidence']['high_confidence_accuracy']:.2%} ({stats['confidence']['high_confidence_games']} games)"
            )

        if stats['confidence']['low_confidence_accuracy'] is not None:
            report_lines.append(
                f"Low Confidence (<60%): {stats['confidence']['low_confidence_accuracy']:.2%} ({stats['confidence']['low_confidence_games']} games)"
            )

        report_lines.extend([
            "",
            "RECENT PERFORMANCE",
            "-" * 80,
        ])

        if stats['recent_performance']['last_7_days_accuracy'] is not None:
            report_lines.append(
                f"Last 7 Days: {stats['recent_performance']['last_7_days_accuracy']:.2%} ({stats['recent_performance']['last_7_days_games']} games)"
            )
        else:
            report_lines.append("Last 7 Days: No games")

        report_lines.extend([
            "",
            "=" * 80
        ])

        report = "\n".join(report_lines)

        # Save to file if requested
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
            logger.info(f"Report saved to {output_file}")

        return report


# Singleton instance
_tracker = None

def get_tracker() -> ModelPerformanceTracker:
    """Get or create the Model Performance Tracker singleton."""
    global _tracker
    if _tracker is None:
        _tracker = ModelPerformanceTracker()
    return _tracker
