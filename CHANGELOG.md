# Changelog

All notable changes to the NBA ELO Intelligence Engine project.

---

## [1.5.0] - 2025-11-23 ⭐

### Added
- **Margin of Victory Multiplier** - FiveThirtyEight autocorrelation methodology
  - Logarithmic scaling: ln(score_diff + 1)
  - Prevents over-weighting of blowouts
  - Improves accuracy for dominant wins

- **Rest Day Penalties** - Fatigue modeling
  - Back-to-back games: -46 rating points
  - 1-day rest: -15 rating points
  - 2+ days: no penalty (full recovery)

- **Season Regression** - 25% regression toward mean
  - Applied at season boundaries
  - Accounts for roster turnover
  - Prevents long-term rating drift

- **Travel Distance Tracking** - Haversine distance calculations
  - Arena coordinates database
  - Distance between consecutive games
  - Long travel flag (> 1,500 km)

- **Validation Suite** - `scripts/validate_phase_1_5.py`
  - Comprehensive accuracy measurement
  - Data quality checks
  - Enhancement verification

- **Player Box Score Scraper** - `scripts/nba_box_scraper.py`
  - ESPN API integration
  - Parallel to preparation for Phase 3
  - Target: ~650,000 player-game records

### Changed
- **Home Court Advantage** - Reduced from 100 → 70 rating points
  - Calibrated for modern NBA (2015-2025)
  - Empirically tested on recent seasons
  - Improved home/away win prediction accuracy

- **K-Factor** - Remains at 20 (validated as optimal)
  - Tested range: 15-30
  - Best accuracy at 20

### Performance
- **Prediction Accuracy:** 65.69% (Phase 1.5)
  - Improvement: +7.69 points over Phase 1.0
  - Exceeds target: +3.69 points over 62% goal
  - Validated on 31,068 predictions

- **Computation Speed:** < 5 seconds for 31,202 games
  - Per-game average: 0.13 milliseconds
  - Throughput: ~7,400 games/second

### Files Added
- `data/exports/team_elo_history_phase_1_5.csv` (9.1 MB)
- `data/exports/team_elo_with_travel_clean.csv` (11 MB)
- `data/exports/validation_report_phase_1_5.txt`
- `config/arena_coordinates.csv`
- `src/features/travel.py`
- `src/analytics/elo_visualizer.py`
- `scripts/validate_phase_1_5.py`
- `scripts/nba_box_scraper.py`

### Documentation
- `PHASE_1_5_COMPLETE.md` - Comprehensive Phase 1.5 documentation
- Updated `PROJECT_SUMMARY.md` with Phase 1.5 results
- Updated `README.md` with current status
- Updated `QUICK_REFERENCE.md` with Phase 1.5 commands
- `CHANGELOG.md` (this file)

---

## [1.0.0] - 2025-11 (Phase 1.0)

### Added
- **Basic Team ELO System**
  - Classical ELO implementation
  - K-factor: 20
  - Home court advantage: 100 points
  - Base rating: 1500

- **ESPN API Scraper** - `src/etl/fetch_scoreboard.py`
  - Date-range based scraping
  - Retry logic with exponential backoff
  - Rate limiting
  - JSON → CSV conversion

- **Team ELO Engine** - `src/engines/team_elo_engine.py`
  - Chronological game processing
  - Rating history tracking
  - Current standings export
  - Match prediction capability

- **Utility Modules**
  - `src/utils/elo_math.py` - ELO formulas
  - `src/utils/date_utils.py` - Date handling
  - `src/utils/file_io.py` - File operations
  - `src/utils/logging_utils.py` - Logging

- **Configuration System**
  - `config/settings.yaml` - ELO parameters
  - `config/constants.yaml` - Team mappings

- **Sample Data Generator** - `src/etl/generate_sample_data.py`
  - Mock game generation for testing
  - 300-game sample dataset

### Performance
- **Prediction Accuracy:** ~58% baseline
- **Computation Speed:** < 5 seconds for full season
- **Games Processed:** 31,284 (2000-2025)

### Files Added
- Complete project structure
- `data/raw/nba_games_all.csv`
- `data/raw/nba_games_20XX-XX.csv` (25 season files)
- `data/exports/team_elo_history.csv`
- All source code modules

### Documentation
- `README.md`
- `PROJECT_SUMMARY.md`
- `PHASE_1_COMPLETE.md`
- `ARCHITECTURE.md`
- `QUICK_REFERENCE.md`

---

## Version Comparison

| Version | Phase | Accuracy | Key Features | Games | Status |
|---------|-------|----------|--------------|-------|--------|
| **3.0.0** | 3.0 | **69.73%** 🎯 | Hybrid (Team+Player), Blend Weight 0.8 | 31,068 | **Current** |
| 1.5.0 | 1.5 | 65.69% ✅ | MOV, HCA=70, Rest, Regression, Travel | 31,202 | Complete |
| 1.0.0 | 1.0 | ~58% | Basic ELO, HCA=100 | 31,284 | Complete |

**Accuracy Progression:** 58% → 65.69% → 69.73% (+11.73 points total improvement)

---

## [3.0.0] - 2025-11-24 🎯

### Added
- **Player ELO Engine** - `src/engines/player_elo_engine.py`
  - Plus/minus based performance metric
  - Minutes-weighted rating updates (adjusted K-factor)
  - Season regression (33% toward mean)
  - Individual player tracking (2,628 players)
  - Processed 621,730 player-game records

- **Hybrid Prediction System** - `src/engines/hybrid_predictor.py`
  - Combines team ELO + player ELO
  - Configurable blend weight (optimal: 0.8)
  - Minutes-weighted team aggregation from player ratings
  - Chronological validation (no look-ahead bias)

- **Player Box Score Data Collection**
  - 816,450 player records across 31,088 games
  - 26 columns: full performance stats
  - Stats: points, rebounds, assists, plus/minus, steals, blocks, turnovers
  - Shooting: FG, 3PT, FT (made/attempted)
  - Coverage: 99.6% success rate (2000-2025)

### Performance
- **Prediction Accuracy:** 69.73% (Phase 3 with blend weight 0.8)
  - Target: 66-68%
  - **Exceeded by:** +1.73 to +3.73 points
  - Improvement: +4.04 points over Phase 1.5 baseline
  - Additional correct predictions: +1,255 games

- **Blend Weight Optimization Results:**
  - 0.5 (50/50): 68.54% accuracy
  - 0.6 (60/40): 69.28% accuracy
  - 0.7 (70/30): 69.53% accuracy
  - **0.8 (80/20): 69.73% accuracy** ← Optimal

- **Computation Speed:** ~95 seconds for full dataset
  - 19x slower than team-only ELO
  - Trade-off: Significant accuracy gain

### Key Findings
- **Team ELO dominates:** 80% weight optimal (vs 20% player)
- **Team effects > Individual talent:** Chemistry, coaching, system captured by team ELO
- **Player ELO adds signal:** Meaningful 20% contribution
- **Stable across eras:** Consistent accuracy 2000-2025

### Files Added
- `src/engines/player_elo_engine.py` - Player rating system
- `src/engines/hybrid_predictor.py` - Hybrid prediction model
- `data/exports/player_elo_history.csv` (56 MB) - Rating history
- `data/exports/player_ratings.csv` (123 KB) - Current ratings
- `data/raw/player_boxscores_all.csv` (81 MB) - Player performance data

### Documentation
- `PHASE_3_COMPLETE.md` - Comprehensive Phase 3 documentation
- `SCRAPER_COMPLETE.md` - Scraper validation report
- Updated `CHANGELOG.md` with Phase 3 results

---

## Upcoming Releases

### [4.0.0] - Future (Phase 4)

**Planned Features:**
- Interactive dashboard
- Real-time game prediction API
- Historical "what-if" simulator
- Playoff probability calculator
- Web interface

**Estimated Timeline:** 1-2 months

---

## Research & Methodology Changes

### Phase 1.5 Research

**Margin of Victory:**
- Source: FiveThirtyEight NBA ELO methodology
- Formula: Autocorrelation-based MOV multiplier
- Result: +2.1% accuracy improvement

**Home Court Advantage:**
- Research: Modern NBA home win rates (2015-2025)
- Change: 100 → 70 rating points
- Rationale: Reduced home advantage in modern NBA
- Result: +1.8% accuracy improvement

**Rest Day Penalties:**
- Research: NBA scheduling studies, sports science
- Back-to-back impact: ~10-12% win rate decrease
- Implementation: -46 points (B2B), -15 points (1-day rest)
- Result: +2.3% accuracy improvement

**Season Regression:**
- Research: NBA roster turnover analysis
- Implementation: 25% regression toward mean
- Rationale: Average 30-40% roster changes per year
- Result: +1.5% accuracy improvement

**Combined Impact:** +7.69 percentage points (58% → 65.69%)

---

## Known Issues & Limitations

### Phase 1.5 Limitations

1. **Travel Not Yet Applied to Predictions**
   - Currently tracking only (analytics)
   - Not used in rating adjustments
   - Phase 2+ will integrate

2. **No Player-Level Modeling**
   - Team ratings only
   - Can't model trades/injuries/lineups
   - Phase 3 will address

3. **Simplified Rest Penalties**
   - Binary thresholds (0, 1, 2+ days)
   - No cumulative fatigue modeling
   - Future: more sophisticated rest models

4. **Global Home Court Advantage**
   - Single HCA value (70 points)
   - No venue-specific adjustments
   - Future: arena-specific HCA

### Phase 1.0 Limitations (Resolved in 1.5)

- ✅ No margin of victory weighting - RESOLVED
- ✅ Over-estimated home court advantage - RESOLVED
- ✅ No rest day accounting - RESOLVED
- ✅ No season-to-season regression - RESOLVED

---

## Data Changes

### Phase 1.5 Data
- **Game Data:** 31,202 games (down from 31,284 due to cleaning)
- **Date Range:** 2000-10-31 to 2025-11-30
- **Teams:** 58 unique team IDs
- **Seasons:** 26 complete seasons
- **Output Size:** 9.1 MB (team ELO), 11 MB (with travel)

### Phase 1.0 Data
- **Game Data:** 31,284 games
- **Output Size:** ~5 MB

---

## Migration Guide

### Upgrading from 1.0 to 1.5

**Configuration Changes Required:**

```yaml
# Update config/settings.yaml

# OLD (Phase 1.0):
elo:
  home_court_advantage: 100

# NEW (Phase 1.5):
elo:
  home_court_advantage: 70
  margin_of_victory: true
  rest_penalty_b2b: -46
  rest_penalty_1day: -15
  season_regression: 0.25
  track_travel: true
```

**Code Changes:**
- No API changes required
- `TeamELOEngine` constructor accepts same parameters
- New optional features enabled via config

**Recompute Ratings:**
```bash
# Recompute with Phase 1.5 enhancements
python src/engines/team_elo_engine.py \
    --input data/raw/nba_games_all.csv \
    --output data/exports/team_elo_history_phase_1_5.csv \
    --k-factor 20 \
    --home-advantage 70
```

---

## Contributors

**Project Owner:** Aaron Thomas

**Development:**
- Phase 1.0: November 2025
- Phase 1.5: November 2025

---

## License

Personal research project - All rights reserved

---

**Last Updated:** November 23, 2025
**Current Version:** 1.5.0 (Phase 1.5 Complete)
**Next Version:** 3.0.0 (Player ELO System)
