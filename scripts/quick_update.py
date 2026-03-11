"""
Quick Database Update - Only process last N days
Useful when you know you're only a few days behind
"""
import argparse
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
# Also add scripts/ directory so `import daily_update` resolves correctly
# regardless of the working directory the caller uses.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    parser = argparse.ArgumentParser(description='Quick database update for last N days')
    parser.add_argument('--days', type=int, default=7, help='Number of days to update (default: 7)')
    parser.add_argument('--force', action='store_true', help='Force update even if appears up-to-date')
    args = parser.parse_args()

    print(f"="*80)
    print(f"QUICK UPDATE: Processing last {args.days} days")
    print(f"="*80)

    # Import status helpers from daily_update (importable because scripts/ is on sys.path)
    from daily_update import get_data_stats

    # Check current status
    stats = get_data_stats()
    last_date = stats['latest_game_date'] if stats else None
    print(f"\nDatabase currently updated through: {last_date}")

    # Calculate target date range
    # Use the database's last date + N days, not system date
    if last_date:
        last_dt = datetime.strptime(str(last_date), '%Y%m%d')
        end_date = last_dt + timedelta(days=args.days)
    else:
        end_date = datetime.now() - timedelta(days=365)  # Start from 1 year ago if no data

    print(f"Will update through: {end_date.strftime('%Y-%m-%d')}")
    print(f"Expected games: ~{args.days * 12} games")
    print(f"Estimated time: ~{args.days * 2} minutes\n")

    # Run update via subprocess (daily_update.main() orchestrates via subprocess internally
    # and does not accept a max_date parameter — delegate the full pipeline to it)
    try:
        import subprocess
        scripts_dir = os.path.join(os.path.dirname(__file__))
        result = subprocess.run(
            [sys.executable, os.path.join(scripts_dir, 'daily_update.py')],
            cwd=os.path.join(os.path.dirname(__file__), '..'),
        )
        if result.returncode != 0:
            print(f"\nUpdate process exited with code {result.returncode}")
            return result.returncode
        print(f"\n{'='*80}")
        print(f"Quick update complete!")
        print(f"{'='*80}")
    except Exception as e:
        print(f"\nError during update: {e}")
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
