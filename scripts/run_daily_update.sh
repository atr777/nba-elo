#!/bin/bash
# NBA_ELO Daily Pipeline — Linux/VPS version
# Scheduled via cron at 7AM, 11AM, 2PM, 6PM, 11PM ET
# Logs to: /opt/nba-elo/nba-elo-engine/logs/daily_update.log

export PATH="/opt/nba-elo/venv/bin:$PATH"
set -e

PROJECT_DIR="/opt/nba-elo/nba-elo-engine"
PYTHON="/opt/nba-elo/venv/bin/python"
LOG="$PROJECT_DIR/logs/daily_update.log"

mkdir -p "$PROJECT_DIR/logs"
cd "$PROJECT_DIR" || exit 1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === Pipeline starting ===" >> "$LOG"

# Pull latest code from GitHub. --autostash because the VPS accumulates local churn
# (regenerated CSVs) that would otherwise block the pull.
git pull --autostash origin master >> "$LOG" 2>&1 || echo "[WARN] git pull failed" >> "$LOG"

# Step 1: Full daily update (fetch games + recalculate ELO)
$PYTHON scripts/daily_update.py >> "$LOG" 2>&1

# THIS FILE IS THE PIPELINE. cron calls /opt/nba-elo/run_daily_update.sh, which as
# of 2026-07-29 is a two-line wrapper that execs this script, so there is one
# definition again. Before that it was a full second copy that had silently drifted
# (it had `set -e` and `--autostash`, both now folded in above), and that drift is
# why a deploy change made here would not have shipped. Note the one-run lag: this
# file is read before the git pull below, so an edit to THIS script takes effect on
# the following run.

# Step 2: Social card, before the HTML that references it. Reads the honest log, so
# the shared image can never show a number the record does not support.
#
# NON-FATAL ON PURPOSE. This is the least important artifact in the pipeline and it
# has the most fragile dependency (Pillow, plus Windows font paths that do not exist
# here). On 2026-07-29 a missing PIL took down the entire site update under set -e:
# a link preview image stopped the predictions from publishing. The site keeps its
# previous card and carries on.
$PYTHON scripts/generate_og_card.py >> "$LOG" 2>&1 \
  || echo "[WARN] og card generation failed, keeping the previous one" >> "$LOG"

# Step 3: Generate GitHub Pages HTML (also writes pages/sitemap.xml)
$PYTHON scripts/export_github_pages.py >> "$LOG" 2>&1

# Step 4: Push to GitHub Pages
# `git reset --hard` wipes anything not committed here, so every file the site needs
# must be copied on EVERY run, not once by hand.
#
# Staging and the commit decision are deliberately SEPARATE statements. The old
# one-liner joined them with && ... ||, which meant a failed cp fell through to the
# || and tried to commit anyway. Under set -e that aborted the run before the
# "Pipeline complete" line, with the real cause buried mid-chain.
SITE_SRC="/opt/nba-elo/nba-elo-engine/pages"
cd /opt/nba-elo/pages

git fetch origin main >> "$LOG" 2>&1
git reset --hard origin/main >> "$LOG" 2>&1

mkdir -p assets
cp "$SITE_SRC/index.html" .
cp "$SITE_SRC/robots.txt" .
cp "$SITE_SRC/sitemap.xml" .
git add index.html robots.txt sitemap.xml

# The card is optional (step 2 is allowed to fail), so its copy must be too, or a
# skipped card would abort the deploy under set -e and take the site with it. If it
# was not regenerated this run, whatever is already committed stays live.
if [ -f "$SITE_SRC/assets/og_card.png" ]; then
  cp "$SITE_SRC/assets/og_card.png" assets/
  git add assets/og_card.png
fi

# Only sitemap's <lastmod> and the page's timestamp change on a quiet day, so this
# still commits most runs. That is fine and intended: the site says when it last ran.
if git diff --cached --quiet; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] site unchanged, nothing to push" >> "$LOG"
else
  git commit -m "Predictions $(date '+%a %m/%d/%Y')" >> "$LOG" 2>&1
  git push origin main >> "$LOG" 2>&1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === Pipeline complete ===" >> "$LOG"
