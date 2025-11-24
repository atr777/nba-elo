# Data Filtering - Scheduled vs Completed Games

## Overview

The NBA ELO system automatically handles scheduled games (future games with 0-0 scores) to ensure accurate calculations while maintaining scheduling information.

## How It Works

### Raw Data Storage
**Location:** `data/raw/nba_games_all.csv`

**Contains:**
- ✓ All completed games with actual scores
- ✓ Scheduled future games (0-0 scores)
- ✓ Historical scheduled games that were never played

**Why keep scheduled games?**
- Useful for scheduling reference
- Can predict upcoming matchups
- Historical record of what was scheduled

### ELO Calculations
**Automatic filtering applied in:**
- `src/engines/team_elo_engine.py` (Team ELO computation)
- `scripts/validate_phase_1_5.py` (Validation)

**Filter logic:**
```python
# Only process games with actual scores
completed_games = games_df[
    (games_df['home_score'].astype(int) > 0) |
    (games_df['away_score'].astype(int) > 0)
]
```

**Result:** Scheduled games (0-0) are automatically excluded from:
- ELO rating calculations
- Accuracy validation
- Prediction metrics
- Statistical analysis

## Current Data Status

Run anytime to check:
```bash
python scripts/check_data_status.py
```

**Example output:**
```
TOTAL GAMES IN FILE: 31,202
  [OK] Completed games:  31,068
  [..] Scheduled games:  134

LATEST COMPLETED GAME:
  Date: 2025-11-22
  LA Clippers @ Charlotte Hornets
  Score: 131-116
  Status: [OK] CURRENT (1 day behind)
```

## Why Some Scheduled Games are Old

You may see scheduled games from past dates that were never played:
- Postponed games
- Cancelled games (COVID-19, etc.)
- Exhibition games
- Games that were rescheduled

These don't affect ELO calculations and can be safely ignored.

## Update Workflow

**When scraping new data:**
1. ESPN API returns both completed AND scheduled games
2. Scraper saves everything to raw data (intentional)
3. ELO engine automatically filters out 0-0 games
4. No manual cleanup needed ✓

**Best practice:**
- Scrape data when no games are currently in progress
- Wait until all games for the day are final
- Run updates in the morning (after all games finished)

## Manual Cleanup (Optional)

If you want to remove old scheduled games from raw data:

```bash
python scripts/clean_scheduled_games.py
```

**This script would:**
- Keep completed games (non-zero scores)
- Keep future scheduled games (today onwards)
- Remove old scheduled games (past dates, 0-0 scores)

**Note:** This is optional - the automatic filtering handles everything.

## Technical Details

### Filter Implementation

**Team ELO Engine** (`src/engines/team_elo_engine.py`):
```python
def compute_season_elo(self, games_df: pd.DataFrame, reset: bool = True):
    # Filter out scheduled/incomplete games (0-0 scores)
    original_count = len(games_df)
    games_df = games_df[
        (games_df['home_score'].astype(int) > 0) |
        (games_df['away_score'].astype(int) > 0)
    ].copy()

    filtered_count = original_count - len(games_df)
    if filtered_count > 0:
        logger.info(f"Filtered out {filtered_count} scheduled/incomplete games")
```

**Validation Script** (`scripts/validate_phase_1_5.py`):
```python
def validate_data_quality(self):
    # Filter out scheduled/incomplete games
    original_count = len(self.data)
    self.data = self.data[
        (self.data['home_score'].astype(int) > 0) |
        (self.data['away_score'].astype(int) > 0)
    ].copy()

    scheduled_games = original_count - len(self.data)
    if scheduled_games > 0:
        logger.info(f"Filtered out {scheduled_games} scheduled games")
```

### Edge Cases Handled

1. **Games in progress:** Score might be non-zero but game incomplete
   - Solution: Only scrape when all games are final

2. **Forfeits/technical wins:** Might have unusual scores
   - Solution: Any non-zero score counts as completed

3. **Exhibition games:** Some have 0-0 placeholder scores
   - Solution: Filtered out automatically

## Validation

After any update, verify filtering is working:

```bash
# Run validation
python scripts/validate_phase_1_5.py

# Check data status
python scripts/check_data_status.py

# Should show:
#   - Completed games count
#   - Scheduled games count (filtered)
#   - No errors about 0-0 scores
```

## Summary

✓ **Scheduled games** kept in raw data for reference
✓ **Automatic filtering** in all ELO calculations
✓ **No manual cleanup** required
✓ **Check anytime** with `check_data_status.py`

**Bottom line:** The system is designed to handle this automatically. You don't need to worry about scheduled games affecting your ELO calculations! 🎯
