# NBA ELO Engine - Quick Reference

**Version 1.5** | Last Updated: November 23, 2025

---

## Common Commands

### Phase 1.5 - View Current Results

```bash
# View Phase 1.5 validation report
cat data/exports/validation_report_phase_1_5.txt

# View latest team ratings (with travel data)
head -50 data/exports/team_elo_with_travel_clean.csv

# View ELO history
tail -100 data/exports/team_elo_history_phase_1_5.csv

# Count total games processed
wc -l data/raw/nba_games_all.csv

# View unique teams
cut -d',' -f4 data/exports/team_elo_with_travel_clean.csv | sort -u | wc -l
```

### Data Scraping

```bash
# Scrape NBA games for a season
python src/etl/fetch_scoreboard.py \
    --start-date 20231024 \
    --end-date 20240430 \
    --output data/raw/nba_games_2023-24.csv

# Scrape player box scores (Phase 3 prep)
python scripts/nba_box_scraper.py \
    --start-date 20231024 \
    --end-date 20240430
```

### ELO Computation (Phase 1.5 Parameters)

```bash
# Compute team ELO with Phase 1.5 settings
python src/engines/team_elo_engine.py \
    --input data/raw/nba_games_all.csv \
    --output data/exports/team_elo_history.csv \
    --k-factor 20 \
    --home-advantage 70

# Custom parameters (experiment)
python src/engines/team_elo_engine.py \
    --input data/raw/nba_games_all.csv \
    --k-factor 25 \
    --home-advantage 80
```

### Validation & Analysis

```bash
# Run Phase 1.5 validation suite
python scripts/validate_phase_1_5.py

# Generate visualizations
python scripts/elo_visualizer.py

# Inspect ELO output
python scripts/inspect_elo_output.py
```

---

## Python API Quick Start

### Basic Usage (Phase 1.5)

```python
from src.engines.team_elo_engine import TeamELOEngine
from src.utils.file_io import load_csv_to_dataframe

# Load game data
games = load_csv_to_dataframe('data/raw/nba_games_all.csv')

# Create engine with Phase 1.5 parameters
engine = TeamELOEngine(
    base_rating=1500,
    k_factor=20,
    home_advantage=70  # Phase 1.5: reduced from 100
)

# Compute ratings
history = engine.compute_season_elo(games)

# Get current standings
standings = engine.get_current_ratings()
print(standings.sort_values('rating', ascending=False).head(10))
```

### Predict Game Outcomes

```python
# Predict Lakers vs Warriors
prediction = engine.predict_game(
    home_team_id='14',  # Lakers
    away_team_id='10'   # Warriors
)

print(f"Home Win Probability: {prediction['home_win_probability']:.1%}")
print(f"Expected Spread: {prediction['expected_spread']:.1f} points")
```

### Travel Distance Analysis

```python
from src.features.travel import add_travel_to_games, load_arena_coordinates

# Load arena coordinates
arenas = load_arena_coordinates('config/arena_coordinates.csv')

# Add travel distances to game data
games_with_travel = add_travel_to_games(games, arenas)

# Filter long travel games (> 1,500 km)
long_travel = games_with_travel[games_with_travel['long_travel'] == True]
print(f"Long travel games: {len(long_travel)}")
```

### Visualization

```python
from src.analytics.elo_visualizer import ELOVisualizer

# Create visualizer
viz = ELOVisualizer('data/exports/team_elo_history_phase_1_5.csv')

# Plot team ELO over time
viz.plot_team_elo_timeseries(
    team_name='Los Angeles Lakers',
    season='2023-24',
    show_context=True  # Highlights back-to-back games
)

# Compare multiple teams
viz.plot_team_comparison(
    teams=['Los Angeles Lakers', 'Boston Celtics', 'Golden State Warriors'],
    season='2023-24'
)

# League-wide distribution
viz.plot_league_elo_distribution(season='2023-24')
```

---

## File Structure

```
nba-elo-engine/
├── data/
│   ├── raw/
│   │   ├── nba_games_all.csv              # All games (31,284 games)
│   │   ├── nba_games_20XX-XX.csv          # Season files (25 seasons)
│   │   └── player_boxscores_all.csv       # PENDING - scraping now
│   └── exports/
│       ├── team_elo_history_phase_1_5.csv        # 9.1 MB
│       ├── team_elo_with_travel_clean.csv        # 11 MB
│       ├── validation_report_phase_1_5.txt       # Latest results
│       └── visualizations/                       # Charts
│
├── config/
│   ├── settings.yaml                      # ELO parameters (K=20, HCA=70)
│   ├── constants.yaml                     # Team ID mappings
│   └── arena_coordinates.csv              # Arena lat/lon for travel
│
├── src/
│   ├── engines/team_elo_engine.py        # Core team ELO
│   ├── features/travel.py                # Travel distance
│   ├── analytics/elo_visualizer.py       # Charting
│   └── utils/elo_math.py                 # ELO formulas
│
└── scripts/
    ├── nba_box_scraper.py                # Player data (ACTIVE)
    ├── validate_phase_1_5.py             # Validation suite
    └── elo_visualizer.py                 # Visualization script
```

---

## Phase 1.5 ELO Formula Reference

### Expected Score Calculation

```
Expected_Score = 1 / (1 + 10^((Opp_Rating_Adjusted - Team_Rating_Adjusted) / 400))

Where:
Team_Rating_Adjusted = Team_Rating + Home_Advantage (if home) + Rest_Penalty
Opp_Rating_Adjusted = Opp_Rating + Home_Advantage (if opp is home) + Opp_Rest_Penalty

Home_Advantage = 70 (Phase 1.5, down from 100)
Rest_Penalty = -46 (back-to-back) or -15 (1-day rest) or 0 (2+ days)
```

### Rating Update with MOV Multiplier

```
New_Rating = Old_Rating + K_effective × (Actual - Expected)

Where:
K_effective = K_base × MOV_multiplier
MOV_multiplier = ln(abs(score_diff) + 1) × correction_factor
K_base = 20 (default)
Actual = 1 (win) or 0 (loss)
```

### Season Regression

```
New_Season_Rating = Current_Rating × 0.75 + Base_Rating × 0.25

Applied at the start of each new NBA season
Base_Rating = 1500
Regression Factor = 25%
```

---

## Configuration Parameters (Phase 1.5)

### Current Settings (`config/settings.yaml`)

| Parameter | Value | Description |
|-----------|-------|-------------|
| `base_rating` | 1500 | Starting rating for all teams |
| `k_factor` | 20 | Base rating sensitivity |
| `home_court_advantage` | **70** | Home bonus (reduced from 100) |
| `margin_of_victory` | true | Enable MOV multiplier |
| `rest_penalty_b2b` | -46 | Back-to-back games penalty |
| `rest_penalty_1day` | -15 | 1-day rest penalty |
| `season_regression` | 0.25 | 25% regression toward mean |
| `track_travel` | true | Enable travel tracking |
| `long_travel_threshold_km` | 1500 | Long travel flag threshold |

### Customization Examples

```yaml
# More volatile ratings (responds faster to wins/losses)
elo:
  k_factor: 30

# Stronger home court advantage
elo:
  home_court_advantage: 90

# More conservative season regression
elo:
  season_regression: 0.15  # Only 15% regression

# Stricter back-to-back penalty
elo:
  rest_penalty_b2b: -60
```

---

## Rating Interpretation

### Team Strength Tiers

| Rating Range | Team Quality | Examples (Historical) |
|--------------|--------------|------------------------|
| **1700+** | All-time great | 2016-17 Warriors, 1995-96 Bulls |
| **1650-1700** | Elite championship | 2012-13 Heat, 2019-20 Lakers |
| **1600-1650** | Strong playoff | Most 1-4 seeds |
| **1550-1600** | Playoff contender | Most 5-8 seeds |
| **1500-1550** | Average/bubble | Fringe playoff teams |
| **1450-1500** | Below average | Lottery teams |
| **1400-1450** | Weak | Bottom 5 teams |
| **<1400** | Very poor | Historically bad seasons |

### Win Probability by Rating Difference

| Rating Diff | Home Win % | Away Win % | Neutral Win % |
|-------------|------------|------------|---------------|
| 0 | 60% | 40% | 50% |
| 50 | 69% | 31% | 61% |
| 100 | 77% | 23% | 71% |
| 150 | 84% | 16% | 79% |
| 200 | 89% | 11% | 85% |
| 300 | 95% | 5% | 93% |

*Note: Home Win % assumes 70-point home court advantage*

---

## Common Workflows

### Workflow 1: Update ELO with New Games

```bash
# 1. Scrape latest games
python src/etl/fetch_scoreboard.py \
    --start-date 20251120 \
    --end-date 20251130

# 2. Merge with existing data
cat data/raw/nba_games_all.csv data/raw/nba_games_new.csv > data/raw/nba_games_updated.csv

# 3. Recompute ELO
python src/engines/team_elo_engine.py \
    --input data/raw/nba_games_updated.csv \
    --output data/exports/team_elo_history_updated.csv

# 4. Validate results
python scripts/validate_phase_1_5.py
```

### Workflow 2: Compare Parameter Settings

```bash
# Test different K-factors
for k in 15 20 25 30; do
    python src/engines/team_elo_engine.py \
        --input data/raw/nba_games_all.csv \
        --output data/exports/elo_k${k}.csv \
        --k-factor $k
done

# Compare accuracy (manual analysis)
python scripts/validate_phase_1_5.py --input data/exports/elo_k15.csv
python scripts/validate_phase_1_5.py --input data/exports/elo_k20.csv
# ... etc
```

### Workflow 3: Generate Season Report

```bash
# 1. Compute ratings
python src/engines/team_elo_engine.py \
    --input data/raw/nba_games_2023-24.csv \
    --output data/exports/elo_2023-24.csv

# 2. Create visualizations
python scripts/elo_visualizer.py --season 2023-24

# 3. Generate validation report
python scripts/validate_phase_1_5.py --input data/exports/elo_2023-24.csv

# 4. View outputs
cat data/exports/validation_report_phase_1_5.txt
open data/exports/visualizations/
```

---

## Troubleshooting

### Import Errors

```bash
# Windows
set PYTHONPATH=C:\Users\Aaron\Desktop\NBA_ELO\nba-elo-engine

# Linux/Mac
export PYTHONPATH=/path/to/nba-elo-engine
```

### No Games Found

- Check date format: YYYYMMDD (e.g., 20231024, not 2023-10-24)
- Ensure date range has NBA games (season runs Oct-June)
- Verify ESPN API access or use existing data files

### Accuracy Lower Than Expected

- Ensure using Phase 1.5 parameters (HCA=70, not 100)
- Check that MOV multiplier is enabled
- Verify rest penalties are applied
- Confirm season regression is enabled

### Missing Data

```bash
# Check for null values
python -c "import pandas as pd; df = pd.read_csv('data/raw/nba_games_all.csv'); print(df.isnull().sum())"

# Remove duplicates
python -c "import pandas as pd; df = pd.read_csv('data/raw/nba_games_all.csv'); df.drop_duplicates().to_csv('data/raw/nba_games_clean.csv', index=False)"
```

### Visualization Errors

```bash
# Install matplotlib backend
pip install matplotlib --upgrade

# For WSL/headless systems
export MPLBACKEND=Agg

# Then rerun visualization
python scripts/elo_visualizer.py
```

---

## Performance Tips

### Speed Optimization

```python
# Use vectorized operations (already implemented in Phase 1.5)
# Avoid row-by-row iteration

# For large datasets, use chunking
chunk_size = 10000
for chunk in pd.read_csv('large_file.csv', chunksize=chunk_size):
    # Process chunk
    pass
```

### Memory Management

```python
# Read only required columns
df = pd.read_csv('nba_games_all.csv', usecols=['game_id', 'date', 'home_team_id', 'away_team_id', 'home_score', 'away_score'])

# Use appropriate data types
df['game_id'] = df['game_id'].astype('int32')
df['date'] = df['date'].astype('int32')
```

---

## Phase 3 Preview (Coming Soon)

### Planned Commands

```bash
# Compute player ELO ratings
python src/engines/player_elo_engine.py \
    --boxscores data/raw/player_boxscores_all.csv \
    --output data/exports/player_elo_history.csv

# Predict game with lineup analysis
python src/analytics/lineup_predictor.py \
    --home-lineup "LeBron,AD,Reaves,Rui,DLo" \
    --away-lineup "Curry,Klay,Draymond,Wiggins,Looney"

# Analyze trade impact
python src/analytics/trade_analyzer.py \
    --team "Los Angeles Lakers" \
    --player-in "Kyrie Irving" \
    --player-out "D'Angelo Russell"
```

---

## Useful One-Liners

```bash
# Top 10 teams current ratings
tail -58 data/exports/team_elo_with_travel_clean.csv | sort -t',' -k11 -nr | head -10

# Count games by season
cut -d',' -f2 data/raw/nba_games_all.csv | cut -c1-4 | sort | uniq -c

# Average rating by team
awk -F',' '{sum[$4]+=$11; count[$4]++} END {for (team in sum) print team, sum[team]/count[team]}' data/exports/team_elo_history_phase_1_5.csv | sort -t' ' -k2 -nr

# Find all back-to-back games
awk -F',' '$14==0 {print}' data/exports/team_elo_with_travel_clean.csv | wc -l

# Calculate average travel distance
awk -F',' 'NR>1 {sum+=$15; count++} END {print sum/count}' data/exports/team_elo_with_travel_clean.csv
```

---

## Documentation Links

- **[README.md](README.md)** - Project overview and getting started
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Comprehensive project summary
- **[PHASE_1_5_COMPLETE.md](PHASE_1_5_COMPLETE.md)** - Phase 1.5 detailed documentation
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and design
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and changes

---

**Quick Reference Version:** 1.5
**Last Updated:** November 23, 2025
**Current Phase:** 1.5 Complete | Phase 3 In Progress
