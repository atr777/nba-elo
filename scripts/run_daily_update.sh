#!/bin/bash
# NBA_ELO Daily Pipeline — Linux/VPS version
# Scheduled via cron at 7AM, 11AM, 2PM, 6PM, 11PM ET
# Logs to: /opt/nba-elo/nba-elo-engine/logs/daily_update.log

export PATH="/opt/nba-elo/venv/bin:$PATH"

PROJECT_DIR="/opt/nba-elo/nba-elo-engine"
PYTHON="/opt/nba-elo/venv/bin/python"
LOG="$PROJECT_DIR/logs/daily_update.log"

mkdir -p "$PROJECT_DIR/logs"
cd "$PROJECT_DIR" || exit 1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === Pipeline starting ===" >> "$LOG"

# Pull latest code from GitHub
git pull origin master >> "$LOG" 2>&1 || echo "[WARN] git pull failed" >> "$LOG"

# Step 1: Full daily update (fetch games + recalculate ELO)
$PYTHON scripts/daily_update.py >> "$LOG" 2>&1

# Step 2: Generate GitHub Pages HTML
$PYTHON scripts/export_github_pages.py >> "$LOG" 2>&1

# Step 3: Push to GitHub Pages
cd /opt/nba-elo/pages \
  && git fetch origin main >> "$LOG" 2>&1 \
  && git reset --hard origin/main >> "$LOG" 2>&1 \
  && cp /opt/nba-elo/nba-elo-engine/pages/index.html . \
  && git add index.html \
  && git diff --cached --quiet \
  || (git commit -m "Predictions $(date '+%a %m/%d/%Y')" && git push origin main) >> "$LOG" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === Pipeline complete ===" >> "$LOG"
