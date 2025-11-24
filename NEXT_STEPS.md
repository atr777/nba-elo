# NBA ELO Next Steps - Detailed Task Breakdown

## Overview

This document breaks down the 5 next steps into actionable issues and sub-tasks for implementation. Each task includes specifications, acceptance criteria, and estimated effort.

**Status:** Player boxscore scraping complete ✅ (443,708 records, ~25MB)

---

## Task 1: ✅ Wait for Current Scrape to Complete

**Status:** COMPLETE
- Player boxscores: 443,708 records collected
- File size: ~25MB
- Ready for Phase 3 implementation

---

## Task 2: Create Helper Scripts

### 2.1 Deduplication Script

**File:** `scripts/remove_duplicates.py`

**Purpose:** Remove duplicate games from master dataset based on game_id

**Specifications:**
```python
"""
Remove duplicate games from master dataset

Usage:
    python scripts/remove_duplicates.py [--input FILE] [--output FILE]

Arguments:
    --input: Path to input CSV (default: data/raw/nba_games_all.csv)
    --output: Path to output CSV (default: same as input)

Output:
    - Deduplicated CSV sorted by date
    - Log message showing duplicates removed
    - Total game count
"""

import pandas as pd
import argparse
from pathlib import Path

def remove_duplicates(input_path: str, output_path: str = None):
    """
    Remove duplicate games based on game_id.

    Strategy:
    - Keep 'last' duplicate (most recent scrape has freshest data)
    - Sort by date for chronological processing
    - Preserve all columns

    Returns:
        dict with 'original', 'duplicates', 'final' counts
    """
    pass  # Implementation
```

**Sub-tasks:**
- [ ] Implement core deduplication logic
- [ ] Add command-line argument parsing
- [ ] Add logging (INFO level)
- [ ] Test with sample data containing duplicates
- [ ] Test with full dataset
- [ ] Update UPDATE_WORKFLOW.md to reference script

**Acceptance Criteria:**
- Removes duplicates based on game_id
- Preserves most recent version of duplicates
- Sorts output by date
- Logs clear summary of actions taken
- Handles edge cases (empty file, no duplicates)

**Estimated Effort:** 30 minutes

---

### 2.2 Incremental ELO Update Script

**File:** `scripts/incremental_elo.py`

**Purpose:** Update ELO ratings for new games only (faster than full recalculation)

**Specifications:**
```python
"""
Incrementally update ELO ratings for new games only.

Usage:
    python scripts/incremental_elo.py --new-games FILE [--state FILE]

Arguments:
    --new-games: Path to CSV with new games only
    --state: Path to current ELO state file (default: data/exports/team_elo_current_state.csv)

Process:
    1. Load current ELO state (team ratings, last processed date)
    2. Load new games CSV
    3. Process only games after last processed date
    4. Append to history
    5. Save updated state

Output:
    - Updated team_elo_history.csv (appended)
    - Updated team_elo_current_state.csv (overwritten)
    - Log showing games processed
"""

from src.engines.team_elo_engine import TeamELOEngine
import pandas as pd

def incremental_update(new_games_path: str, state_path: str):
    """
    Load ELO state, process new games, save results.

    State file format:
        team_name,rating,last_game_date,games_played
        Boston Celtics,1650.5,20251122,25
        ...

    Returns:
        int: Number of games processed
    """
    pass  # Implementation
```

**Sub-tasks:**
- [ ] Design ELO state file format (team_name, rating, last_game_date, games_played)
- [ ] Implement state save/load in TeamELOEngine
- [ ] Implement incremental processing logic
- [ ] Add date filtering to skip already-processed games
- [ ] Test with sample new games
- [ ] Test full workflow (state → process → save)
- [ ] Document state file format in ARCHITECTURE.md

**Acceptance Criteria:**
- Loads current ELO state correctly
- Processes only new games (after last_processed_date)
- Appends to history without duplicating
- Saves current state for next run
- 10x+ faster than full recalculation for small updates

**Estimated Effort:** 2 hours

**Note:** This is a performance optimization. For now, full recalculation (5 seconds) is acceptable. This becomes valuable when dataset grows larger or updates become more frequent.

---

### 2.3 Daily Report Generator

**File:** `scripts/generate_daily_report.py`

**Purpose:** Generate markdown summary of daily updates with ELO changes

**Specifications:**
```python
"""
Generate daily update report showing games and ELO changes.

Usage:
    python scripts/generate_daily_report.py [--date YYYYMMDD] [--output DIR]

Arguments:
    --date: Date to report on (default: yesterday)
    --output: Output directory (default: reports/)

Output:
    reports/update_YYYYMMDD.md containing:
    - Games played that day
    - Final scores
    - ELO rating changes
    - Biggest movers (top 5 gains, top 5 losses)
    - Upset alerts (lower-rated team won)
"""

import pandas as pd
from datetime import datetime, timedelta

def generate_report(date: str, output_dir: str = 'reports/'):
    """
    Create markdown report for a specific date.

    Report sections:
    1. Summary (# games, date)
    2. All games with scores
    3. Biggest rating gains (top 5)
    4. Biggest rating losses (top 5)
    5. Upset alerts (underdog wins)
    6. Current top 10 teams by rating

    Returns:
        Path to generated report
    """
    pass  # Implementation
```

**Report Format Example:**
```markdown
# NBA ELO Update - November 23, 2025

## Summary
- **Games Played:** 12
- **Date:** 2025-11-23
- **Update Time:** 2025-11-24 06:00 AM

## Games

| Away Team | Score | Home Team | Score | Winner | Upset? |
|-----------|-------|-----------|-------|--------|--------|
| Lakers | 108 | Celtics | 112 | Celtics | - |
| Warriors | 98 | Suns | 95 | Warriors | ✓ |
...

## Biggest Rating Gains

1. **Golden State Warriors**: +15.2 pts (1625.3 → 1640.5)
   - Beat Phoenix Suns (1680.2) on the road
2. **Miami Heat**: +12.8 pts (1555.0 → 1567.8)
...

## Biggest Rating Losses

1. **Phoenix Suns**: -15.2 pts (1680.2 → 1665.0)
   - Lost to Golden State Warriors (1625.3) at home
...

## Upset Alerts

- **Warriors** (1625.3) defeated **Suns** (1680.2) - 54.9 point underdog
- **Pelicans** (1545.0) defeated **Nuggets** (1590.5) - 45.5 point underdog

## Current Top 10 Teams

1. Boston Celtics - 1705.2
2. Milwaukee Bucks - 1690.5
3. Denver Nuggets - 1685.0
...
```

**Sub-tasks:**
- [ ] Implement data loading and filtering
- [ ] Calculate rating changes from history
- [ ] Identify upset games (lower-rated winner)
- [ ] Generate markdown table formatting
- [ ] Create reports/ directory if missing
- [ ] Test with historical date
- [ ] Add email/Slack notification option (future)

**Acceptance Criteria:**
- Generates clean markdown report
- Shows all games for specified date
- Correctly identifies upsets
- Ranks biggest movers accurately
- Creates output directory if needed
- Handles dates with no games gracefully

**Estimated Effort:** 1.5 hours

---

### 2.4 Clean Scheduled Games Script (Optional)

**File:** `scripts/clean_scheduled_games.py`

**Purpose:** Remove old scheduled games from raw data (optional maintenance)

**Specifications:**
```python
"""
Remove old scheduled games from raw data (optional cleanup).

Usage:
    python scripts/clean_scheduled_games.py [--input FILE] [--dry-run]

Arguments:
    --input: Path to input CSV (default: data/raw/nba_games_all.csv)
    --dry-run: Show what would be removed without modifying file

Logic:
    Keep:
    - All completed games (non-zero scores)
    - Future scheduled games (today onwards)

    Remove:
    - Old scheduled games (past dates with 0-0 scores)
    - Cancelled/postponed games that never happened
"""

def clean_scheduled_games(input_path: str, dry_run: bool = False):
    """
    Remove outdated scheduled games.

    Returns:
        dict with 'kept', 'removed' counts by category
    """
    pass  # Implementation
```

**Sub-tasks:**
- [ ] Implement filtering logic (keep completed + future scheduled)
- [ ] Add dry-run mode for safety
- [ ] Log detailed breakdown of removed games
- [ ] Test with sample data
- [ ] Document when to run (optional, quarterly cleanup)

**Acceptance Criteria:**
- Keeps all completed games
- Keeps future scheduled games
- Removes only old scheduled games
- Dry-run shows changes without modifying
- Logs clear summary

**Estimated Effort:** 45 minutes

**Priority:** LOW (automatic filtering makes this optional)

---

## Workflow Philosophy: Daily vs Weekly

### Daily Workflow (Lightweight & Fast)
**Purpose:** Quick updates during the season for games that happened yesterday

**Characteristics:**
- **Frequency:** Every day during NBA season
- **Scope:** Yesterday's games only (typically 5-15 games)
- **Time:** 2-5 minutes total
- **Automation:** Runs via Task Scheduler at 6 AM
- **Operations:**
  1. Fetch yesterday's games (1-2 seconds)
  2. Append to master file (instant)
  3. Recompute ELO (5 seconds - full dataset)
  4. Auto-commit and push (10 seconds)

**What it DOESN'T do:**
- ❌ Generate reports
- ❌ Run validation suite
- ❌ Clean up old data
- ❌ Check data quality metrics
- ❌ Backup data

**Use case:** Keep data fresh during active season without manual intervention

---

### Weekly Workflow (Comprehensive & Thorough)
**Purpose:** Maintenance, reporting, validation, and cleanup

**Characteristics:**
- **Frequency:** Once per week (recommended: Monday morning)
- **Scope:** Full week's games + maintenance tasks
- **Time:** 10-15 minutes total
- **Automation:** Manual (run when convenient)
- **Operations:**
  1. Fetch past week's games (backup in case daily missed any)
  2. Deduplicate entire dataset
  3. Recompute ELO from scratch
  4. **Run full validation suite** (accuracy, data quality)
  5. **Generate weekly report** (top movers, upsets, trends)
  6. **Clean up old scheduled games**
  7. **Backup data files**
  8. Review and commit with detailed message

**What it DOES that daily doesn't:**
- ✅ Full validation and accuracy check
- ✅ Weekly performance report
- ✅ Data cleanup and optimization
- ✅ Backup creation
- ✅ Trend analysis
- ✅ Manual review opportunity

**Use case:** Weekly health check + comprehensive reporting

---

## Task 3: Weekly Workflow Implementation

### 3.1 Create Weekly Update Script

**File:** `scripts/weekly_update.sh`

**Purpose:** Comprehensive weekly maintenance and reporting script

**Specifications:**
```bash
#!/bin/bash
# Weekly NBA ELO Update & Maintenance Script
# Run every Monday morning for comprehensive weekly maintenance
#
# What this does that daily updates DON'T:
# - Full validation and accuracy checking
# - Weekly performance reports
# - Data cleanup and deduplication
# - Backup creation
# - Trend analysis

set -e  # Exit on error

# Configuration
PROJECT_DIR="c:/Users/Aaron/Desktop/NBA_ELO/nba-elo-engine"
cd $PROJECT_DIR

# Calculate date range (previous 7 days)
END_DATE=$(date -d "yesterday" +%Y%m%d)
START_DATE=$(date -d "7 days ago" +%Y%m%d)
WEEK_NUM=$(date +%U)

echo "========================================================================"
echo "NBA ELO WEEKLY MAINTENANCE - Week $WEEK_NUM"
echo "Date range: $START_DATE to $END_DATE"
echo "Started: $(date)"
echo "========================================================================"

# Step 1: Backup BEFORE any changes
echo ""
echo "[1/8] Creating backup..."
BACKUP_DIR="backups/weekly/week_$WEEK_NUM"
mkdir -p $BACKUP_DIR
cp data/raw/nba_games_all.csv $BACKUP_DIR/nba_games_all.csv
cp data/exports/team_elo_history.csv $BACKUP_DIR/team_elo_history.csv 2>/dev/null || true
echo "  Backup saved to: $BACKUP_DIR"

# Cleanup old weekly backups (keep last 4 weeks)
find backups/weekly -type d -mtime +28 -exec rm -rf {} + 2>/dev/null || true

# Step 2: Fetch week's games (catch any missed by daily updates)
echo ""
echo "[2/8] Fetching past week's games (backup check)..."
python src/etl/fetch_scoreboard.py \
    --start-date $START_DATE \
    --end-date $END_DATE \
    --output data/raw/nba_games_weekly.csv

# Check if any games found
if [ -s data/raw/nba_games_weekly.csv ]; then
    GAME_COUNT=$(wc -l < data/raw/nba_games_weekly.csv)
    echo "  Found $GAME_COUNT games from API"

    # Append new games
    tail -n +2 data/raw/nba_games_weekly.csv >> data/raw/nba_games_all.csv
else
    echo "  No new games found (daily updates likely caught everything)"
fi

# Step 3: Deduplicate entire dataset
echo ""
echo "[3/8] Deduplicating entire dataset..."
python scripts/remove_duplicates.py
echo "  Deduplication complete"

# Step 4: Clean up old scheduled games (weekly maintenance)
echo ""
echo "[4/8] Cleaning up old scheduled games..."
python scripts/clean_scheduled_games.py --dry-run
# Uncomment after reviewing dry-run results:
# python scripts/clean_scheduled_games.py

# Step 5: Recompute ELO from scratch (full recalculation)
echo ""
echo "[5/8] Recomputing ELO ratings (full recalculation)..."
python src/engines/team_elo_engine.py \
    --input data/raw/nba_games_all.csv \
    --output data/exports/team_elo_history.csv \
    --k-factor 20 \
    --home-advantage 70
echo "  ELO computation complete"

# Step 6: Full validation suite
echo ""
echo "[6/8] Running full validation suite..."
python scripts/validate_phase_1_5.py > reports/weekly/week_${WEEK_NUM}_validation.txt
cat reports/weekly/week_${WEEK_NUM}_validation.txt
echo "  Validation saved to: reports/weekly/week_${WEEK_NUM}_validation.txt"

# Step 7: Generate weekly report
echo ""
echo "[7/8] Generating weekly performance report..."
python scripts/generate_weekly_report.py --week $WEEK_NUM \
    --start-date $START_DATE \
    --end-date $END_DATE
echo "  Report saved to: reports/weekly/week_${WEEK_NUM}_report.md"

# Step 8: Data status summary
echo ""
echo "[8/8] Final data status check..."
python scripts/check_data_status.py

# Summary
echo ""
echo "========================================================================"
echo "WEEKLY MAINTENANCE COMPLETE"
echo "========================================================================"
echo ""
echo "Summary:"
echo "  - Week: $WEEK_NUM ($START_DATE to $END_DATE)"
echo "  - Backup: $BACKUP_DIR"
echo "  - Validation: reports/weekly/week_${WEEK_NUM}_validation.txt"
echo "  - Report: reports/weekly/week_${WEEK_NUM}_report.md"
echo ""
echo "Next steps:"
echo "  1. Review weekly report: cat reports/weekly/week_${WEEK_NUM}_report.md"
echo "  2. Check validation results above"
echo "  3. Review git changes: git diff"
echo "  4. Commit: git add . && git commit -m 'Weekly update: Week $WEEK_NUM'"
echo "  5. Push: git push"
echo ""
echo "Completed: $(date)"
echo "========================================================================"
```

**Sub-tasks:**
- [ ] Create scripts/weekly_update.sh
- [ ] Add execute permissions (chmod +x)
- [ ] Test with dry run (comment out file modifications)
- [ ] Test with real data (small date range)
- [ ] Add error handling and rollback
- [ ] Document in UPDATE_WORKFLOW.md

**Acceptance Criteria:**
- Automatically calculates previous week's date range
- Backs up data before modifications
- Handles "no new games" gracefully
- Shows clear progress indicators
- Exits on errors (set -e)
- Provides next steps for user

**Estimated Effort:** 1 hour

---

### 3.2 Dry Run Testing

**Purpose:** Test weekly workflow with sample data before using in production

**Procedure:**
1. Create test branch: `git checkout -b test/weekly-update`
2. Manually set date range to known period (e.g., Nov 15-21)
3. Run weekly_update.sh with modifications commented out
4. Verify each step executes correctly
5. Enable modifications, test with small date range (1 day)
6. Validate results match expected
7. Document any issues found
8. Create final production-ready script

**Sub-tasks:**
- [ ] Create test branch
- [ ] Test each script step independently
- [ ] Test full workflow with 1-day range
- [ ] Verify backup creation
- [ ] Verify deduplication works
- [ ] Verify ELO recalculation accuracy
- [ ] Verify validation passes
- [ ] Document test results

**Acceptance Criteria:**
- All steps execute without errors
- Backups created correctly
- Duplicates removed as expected
- ELO calculations match manual verification
- Validation reports expected accuracy
- No data loss or corruption

**Estimated Effort:** 1.5 hours

---

### 3.3 Documentation Update

**Purpose:** Document weekly workflow in UPDATE_WORKFLOW.md

**Sub-tasks:**
- [ ] Add "Tested Workflow" section to UPDATE_WORKFLOW.md
- [ ] Include example commands
- [ ] Add troubleshooting section
- [ ] Document backup/restore procedure
- [ ] Add rollback procedure for failed updates

**Estimated Effort:** 30 minutes

---

### 3.4 Create Weekly Report Generator

**File:** `scripts/generate_weekly_report.py`

**Purpose:** Generate comprehensive weekly performance report with trends and insights

**Specifications:**
```python
"""
Generate weekly NBA ELO performance report

Usage:
    python scripts/generate_weekly_report.py --week 47 --start-date 20251117 --end-date 20251123

Output: reports/weekly/week_47_report.md
"""

import pandas as pd
import argparse
from datetime import datetime

def generate_weekly_report(week_num, start_date, end_date):
    """
    Generate comprehensive weekly report

    Sections:
    1. Summary (games, dates, accuracy)
    2. Biggest Rating Changes (top gainers/losers)
    3. Upset Alert (biggest upsets of the week)
    4. Current Top 10 Teams
    5. Trending Up/Down (week-over-week changes)
    6. Key Insights (notable patterns)
    """

    # Load data
    games = pd.read_csv('data/raw/nba_games_all.csv')
    elo_history = pd.read_csv('data/exports/team_elo_history.csv')

    # Filter to this week
    week_games = games[(games['date'] >= int(start_date)) & (games['date'] <= int(end_date))]

    report = f"""# NBA ELO Weekly Report - Week {week_num}

**Period:** {start_date[:4]}-{start_date[4:6]}-{start_date[6:8]} to {end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## Summary

- **Games Played:** {len(week_games)}
- **Teams Active:** {week_games['home_team_name'].nunique()}
- **Total Points Scored:** {week_games['home_score'].sum() + week_games['away_score'].sum():,}
- **Average Margin:** {abs(week_games['home_score'] - week_games['away_score']).mean():.1f} points

---

## Biggest Rating Changes

### Top 5 Gainers
[Team rankings with biggest ELO gains this week]

### Top 5 Losers
[Team rankings with biggest ELO drops this week]

---

## Upset Alert

[Biggest upsets where lower-rated team won]

---

## Current Top 10 Teams

[ELO rankings as of end of week]

---

## Trending Analysis

**Rising Teams:** [Teams with consistent gains]
**Falling Teams:** [Teams with consistent losses]

---

## Key Insights

- Notable streaks
- Surprising performances
- Statistical anomalies

---

*Report generated automatically by NBA ELO system*
"""

    return report
```

**Sub-tasks:**
- [ ] Implement weekly report generator
- [ ] Add top gainers/losers analysis
- [ ] Add upset detection logic
- [ ] Add trend analysis (3-week rolling)
- [ ] Add visual formatting (tables, emoji indicators)
- [ ] Test with sample week

**Acceptance Criteria:**
- Generates markdown report
- Identifies top movers accurately
- Detects upsets (lower ELO wins)
- Shows current rankings
- Trend analysis over 3 weeks
- Clean, readable format

**Estimated Effort:** 2 hours

---

## Task 4: Finalize Daily Update Workflow

### 4.1 Create Daily Update Script

**File:** `scripts/daily_update.sh`

**Purpose:** Automated daily update for tracking current season

**Specifications:**
```bash
#!/bin/bash
# Daily NBA ELO Update Script
# Designed to run via Windows Task Scheduler every morning at 6:00 AM

set -e

# Configuration
PROJECT_DIR="c:/Users/Aaron/Desktop/NBA_ELO/nba-elo-engine"
LOG_DIR="$PROJECT_DIR/logs"
TODAY=$(date +%Y%m%d)
YESTERDAY=$(date -d "yesterday" +%Y%m%d)

cd $PROJECT_DIR
mkdir -p $LOG_DIR

# Log file
LOG_FILE="$LOG_DIR/daily_update_$TODAY.log"

# Redirect all output to log
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

echo "========================================"
echo "NBA ELO Daily Update - $TODAY"
echo "Started: $(date)"
echo "========================================"

# Step 1: Fetch yesterday's games
echo ""
echo "[1/5] Fetching games from $YESTERDAY..."
python src/etl/fetch_scoreboard.py \
    --start-date $YESTERDAY \
    --end-date $YESTERDAY \
    --output data/raw/daily_update.csv

# Check if games found
if [ ! -s data/raw/daily_update.csv ]; then
    echo "No games found for $YESTERDAY. This is normal for off-days."
    echo "Completed: $(date)"
    exit 0
fi

GAME_COUNT=$(wc -l < data/raw/daily_update.csv)
echo "Found $GAME_COUNT games"

# Step 2: Quick backup (keep last 7 days)
echo ""
echo "[2/5] Creating backup..."
BACKUP_FILE="backups/daily/nba_games_all_$TODAY.csv"
mkdir -p backups/daily
cp data/raw/nba_games_all.csv $BACKUP_FILE

# Cleanup old backups (keep last 7 days)
find backups/daily -name "*.csv" -mtime +7 -delete

# Step 3: Append new games
echo ""
echo "[3/5] Appending to master file..."
tail -n +2 data/raw/daily_update.csv >> data/raw/nba_games_all.csv

# Step 4: Deduplicate
echo ""
echo "[4/5] Removing duplicates..."
python scripts/remove_duplicates.py

# Step 5: Recompute ELO (incremental in future)
echo ""
echo "[5/5] Updating ELO ratings..."
python src/engines/team_elo_engine.py \
    --input data/raw/nba_games_all.csv \
    --output data/exports/team_elo_history.csv

# Generate daily report
echo ""
echo "Generating daily report..."
python scripts/generate_daily_report.py --date $YESTERDAY

# Data status
echo ""
python scripts/check_data_status.py

# Auto-commit (enabled by default for daily updates)
AUTO_COMMIT=${AUTO_COMMIT:-true}  # Default to true unless explicitly disabled

if [ "$AUTO_COMMIT" = "true" ]; then
    echo ""
    echo "Auto-committing changes..."
    git add data/raw/nba_games_all.csv data/exports/ reports/
    git commit -m "Auto-update: Games from $YESTERDAY ($GAME_COUNT games)"

    if git push origin main; then
        echo "Successfully pushed to GitHub"
    else
        echo "ERROR: Failed to push to GitHub"
        python scripts/send_alert.py --type error --message "Daily update: Git push failed"
        exit 1
    fi
fi

echo ""
echo "========================================"
echo "Daily update complete!"
echo "Completed: $(date)"
echo "Log saved to: $LOG_FILE"
echo "========================================"
```

**Sub-tasks:**
- [ ] Create scripts/daily_update.sh
- [ ] Add logging to file
- [ ] Add automatic backup cleanup (keep 7 days)
- [ ] Add optional auto-commit (disabled by default)
- [ ] Test manually
- [ ] Document log file locations

**Acceptance Criteria:**
- Fetches only yesterday's games
- Handles off-days (no games) gracefully
- Logs all output to file
- Cleans up old backups automatically
- Optional auto-commit works
- Exit codes correct for scheduler

**Estimated Effort:** 1 hour

---

### 4.2 Windows Task Scheduler Setup

**Purpose:** Configure Windows to run daily updates automatically

**Documentation:**
```markdown
# Windows Task Scheduler Configuration

## Create Scheduled Task

1. Open Task Scheduler (taskschd.msc)
2. Create Task (not Basic Task)

**General Tab:**
- Name: NBA ELO Daily Update
- Description: Updates NBA game data and ELO ratings daily
- Run whether user is logged on or not: ✓
- Run with highest privileges: ✓

**Triggers Tab:**
- New Trigger
- Begin: On a schedule
- Daily, 6:00 AM
- Repeat: No
- Enabled: ✓

**Actions Tab:**
- New Action
- Action: Start a program
- Program: C:\Program Files\Git\bin\bash.exe
- Arguments: scripts/daily_update.sh
- Start in: c:\Users\Aaron\Desktop\NBA_ELO\nba-elo-engine

**Conditions Tab:**
- Start only if computer is on AC power: ✗
- Wake computer to run: ✓

**Settings Tab:**
- Allow task to be run on demand: ✓
- If task fails, restart every: 10 minutes (3 attempts)
- Stop task if runs longer than: 1 hour

## Test the Task

Right-click task → Run

Check log file: logs/daily_update_YYYYMMDD.log

## Troubleshooting

**Task runs but nothing happens:**
- Check "Start in" directory is correct
- Verify Git bash path
- Check logs/ directory for output

**Task fails immediately:**
- Run manually: bash scripts/daily_update.sh
- Check Python is in PATH
- Verify all scripts exist
```

**Sub-tasks:**
- [ ] Document Task Scheduler configuration
- [ ] Create XML export of task configuration
- [ ] Test task runs correctly
- [ ] Test wake-from-sleep functionality
- [ ] Document troubleshooting steps

**Estimated Effort:** 45 minutes

---

### 4.3 Email Alert System

**Purpose:** Send email notifications on errors or accuracy drops

**File:** `scripts/send_alert.py`

**Specifications:**
```python
"""
Send email alerts for NBA ELO system events.

Usage:
    python scripts/send_alert.py --type error --message "Failed to fetch data"
    python scripts/send_alert.py --type accuracy --current 64.5 --threshold 65.0

Arguments:
    --type: Alert type (error, accuracy, success)
    --message: Custom message
    --current: Current accuracy (for accuracy alerts)
    --threshold: Accuracy threshold (for accuracy alerts)

Email configuration (environment variables):
    ALERT_EMAIL_TO: Recipient email (e.g., your@email.com)
    ALERT_EMAIL_FROM: Sender email (e.g., nba-elo-bot@gmail.com)
    ALERT_EMAIL_PASSWORD: App-specific password
    ALERT_SMTP_SERVER: SMTP server (default: smtp.gmail.com)
    ALERT_SMTP_PORT: SMTP port (default: 587)
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def send_email_alert(alert_type: str, message: str, current_accuracy: float = None):
    """
    Send email alert using Gmail SMTP.

    Setup:
    1. Create Gmail app-specific password:
       - Google Account → Security → 2-Step Verification → App passwords
       - Generate password for "Mail" on "Windows Computer"

    2. Set environment variables:
       - ALERT_EMAIL_TO=your@email.com
       - ALERT_EMAIL_FROM=nba-elo-bot@gmail.com
       - ALERT_EMAIL_PASSWORD=xxxx-xxxx-xxxx-xxxx

    3. Test:
       python scripts/send_alert.py --type test --message "Testing email alerts"
    """
    to_email = os.getenv('ALERT_EMAIL_TO')
    from_email = os.getenv('ALERT_EMAIL_FROM')
    password = os.getenv('ALERT_EMAIL_PASSWORD')
    smtp_server = os.getenv('ALERT_SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('ALERT_SMTP_PORT', '587'))

    if not all([to_email, from_email, password]):
        print("Email alerts not configured. Set ALERT_EMAIL_* environment variables.")
        return False

    # Compose message
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if alert_type == 'error':
        msg['Subject'] = f'[NBA ELO] ERROR - Daily Update Failed'
        body = f"""
NBA ELO Daily Update encountered an error:

{message}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Check logs at: c:/Users/Aaron/Desktop/NBA_ELO/nba-elo-engine/logs/

Action required: Review and manually run update.
"""
    elif alert_type == 'accuracy':
        msg['Subject'] = f'[NBA ELO] WARNING - Accuracy Drop Detected'
        body = f"""
NBA ELO prediction accuracy has dropped below threshold:

Current Accuracy: {current_accuracy:.2f}%
Threshold: 65.0%
Drop: {65.0 - current_accuracy:.2f} percentage points

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Possible causes:
- Recent games had unusual outcomes
- Data quality issues
- Model parameters need adjustment

Action: Review recent games and validation results.
"""
    elif alert_type == 'success':
        msg['Subject'] = f'[NBA ELO] Daily Update Successful'
        body = f"""
NBA ELO daily update completed successfully.

{message}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    else:  # test
        msg['Subject'] = f'[NBA ELO] Test Alert'
        body = f"""
Test alert from NBA ELO system.

{message}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Email alerts are configured correctly!
"""

    msg.attach(MIMEText(body, 'plain'))

    try:
        # Connect and send
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(from_email, password)
        server.send_message(msg)
        server.quit()
        print(f"Email alert sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--type', required=True, choices=['error', 'accuracy', 'success', 'test'])
    parser.add_argument('--message', required=True)
    parser.add_argument('--current', type=float, help='Current accuracy (for accuracy alerts)')
    args = parser.parse_args()

    send_email_alert(args.type, args.message, args.current)
```

**Email Setup Instructions:**

**Step 1: Create Gmail App Password**
1. Go to Google Account → Security
2. Enable 2-Step Verification
3. Go to App Passwords
4. Generate password for "Mail" on "Windows Computer"
5. Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)

**Step 2: Configure Environment Variables**

Create `.env` file in project root:
```bash
# Email Alert Configuration
ALERT_EMAIL_TO=your@email.com
ALERT_EMAIL_FROM=nba-elo-bot@gmail.com
ALERT_EMAIL_PASSWORD=abcdefghijklmnop
```

Add to `.gitignore`:
```
.env
```

Load in scripts:
```bash
# Add to daily_update.sh
if [ -f .env ]; then
    export $(cat .env | xargs)
fi
```

**Step 3: Test Email Alerts**
```bash
# Test basic email
python scripts/send_alert.py --type test --message "Testing email alerts"

# Test error alert
python scripts/send_alert.py --type error --message "Simulated failure"

# Test accuracy alert
python scripts/send_alert.py --type accuracy --current 64.5 --message "Accuracy dropped"
```

**Integration with daily_update.sh:**
```bash
# Load environment variables
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# Notify on error
if ! python src/etl/fetch_scoreboard.py ...; then
    python scripts/send_alert.py --type error --message "Failed to fetch scoreboard data"
    exit 1
fi

# Notify on accuracy drop (add to validation step)
ACCURACY=$(python scripts/validate_phase_1_5.py | grep "Accuracy:" | awk '{print $2}' | tr -d '%')
if (( $(echo "$ACCURACY < 65.0" | bc -l) )); then
    python scripts/send_alert.py --type accuracy --current "$ACCURACY" --message "Accuracy below threshold"
fi

# Optional: Notify on success
if [ "$NOTIFY_SUCCESS" = "true" ]; then
    python scripts/send_alert.py --type success --message "Updated $GAME_COUNT games, accuracy: ${ACCURACY}%"
fi
```

**Sub-tasks:**
- [ ] Create scripts/send_alert.py
- [ ] Document Gmail app password setup
- [ ] Create .env template file
- [ ] Add .env to .gitignore
- [ ] Test email sending
- [ ] Integrate into daily_update.sh
- [ ] Test error scenarios
- [ ] Test accuracy drop scenario

**Acceptance Criteria:**
- Email alerts send successfully
- Error alerts triggered on failures
- Accuracy alerts triggered when < 65%
- Success alerts optional (disabled by default)
- Environment variables loaded securely
- .env file not committed to git

**Estimated Effort:** 1.5 hours

---

## Task 5: Phase 3 - Implement Player ELO

**Reference:** PHASE_3_PLAN.md (15-day implementation schedule)

### Week 1: Data Validation & Player ELO Engine

#### 5.1 Validate Player Boxscore Data

**File:** `scripts/validate_player_data.py`

**Purpose:** Ensure scraped player data is complete and accurate

**Sub-tasks:**
- [ ] Load player_boxscores_all.csv (443,708 records)
- [ ] Check for missing critical fields (player_id, game_id, minutes, +/-)
- [ ] Verify game_id matches games in nba_games_all.csv
- [ ] Check date ranges (should match team game dates)
- [ ] Identify players with most games (sanity check)
- [ ] Calculate total minutes per game (should ≈ 240)
- [ ] Generate validation report

**Acceptance Criteria:**
- All games have corresponding player boxscores
- No critical missing data
- Minutes per game sum to ~240 (accounting for OT)
- Player IDs consistent
- Date ranges match team data

**Estimated Effort:** 2 hours

---

#### 5.2 Create Player ELO Engine

**File:** `src/engines/player_elo_engine.py`

**Purpose:** Core player ELO calculation engine

**Specifications:**
```python
"""
Player ELO Engine - Individual player rating system

Algorithm:
1. Each player starts at 1500 rating
2. After each game, rating adjusted based on:
   - Game outcome (win/loss)
   - Plus/Minus performance
   - Minutes played (weight)
   - Opponent team strength

Formula:
    Expected_Score = 1 / (1 + 10^((OpponentTeamELO - PlayerELO) / 400))
    Actual_Score = (PlusMinus + 20) / 40  # Normalize ±20 to 0-1 scale

    Rating_Change = K * Minutes/48 * (Actual - Expected)

    Where:
    - K = 20 (same as team ELO)
    - Minutes/48 = weight (players with more minutes weighted higher)
"""

class PlayerELOEngine:
    def __init__(self, k_factor=20, initial_rating=1500):
        self.k_factor = k_factor
        self.initial_rating = initial_rating
        self.player_ratings = {}  # {player_id: rating}

    def get_rating(self, player_id: str) -> float:
        """Get player's current rating"""
        pass

    def process_game(self, boxscore_row: dict, team_elo_home: float, team_elo_away: float):
        """
        Update player rating based on single game performance.

        Args:
            boxscore_row: Player's boxscore stats
            team_elo_home: Home team's ELO rating
            team_elo_away: Away team's ELO rating
        """
        pass

    def compute_all_ratings(self, boxscores_df: pd.DataFrame, team_elo_history: pd.DataFrame):
        """Process all player boxscores chronologically"""
        pass
```

**Sub-tasks:**
- [ ] Implement PlayerELOEngine class
- [ ] Implement get_rating() method
- [ ] Implement process_game() with plus/minus formula
- [ ] Add minutes-weighting (players with more minutes = larger updates)
- [ ] Join with team ELO data for opponent strength
- [ ] Test with sample player (LeBron James)
- [ ] Validate ratings make sense (stars > role players)

**Acceptance Criteria:**
- Player ratings start at 1500
- Updates based on plus/minus and minutes
- Stars (high plus/minus, high minutes) rated 1700+
- Role players (low minutes) rated 1400-1600
- Chronological processing (games in order)

**Estimated Effort:** 4 hours

---

#### 5.3 Export Player ELO History

**File:** `data/exports/player_elo_history.csv`

**Format:**
```csv
player_id,player_name,game_id,date,team,opponent,minutes,plus_minus,rating_before,rating_after,rating_change
2544,LeBron James,401584901,20231025,LAL,DEN,35,+12,1685.5,1702.3,+16.8
2544,LeBron James,401584920,20231027,LAL,PHX,38,-5,1702.3,1695.1,-7.2
...
```

**Sub-tasks:**
- [ ] Design export format
- [ ] Implement export in player_elo_engine.py
- [ ] Generate full history file
- [ ] Verify chronological order
- [ ] Spot-check star players' ratings

**Estimated Effort:** 1 hour

---

### Week 2: Minutes-Weighted Team Aggregation

#### 5.4 Aggregate Player Ratings to Team Rating

**Purpose:** Combine individual player ELOs into team rating based on minutes distribution

**Algorithm:**
```python
def aggregate_team_rating(player_ratings: dict, minutes_distribution: dict) -> float:
    """
    Aggregate player ratings into single team rating.

    Args:
        player_ratings: {player_id: elo_rating}
        minutes_distribution: {player_id: minutes_played_this_season}

    Returns:
        Weighted average team rating

    Example:
        Lakers rotation:
        - LeBron: 1750 ELO, 1200 minutes (35 mpg) → weight: 35%
        - AD: 1720 ELO, 1150 minutes (34 mpg) → weight: 33%
        - Reaves: 1580 ELO, 850 minutes (25 mpg) → weight: 25%
        - Bench: 1500 ELO, 200 minutes (6 mpg) → weight: 7%

        Team Rating = 0.35*1750 + 0.33*1720 + 0.25*1580 + 0.07*1500
                    = 1680.5
    """
    total_minutes = sum(minutes_distribution.values())
    weighted_rating = 0

    for player_id, minutes in minutes_distribution.items():
        weight = minutes / total_minutes
        weighted_rating += weight * player_ratings[player_id]

    return weighted_rating
```

**Sub-tasks:**
- [ ] Implement aggregate_team_rating() function
- [ ] Calculate season-to-date minutes for each team
- [ ] Generate team ratings from player ELOs
- [ ] Compare to pure team ELO (Phase 1.5)
- [ ] Analyze differences (should be similar for established teams)

**Estimated Effort:** 3 hours

---

#### 5.5 Handle Trade Impact

**Purpose:** Adjust team ratings when players are traded

**Algorithm:**
```python
def handle_trade(team_ratings: dict, player_id: str,
                 from_team: str, to_team: str,
                 trade_date: str):
    """
    Update team ratings when player changes teams.

    Logic:
    1. Remove player's weighted contribution from old team
    2. Add player's weighted contribution to new team
    3. Redistribute minutes (assume traded player gets 20 mpg initially)

    Example:
        Trade: Russell Westbrook (1620 ELO) from Lakers to Clippers

        Lakers before: 1680 (includes Westbrook's 25 mpg)
        Lakers after: 1685 (reallocate 25 mpg to other players)

        Clippers before: 1650
        Clippers after: 1655 (add Westbrook at 20 mpg)
    """
    pass
```

**Sub-tasks:**
- [ ] Research 2024-25 trades (test data)
- [ ] Implement trade handling logic
- [ ] Test with known trades (James Harden to Clippers, etc.)
- [ ] Validate ratings adjust reasonably
- [ ] Document trade impact in reports

**Estimated Effort:** 2 hours

**Note:** This is a future enhancement. Initial implementation can skip trades.

---

### Week 3: Testing & Integration

#### 5.6 Run Full Player ELO Calculation

**Purpose:** Generate complete player ELO history for all 443K boxscores

**Sub-tasks:**
- [ ] Run player_elo_engine.py on full dataset
- [ ] Measure computation time (target: < 60 seconds)
- [ ] Generate player_elo_history.csv
- [ ] Generate player_elo_current.csv (current ratings)
- [ ] Spot-check top players (LeBron, Steph, KD, Giannis)
- [ ] Verify ratings distribution (bell curve around 1500)

**Acceptance Criteria:**
- All 443K boxscores processed
- Computation time < 60 seconds
- Top 10 players rated 1700+
- Rookies/bench rated 1300-1500
- No crashes or errors

**Estimated Effort:** 1 hour (mostly runtime)

---

#### 5.7 Hybrid Prediction Model

**Purpose:** Combine team ELO and player ELO for improved predictions

**Algorithm:**
```python
def hybrid_prediction(team_elo_home: float, team_elo_away: float,
                      player_elo_home: float, player_elo_away: float,
                      blend_weight: float = 0.7) -> float:
    """
    Blend team-based and player-based ELO predictions.

    Args:
        team_elo_home: Pure team ELO rating (Phase 1.5)
        team_elo_away: Pure team ELO rating (Phase 1.5)
        player_elo_home: Aggregated player ELO
        player_elo_away: Aggregated player ELO
        blend_weight: How much to trust team ELO (0.7 = 70% team, 30% player)

    Returns:
        Blended ELO rating for home team

    Example:
        Team ELO: Lakers 1680 vs Celtics 1700 (Celtics favored)
        Player ELO: Lakers 1690 vs Celtics 1695 (closer)

        Blended: 0.7 * (1680-1700) + 0.3 * (1690-1695) = -15.5

        Home team 15.5 points weaker → Celtics favored by 15.5 on road
        With 70 HCA → Lakers slight favorite at home
    """
    team_diff = team_elo_home - team_elo_away
    player_diff = player_elo_home - player_elo_away

    blended_diff = blend_weight * team_diff + (1 - blend_weight) * player_diff

    return blended_diff
```

**Sub-tasks:**
- [ ] Implement hybrid prediction function
- [ ] Test blend weights (0.5, 0.6, 0.7, 0.8)
- [ ] Run validation on full dataset
- [ ] Measure accuracy for each blend weight
- [ ] Select optimal weight (target: 66-68% accuracy)

**Acceptance Criteria:**
- Hybrid model outperforms pure team ELO (>65.69%)
- Target accuracy: 66-68%
- Blend weight optimized
- Predictions make intuitive sense

**Estimated Effort:** 3 hours

---

#### 5.8 Phase 3 Validation

**File:** `scripts/validate_phase_3.py`

**Purpose:** Comprehensive validation of player ELO system

**Validation Checks:**
1. Player rating distribution (bell curve)
2. Top 50 players rated 1650+ (superstars)
3. Prediction accuracy (hybrid model)
4. Trade impact (if implemented)
5. Computation performance (< 60 seconds)
6. Data completeness (all games have player data)

**Sub-tasks:**
- [ ] Create validation script
- [ ] Run all validation checks
- [ ] Generate Phase 3 completion report
- [ ] Update PHASE_3_COMPLETE.md
- [ ] Update PROJECT_SUMMARY.md with Phase 3 status

**Estimated Effort:** 2 hours

---

## Summary of Effort Estimates

| Task | Estimated Effort | Priority |
|------|-----------------|----------|
| **Task 2: Helper Scripts** | | |
| 2.1 Deduplication script | 30 min | HIGH |
| 2.2 Incremental ELO | 2 hours | MEDIUM |
| 2.3 Daily report generator | 1.5 hours | MEDIUM |
| 2.4 Clean scheduled games | 45 min | LOW |
| **Task 3: Weekly Workflow** | | |
| 3.1 Weekly update script | 1 hour | HIGH |
| 3.2 Dry run testing | 1.5 hours | HIGH |
| 3.3 Documentation | 30 min | MEDIUM |
| 3.4 Weekly report generator | 2 hours | HIGH |
| **Task 4: Daily Workflow** | | |
| 4.1 Daily update script | 1 hour | HIGH |
| 4.2 Task Scheduler setup | 45 min | HIGH |
| 4.3 Email alert system | 1.5 hours | HIGH |
| **Task 5: Phase 3** | | |
| 5.1 Validate player data | 2 hours | HIGH |
| 5.2 Player ELO engine | 4 hours | HIGH |
| 5.3 Export player history | 1 hour | HIGH |
| 5.4 Team aggregation | 3 hours | HIGH |
| 5.5 Trade impact | 2 hours | LOW |
| 5.6 Full calculation | 1 hour | HIGH |
| 5.7 Hybrid prediction | 3 hours | HIGH |
| 5.8 Phase 3 validation | 2 hours | HIGH |
| **TOTAL** | **~30.5 hours** | |

---

## Recommended Implementation Order

### Quick Comparison: Daily vs Weekly

| Aspect | Daily Workflow | Weekly Workflow |
|--------|---------------|-----------------|
| **Frequency** | Every day (automated) | Once per week (manual) |
| **Duration** | 2-5 minutes | 10-15 minutes |
| **Scope** | Yesterday's games only | Full week + maintenance |
| **Fetch Data** | Yesterday (~10 games) | Week's games (~70 games) |
| **Deduplication** | No | Yes (full dataset) |
| **ELO Calculation** | Full recalc (5 sec) | Full recalc from scratch |
| **Validation** | No | Yes (full suite) |
| **Reports** | No | Yes (comprehensive) |
| **Cleanup** | No | Yes (old scheduled games) |
| **Backup** | No | Yes (weekly snapshots) |
| **Git Commit** | Auto (simple message) | Manual (detailed review) |
| **Email Alerts** | On error only | On completion + summary |
| **Use When** | Season active, hands-off | Weekly check-in, review needed |

---

### Sprint 1: Core Helper Scripts (Day 1-2, ~6 hours)
1. ✅ Deduplication script (30 min)
2. ✅ Daily report generator (1.5 hours)
3. ✅ Weekly update script (1 hour)
4. ✅ Weekly report generator (2 hours)
5. ✅ Dry run testing (1.5 hours)

**Goal:** Enable both daily and weekly workflows

---

### Sprint 2: Automation (Day 3-4, ~5 hours)
1. ✅ Daily update script with auto-commit (1 hour)
2. ✅ Email alert system (1.5 hours)
3. ✅ Task Scheduler setup (45 min)
4. ✅ Test email notifications (30 min)
5. ✅ Incremental ELO (2 hours)

**Goal:** Enable automated daily updates with email notifications

---

### Sprint 3: Phase 3 Foundation (Day 5-6, ~7 hours)
1. ✅ Validate player data (2 hours)
2. ✅ Player ELO engine (4 hours)
3. ✅ Export player history (1 hour)

**Goal:** Player ELO calculations working

---

### Sprint 4: Phase 3 Advanced (Day 7-8, ~6 hours)
1. ✅ Team aggregation (3 hours)
2. ✅ Hybrid prediction (3 hours)
3. ✅ Phase 3 validation (included in #2)

**Goal:** Achieve 66-68% accuracy

---

### Sprint 5: Polish & Documentation (Day 9, ~2 hours)
1. ✅ Documentation updates (PHASE_3_COMPLETE.md, PROJECT_SUMMARY.md)
2. ✅ Final testing across all components
3. ✅ Commit and push to GitHub
4. ⏳ Trade impact (deferred to Phase 4)

**Goal:** Phase 3 complete and documented

---

## Success Metrics

### Task 2-4: Workflows
- ✅ Weekly update runs without errors
- ✅ Daily update runs via Task Scheduler
- ✅ Backups created automatically
- ✅ Reports generated correctly
- ✅ Data status always current

### Task 5: Phase 3
- ✅ Player ELO calculations complete (443K boxscores)
- ✅ Top players rated correctly (1700+)
- ✅ Hybrid model accuracy: **66-68%** (target)
- ✅ Computation time: < 60 seconds
- ✅ All validation checks pass

---

## Questions to Resolve Before Starting ✅

1. **Incremental ELO priority:** ✅ **Needed now** - Implement in Sprint 1
2. **Auto-commit preference:** ✅ **Enable by default** - Daily updates auto-commit & push
3. **Notification method:** ✅ **Email alerts** - Send on errors or accuracy drops
4. **Trade impact:** ✅ **Defer to Phase 4** - Not in initial Phase 3 scope
5. **Blend weight:** ✅ **Start with 0.7, test 0.5-0.8** - Optimize in Task 5.7

### Blend Weight Explanation

**What it is:** Weight determining trust in team ELO (Phase 1.5) vs player ELO (Phase 3)

**Formula:**
```
Hybrid_Rating = (0.7 × Team_ELO) + (0.3 × Player_ELO)  # Default blend weight = 0.7
```

**Why 0.7?**
- Team chemistry, coaching, system > individual talent alone
- FiveThirtyEight uses ~70/30 split in RAPTOR
- Balances team factors with roster changes

**Testing approach (Task 5.7):**
- Test weights: 0.5, 0.6, 0.7, 0.8
- Measure accuracy on 31,068 games
- Select weight with highest accuracy
- Target: 66-68% (vs 65.69% baseline)

---

## Ready to Begin!

All tasks are broken down into actionable sub-tasks with clear acceptance criteria. Let me know which sprint you'd like to start with, or if you'd like to adjust priorities!
