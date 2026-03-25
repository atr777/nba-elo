"""
Score Model Calibration
=======================
Trains a linear regression: actual_margin (home - away) ~ elo_diff

Saves coefficients to config/score_model.yaml.

Usage:
    cd nba-elo-engine
    python scripts/calibrate_score_model.py
"""

import sys
import os
import yaml
import pandas as pd
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

GAMES_CSV        = 'data/raw/nba_games_all.csv'
ELO_HISTORY_CSV  = 'data/exports/team_elo_history_phase_1_6.csv'
CONFIG_OUT       = 'config/score_model.yaml'

# Train on everything before 2024-25 season; evaluate on 2024-25.
HOLDOUT_START    = 20241001   # first day of 2024-25 season


def build_dataset(games: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    """
    Join games to pre-game ELO for each team and compute elo_diff + actual_margin.

    elo_diff  = home rating_before - away rating_before
    actual_margin = home_score - away_score
    """
    # Only completed regular-season games with valid scores
    games = games[
        (games['season_type'] == 'regular') &
        (games['home_score'] > 0) &
        (games['away_score'] > 0)
    ].copy()

    # Home rows from history
    home_hist = history[history['is_home'] == True][
        ['game_id', 'date', 'team_id', 'rating_before']
    ].rename(columns={'team_id': 'home_team_id', 'rating_before': 'home_elo_before'})

    # Away rows from history
    away_hist = history[history['is_home'] == False][
        ['game_id', 'team_id', 'rating_before']
    ].rename(columns={'team_id': 'away_team_id', 'rating_before': 'away_elo_before'})

    # Merge
    df = games.merge(home_hist, on=['game_id', 'date', 'home_team_id'], how='inner')
    df = df.merge(away_hist, on=['game_id', 'away_team_id'], how='inner')

    df['elo_diff']      = df['home_elo_before'] - df['away_elo_before']
    df['actual_margin'] = df['home_score'] - df['away_score']

    return df[['game_id', 'date', 'home_team_id', 'away_team_id',
               'home_score', 'away_score', 'elo_diff', 'actual_margin']].copy()


def fit_linear(X: np.ndarray, y: np.ndarray):
    """Ordinary least squares via closed-form solution."""
    # Design matrix: [1, X]
    A = np.column_stack([np.ones(len(X)), X])
    # (A^T A)^{-1} A^T y
    coef = np.linalg.lstsq(A, y, rcond=None)[0]
    intercept, slope = coef[0], coef[1]
    return intercept, slope


def evaluate(X: np.ndarray, y: np.ndarray, intercept: float, slope: float):
    y_pred = intercept + slope * X
    residuals = y - y_pred
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2  = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    mae = np.mean(np.abs(residuals))
    return r2, mae, y_pred


def main():
    print("=" * 60)
    print("Score Model Calibration")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Load data
    # ------------------------------------------------------------------
    print("\nLoading games data...")
    games   = pd.read_csv(GAMES_CSV)
    print(f"  {len(games):,} total game rows")

    print("Loading ELO history...")
    history = pd.read_csv(ELO_HISTORY_CSV)
    print(f"  {len(history):,} history rows")

    # ------------------------------------------------------------------
    # Build joint dataset
    # ------------------------------------------------------------------
    print("\nBuilding calibration dataset...")
    df = build_dataset(games, history)
    print(f"  {len(df):,} games with both ELO history and scores")

    # ------------------------------------------------------------------
    # Train / holdout split
    # ------------------------------------------------------------------
    train = df[df['date'] <  HOLDOUT_START]
    hold  = df[df['date'] >= HOLDOUT_START]
    print(f"  Training games (pre-2024-25): {len(train):,}")
    print(f"  Holdout games  (2024-25):     {len(hold):,}")

    X_train = train['elo_diff'].values
    y_train = train['actual_margin'].values

    X_hold  = hold['elo_diff'].values
    y_hold  = hold['actual_margin'].values

    # ------------------------------------------------------------------
    # Fit linear regression on training set
    # ------------------------------------------------------------------
    print("\nFitting linear regression (margin ~ intercept + coefficient * elo_diff)...")
    intercept, slope = fit_linear(X_train, y_train)
    print(f"  intercept  = {intercept:.4f}  (home court PPG advantage baseline)")
    print(f"  coefficient= {slope:.6f}  (PPG per ELO point)")

    # ------------------------------------------------------------------
    # Training set evaluation
    # ------------------------------------------------------------------
    r2_train, mae_train, _ = evaluate(X_train, y_train, intercept, slope)
    print(f"\nTraining set performance:")
    print(f"  R²  = {r2_train:.4f}")
    print(f"  MAE = {mae_train:.2f} points")

    # ------------------------------------------------------------------
    # Holdout set evaluation
    # ------------------------------------------------------------------
    if len(hold) > 0:
        r2_hold, mae_hold, _ = evaluate(X_hold, y_hold, intercept, slope)
        print(f"\nHoldout set (2024-25) performance:")
        print(f"  R²  = {r2_hold:.4f}")
        print(f"  MAE = {mae_hold:.2f} points")
    else:
        print("\nNo holdout games found.")
        r2_hold, mae_hold = 0.0, 0.0

    # ------------------------------------------------------------------
    # League-average PPG (2024-25 season only, or last 3 seasons if sparse)
    # ------------------------------------------------------------------
    recent = games[
        (games['season_type'] == 'regular') &
        (games['date'] >= HOLDOUT_START) &
        (games['home_score'] > 0)
    ]
    if len(recent) >= 50:
        all_scores = pd.concat([recent['home_score'], recent['away_score']])
        league_avg_ppg = float(all_scores.mean())
        print(f"\nLeague average PPG (2024-25, {len(recent)} games): {league_avg_ppg:.2f}")
    else:
        # Fall back to last 3 seasons
        recent_3yr = games[
            (games['season_type'] == 'regular') &
            (games['date'] >= 20211001) &
            (games['home_score'] > 0)
        ]
        all_scores = pd.concat([recent_3yr['home_score'], recent_3yr['away_score']])
        league_avg_ppg = float(all_scores.mean())
        print(f"\nLeague average PPG (3-year fallback, {len(recent_3yr)} games): {league_avg_ppg:.2f}")

    # ------------------------------------------------------------------
    # Sanity check: sample predictions
    # ------------------------------------------------------------------
    print("\nSample predictions from holdout:")
    print(f"{'ELO diff':>10}  {'Pred margin':>12}  {'Actual margin':>14}")
    print("-" * 40)
    sample_idx = [0, len(hold)//4, len(hold)//2, 3*len(hold)//4, len(hold)-1]
    for i in sample_idx:
        if i < len(hold):
            ed = X_hold[i]
            actual = y_hold[i]
            pred = intercept + slope * ed
            print(f"{ed:>10.1f}  {pred:>12.1f}  {actual:>14.1f}")

    # ------------------------------------------------------------------
    # Save to config/score_model.yaml
    # ------------------------------------------------------------------
    config_data = {
        'score_model': {
            'intercept':      round(float(intercept), 4),
            'coefficient':    round(float(slope), 6),
            'league_avg_ppg': round(league_avg_ppg, 2),
            'calibration': {
                'train_r2':   round(float(r2_train), 4),
                'train_mae':  round(float(mae_train), 2),
                'holdout_r2': round(float(r2_hold), 4),
                'holdout_mae': round(float(mae_hold), 2),
                'train_games': int(len(train)),
                'holdout_games': int(len(hold)),
            }
        }
    }

    os.makedirs(os.path.dirname(CONFIG_OUT), exist_ok=True)
    with open(CONFIG_OUT, 'w') as f:
        yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

    print(f"\nCoefficients saved to: {CONFIG_OUT}")
    print("\nSummary:")
    print(f"  intercept  = {intercept:.4f}")
    print(f"  coefficient= {slope:.6f}")
    print(f"  league_avg_ppg = {league_avg_ppg:.2f}")
    print(f"  Holdout R² = {r2_hold:.4f}  |  Holdout MAE = {mae_hold:.2f} pts")
    print()
    print("Example predictions using these coefficients:")
    for ed in [-200, -100, 0, 50, 100, 200]:
        margin = intercept + slope * ed
        home_score = round(league_avg_ppg + margin / 2)
        away_score = round(league_avg_ppg - margin / 2)
        home_score = max(70, home_score)
        away_score = max(70, away_score)
        print(f"  ELO diff {ed:>+5}: margin={margin:>+6.1f}  predicted={home_score}–{away_score}")


if __name__ == '__main__':
    main()
