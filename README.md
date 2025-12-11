# NBA ELO Intelligence Engine

**A production-ready NBA prediction system with automated daily newsletters and 69.73% accuracy**

[![Status](https://img.shields.io/badge/Production-Live-success)]() [![Accuracy](https://img.shields.io/badge/Accuracy-69.73%25-brightgreen)]() [![Games](https://img.shields.io/badge/Games-31%2C260-blue)]() [![Players](https://img.shields.io/badge/Players-2%2C628-blue)]()

---

## Overview

The NBA ELO Intelligence Engine is a **production system** that delivers daily NBA game predictions through automated newsletters. The system combines team-level and player-level ELO ratings in a hybrid predictor, incorporating contextual factors like rest/fatigue, momentum, recent form, and injury impact.

**Current Status:**
- **69.73% prediction accuracy** on 31,260 games (2000-2025)
- **Production deployment** with automated daily updates
- **Daily & premium newsletters** generated automatically
- **Real-time data integration** via NBA API and ESPN scrapers

---

## Features

### 📊 Production Newsletter System (LIVE ✅)
- ✅ **Daily Free Newsletter** - Game predictions with matchup breakdowns
- ✅ **Premium Newsletter** - Deep analysis with player insights and injury impact
- ✅ **Automated Generation** - Daily updates via scheduled scripts
- ✅ **Dynamic Visualizations** - Featured teams, momentum tracking, schedule previews
- ✅ **Alternating Content** - Head-to-head analysis (even days) / Pace & Style (odd days)
- ✅ **NBA CDN Integration** - Future game schedule fetching for advance predictions

### 🎯 Hybrid Prediction Engine (69.73% Accuracy ✅)
- ✅ **Team ELO System** - 65.69% accuracy with 6 contextual factors (MOV, HCA, rest, travel)
- ✅ **Player ELO System** - 2,628 players tracked with Box Plus/Minus integration
- ✅ **Hybrid Predictor** - 80% team / 20% player optimal blend (69.73% accuracy)
- ✅ **Close Game Enhancement** - Specialized handling for competitive matchups
- ✅ **Confidence Adjustment** - Dynamic probability caps based on game context
- ✅ **Form Factor** - Recent performance weighting (last 10 games)

### 🔄 Live Data Integration (PRODUCTION ✅)
- ✅ **NBA API Integration** - Real-time game data and player statistics
- ✅ **ESPN Scraper** - Team injury reports and roster updates
- ✅ **Automated Updates** - Daily data refresh with `daily_update.py`
- ✅ **Performance Tracking** - Prediction accuracy monitoring in CSV
- ✅ **Error Handling** - Robust API fallbacks (NBA CDN for schedule data)

### 📈 Analytics & Reporting (PRODUCTION ✅)
- ✅ **Prediction Tracking** - Automated logging of all predictions and outcomes
- ✅ **Performance Reports** - Weekly/monthly accuracy analysis
- ✅ **Matchup Analysis** - Head-to-head history and player comparisons
- ✅ **Game Summaries** - Post-game analysis with prediction validation
- ✅ **Newsletter Visualizations** - Day-specific featured content (7-day rotation)

---

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/atr777/nba-elo.git
cd nba-elo

# Install dependencies
pip install -r requirements.txt
```

### Generate Daily Newsletter

```bash
# Generate free daily newsletter for today
python scripts/export_substack_daily.py

# Generate premium newsletter for today
python scripts/export_substack_premium.py

# Generate for specific date (format: YYYY-MM-DD)
python scripts/export_substack_premium.py --date 2025-12-15
```

### Update Data & Run Predictions

```bash
# Quick daily update (fetches latest games and updates ratings)
python scripts/quick_update.py

# Full daily update (includes data validation)
python scripts/daily_update.py

# Update with new games and generate predictions
python scripts/update_with_new_games.py
```

### View Performance

```bash
# Generate accuracy report
python scripts/generate_accuracy_report.py

# Generate performance report with visualizations
python scripts/generate_performance_report.py

# View prediction tracking history
cat data/exports/prediction_tracking.csv
```

---

## Production Status

### ✅ PHASE 1-3: Core System (COMPLETE)
**Completion:** December 2025

**Achievements:**
- ✅ Team ELO Engine (65.69% accuracy)
- ✅ Player ELO Engine (2,628 players tracked)
- ✅ Hybrid Predictor (69.73% accuracy)
- ✅ 31,260 games analyzed (2000-2025)
- ✅ Box Plus/Minus integration
- ✅ REST/fatigue analysis
- ✅ Momentum tracking

### ✅ PRODUCTION DEPLOYMENT (LIVE)
**Deployment:** December 4, 2025

**Live Features:**
- ✅ **Daily Newsletter System** - Automated free & premium content generation
- ✅ **NBA API Integration** - Real-time game data with CDN fallback
- ✅ **ESPN Injury Scraper** - Live injury report integration
- ✅ **Prediction Tracking** - Automated accuracy monitoring
- ✅ **Performance Reports** - Weekly accuracy analysis
- ✅ **Flask Web App** - Admin interface for data management

**Workflow:**
```
Daily 6am ET: quick_update.py (fetch latest games)
Daily 8am ET: export_substack_daily.py (generate free newsletter)
Daily 9am ET: export_substack_premium.py (generate premium newsletter)
Weekly: generate_performance_report.py (accuracy analysis)
```

### 🎯 Current Accuracy Metrics

**Overall Performance:**
```
Hybrid Model:      69.73% (31,260 games)
Team ELO Only:     65.69%
Player ELO Only:   62.14%
2024-25 Season:    71.2% (partial, 89 games)
```

**By Game Type:**
- Close Games (<5 pts): 56.8%
- Blowouts (>15 pts): 79.1%
- Back-to-Back: 64.7%
- Well-Rested: 71.3%

---

## Project Structure

```
nba-elo-engine/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── app.py                            # Flask admin web interface
│
├── config/
│   ├── settings.yaml                 # ELO parameters (K=20, HCA=70)
│   ├── constants.yaml                # NBA team mappings
│   └── arena_coordinates.csv         # Arena coordinates for travel
│
├── data/
│   ├── raw/                          # Source data (not in git)
│   │   ├── nba_games_all.csv        # 31,260 games (2000-2025)
│   │   └── player_boxscores_all.csv # 650K+ player-game records
│   └── exports/                      # Generated outputs (not in git)
│       ├── team_elo_history_phase_1_5.csv
│       ├── player_ratings_bpm_adjusted.csv
│       └── prediction_tracking.csv   # Live prediction log
│
├── src/
│   ├── engines/
│   │   ├── team_elo_engine.py       # Team ELO calculator
│   │   ├── player_elo_engine.py     # Player ELO calculator
│   │   └── hybrid_predictor.py      # Combined predictor
│   │
│   ├── predictors/
│   │   ├── hybrid_team_player.py    # Main prediction engine
│   │   ├── schedule_fetcher.py      # NBA schedule retrieval
│   │   └── season_predictor.py      # Season simulation
│   │
│   ├── scrapers/
│   │   ├── nba_api_data_fetcher.py  # NBA API + CDN integration
│   │   ├── espn_scraper.py          # ESPN data scraper
│   │   └── espn_team_injuries.py    # Injury reports
│   │
│   ├── analytics/
│   │   ├── newsletter_viz.py        # Newsletter visualizations
│   │   ├── matchup_analysis.py      # Head-to-head analysis
│   │   ├── game_summary.py          # Post-game summaries
│   │   ├── prediction_tracking.py   # Accuracy monitoring
│   │   └── player_h2h_analysis.py   # Player comparisons
│   │
│   ├── features/
│   │   ├── rest_fatigue_analyzer.py # Rest/back-to-back tracking
│   │   ├── momentum_tracker.py      # Win streak analysis
│   │   ├── form_factor.py           # Recent performance
│   │   └── close_game_enhancer.py   # Close game adjustments
│   │
│   └── utils/
│       ├── elo_math.py              # ELO formulas
│       ├── confidence_adjuster.py   # Probability caps
│       └── top_player_concentration.py
│
├── scripts/
│   ├── export_substack_daily.py     # Free newsletter generator
│   ├── export_substack_premium.py   # Premium newsletter generator
│   ├── daily_update.py              # Daily data refresh
│   ├── quick_update.py              # Fast update script
│   ├── update_with_new_games.py     # Game data updater
│   ├── calculate_bpm.py             # Box Plus/Minus calculator
│   ├── auto_track_predictions.py    # Auto prediction logging
│   ├── generate_accuracy_report.py  # Accuracy reporting
│   └── generate_performance_report.py
│
└── docs/
    ├── README.md                     # Documentation index
    └── DAILY_NEWSLETTER_WORKFLOW.md  # Newsletter guide
```

---

## Configuration

Edit `config/settings.yaml` to customize ELO parameters:

```yaml
elo:
  # Core Parameters
  base_rating: 1500              # Starting rating for all teams
  k_factor: 20                   # Rating sensitivity (15-30 range)

  # Phase 1.5 Enhancements
  home_court_advantage: 70       # Home bonus (reduced from 100)
  margin_of_victory: true        # Enable MOV multiplier

  # Rest Penalties
  rest_penalty_b2b: -46          # Back-to-back games (0 days rest)
  rest_penalty_1day: -15         # Short rest (1 day)

  # Season Management
  season_regression: 0.25        # 25% regression toward mean

  # Travel Tracking
  track_travel: true             # Enable distance calculations
  long_travel_threshold_km: 1500 # Long travel threshold
```

---

## Performance Metrics

### Accuracy by Context (Phase 1.5)

| Context | Accuracy | Notes |
|---------|----------|-------|
| **Overall** | **65.69%** | 31,068 predictions |
| Home Team Wins | 71.2% | Strong home court modeling |
| Away Team Wins | 58.7% | Challenging road predictions |
| Back-to-Back Games | 62.3% | Improved from 56% (Phase 1.0) |
| Normal Rest | 66.8% | Well-rested teams |
| Close Games (< 5 pts) | 55.1% | Inherently difficult |
| Blowouts (> 15 pts) | 78.4% | Strong favorite detection |

### Recent Seasons Performance

| Season | Accuracy | Games |
|--------|----------|-------|
| 2024-25 | 67.2% | Partial season |
| 2023-24 | 66.1% | Full season |
| 2022-23 | 65.8% | Full season |
| 2021-22 | 64.9% | Full season |
| 2020-21 | 63.7% | COVID bubble (outlier) |

### Computational Performance

```
Full Dataset (31,202 games): 4.2 seconds
Per-Game Average: 0.13 milliseconds
Throughput: ~7,400 games/second
Memory Usage: ~250 MB peak
```

---

## Python API Usage

```python
from src.engines.team_elo_engine import TeamELOEngine
from src.utils.file_io import load_csv_to_dataframe

# Load game data
games_df = load_csv_to_dataframe('data/raw/nba_games_all.csv')

# Initialize engine with Phase 1.5 parameters
engine = TeamELOEngine(
    base_rating=1500,
    k_factor=20,
    home_advantage=70
)

# Compute ratings
history_df = engine.compute_season_elo(games_df)

# Get current standings
current_ratings = engine.get_current_ratings()
print(current_ratings.sort_values('rating', ascending=False).head(10))

# Predict a matchup
prediction = engine.predict_game(
    home_team_id='14',  # Los Angeles Lakers
    away_team_id='10'   # Golden State Warriors
)

print(f"Home Win Probability: {prediction['home_win_probability']:.1%}")
print(f"Expected Spread: {prediction['expected_spread']:.1f} points")
```

---

## Data Assets

### Current Files (Production Data)

- **Game Data:** 31,260 games across 25 seasons (2000-2025)
- **Player Box Scores:** 650,000+ player-game records with BPM
- **Team ELO History:** 62,520 team-game records (daily updated)
- **Player Ratings:** 2,628 active players with ELO tracking
- **Prediction Log:** All predictions since Dec 2025 with outcomes
- **Injury Reports:** Live ESPN injury data (refreshed daily)

---

## Key Achievements

✅ **Production System** - Live daily newsletter generation since Dec 2025
✅ **69.73% Accuracy** - Hybrid model exceeds 66-68% target
✅ **650K+ Player Records** - Complete box score database (2000-2025)
✅ **2,628 Players Tracked** - Individual ELO ratings with BPM integration
✅ **Automated Workflow** - Daily updates, predictions, and reporting
✅ **Real-time Integration** - NBA API + ESPN scrapers with fallbacks
✅ **Performance Monitoring** - Automated accuracy tracking and reporting
✅ **25 Years of Data** - Complete NBA coverage (2000-2025)

---

## Documentation

- **[docs/README.md](docs/README.md)** - Documentation index
- **[docs/DAILY_NEWSLETTER_WORKFLOW.md](docs/DAILY_NEWSLETTER_WORKFLOW.md)** - Newsletter generation guide

---

## Newsletter Features

### Free Daily Newsletter
- **Today's Schedule** - All games with times
- **Top Matchups** - Best games of the day
- **Upset Alerts** - Competitive matchup warnings
- **Key Insights** - Momentum, rest factors, pace analysis
- **Prediction Summary** - Win probabilities for all games

### Premium Newsletter
- **Detailed Game Analysis** - Full ELO breakdowns
- **Matchup Breakdown** - Why the favorite is favored (ELO edge, form, home court)
- **Player Impact** - Top player H2H comparisons
- **Injury Analysis** - Impact of missing players
- **Head-to-Head History** (Even Days) - Last 3 games between teams
- **Pace & Style Analysis** (Odd Days) - Offensive/defensive ratings, tempo
- **Featured Teams Track Record** (Wednesdays) - Last 10 games momentum
- **Prediction Confidence** (Thursdays) - Model confidence visualization
- **Upset Alert Detail** - Toss-up vs competitive game identification

### Content Rotation
- **Sunday:** Hottest/Coldest Teams (7-day streaks)
- **Monday:** Team Performance Trends
- **Tuesday:** Key Storylines
- **Wednesday:** Featured Teams Track Record
- **Thursday:** Prediction Confidence Visualization
- **Friday:** Playoff Implications
- **Saturday:** Weekly Recap

---

## Research & Methodology

The Phase 1.5 system implements research-backed methodologies:

- **FiveThirtyEight NBA ELO** - Margin of victory autocorrelation
- **Modern NBA Studies** - Home court advantage calibration (70 vs 100)
- **NBA Rest Research** - Back-to-back and recovery impact
- **Travel Analysis** - Distance vs performance correlation

See [PHASE_1_5_COMPLETE.md](PHASE_1_5_COMPLETE.md) for detailed research references.

---

## Requirements

```
Python 3.8+
pandas >= 1.3.0
numpy >= 1.21.0
matplotlib >= 3.4.0
requests >= 2.26.0
pyyaml >= 5.4.0
```

Install all dependencies:
```bash
pip install -r requirements.txt
```

---

## Contributing

This is a personal research project by Aaron Thomas. For questions or collaboration:

- Review documentation in `/docs` directory
- Check [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- See [PHASE_1_5_COMPLETE.md](PHASE_1_5_COMPLETE.md) for methodology

---

## License

Personal research project - All rights reserved

---

## Project Information

**Owner:** Aaron Thomas
**Current Version:** 3.0 Production (Hybrid ELO System)
**Status:** Live Production
**Started:** November 2025
**Production Deployment:** December 4, 2025
**Last Updated:** December 10, 2025

---

**Production Status:** ✅ LIVE | Newsletter System Active | Daily Updates Running | 69.73% Accuracy
