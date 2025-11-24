# Phase 3: Player ELO System - Implementation Plan

**Status:** Planning / Data Collection
**Target Start:** Upon completion of player box score scraping
**Estimated Duration:** 8-12 hours development + 2-3 hours testing
**Target Accuracy:** 66-68% (additional +1-2 points over Phase 1.5's 65.69%)

---

## Executive Summary

Phase 3 will implement a player-level ELO rating system that tracks individual player skill and aggregates player ratings to calculate dynamic team strength. This enables modeling of trades, injuries, lineup combinations, and roster changes - capabilities not possible with team-only ratings.

**Key Innovation:** Minutes-weighted player aggregation allows real-time team strength calculation based on who's actually playing.

---

## Prerequisites

### Data Requirements

**✅ COMPLETE:**
- Team game data (31,284 games, 2000-2025)
- Team ELO history (Phase 1.5)
- Arena coordinates for travel

**🔄 IN PROGRESS:**
- Player box score data (~650,000 records)
  - Status: Currently scraping from ESPN API
  - ETA: 4-5 hours to completion
  - Fields: Player, Team, Opponent, Date, MIN, PTS, REB, AST, STL, BLK, TO, FG%, 3P%, FT%, +/-

**⏳ NEEDED (Phase 3):**
- Trade/transaction database
  - Date, player, from_team, to_team
  - Can be manually curated or scraped
  - ~500-1000 transactions per season

- Roster data (optional enhancement)
  - Active rosters per game
  - Injury reports
  - DNP (Did Not Play) reasons

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                  PHASE 3 ARCHITECTURE                    │
└─────────────────────────────────────────────────────────┘

┌──────────────────┐     ┌──────────────────┐
│  Player Boxscores│     │  Trade Database  │
│  (650K records)  │     │  (Transactions)  │
└────────┬─────────┘     └────────┬─────────┘
         │                        │
         └────────┬───────────────┘
                  ▼
         ┌────────────────┐
         │ Player ELO     │
         │ Engine         │
         │ - Individual   │
         │   ratings      │
         │ - Trade impact │
         └────────┬───────┘
                  │
                  ▼
         ┌────────────────┐
         │ Minutes-       │
         │ Weighted       │
         │ Aggregator     │
         │ - Team strength│
         │ - Lineup calc  │
         └────────┬───────┘
                  │
                  ▼
         ┌────────────────┐     ┌────────────────┐
         │ Enhanced Team  │────▶│  Game          │
         │ ELO (Dynamic)  │     │  Predictor     │
         └────────────────┘     └────────────────┘
```

### Data Flow

```
Player Boxscore → Player ELO Update → Team Strength Calc → Prediction

Example:
1. LeBron plays 36 min, team wins
   → LeBron ELO: 1850 → 1858 (+8)

2. Lakers current strength =
   Σ(player_elo × minutes_share) for active roster
   = (LeBron×0.30 + AD×0.28 + ... ) = 1645 team rating

3. Prediction: Lakers (1645) vs Warriors (1620)
   → Lakers 58% win probability
```

---

## Implementation Plan

### Phase 3.1: Player ELO Engine (3-4 hours)

**Goal:** Calculate individual player ELO ratings based on performance and game outcomes.

**Algorithm:**

```python
class PlayerELOEngine:
    """
    Player-level ELO rating system.

    Key Differences from Team ELO:
    - Minutes-weighted contribution
    - Performance metrics considered (PTS, +/-, etc.)
    - Faster volatility (K-factor ~32 vs 20)
    - Separate offensive/defensive ratings (optional)
    """

    def __init__(self):
        self.base_rating = 1500  # Average NBA player
        self.k_factor = 32       # Higher than team (players change faster)
        self.min_minutes = 5     # Minimum playing time to update rating

    def update_player_rating(self, player, game_result, minutes_played, plus_minus):
        """
        Update player ELO based on game outcome and performance.

        Formula:
        1. Expected score based on team matchup
        2. Minutes weight: impact = minutes / 48
        3. Performance multiplier: f(+/-, PTS, etc.)
        4. Rating change: K × minutes_weight × (actual - expected)
        """
        pass
```

**Features:**
- Individual player tracking (2,500+ active players)
- Historical rating evolution
- Rookie initialization (1400-1450 based on draft position)
- Minutes-weighted updates (starters change more than bench)
- Performance multipliers (blowout wins count less for bench players)

**Output:**
- `data/exports/player_elo_history.csv`
  - player_id, player_name, game_date, team, minutes, rating_before, rating_after, +/-

### Phase 3.2: Minutes-Weighted Team Aggregation (2-3 hours)

**Goal:** Calculate dynamic team strength from active player ratings.

**Algorithm:**

```python
def calculate_team_strength(roster, minutes_distribution):
    """
    Aggregate player ratings into team strength.

    Args:
        roster: List of (player_id, player_elo) tuples
        minutes_distribution: Expected minutes for each player

    Returns:
        team_strength: Weighted average ELO rating

    Formula:
        team_strength = Σ(player_elo × (player_minutes / 240))

    Where 240 = total team minutes per game (48 min × 5 players)

    Example:
    Starters (30-36 min each): weighted heavily
    Bench (5-15 min each): smaller contribution
    DNPs (0 min): no contribution
    """
    total_minutes = sum(m for _, m in minutes_distribution)

    team_strength = 0
    for (player_id, player_elo), minutes in zip(roster, minutes_distribution):
        weight = minutes / total_minutes
        team_strength += player_elo × weight

    return team_strength
```

**Features:**
- Dynamic roster composition
- Typical rotation minutes (based on recent games)
- Lineup-specific calculations
- Injury/absence handling

**Output:**
- `data/exports/team_strength_dynamic.csv`
  - team_id, date, traditional_elo, player_based_elo, active_roster

### Phase 3.3: Trade Impact Analysis (2-3 hours)

**Goal:** Quantify team strength changes from player transactions.

**Algorithm:**

```python
def analyze_trade_impact(team, players_in, players_out, minutes_redistribution):
    """
    Calculate team strength change from trade.

    Args:
        team: Team making the trade
        players_in: List of acquired players with their ELOs
        players_out: List of traded players with their ELOs
        minutes_redistribution: How minutes are reallocated

    Returns:
        impact: Change in team strength rating

    Example:
    Lakers trade D'Angelo Russell (1580 ELO, 28 min) for
    Kyrie Irving (1680 ELO, 32 min)

    Before: team_strength = 1620
    After: team_strength = 1620 - (1580×0.28/5) + (1680×0.32/5)
           = 1620 - 88.5 + 107.5 = 1639
    Impact: +19 points
    """
    pass
```

**Features:**
- Pre/post trade team strength
- Multi-player trade analysis
- Minutes reallocation modeling
- Historical trade impact database

**Output:**
- `data/exports/trade_impact_analysis.csv`
  - trade_date, team, players_in, players_out, strength_before, strength_after, delta

### Phase 3.4: Enhanced Prediction System (2-3 hours)

**Goal:** Integrate player ELO with team ELO for improved predictions.

**Hybrid Model:**

```python
def predict_game_hybrid(home_team, away_team, use_player_elo=True):
    """
    Predict game outcome using both team and player ELO.

    Approaches:

    1. Player-Only (Phase 3):
       - Calculate team strength from current roster
       - Use player-based ratings for prediction
       - Advantage: Reflects current lineup

    2. Weighted Average (Best accuracy):
       - Combine traditional team ELO + player-based ELO
       - team_rating = 0.6 × traditional_elo + 0.4 × player_based_elo
       - Advantage: Stability + adaptability

    3. Lineup-Specific (Future):
       - Predict based on expected starting 5
       - Adjust for injuries/rest
       - Advantage: Most accurate for known lineups
    """
    pass
```

**Features:**
- Hybrid team+player model
- Lineup scenario simulator
- Injury impact calculator
- "What-if" trade simulator

**Output:**
- Enhanced prediction accuracy: Target 66-68%
- Lineup strength rankings
- Trade recommendation engine

---

## Technical Specifications

### Player ELO Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Base Rating | 1500 | Average NBA player |
| K-Factor | 32 | Higher volatility than teams (players develop/decline faster) |
| Rookie Base | 1400-1450 | Based on draft position (#1 pick: 1450, #60 pick: 1400) |
| Veteran Minimum | 1300 | Replacement-level player |
| Elite Threshold | 1800+ | MVP-caliber players |
| Min Minutes | 5 | Minimum playing time for rating update |

### Minutes Weighting

```
Starter (30-36 min): ~25-30% of team strength
Key Reserve (18-25 min): ~15-20% of team strength
Bench (8-15 min): ~6-12% of team strength
Deep Bench (< 8 min): ~0-5% of team strength

Total: 240 team-minutes = 100% weighting
```

### Rating Tiers (Player ELO)

| Rating | Tier | Example Players (Historical) |
|--------|------|------------------------------|
| 1900+ | Generational | LeBron '13, Jordan '96, Curry '16 |
| 1800-1900 | MVP | Durant, Giannis, Jokic |
| 1700-1800 | All-Star | Top 20-30 players |
| 1600-1700 | Starter | Solid rotation starters |
| 1500-1600 | Rotation | Average NBA player |
| 1400-1500 | Bench | Deep bench, rookies |
| < 1400 | Replacement | G-League call-ups |

---

## Expected Improvements

### Accuracy Gains

**Target: 66-68% prediction accuracy** (+1-2 points over Phase 1.5's 65.69%)

**Breakdown by Enhancement:**

| Enhancement | Expected Gain | Rationale |
|-------------|---------------|-----------|
| Player-based team strength | +0.8-1.2% | Better reflects roster changes |
| Trade impact modeling | +0.3-0.5% | Captures mid-season team changes |
| Injury/absence handling | +0.2-0.4% | Accounts for missing key players |
| Lineup optimization | +0.2-0.3% | Better rotation analysis |
| **Total** | **+1.5-2.4%** | **Target: 67% accuracy** |

### New Capabilities

1. **Trade Analysis**
   - "What if Lakers trade Reaves for Siakam?"
   - Quantified team strength impact
   - Historical trade success rate

2. **Injury Impact**
   - "How do Warriors perform without Curry?"
   - Replacement player analysis
   - Lineup strength degradation

3. **Lineup Simulator**
   - "Best 5-man lineup for Lakers?"
   - Defensive vs offensive lineups
   - Matchup-specific rotations

4. **Player Value**
   - Individual player win shares
   - Trade value calculator
   - Contract efficiency analysis

---

## Implementation Schedule

### Week 1: Data Preparation & Engine Development
**Days 1-2:** Data cleaning and validation
- Clean player box score data (~650K records)
- Handle missing values, duplicates
- Normalize player names/IDs
- Create player ID mapping

**Days 3-4:** Player ELO Engine
- Implement core player ELO algorithm
- Minutes-weighted updates
- Performance multipliers
- Historical rating calculation

**Days 5-6:** Initial validation
- Test on sample season (2023-24)
- Validate rating distributions
- Check for anomalies
- Tune K-factor and parameters

### Week 2: Team Aggregation & Integration
**Days 7-8:** Minutes-Weighted Aggregation
- Implement team strength calculator
- Roster composition tracking
- Minutes distribution modeling
- Active roster management

**Days 9-10:** Trade Impact System
- Trade database integration
- Impact calculation algorithm
- Historical trade analysis
- Validation against known trades

**Days 11-12:** Prediction Integration
- Hybrid team+player model
- Accuracy testing
- Parameter optimization
- Final validation

### Week 3: Testing & Refinement
**Days 13-14:** Comprehensive testing
- Full historical recalculation (2000-2025)
- Accuracy measurement across seasons
- Edge case handling
- Performance optimization

**Day 15:** Documentation & Deployment
- API documentation
- Usage examples
- Phase 3 completion report

---

## Data Requirements

### Player Box Scores

**Required Fields:**
- game_id, date
- player_id, player_name
- team_id, team_name
- opponent_id
- minutes_played
- points, rebounds, assists
- field_goals_made/attempted
- three_pointers_made/attempted
- free_throws_made/attempted
- steals, blocks, turnovers
- plus_minus

**Data Size:**
- ~650,000 player-game records
- ~30 MB compressed CSV
- 2000-2025 seasons

### Trade Database

**Required Fields:**
- trade_date
- player_id, player_name
- from_team_id, from_team_name
- to_team_id, to_team_name
- trade_type (trade, free_agency, draft, waiver)

**Data Size:**
- ~10,000-15,000 transactions (2000-2025)
- ~1-2 MB CSV

**Sources:**
- Basketball Reference
- ESPN transaction log
- Manual curation for major trades

---

## Validation Plan

### Accuracy Metrics

1. **Overall Prediction Accuracy**
   - Target: 66-68%
   - Current Phase 1.5: 65.69%
   - Minimum acceptable: 65.5%

2. **Accuracy by Context**
   - Games with recent trades: Target 63-65%
   - Games with injuries: Target 64-66%
   - Normal games: Target 67-69%

3. **Trade Impact Validation**
   - Compare predicted vs actual post-trade win rates
   - Historical trade success correlation
   - Target: R² > 0.60

### Test Scenarios

**Scenario 1: Known Major Trade**
- 2023 Lakers trade for D'Angelo Russell
- Predicted impact: +15 team strength
- Actual win rate change: Validate

**Scenario 2: Injury Impact**
- 2023 Warriors without Curry
- Predicted strength: -120 points
- Actual record: Validate

**Scenario 3: Rookie Integration**
- Wembanyama 2024 impact on Spurs
- Predicted rookie rating: 1520
- Team strength change: Validate

---

## Risk Mitigation

### Potential Challenges

1. **Data Quality**
   - **Risk:** Missing/incorrect player box scores
   - **Mitigation:** Data validation pipeline, manual spot checks
   - **Fallback:** Use team ELO for games with incomplete data

2. **Minutes Distribution**
   - **Risk:** Unpredictable rotations (injuries, load management)
   - **Mitigation:** Rolling average of recent games
   - **Fallback:** Use typical season averages

3. **Computation Performance**
   - **Risk:** 650K player-games slower than 31K team-games
   - **Mitigation:** Vectorized operations, parallel processing
   - **Target:** < 30 seconds for full recalculation

4. **Model Overfitting**
   - **Risk:** Too many parameters, overfit to training data
   - **Mitigation:** Cross-validation, holdout test set
   - **Validation:** Test on 2024-25 (unseen data)

---

## Success Criteria

### Phase 3 Complete When:

✅ **Functionality:**
- [ ] Player ELO ratings calculated for all players (650K records)
- [ ] Minutes-weighted team aggregation working
- [ ] Trade impact analysis operational
- [ ] Hybrid prediction system integrated

✅ **Accuracy:**
- [ ] Overall prediction accuracy ≥ 66%
- [ ] Improvement of ≥ +0.5% over Phase 1.5
- [ ] Trade impact validation R² ≥ 0.55

✅ **Performance:**
- [ ] Full recalculation < 30 seconds
- [ ] Real-time prediction < 1 second
- [ ] Memory usage < 1 GB

✅ **Documentation:**
- [ ] PHASE_3_COMPLETE.md written
- [ ] API documentation updated
- [ ] Usage examples provided
- [ ] Validation report generated

---

## Future Enhancements (Phase 4+)

### Beyond Phase 3

1. **Separate Offensive/Defensive Ratings**
   - Split player ELO into offense and defense
   - Better matchup modeling
   - Target: +0.5-1% accuracy

2. **Position-Specific Modeling**
   - Different K-factors by position
   - Positional scarcity adjustments
   - Target: More accurate player valuation

3. **Advanced Lineup Analytics**
   - 5-man lineup historical performance
   - Synergy factors (players who play well together)
   - Opponent-specific lineups

4. **Real-Time Updates**
   - Live game ELO updates
   - In-game win probability
   - Momentum modeling

5. **Machine Learning Layer**
   - Gradient boosting on ELO features
   - Neural network enhancements
   - Target: 70%+ accuracy

---

## Appendix: Example Outputs

### Player ELO History Sample

```csv
player_id,player_name,date,team,minutes,rating_before,rating_after,+/-,pts,reb,ast
2544,LeBron James,20231024,Lakers,36,1855.2,1861.5,+12,28,7,9
203954,Joel Embiid,20231024,76ers,34,1842.1,1848.3,+15,31,11,4
201939,Stephen Curry,20231024,Warriors,32,1838.7,1833.2,-8,22,3,7
```

### Trade Impact Analysis Sample

```csv
trade_date,team,players_in,players_out,strength_before,strength_after,delta
20230208,Lakers,D'Angelo Russell,Russell Westbrook,1612.3,1627.5,+15.2
20230209,Mavericks,Kyrie Irving,Spencer Dinwiddie,1598.7,1619.2,+20.5
```

### Dynamic Team Strength Sample

```csv
date,team,traditional_elo,player_based_elo,hybrid_elo,active_roster_count
20231024,Lakers,1645.2,1651.8,1647.8,12
20231024,Warriors,1638.5,1629.3,1634.7,11
```

---

**Document Version:** 1.0 (Draft)
**Last Updated:** November 23, 2025
**Status:** Planning Phase
**Author:** Aaron Thomas
**Next Review:** Upon box score data completion
