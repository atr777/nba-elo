"""
Generate Model Performance Report

Script to generate comprehensive performance reports for model accuracy tracking.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analytics.model_performance_tracker import get_tracker
from datetime import datetime, timedelta
import argparse


def main():
    """Generate performance report with optional date filtering."""

    parser = argparse.ArgumentParser(description='Generate model performance report')
    parser.add_argument('--start-date', help='Start date (YYYYMMDD)')
    parser.add_argument('--end-date', help='End date (YYYYMMDD)')
    parser.add_argument('--output', help='Output file path (optional)')
    parser.add_argument('--last-n-days', type=int, help='Report on last N days')
    parser.add_argument('--today', action='store_true', help='Report on today only')

    args = parser.parse_args()

    tracker = get_tracker()

    # Handle date filters
    start_date = args.start_date
    end_date = args.end_date

    if args.last_n_days:
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=args.last_n_days)).strftime('%Y%m%d')
        print(f"\nGenerating report for last {args.last_n_days} days...\n")

    elif args.today:
        today = datetime.now().strftime('%Y%m%d')
        daily_stats = tracker.get_daily_stats(today)

        print("=" * 80)
        print(f"DAILY REPORT - {today}")
        print("=" * 80)
        print(f"Total Predictions: {daily_stats['total_predictions']}")
        print(f"Completed Games: {daily_stats['completed_games']}")

        if daily_stats['accuracy'] is not None:
            print(f"Accuracy: {daily_stats['accuracy']:.2%} ({daily_stats['correct']}/{daily_stats['completed_games']})")
        else:
            print("Accuracy: N/A (no completed games)")

        print(f"Close Games: {daily_stats['close_games']}")
        print(f"Enhancements Active: {daily_stats['enhancements_active']}")
        print(f"Average Confidence: {daily_stats['avg_confidence']:.2%}")
        print("=" * 80)
        return

    # Generate full report
    report = tracker.generate_report(start_date, end_date, args.output)
    print(report)

    if args.output:
        print(f"\nReport saved to: {args.output}")


if __name__ == '__main__':
    main()
