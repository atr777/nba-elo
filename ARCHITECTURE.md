# NBA ELO Intelligence Engine - System Architecture

## Phase 1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ESPN API                          Sample Data                   │
│  ┌──────────────────┐             ┌──────────────────┐          │
│  │ Scoreboard API   │             │ Generate Mock    │          │
│  │ /nba/scoreboard  │             │ Game Data        │          │
│  └────────┬─────────┘             └────────┬─────────┘          │
│           │                                 │                    │
└───────────┼─────────────────────────────────┼────────────────────┘
            │                                 │
            └─────────────┬───────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                       ETL LAYER                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────────────────────────────────────────┐         │
│  │  fetch_scoreboard.py                               │         │
│  │  - Date range iteration                            │         │
│  │  - API calls with retry logic                      │         │
│  │  - Rate limiting                                   │         │
│  │  - JSON → CSV conversion                           │         │
│  └───────────────────────┬────────────────────────────┘         │
│                          │                                       │
└──────────────────────────┼───────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     DATA STORAGE                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  data/raw/nba_games.csv                                          │
│  ┌──────────────────────────────────────────────────┐           │
│  │ game_id | date | home_team | away_team | scores  │           │
│  │ 401234  | 1024 | Lakers    | Warriors  | 112-108 │           │
│  │ 401235  | 1024 | Celtics   | Heat      | 105-98  │           │
│  │ ...                                               │           │
│  └───────────────────────┬──────────────────────────┘           │
│                          │                                       │
└──────────────────────────┼───────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    COMPUTATION ENGINE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────────────────────────────────────────┐         │
│  │  TeamELOEngine                                     │         │
│  │                                                     │         │
│  │  1. Initialize all teams at base rating (1500)     │         │
│  │  2. Sort games chronologically                     │         │
│  │  3. For each game:                                 │         │
│  │     a. Get current team ratings                    │         │
│  │     b. Calculate expected scores                   │         │
│  │        E = 1/(1+10^((R_opp-R_team)/400))          │         │
│  │     c. Update ratings                              │         │
│  │        R_new = R_old + K*(actual-expected)         │         │
│  │     d. Record history                              │         │
│  │  4. Export results                                 │         │
│  └───────────────────────┬────────────────────────────┘         │
│                          │                                       │
│  ┌────────────────────────────────────────────────────┐         │
│  │  elo_math.py - Core Formulas                       │         │
│  │  - calculate_expected_score()                      │         │
│  │  - update_elo_rating()                             │         │
│  │  - process_game_elo_update()                       │         │
│  └────────────────────────────────────────────────────┘         │
│                                                                   │
└──────────────────────────┼───────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       OUTPUT LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  data/exports/team_elo_history.csv                              │
│  ┌──────────────────────────────────────────────────┐           │
│  │ game | date | team | rating_before | rating_after│           │
│  │ 401234| 1024 | LAL  | 1500.0        | 1507.2      │           │
│  │ 401234| 1024 | GSW  | 1500.0        | 1492.8      │           │
│  │ ...                                               │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                   │
│  Current Standings                                               │
│  ┌──────────────────────────────────────────────────┐           │
│  │ Rank | Team                    | ELO Rating      │           │
│  │   1  | Orlando Magic           | 1576.5          │           │
│  │   2  | New York Knicks         | 1569.3          │           │
│  │   3  | Portland Trail Blazers  | 1542.7          │           │
│  │ ...                                               │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

```

## Data Flow Diagram

```
┌──────────┐
│  ESPN    │
│   API    │
└────┬─────┘
     │ JSON (games, scores, teams)
     ▼
┌────────────┐
│  Scraper   │  ← date_utils.py (date ranges)
│  Module    │  ← logging_utils.py (error tracking)
└────┬───────┘
     │ CSV (raw game data)
     ▼
┌─────────────┐
│ Raw Storage │
│  nba_games  │
│    .csv     │
└────┬────────┘
     │
     ▼
┌──────────────┐
│  ELO Engine  │  ← elo_math.py (calculations)
│              │  ← file_io.py (config loading)
│ 1. Load      │
│ 2. Sort      │
│ 3. Calculate │
│ 4. Record    │
└────┬─────────┘
     │ CSV (rating history)
     ▼
┌──────────────┐
│   Exports    │
│ team_elo_    │
│  history.csv │
└──────────────┘
     │
     ▼
┌──────────────┐
│  Analysis /  │
│  Prediction  │
│  Dashboard   │  ← Phase 2
└──────────────┘
```

## Component Dependencies

```
TeamELOEngine
    ├─ depends on → elo_math.py
    │               ├─ calculate_expected_score()
    │               ├─ update_elo_rating()
    │               └─ process_game_elo_update()
    │
    ├─ depends on → file_io.py
    │               ├─ load_csv_to_dataframe()
    │               ├─ save_dataframe_to_csv()
    │               └─ load_settings()
    │
    └─ depends on → logging_utils.py
                    └─ get_logger()

ESPNScoreboardScraper
    ├─ depends on → date_utils.py
    │               ├─ generate_date_range()
    │               └─ parse_date()
    │
    ├─ depends on → file_io.py
    │               └─ save_dataframe_to_csv()
    │
    └─ depends on → logging_utils.py
                    └─ get_logger()
```

## Configuration Flow

```
config/settings.yaml
    ├─ elo.base_rating: 1500
    ├─ elo.k_factor: 20
    ├─ elo.home_court_advantage: 100
    ├─ api.espn_scoreboard: URL
    ├─ api.request_timeout: 10
    └─ api.rate_limit_delay: 0.5
         │
         ▼
    file_io.load_settings()
         │
         ▼
    Used by engines and scrapers
```

## Execution Flow

```
START
  │
  ├─ Option 1: Scrape Real Data
  │   ├─ fetch_scoreboard.py
  │   │   ├─ Generate date range
  │   │   ├─ For each date:
  │   │   │   ├─ Call ESPN API
  │   │   │   ├─ Parse JSON response
  │   │   │   └─ Extract game data
  │   │   └─ Save to CSV
  │   └─ → nba_games_raw.csv
  │
  ├─ Option 2: Generate Sample Data
  │   ├─ generate_sample_data.py
  │   │   ├─ Create random matchups
  │   │   ├─ Generate realistic scores
  │   │   └─ Sort by date
  │   └─ → nba_games_sample.csv
  │
  ▼
Load Game Data
  │
  ▼
Initialize ELO Engine
  │ ├─ Set base_rating = 1500
  │ ├─ Set k_factor = 20
  │ └─ Set home_advantage = 100
  │
  ▼
Process Games Chronologically
  │
  ├─ For each game:
  │   ├─ Get team ratings
  │   │   Home: R_h, Away: R_a
  │   │
  │   ├─ Calculate expected scores
  │   │   E_h = 1/(1+10^((R_a-(R_h+100))/400))
  │   │   E_a = 1 - E_h
  │   │
  │   ├─ Determine actual scores
  │   │   A_h = 1 if win, 0 if loss
  │   │   A_a = 1 if win, 0 if loss
  │   │
  │   ├─ Update ratings
  │   │   R_h_new = R_h + K*(A_h - E_h)
  │   │   R_a_new = R_a + K*(A_a - E_a)
  │   │
  │   └─ Record history
  │       ├─ game_id, date, teams
  │       ├─ scores, winner
  │       ├─ ratings (before/after)
  │       └─ expected vs actual
  │
  ▼
Export Results
  │ ├─ team_elo_history.csv
  │ └─ current_ratings.csv
  │
END
```

## Key Design Decisions

### 1. Modularity
- **Separation of Concerns**: ETL, engines, utils isolated
- **Benefits**: Easy testing, clear dependencies, maintainable

### 2. Configuration-Driven
- **YAML Settings**: All parameters externalized
- **Benefits**: No code changes for tuning, easy experiments

### 3. CSV-Based Storage
- **Simple Format**: Easy inspection, portable
- **Benefits**: Tool-agnostic, human-readable, Git-friendly

### 4. Chronological Processing
- **Date-Sorted**: Games processed in order
- **Benefits**: Accurate history, reproducible results

### 5. Zero-Sum Ratings
- **Conservation**: Total rating change = 0
- **Benefits**: Fair system, no rating inflation

## Performance Characteristics

```
Complexity Analysis:
- Scraping: O(n) where n = number of days
- ELO Calculation: O(m) where m = number of games
- Memory: O(m) to store history

Expected Performance:
- Scraping: ~0.5s per day (rate limited)
- Calculation: ~0.0003s per game
- Full Season (1,230 games): < 2 seconds total
```

## Phase 2 Extension Points

The architecture is designed for easy extension:

```
CURRENT (Phase 1):
    Games → ELO Engine → Ratings

PHASE 2 ADDITIONS:
    Games → [Contextual Features] → ELO Engine → Ratings
              ├─ rest_days.py
              ├─ travel.py
              └─ trade_injury_joiner.py
    
    Ratings → [Visualization] → Dashboard
               ├─ elo_time_series.py
               ├─ team_charts.py
               └─ predictor_ui.py
```

---

This architecture provides:
✅ Clear data flow  
✅ Modular design  
✅ Easy testing  
✅ Simple extension  
✅ Good performance
