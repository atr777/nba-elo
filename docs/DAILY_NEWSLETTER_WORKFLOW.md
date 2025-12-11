# Daily Newsletter Workflow
**Complete guide for generating daily NBA ELO predictions newsletters**

## Overview
This workflow allows you to generate professional newsletters with predictions, recent form analysis, injury impacts, and yesterday's results - all with just a few clicks.

---

## Method 1: Using the Admin Web App (RECOMMENDED)

### Prerequisites
- Flask app running: `python app.py`
- Browser open at: `http://localhost:5000`

### Steps
1. **Navigate to Newsletter Generator**
   - Click "Newsletter" in the navigation menu

2. **Select Date**
   - **Today's Newsletter**: Click "Generate for Today"
   - **Tomorrow's Newsletter**: Click "Generate for Tomorrow"
   - **Custom Date**: Select date from calendar picker

3. **Review Preview**
   - Newsletter preview loads automatically
   - Shows:
     - Today's game predictions
     - Yesterday's results with accuracy
     - Team recent form (last 10 games)
     - Injury impact analysis
     - Full game breakdown

4. **Download or Copy**
   - Click "Download MD" to save file
   - OR Click "Copy to Clipboard" for Substack
   - Newsletter saved to: `newsletters/newsletter_YYYY-MM-DD.md`

5. **Paste into Substack**
   - Open Substack editor
   - Paste markdown content
   - Publish!

**Total Time**: ~30 seconds per newsletter

---

## Method 2: Command Line (Manual)

### Today's Newsletter
```bash
cd nba-elo-engine
python scripts/export_substack_daily.py --date $(date +%Y-%m-%d) --output newsletters/newsletter_$(date +%Y-%m-%d).md
```

### Tomorrow's Newsletter
```bash
cd nba-elo-engine
python scripts/export_substack_daily.py --date $(date -d "+1 day" +%Y-%m-%d) --output newsletters/newsletter_$(date -d "+1 day" +%Y-%m-%d).md
```

### Custom Date
```bash
python scripts/export_substack_daily.py --date 2025-11-26 --output newsletters/newsletter_2025-11-26.md
```

**Parameters**:
- `--date`: Target date in YYYY-MM-DD format
- `--output`: Output file path (creates if doesn't exist)
- `--featured-game`: Optional, e.g., "Lakers Warriors"

---

## What's Included in Each Newsletter

### 1. Header
- Date
- Number of games
- Model accuracy (65.69%)

### 2. Featured Game (Full Analysis)
- **Prediction**: Winner with probability
- **ELO Ratings**: Team ratings with home court advantage
- **Analysis**: Why the model favors this team
- **Recent Form**: Actual W-L record from last 10 games
- **Injury Impact**: Top 3 players per team with impact percentages

### 3. Other Games (Quick Picks)
- All remaining games with predictions
- ELO ratings
- Win probabilities

### 4. Yesterday's Results
- **Accuracy**: Correct predictions / Total games
- **Game Results**:
  - [OK] = Correct prediction
  - [X] = Incorrect prediction
  - [UPSET!] = Favorite lost
- **Scores**: Bold for winner
- **Comparison**: vs overall model accuracy

### 5. Premium Upsell
- Features list
- Pricing

---

## Daily Routine (Best Practice)

### Morning Routine (9:00 AM)
1. Open admin app
2. Generate today's newsletter
3. Review yesterday's results accuracy
4. Copy to Substack
5. Schedule/publish

### Evening Routine (7:00 PM)
1. Generate tomorrow's newsletter
2. Review tonight's games for tomorrow's context
3. Save for morning publish

**Total Daily Time**: ~2 minutes

---

## Automation Options

### Option A: Windows Task Scheduler
1. Create batch script: `generate_newsletters.bat`
2. Schedule for 8:00 AM daily
3. Auto-generates both today and tomorrow

### Option B: Cron Job (Linux/Mac)
```cron
0 8 * * * cd /path/to/nba-elo-engine && python scripts/export_substack_daily.py --date $(date +%Y-%m-%d) --output newsletters/newsletter_$(date +%Y-%m-%d).md
```

### Option C: GitHub Actions
- Auto-generates on schedule
- Commits to repo
- Sends notification

---

## Output Files

### Location
```
nba-elo-engine/
└── newsletters/
    ├── newsletter_2025-11-25.md
    ├── newsletter_2025-11-26.md
    └── newsletter_2025-11-27.md
```

### Format
- Markdown (.md)
- Ready for Substack paste
- UTF-8 encoded
- ~500-800 lines per newsletter

---

## Troubleshooting

### No games available
**Solution**: Check NBA schedule, might be off-day

### Yesterday's results unavailable
**Cause**: No games played yesterday
**Result**: Shows "*No games available for yesterday*"

### Import errors
**Solution**: Ensure you're in nba-elo-engine directory

### FileNotFoundError
**Solution**: Create newsletters directory:
```bash
mkdir -p newsletters
```

---

## Data Requirements

### Must Be Current
- `data/raw/nba_games_all.csv` - Updated through yesterday
- `data/exports/team_elo_history_phase_1_5.csv` - Latest team ratings
- `data/exports/player_ratings_bpm.csv` - Current player ratings
- `data/exports/player_team_mapping.csv` - Active rosters

### Update Process
Run before generating newsletters:
```bash
python scripts/daily_update.py
```

This ensures:
- Latest game results
- Updated ELO ratings
- Current rosters

---

## Example Workflow (Nov 25, 2025)

### Step-by-Step
1. **Update Data** (if needed)
   ```bash
   python scripts/daily_update.py
   ```

2. **Generate Today** (Nov 25)
   ```bash
   python scripts/export_substack_daily.py --date 2025-11-25 --output newsletters/newsletter_2025-11-25.md
   ```
   - Fetches 3 games for Nov 25
   - Shows Nov 24 results (10 games, 60% accuracy)

3. **Generate Tomorrow** (Nov 26)
   ```bash
   python scripts/export_substack_daily.py --date 2025-11-26 --output newsletters/newsletter_2025-11-26.md
   ```
   - Fetches 9 games for Nov 26
   - Shows Nov 25 results (when available)

4. **Review Files**
   ```bash
   ls newsletters/
   # newsletter_2025-11-25.md
   # newsletter_2025-11-26.md
   ```

5. **Publish**
   - Open `newsletter_2025-11-25.md`
   - Copy content
   - Paste into Substack
   - Hit publish!

**Total Time**: ~60 seconds

---

## Success Metrics

### Quality Checks
- ✅ All percentages single `%` (not `%%`)
- ✅ No betting references
- ✅ Real recent form data (not "Moderate momentum")
- ✅ Yesterday's results showing (when games exist)
- ✅ Injury impacts calculated
- ✅ All games included

### Accuracy Tracking
- Monitor daily accuracy in "Yesterday's Results"
- Compare to 65.69% overall model accuracy
- Track upsets and patterns

---

## Future Enhancements

### Planned Features
1. **Email Integration**: Auto-send newsletters
2. **Substack API**: Auto-publish without copy/paste
3. **Prediction CSV**: Growing database of all predictions
4. **Weekly Digest**: Summary of week's accuracy

### Wishlist
- Interactive newsletter with clickable predictions
- Real-time injury updates from NBA API
- Betting line comparisons (optional)
- Social media auto-posts

---

**Last Updated**: November 25, 2025
**Version**: 2.0 (Post-Improvements)
