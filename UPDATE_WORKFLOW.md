# NBA ELO Update Workflow

## Daily/Weekly Update Process for Ongoing Season

### Option 1: Manual Updates (Recommended for Now)

**Weekly Update (Every Monday):**

```bash
# 1. Scrape new games from the past week
python src/etl/fetch_scoreboard.py \
    --start-date 20251117 \
    --end-date 20251123 \
    --output data/raw/nba_games_latest.csv

# 2. Append to master file
cat data/raw/nba_games_latest.csv >> data/raw/nba_games_all.csv

# 3. Remove duplicates and sort
python scripts/clean_and_dedupe.py

# 4. Recompute ELO ratings (fast - only takes 5 seconds)
python src/engines/team_elo_engine.py \
    --input data/raw/nba_games_all.csv \
    --output data/exports/team_elo_history_current.csv \
    --k-factor 20 \
    --home-advantage 70

# 5. Validate accuracy
python scripts/validate_phase_1_5.py

# 6. Commit changes
git add data/raw/nba_games_all.csv data/exports/
git commit -m "Update: Week of Nov 17-23, 2025 - [X] new games"
git push
```

**For Player Data (Phase 3 - After Implementation):**
```bash
# Scrape player box scores for new games
python scripts/nba_box_scraper.py \
    --start-date 20251117 \
    --end-date 20251123

# Append to player boxscore file
cat data/raw/player_boxscores_new.csv >> data/raw/player_boxscores_all.csv

# Recompute player ELO (Phase 3)
python src/engines/player_elo_engine.py
```

---

### Option 2: Automated Daily Updates (Future Enhancement)

**Create a scheduled script** (`scripts/daily_update.sh`):

```bash
#!/bin/bash
# Daily NBA ELO Update Script

# Configuration
TODAY=$(date +%Y%m%d)
YESTERDAY=$(date -d "yesterday" +%Y%m%d)
PROJECT_DIR="c:/Users/Aaron/Desktop/NBA_ELO/nba-elo-engine"

cd $PROJECT_DIR

echo "=== NBA ELO Daily Update: $TODAY ==="

# 1. Fetch yesterday's games
echo "Fetching games from $YESTERDAY..."
python src/etl/fetch_scoreboard.py \
    --start-date $YESTERDAY \
    --end-date $YESTERDAY \
    --output data/raw/daily_update.csv

# Check if any games were found
if [ ! -s data/raw/daily_update.csv ]; then
    echo "No games found for $YESTERDAY - exiting"
    exit 0
fi

# 2. Append to master dataset
echo "Appending to master dataset..."
tail -n +2 data/raw/daily_update.csv >> data/raw/nba_games_all.csv

# 3. Deduplicate (in case script runs multiple times)
python scripts/remove_duplicates.py

# 4. Recompute ELO
echo "Recomputing ELO ratings..."
python src/engines/team_elo_engine.py \
    --input data/raw/nba_games_all.csv \
    --output data/exports/team_elo_history.csv

# 5. Generate daily report
echo "Generating update report..."
python scripts/generate_daily_report.py --date $YESTERDAY

# 6. Optional: Auto-commit
if [ "$AUTO_COMMIT" = "true" ]; then
    git add data/raw/nba_games_all.csv data/exports/
    git commit -m "Auto-update: Games from $YESTERDAY"
    git push
fi

echo "=== Update complete ==="
```

**Schedule with Windows Task Scheduler:**
- **Trigger:** Daily at 6:00 AM (after all games finish)
- **Action:** Run `bash scripts/daily_update.sh`
- **Environment:** Set `AUTO_COMMIT=false` initially (review before auto-pushing)

---

### Option 3: Real-Time Updates (Advanced)

**For live game tracking:**

```python
# scripts/live_tracker.py
import time
from datetime import datetime
from src.etl.fetch_scoreboard import ESPNScoreboardScraper

def track_live_games():
    """Poll ESPN API for live game updates"""
    scraper = ESPNScoreboardScraper()

    while True:
        today = datetime.now().strftime('%Y%m%d')
        games = scraper.fetch_games(today, today)

        # Update only completed games
        completed = [g for g in games if g['status'] == 'FINAL']

        if completed:
            # Update database
            update_games(completed)
            # Recompute ELO incrementally
            recompute_elo_incremental(completed)

        # Sleep for 5 minutes
        time.sleep(300)

if __name__ == '__main__':
    track_live_games()
```

---

## Helper Scripts to Create

### 1. Deduplication Script

**File:** `scripts/remove_duplicates.py`

```python
"""Remove duplicate games from master dataset"""
import pandas as pd

# Load data
df = pd.read_csv('data/raw/nba_games_all.csv')

# Remove duplicates based on game_id
original_count = len(df)
df = df.drop_duplicates(subset=['game_id'], keep='last')
removed = original_count - len(df)

# Sort by date
df = df.sort_values('date')

# Save
df.to_csv('data/raw/nba_games_all.csv', index=False)

print(f"Removed {removed} duplicate games")
print(f"Total games: {len(df)}")
```

### 2. Incremental ELO Update

**File:** `scripts/incremental_elo.py`

```python
"""
Update ELO ratings incrementally (only process new games).
Much faster than full recalculation for daily updates.
"""
import pandas as pd
from src.engines.team_elo_engine import TeamELOEngine

def incremental_update(new_games_csv):
    """
    Load current ELO state, process only new games, save results.

    Args:
        new_games_csv: Path to CSV with new games only
    """
    # Load current ELO state
    current_state = pd.read_csv('data/exports/team_elo_current_state.csv')
    engine = TeamELOEngine()
    engine.load_state(current_state)  # Restore team ratings

    # Load new games
    new_games = pd.read_csv(new_games_csv)

    # Process only new games
    history = engine.process_games(new_games)

    # Append to history
    history.to_csv('data/exports/team_elo_history.csv',
                   mode='a', header=False, index=False)

    # Save current state
    engine.save_state('data/exports/team_elo_current_state.csv')

    return len(new_games)
```

### 3. Daily Report Generator

**File:** `scripts/generate_daily_report.py`

```python
"""Generate daily update summary"""
import pandas as pd
from datetime import datetime

def generate_report(date):
    """
    Create markdown report of yesterday's games and ELO changes.
    """
    games = pd.read_csv('data/raw/nba_games_all.csv')
    elo = pd.read_csv('data/exports/team_elo_history.csv')

    # Filter to yesterday
    yesterday_games = games[games['date'] == date]

    if len(yesterday_games) == 0:
        return "No games on this date."

    report = f"# NBA ELO Update - {date}\n\n"
    report += f"## Games Played: {len(yesterday_games)}\n\n"

    # Top movers
    yesterday_elo = elo[elo['date'] == date]
    movers = yesterday_elo.nlargest(5, 'rating_change')

    report += "## Biggest Rating Gains:\n"
    for _, row in movers.iterrows():
        report += f"- **{row['team_name']}**: {row['rating_change']:+.1f} "
        report += f"({row['rating_before']:.1f} → {row['rating_after']:.1f})\n"

    # Save report
    with open(f'reports/update_{date}.md', 'w') as f:
        f.write(report)

    print(report)

if __name__ == '__main__':
    import sys
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y%m%d')
    generate_report(date)
```

---

## Recommended Workflow for You

**Phase 1.5 (Current - Team ELO Only):**

**Weekly Manual Updates:**
1. Every Monday morning, scrape previous week's games
2. Append to master file
3. Run full ELO recalculation (only takes 5 seconds anyway)
4. Review accuracy metrics
5. Commit to GitHub

```bash
# Quick weekly update script
./scripts/weekly_update.sh
```

**Phase 3 (After Player ELO Implementation):**

**Twice-Weekly Updates:**
1. Scrape games + player boxscores
2. Run incremental ELO update (both team + player)
3. Generate reports
4. Commit

---

## Git Update Strategy

**Branch Strategy:**
```
main          → Stable, validated data
├── develop   → Weekly updates, testing
└── daily     → Daily auto-updates (if implemented)
```

**Workflow:**
1. Daily/weekly updates go to `develop` branch
2. Validate accuracy on `develop`
3. Merge to `main` weekly after validation

**Example:**
```bash
# Create update branch
git checkout -b update/week-nov-17-23

# Run updates
./scripts/weekly_update.sh

# Review changes
git diff data/raw/nba_games_all.csv
python scripts/validate_phase_1_5.py

# Commit and push
git add .
git commit -m "Update: Week 47 - Added 85 games, accuracy: 65.71%"
git push origin update/week-nov-17-23

# Merge to main
git checkout main
git merge update/week-nov-17-23
git push origin main
```

---

## Data Backup Strategy

**Weekly Backups:**
```bash
# Backup before each update
cp data/raw/nba_games_all.csv \
   backups/nba_games_all_$(date +%Y%m%d).csv

cp data/exports/team_elo_history.csv \
   backups/team_elo_history_$(date +%Y%m%d).csv
```

**Keep last 4 weeks** (automatic cleanup):
```bash
# In weekly update script
find backups/ -name "*.csv" -mtime +28 -delete
```

---

## Performance Optimization

**For large datasets:**

1. **Use SQLite instead of CSV** (Future enhancement):
   ```python
   # Faster queries, better concurrency
   import sqlite3
   conn = sqlite3.connect('data/nba_elo.db')
   ```

2. **Incremental updates only** (avoid full recalc):
   - Store current ELO state
   - Process only new games
   - Append to history

3. **Parallel processing** (Phase 3):
   - Process multiple seasons in parallel
   - Use `multiprocessing` for player ELO

---

## Monitoring & Alerts

**Check data quality after each update:**

```python
# scripts/data_quality_check.py
def validate_update():
    """Run after each update"""
    checks = {
        'duplicates': check_duplicates(),
        'missing_data': check_missing_fields(),
        'date_gaps': check_date_continuity(),
        'accuracy': check_prediction_accuracy(),
    }

    if all(checks.values()):
        print("✅ All quality checks passed")
    else:
        print("❌ Quality issues detected:")
        for check, passed in checks.items():
            if not passed:
                print(f"  - {check} FAILED")
```

**Email alerts** (optional):
```python
# Send email if accuracy drops
if accuracy < 0.64:
    send_alert(f"Accuracy dropped to {accuracy:.2%}")
```

---

## Data Quality Notes

**Scheduled vs Completed Games:**

The scraper may pull future scheduled games (with 0-0 scores). This is **intentional**:
- ✓ Scheduled games kept in raw data for scheduling reference
- ✓ Automatically filtered out during ELO calculations
- ✓ No manual intervention needed

**Check data status anytime:**
```bash
python scripts/check_data_status.py
```

This shows:
- Latest completed game date
- Number of scheduled games
- Data freshness (how many days behind)

## Quick Reference

**Most common update commands:**

```bash
# Check current data status
python scripts/check_data_status.py

# Weekly update (recommended)
python src/etl/fetch_scoreboard.py --start-date YYYYMMDD --end-date YYYYMMDD
python scripts/remove_duplicates.py
python src/engines/team_elo_engine.py --input data/raw/nba_games_all.csv
python scripts/validate_phase_1_5.py

# Check current accuracy
python scripts/validate_phase_1_5.py

# View recent games
tail -20 data/raw/nba_games_all.csv

# View top teams current ratings
python scripts/current_standings.py

# Backup before major update
cp data/raw/nba_games_all.csv backups/nba_games_$(date +%Y%m%d).csv
```

---

## Timeline Recommendations

**During Season (Oct-June):**
- Update **weekly** (every Monday)
- Full validation **monthly**
- Backup before each update

**Offseason (July-Sept):**
- Update **once** after playoffs complete
- Focus on Phase 3 development
- Historical data analysis

**Playoffs (April-June):**
- Update **twice weekly** (high activity)
- Generate playoff prediction reports
- Track accuracy on high-stakes games

---

## Next Steps

1. ✅ **Wait for current scrape to complete** (~4 hours remaining)
2. **Create helper scripts** (dedupe, incremental update)
3. **Test weekly update workflow** (dry run)
4. **Set up weekly calendar reminder** (update every Monday)
5. **Phase 3**: Implement player ELO (after workflow tested)

Your system is production-ready for ongoing updates! 🚀
