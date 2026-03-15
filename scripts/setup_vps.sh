#!/bin/bash
# =============================================================================
# Second Bounce — VPS Bootstrap Script
# Hostinger Ubuntu 24.04 LTS
#
# HOW TO USE:
#   Open Hostinger → VPS → Terminal (the web terminal button)
#   Paste this entire script and press Enter.
#   That's it. Follow the one prompt about a GitHub key.
#
# WHAT THIS DOES:
#   1. Removes clawdbot if found
#   2. Installs Python 3.12 and system dependencies
#   3. Clones the nba-elo repo from GitHub
#   4. Sets up Python virtual environment + all pip dependencies
#   5. Creates the SSH deploy key for GitHub Pages pushes
#   6. Prompts you to add the key to GitHub (one copy-paste to a web page)
#   7. Sets up the pages repo
#   8. Sets timezone to Eastern Time
#   9. Registers 5 cron jobs (7AM, 11AM, 2PM, 6PM, 11PM ET)
#   10. Sets up log rotation
#   11. Runs the pipeline once to confirm everything works
#   12. Prints what to do next (data transfer from Windows)
# =============================================================================

set -e  # Exit on any unexpected error

REPO_URL="https://github.com/atr777/nba-elo.git"
INSTALL_DIR="/opt/nba-elo"
PROJECT_DIR="$INSTALL_DIR/nba-elo-engine"
VENV_DIR="$INSTALL_DIR/venv"
PAGES_DIR="$PROJECT_DIR/pages"
LOG_DIR="$PROJECT_DIR/logs"
PIPELINE_SCRIPT="$PROJECT_DIR/scripts/run_daily_update.sh"
PAGES_REMOTE="git@github-pages:atr777/nba-predictions.git"
SSH_KEY_FILE="$HOME/.ssh/nba_pages_deploy"

# Colors for readable output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log()  { echo -e "${GREEN}[SETUP]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; }
info() { echo -e "${BLUE}[INFO]${NC}  $1"; }

echo ""
echo "============================================================"
echo "  Second Bounce — VPS Setup"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================================"
echo ""

# =============================================================================
# STEP 1: Remove clawdbot if present
# =============================================================================
log "Step 1/11: Checking for clawdbot..."

CLAWDBOT_FOUND=false

# Check systemd service
if systemctl list-units --all 2>/dev/null | grep -qi claw; then
  warn "Found clawdbot systemd service — stopping and removing..."
  systemctl stop clawdbot 2>/dev/null || true
  systemctl disable clawdbot 2>/dev/null || true
  rm -f /etc/systemd/system/clawdbot* /etc/systemd/system/clawdbot.service 2>/dev/null || true
  systemctl daemon-reload 2>/dev/null || true
  CLAWDBOT_FOUND=true
fi

# Check crontab
if crontab -l 2>/dev/null | grep -qi claw; then
  warn "Found clawdbot in crontab — removing..."
  crontab -l 2>/dev/null | grep -iv claw | crontab - 2>/dev/null || true
  CLAWDBOT_FOUND=true
fi

# Check common install directories
for dir in /opt/clawdbot /opt/claude-bot /root/clawdbot /home/clawdbot; do
  if [ -d "$dir" ]; then
    warn "Found clawdbot directory at $dir — removing..."
    rm -rf "$dir"
    CLAWDBOT_FOUND=true
  fi
done

# Check processes
if pgrep -f clawdbot > /dev/null 2>&1; then
  warn "Found running clawdbot process — killing..."
  pkill -f clawdbot 2>/dev/null || true
  CLAWDBOT_FOUND=true
fi

if [ "$CLAWDBOT_FOUND" = true ]; then
  log "Clawdbot removed."
else
  log "No clawdbot found — clean slate."
fi

# =============================================================================
# STEP 2: System packages
# =============================================================================
log "Step 2/11: Installing system packages..."

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3.12 python3.12-venv python3-pip git rsync curl 2>&1 | tail -3

# Confirm python
PYTHON_VERSION=$(python3.12 --version 2>&1)
log "Python: $PYTHON_VERSION"

# =============================================================================
# STEP 3: Clone the repo
# =============================================================================
log "Step 3/11: Cloning nba-elo repo..."

mkdir -p "$INSTALL_DIR"

if [ -d "$PROJECT_DIR/.git" ]; then
  warn "Repo already exists at $PROJECT_DIR — pulling latest..."
  cd "$PROJECT_DIR"
  git pull origin master 2>&1 || warn "git pull failed — continuing with existing code"
else
  git clone "$REPO_URL" "$PROJECT_DIR" 2>&1
  log "Repo cloned to $PROJECT_DIR"
fi

cd "$PROJECT_DIR"

# =============================================================================
# STEP 4: Python virtual environment + dependencies
# =============================================================================
log "Step 4/11: Creating Python virtual environment..."

python3.12 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

log "Installing pip dependencies (this takes ~60 seconds)..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Confirm key imports work
python3 -c "import pandas, numpy, requests, yaml, nba_api; print('All core imports OK')" \
  && log "Import check passed." \
  || { err "Import check failed — check requirements.txt"; exit 1; }

# =============================================================================
# STEP 5: Create directories
# =============================================================================
log "Step 5/11: Creating log and data directories..."

mkdir -p "$LOG_DIR"
mkdir -p "$PROJECT_DIR/data/raw"
mkdir -p "$PROJECT_DIR/data/exports"
mkdir -p "$PAGES_DIR"

touch "$LOG_DIR/daily_update.log"
log "Directories ready."

# =============================================================================
# STEP 6: SSH deploy key for GitHub Pages
# =============================================================================
log "Step 6/11: Generating SSH deploy key for GitHub Pages..."

mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

if [ ! -f "$SSH_KEY_FILE" ]; then
  ssh-keygen -t ed25519 -C "nba-elo-vps" -f "$SSH_KEY_FILE" -N "" -q
  log "SSH key generated at $SSH_KEY_FILE"
else
  warn "SSH key already exists at $SSH_KEY_FILE — reusing it."
fi

# Add GitHub to known_hosts to avoid interactive prompt during push
ssh-keyscan github.com >> "$HOME/.ssh/known_hosts" 2>/dev/null

# Create SSH config for the deploy key alias
SSH_CONFIG="$HOME/.ssh/config"
if ! grep -q "Host github-pages" "$SSH_CONFIG" 2>/dev/null; then
  cat >> "$SSH_CONFIG" << EOF

Host github-pages
    HostName github.com
    User git
    IdentityFile $SSH_KEY_FILE
EOF
  chmod 600 "$SSH_CONFIG"
fi

# =============================================================================
# STEP 6b: Prompt to add key to GitHub — THE ONE MANUAL STEP
# =============================================================================
echo ""
echo "============================================================"
echo -e "  ${YELLOW}ACTION REQUIRED — One copy-paste to GitHub${NC}"
echo "============================================================"
echo ""
echo "  Copy the key below:"
echo ""
cat "${SSH_KEY_FILE}.pub"
echo ""
echo "  Then:"
echo "  1. Open this URL in your browser:"
echo "     https://github.com/atr777/nba-predictions/settings/keys"
echo "  2. Click 'Add deploy key'"
echo "  3. Title: nba-elo-vps"
echo "  4. Paste the key above"
echo "  5. Check 'Allow write access'"
echo "  6. Click 'Add key'"
echo ""
read -p "  Press Enter when you've added the key to GitHub... "
echo ""

# Test the key
log "Testing GitHub connection..."
ssh -o StrictHostKeyChecking=no -T git@github-pages 2>&1 | grep -q "successfully authenticated" \
  && log "GitHub SSH key verified." \
  || warn "Could not verify SSH key — will retry during pipeline run."

# =============================================================================
# STEP 7: Set up pages repo
# =============================================================================
log "Step 7/11: Setting up GitHub Pages repo..."

cd "$PAGES_DIR"

if [ ! -d ".git" ]; then
  git init -q
  git remote add origin "$PAGES_REMOTE"
  git config user.email "nba-elo-vps@noreply"
  git config user.name "NBA ELO VPS"

  # Create a placeholder index.html so we can do the initial push
  if [ ! -f "index.html" ]; then
    echo "<!-- placeholder -->" > index.html
    cp "$PROJECT_DIR/pages/logo.png" . 2>/dev/null || true
  fi

  git add .
  git commit -m "VPS initial setup" -q
  git push -u origin main 2>&1 \
    && log "Pages repo connected to GitHub." \
    || warn "Initial pages push failed — will work after data transfer."
else
  warn "Pages repo already initialized — skipping."
fi

cd "$PROJECT_DIR"

# =============================================================================
# STEP 8: Timezone
# =============================================================================
log "Step 8/11: Setting timezone to America/New_York (Eastern Time)..."
timedatectl set-timezone America/New_York
log "Timezone: $(timedatectl | grep 'Time zone')"

# =============================================================================
# STEP 9: Cron jobs (5x/day)
# =============================================================================
log "Step 9/11: Installing cron jobs (5x/day at ET times)..."

# Make pipeline script executable
chmod +x "$PIPELINE_SCRIPT"

# Confirm cron daemon is running
systemctl enable cron 2>/dev/null || systemctl enable crond 2>/dev/null || true
systemctl start cron 2>/dev/null || systemctl start crond 2>/dev/null || true

# Remove any old NBA_ELO cron entries, then add fresh ones
(crontab -l 2>/dev/null | grep -v "run_daily_update"; cat << EOF
# Second Bounce — NBA_ELO Pipeline (5x/day, America/New_York timezone)
0  7  * * *  $PIPELINE_SCRIPT
0 11  * * *  $PIPELINE_SCRIPT
0 14  * * *  $PIPELINE_SCRIPT
0 18  * * *  $PIPELINE_SCRIPT
0 23  * * *  $PIPELINE_SCRIPT
EOF
) | crontab -

log "Cron jobs registered:"
crontab -l | grep "run_daily_update"

# =============================================================================
# STEP 10: Log rotation
# =============================================================================
log "Step 10/11: Setting up log rotation..."

cat > /etc/logrotate.d/nba-elo << EOF
$LOG_DIR/daily_update.log {
    weekly
    rotate 8
    compress
    missingok
    notifempty
}
EOF
log "Log rotation configured (weekly, 8 weeks retained)."

# =============================================================================
# STEP 11: First pipeline run
# =============================================================================
log "Step 11/11: Running pipeline for the first time..."
info "(This will likely show 'data not found' until you transfer data from Windows)"
info "That's OK — it confirms Python and cron are working."

bash "$PIPELINE_SCRIPT" && log "Pipeline ran." || warn "Pipeline run had errors (expected before data transfer)."

# =============================================================================
# DONE — Print next steps
# =============================================================================
echo ""
echo "============================================================"
echo -e "  ${GREEN}VPS SETUP COMPLETE${NC}"
echo "============================================================"
echo ""
echo "  The VPS is now configured. One step remains:"
echo "  Transfer your data files from Windows to the VPS."
echo ""
echo "  Open Git Bash on your Windows PC and run these commands:"
echo ""
echo -e "  ${YELLOW}VPSROOT=\"root@$(curl -s ifconfig.me 2>/dev/null || echo '76.13.124.2'):/opt/nba-elo/nba-elo-engine\"${NC}"
echo ""
echo -e "  ${YELLOW}rsync -avz --progress \\${NC}"
echo -e "  ${YELLOW}  \"/c/Users/Aaron/Desktop/NBA_ELO/nba-elo-engine/data/raw/nba_games_all.csv\" \\${NC}"
echo -e "  ${YELLOW}  \"\$VPSROOT/data/raw/\"${NC}"
echo ""
echo -e "  ${YELLOW}rsync -avz --progress \\${NC}"
echo -e "  ${YELLOW}  \"/c/Users/Aaron/Desktop/NBA_ELO/nba-elo-engine/data/raw/player_boxscores_all.csv\" \\${NC}"
echo -e "  ${YELLOW}  \"\$VPSROOT/data/raw/\"${NC}"
echo ""
echo -e "  ${YELLOW}rsync -avz --progress \\${NC}"
echo -e "  ${YELLOW}  \"/c/Users/Aaron/Desktop/NBA_ELO/nba-elo-engine/data/exports/\" \\${NC}"
echo -e "  ${YELLOW}  \"\$VPSROOT/data/exports/\"${NC}"
echo ""
echo "  After the transfer (~275MB, ~5-10 min), the next cron run"
echo "  will update the live site automatically."
echo ""
echo "  Making future code changes:"
echo "  → Edit in Claude Code on your PC as normal"
echo "  → Push to GitHub"
echo "  → VPS auto-pulls on the next scheduled run (within a few hours)"
echo "  → You never need to open this terminal again"
echo ""
echo "  Log file:  $LOG_DIR/daily_update.log"
echo "  Cron runs: 7AM, 11AM, 2PM, 6PM, 11PM ET"
echo ""
echo "  ⚠️  REMINDER: Renew your VPS at hostinger.com before April 3, 2026"
echo ""
echo "============================================================"
