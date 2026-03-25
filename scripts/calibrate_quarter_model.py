"""
Quarter Score Model Calibration
================================
Trains 4 separate linear regression models (one per quarter) that map
ELO differential to expected quarter-level margin.

Follows the same pattern as calibrate_score_model.py.

Output: config/quarter_model.yaml
"""

import sys
import os
import pandas as pd
import numpy as np
import yaml

# Ensure engine root is on path
_engine_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _engine_root not in sys.path:
    sys.path.insert(0, _engine_root)

from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
QUARTER_CSV  = os.path.join(_engine_root, 'data', 'raw', 'nba_quarter_scores.csv')
ELO_HISTORY  = os.path.join(_engine_root, 'data', 'exports', 'team_elo_history_phase_1_6.csv')
OUTPUT_YAML  = os.path.join(_engine_root, 'config', 'quarter_model.yaml')


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
def load_quarter_scores() -> pd.DataFrame:
    df = pd.read_csv(QUARTER_CSV)
    # Normalize game_date to date string YYYY-MM-DD
    df['game_date'] = pd.to_datetime(df['game_date']).dt.strftime('%Y-%m-%d')
    return df


def load_elo_history() -> pd.DataFrame:
    df = pd.read_csv(ELO_HISTORY, low_memory=False)
    # date column is an integer like 20201222 — convert to YYYY-MM-DD string
    df['date_str'] = pd.to_datetime(df['date'].astype(str), format='%Y%m%d').dt.strftime('%Y-%m-%d')
    return df


# ---------------------------------------------------------------------------
# Join quarter scores to ELO ratings
# ---------------------------------------------------------------------------
def build_training_set(qdf: pd.DataFrame, edf: pd.DataFrame) -> pd.DataFrame:
    """
    For each game in qdf, look up the home team's ELO rating_before on game_date
    and the away team's ELO rating_before on game_date, then compute elo_diff.

    We join on (date_str, team_id) using only home game rows from the ELO history
    (is_home == True) to get the home team's ELO, then separately get the away
    team's ELO from rows where is_home == False.
    """
    # Build a lookup: (date_str, team_id) -> rating_before
    # We use ALL rows (home and away) because we may need either side
    elo_lookup = (
        edf[['date_str', 'team_id', 'team_name', 'rating_before']]
        .drop_duplicates(subset=['date_str', 'team_id'])
        .set_index(['date_str', 'team_id'])['rating_before']
    )

    # Build a mapping from 3-letter abbreviation to team_id
    # The ELO history has team_name (full name); quarter CSV has home_team_abbr
    # We need an abbrev -> team_id mapping.  Build it from the ELO history by
    # pulling the most recent row per team_id and matching against a known table.
    ABBREV_TO_ID = {
        'ATL': 1,  'BOS': 2,  'BKN': 17, 'CHA': 30, 'CHI': 4,
        'CLE': 5,  'DAL': 6,  'DEN': 7,  'DET': 8,  'GSW': 9,
        'HOU': 10, 'IND': 11, 'LAC': 12, 'LAL': 13, 'MEM': 29,
        'MIA': 14, 'MIL': 15, 'MIN': 16, 'NOP': 3,  'NYK': 18,
        'OKC': 25, 'ORL': 19, 'PHI': 20, 'PHX': 21, 'POR': 22,
        'SAC': 23, 'SAS': 24, 'TOR': 28, 'UTA': 26, 'WAS': 27,
        'WSH': 27, 'BRK': 17, 'NJN': 17, 'NOH': 3,  'NOK': 3,
        'SEA': 25, 'VAN': 16, 'CHH': 30, 'CHB': 4,
    }

    records = []
    for _, row in qdf.iterrows():
        date  = row['game_date']
        h_abbr = str(row['home_team_abbr']).strip().upper()
        a_abbr = str(row['away_team_abbr']).strip().upper()

        h_id = ABBREV_TO_ID.get(h_abbr)
        a_id = ABBREV_TO_ID.get(a_abbr)
        if h_id is None or a_id is None:
            continue  # unknown team code — skip

        try:
            h_elo = elo_lookup.loc[(date, h_id)]
        except KeyError:
            continue  # no ELO record for this team on this date — skip

        try:
            a_elo = elo_lookup.loc[(date, a_id)]
        except KeyError:
            continue

        records.append({
            'game_date': date,
            'home_team_abbr': h_abbr,
            'away_team_abbr': a_abbr,
            'home_elo': h_elo,
            'away_elo': a_elo,
            'elo_diff': h_elo - a_elo,
            'home_q1': row['home_q1'], 'away_q1': row['away_q1'],
            'home_q2': row['home_q2'], 'away_q2': row['away_q2'],
            'home_q3': row['home_q3'], 'away_q3': row['away_q3'],
            'home_q4': row['home_q4'], 'away_q4': row['away_q4'],
        })

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Distribution analysis
# ---------------------------------------------------------------------------
def analyze_distribution(df: pd.DataFrame):
    print(f"\n{'='*60}")
    print(f"  QUARTER SCORE DISTRIBUTION ANALYSIS")
    print(f"  Games available: {len(df):,}")
    print(f"{'='*60}")

    for side in ['home', 'away']:
        for q in [1, 2, 3, 4]:
            col = f'{side}_q{q}'
            vals = df[col]
            print(f"  {side.upper()} Q{q}: mean={vals.mean():.2f}  std={vals.std():.2f}  "
                  f"min={vals.min()}  max={vals.max()}")

    print()
    # Combined quarter averages (league avg per quarter)
    print("  League avg per quarter (home+away)/2:")
    for q in [1, 2, 3, 4]:
        combined = (df[f'home_q{q}'] + df[f'away_q{q}']) / 2
        print(f"    Q{q}: {combined.mean():.2f}  (std {combined.std():.2f})")

    # Pattern notes
    q4_avg = ((df['home_q4'] + df['away_q4']) / 2).mean()
    q1_avg = ((df['home_q1'] + df['away_q1']) / 2).mean()
    print(f"\n  Q4 vs Q1 delta: {q4_avg - q1_avg:+.2f} pts "
          f"({'Q4 higher as expected (FT pressure)' if q4_avg > q1_avg else 'Q1 higher — unusual'})")
    print()


# ---------------------------------------------------------------------------
# Fit per-quarter models
# ---------------------------------------------------------------------------
def fit_quarter_models(df: pd.DataFrame) -> dict:
    """Fit LinearRegression(q_margin ~ elo_diff) for Q1-Q4. Returns model dict."""
    results = {}
    print(f"  PER-QUARTER LINEAR REGRESSION (target: home_qN - away_qN ~ elo_diff)")
    print(f"  {'Quarter':<10} {'Intercept':>12} {'Coeff':>12} {'R2 train':>10} {'MAE train':>10}")
    print(f"  {'-'*10} {'-'*12} {'-'*12} {'-'*10} {'-'*10}")

    X = df[['elo_diff']].values

    for q in [1, 2, 3, 4]:
        y = (df[f'home_q{q}'] - df[f'away_q{q}']).values

        model = LinearRegression()
        model.fit(X, y)

        y_pred = model.predict(X)
        residuals = y - y_pred
        ss_res = (residuals ** 2).sum()
        ss_tot = ((y - y.mean()) ** 2).sum()
        r2  = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
        mae = mean_absolute_error(y, y_pred)

        league_avg = ((df[f'home_q{q}'] + df[f'away_q{q}']) / 2).mean()

        intercept  = float(model.intercept_)
        coeff      = float(model.coef_[0])

        print(f"  Q{q}         {intercept:>12.4f} {coeff:>12.6f} {r2:>10.4f} {mae:>10.4f}")

        results[f'q{q}'] = {
            'intercept':   round(intercept, 4),
            'coefficient': round(coeff, 6),
            'league_avg':  round(float(league_avg), 4),
            'train_r2':    round(float(r2), 4),
            'train_mae':   round(float(mae), 4),
        }

    print()
    return results


# ---------------------------------------------------------------------------
# Save YAML
# ---------------------------------------------------------------------------
def save_yaml(models: dict, n_games: int):
    config = {
        'quarter_model': {
            'q1': {
                'intercept':   models['q1']['intercept'],
                'coefficient': models['q1']['coefficient'],
                'league_avg':  models['q1']['league_avg'],
            },
            'q2': {
                'intercept':   models['q2']['intercept'],
                'coefficient': models['q2']['coefficient'],
                'league_avg':  models['q2']['league_avg'],
            },
            'q3': {
                'intercept':   models['q3']['intercept'],
                'coefficient': models['q3']['coefficient'],
                'league_avg':  models['q3']['league_avg'],
            },
            'q4': {
                'intercept':   models['q4']['intercept'],
                'coefficient': models['q4']['coefficient'],
                'league_avg':  models['q4']['league_avg'],
            },
            'calibration': {
                'train_games': n_games,
                'q1_r2':  models['q1']['train_r2'],
                'q1_mae': models['q1']['train_mae'],
                'q2_r2':  models['q2']['train_r2'],
                'q2_mae': models['q2']['train_mae'],
                'q3_r2':  models['q3']['train_r2'],
                'q3_mae': models['q3']['train_mae'],
                'q4_r2':  models['q4']['train_r2'],
                'q4_mae': models['q4']['train_mae'],
                'note':   'Preliminary — retrain after full backfill',
            }
        }
    }

    with open(OUTPUT_YAML, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(f"  Saved: {OUTPUT_YAML}")
    print()
    # Pretty-print the YAML for the report
    print("  config/quarter_model.yaml contents:")
    print("  " + "-"*50)
    with open(OUTPUT_YAML) as f:
        for line in f:
            print("  " + line, end='')
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("\nLoading data...")
    qdf = load_quarter_scores()
    edf = load_elo_history()

    print(f"  Quarter scores CSV: {len(qdf):,} rows")
    print(f"  ELO history:        {len(edf):,} rows")

    print("\nJoining quarter scores to ELO history...")
    train_df = build_training_set(qdf, edf)
    print(f"  Joined records:     {len(train_df):,} games")

    if len(train_df) == 0:
        print("\nERROR: No records after join. Check team abbreviation mapping or ELO history dates.")
        sys.exit(1)

    # Filter out games with missing/zero quarter values (data issues)
    for col in ['home_q1','home_q2','home_q3','home_q4','away_q1','away_q2','away_q3','away_q4']:
        train_df = train_df[train_df[col] > 0]
    print(f"  After filtering zero-quarter rows: {len(train_df):,} games")

    analyze_distribution(train_df)

    print(f"{'='*60}")
    models = fit_quarter_models(train_df)

    print(f"{'='*60}")
    save_yaml(models, n_games=len(train_df))
    print("  Done.")


if __name__ == '__main__':
    main()
