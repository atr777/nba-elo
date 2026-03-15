#!/bin/bash
# NBA_ELO Daily Pipeline — Linux/VPS version
# Replaces: run_daily_update.bat + push_github_pages.bat
#
# Scheduled via cron — see setup_vps.sh or crontab -e
# Logs to: /opt/nba-elo/nba-elo-engine/logs/daily_update.log
#
# Auto-pulls latest code from GitHub on every run — changes made via
# Claude Code on Windows PC are picked up automatically after a git push.

PROJECT_DIR="/opt/nba-elo/nba-elo-engine"
PYTHON="/opt/nba-elo/venv/bin/python"
LOG="$PROJECT_DIR/logs/daily_update.log"
PAGES_DIR="$PROJECT_DIR/pages"

cd "$PROJECT_DIR" || exit 1

{
  echo ""
  echo "============================================================"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] NBA_ELO Daily Pipeline Starting"
  echo "============================================================"

  # Auto-pull latest code from GitHub
  # Any changes pushed from the Windows PC are picked up here automatically
  echo "[$(date '+%H:%M:%S')] Pulling latest code from GitHub..."
  git pull origin master 2>&1 || echo "WARNING: git pull failed, continuing with current code"

  # Check data freshness
  python3 -c "
import os, datetime
f='data/raw/nba_games_all.csv'
if os.path.exists(f):
    age=(datetime.datetime.now()-datetime.datetime.fromtimestamp(os.path.getmtime(f))).days
    print(f'WARNING: data is {age} days old' if age>2 else f'OK: data is {age} days old')
else:
    print('ERROR: nba_games_all.csv not found — run data transfer from Windows first')
" 2>&1

  # Step 1: Full daily update (fetches games + recalculates ELO)
  echo "[$(date '+%H:%M:%S')] Step 1/3: Running daily_update.py"
  $PYTHON scripts/daily_update.py
  if [ $? -ne 0 ]; then
    echo "[$(date '+%H:%M:%S')] ERROR: daily_update.py failed with exit code $?"
    exit 1
  fi

  # Step 2: Export newsletter (non-blocking — failure won't stop pipeline)
  echo "[$(date '+%H:%M:%S')] Step 2/3: Running export_substack_daily.py"
  $PYTHON scripts/export_substack_daily.py 2>&1 || echo "[$(date '+%H:%M:%S')] WARNING: Newsletter export failed"

  # Step 3: Generate and push GitHub Pages
  echo "[$(date '+%H:%M:%S')] Step 3/3: Generating GitHub Pages HTML"
  $PYTHON scripts/export_github_pages.py
  if [ $? -eq 0 ]; then
    cd "$PAGES_DIR"
    git add index.html
    if git diff --cached --quiet; then
      echo "[$(date '+%H:%M:%S')] No changes to push today"
    else
      git commit -m "Predictions $(date '+%Y-%m-%d %H:%M')"
      git push origin main \
        && echo "[$(date '+%H:%M:%S')] GitHub Pages updated successfully" \
        || echo "[$(date '+%H:%M:%S')] WARNING: GitHub Pages push failed"
    fi
    cd "$PROJECT_DIR"
  else
    echo "[$(date '+%H:%M:%S')] WARNING: GitHub Pages HTML generation failed"
  fi

  echo "[$(date '+%H:%M:%S')] Daily pipeline COMPLETE"

} >> "$LOG" 2>&1
