# Offseason Roster Handling: Trades, Rookies, Free Agency

**Date:** 2026-07-01 | **Status:** Design approved-pending-backtest | **Owner:** analyst

## Why this matters for revenue

October accuracy is the product demo. New subscribers will judge the model on
opening month, and opening month is exactly when un-handled roster churn hurts
most (last October–December we ran 61–64% before fixes). Every mechanism below
also powers a content stream: "the model's read on this trade" posts require the
roster-delta math to exist. Engine work and newsletter content are the same work.

## Current state (verified in code, 2026-07-01)

| Scenario | What happens today | Risk |
|---|---|---|
| Player traded | Rating follows the player, BUT `player_team_mapping.csv` is static (last refreshed Mar 9) | Player layer credits the wrong team until manually fixed |
| Rookie debuts | No prior; falls back to `default=1500` in `hybrid_predictor.get_player_rating` | Wembanyama-class rookies invisible; bad teams with good rookies underrated |
| Free agency | Nothing. Team ELO carries last season's roster performance wholesale | Teams gutted in July keep their old rating through October |
| Season rollover | No reset at all | Ratings drift; every strong model regresses toward the mean between seasons |
| Retirement/departure | Stale mapping keeps counting them | Phantom production |

## Design

### 1. Automated roster mapping (fixes trades) — Phase A, ~1 day
- Nightly step in `daily_update.py`: pull current rosters from the NBA API
  (`commonteamroster` endpoint, already have scraper infra) and regenerate
  `player_team_mapping.csv`.
- `data/manual/roster_overrides.csv` for announced-but-not-official moves
  (signed but not yet on API rosters). Manual layer wins over API layer.
- Player ELO continues to travel with the player. Nothing else needed for
  in-season trades once the mapping is live.

### 2. Season reset with reversion — Phase A, ~1 day
- FiveThirtyEight-standard: `new_elo = 0.75 * old_elo + 0.25 * 1505`.
- Applied once at season rollover before the first game.
- Backtest across our 25 seasons of history (2000–2025) to confirm the 75/25
  split on our data; Harvard Sports Analysis suggests the optimum is near there
  but we should fit it, not copy it.

### 3. Roster-delta preseason adjustment (fixes free agency) — Phase B, ~3 days
The reset above regresses everyone toward the mean equally. But we know MORE
than the mean: we have player ratings and we know who moved where.

- For each team: `delta = sum(arrivals' adjusted player value, minutes-weighted)
  - sum(departures' adjusted player value, minutes-weighted)`.
- Preseason team ELO = reset ELO + `beta * delta`, with `beta` fit by
  backtesting past offseasons (predict each season's October/November games
  with and without the adjustment; keep whatever beta minimizes log-loss).
- This is our version of what FiveThirtyEight's CARM-Elo did, built from the
  player layer we already maintain.
- **Content payoff:** the per-team `delta` IS the free-agency post series, and
  the fitted model becomes the September "preseason ratings reveal" numbers.

### 4. Rookie priors by draft slot — Phase B, ~2 days
- Reality check from history: rookies are usually below-average players. Fit
  average rookie-season BPM by draft slot from our 25 years of boxscores
  (roughly: top-5 picks ≈ -0.5 BPM, lottery ≈ -1.5, rest of first ≈ -2.0,
  second round ≈ -2.5; fit the actual curve, don't hardcode).
- Convert to player-ELO prior via the existing BPM→rating mapping.
- High uncertainty handling: rookies update at an elevated K (or
  low-games-played weighting) for their first ~20 games so real information
  displaces the prior quickly.
- Two-way/undrafted/unknown players: replacement-level prior (below 1500 —
  today's 1500 default silently calls every unknown an average NBA player,
  which is wrong and flattering).

### 5. Departures — Phase A (free with #1)
Players not on any current roster drop out of the mapping automatically at the
nightly refresh; ratings archive but stop contributing to team strength.

## Validation gates (non-negotiable, per analyst rules)
1. Every phase lands with a before/after backtest on 2024-25 + 2025-26.
2. Specifically measure **October/November accuracy** — that's the metric this
   whole design exists to move (and the one new subscribers will see).
3. qa-validator report after each phase before it reaches the VPS.

## Sequencing
| When | What |
|---|---|
| July wk 1–2 | Phase A: mapping automation, overrides file, 75/25 reset + backtest |
| July wk 3–4 | Phase B: roster-delta fit + rookie prior curve (doubles as FA content) |
| August | Phase C: integrate into daily pipeline on VPS; drift monitors extended to mapping freshness |
| September | Preseason ratings computed from the new machinery → 30-day content series |
