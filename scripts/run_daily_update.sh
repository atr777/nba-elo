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

# WARNING: THIS FILE IS NOT WHAT CRON RUNS. cron calls
# /opt/nba-elo/run_daily_update.sh, a separate copy that lives outside the repo and
# had already drifted from this one (it carries `set -e` and `git pull --autostash`).
# Change both, or the change does not ship. Noted 2026-07-29.

# Step 2: Social card, before the HTML that references it. Reads the honest log, so
# the shared image can never show a number the record does not support.
$PYTHON scripts/generate_og_card.py >> "$LOG" 2>&1

# Step 3: Generate GitHub Pages HTML (also writes pages/sitemap.xml)
$PYTHON scripts/export_github_pages.py >> "$LOG" 2>&1

# Step 4: Push to GitHub Pages
# `git reset --hard` wipes anything not committed here, so every file the site needs
# must be copied on EVERY run, not once by hand.
cd /opt/nba-elo/pages \
  && git fetch origin main >> "$LOG" 2>&1 \
  && git reset --hard origin/main >> "$LOG" 2>&1 \
  && cp /opt/nba-elo/nba-elo-engine/pages/index.html . \
  && cp /opt/nba-elo/nba-elo-engine/pages/robots.txt . \
  && cp /opt/nba-elo/nba-elo-engine/pages/sitemap.xml . \
  && mkdir -p assets \
  && cp /opt/nba-elo/nba-elo-engine/pages/assets/og_card.png assets/ \
  && git add index.html robots.txt sitemap.xml assets/og_card.png \
  && git diff --cached --quiet \
  || (git commit -m "Predictions $(date '+%a %m/%d/%Y')" && git push origin main) >> "$LOG" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === Pipeline complete ===" >> "$LOG"
