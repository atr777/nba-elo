"""
Quick Database Update - Only process last N days
Useful when you know you're only a few days behind
"""
import argparse
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def main():
    parser = argparse.ArgumentParser(description='Quick database update for last N days')
    parser.add_argument('--days', type=int, default=7, help='Number of days to update (default: 7)')
    parser.add_argument('--force', action='store_true', help='Force update even if appears up-to-date')
    args = parser.parse_args()

    print(f"="*80)
    print(f"QUICK UPDATE: Processing last {args.days} days")
    print(f"="*80)

    # Import the daily update script
    from daily_update import update_database, get_last_processed_date

    # Check current status
    last_date = get_last_processed_date()
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

    # Run update with date limit
    try:
        update_database(max_date=end_date.strftime('%Y%m%d'))
        print(f"\n{'='*80}")
        print(f"✓ Quick update complete!")
        print(f"{'='*80}")
    except Exception as e:
        print(f"\n✗ Error during update: {e}")
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
