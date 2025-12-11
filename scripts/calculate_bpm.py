"""
Box Plus/Minus (BPM) Calculator
Calculates simplified BPM from player boxscore statistics.

Based on Basketball Reference methodology but simplified for available stats.
Formula focuses on per-possession contributions normalized to league average.

Usage:
    python scripts/calculate_bpm.py \
        --input data/raw/player_boxscores_all.csv \
        --output data/raw/player_boxscores_with_bpm.csv
"""

import pandas as pd
import numpy as np
import sys
import os
import argparse

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


def calculate_bpm(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate Box Plus/Minus (BPM) for each player game.

    Simplified BPM formula based on:
    - Scoring efficiency (points per shot)
    - Playmaking (assists)
    - Rebounding (total rebounds)
    - Defense (steals + blocks)
    - Ball security (turnovers - negative)
    - Efficiency (plus/minus correlation)

    Scale: ~-10 to +10 (league average = 0)

    Args:
        df: DataFrame with player boxscore stats

    Returns:
        DataFrame with added bpm, obpm, dbpm columns
    """
    logger.info("Calculating BPM for player boxscores...")

    # Create a copy to avoid modifying original
    result = df.copy()

    # Filter out DNP records (no minutes played)
    active_games = result['minutes'] > 0

    # Calculate per-minute statistics (normalized to 36 minutes)
    mins = result.loc[active_games, 'minutes']

    # Offensive components (per 36 minutes)
    pts_per_36 = (result.loc[active_games, 'points'] / mins) * 36
    ast_per_36 = (result.loc[active_games, 'assists'] / mins) * 36
    reb_per_36 = (result.loc[active_games, 'rebounds'] / mins) * 36
    to_per_36 = (result.loc[active_games, 'turnovers'] / mins) * 36

    # Defensive components (per 36 minutes)
    stl_per_36 = (result.loc[active_games, 'steals'] / mins) * 36
    blk_per_36 = (result.loc[active_games, 'blocks'] / mins) * 36

    # Shooting efficiency
    fg_made = result.loc[active_games, 'fg_made']
    fg_att = result.loc[active_games, 'fg_attempted']
    fg_pct = np.where(fg_att > 0, fg_made / fg_att, 0.45)  # Default to league avg if no shots

    # True shooting approximation (accounts for 3PT and FT value)
    pts = result.loc[active_games, 'points']
    fga = result.loc[active_games, 'fg_attempted']
    fta = result.loc[active_games, 'ft_attempted']
    ts_pct = np.where(
        (fga + 0.44 * fta) > 0,
        pts / (2 * (fga + 0.44 * fta)),
        0.55  # Default to league avg
    )

    # Simplified BPM formula (weights tuned to correlate with plus/minus)

    # Offensive BPM components
    scoring_value = (pts_per_36 - 15) * 0.12  # Above/below league avg ~15 pts/36
    efficiency_bonus = (ts_pct - 0.55) * 15   # TS% above/below league avg
    playmaking_value = (ast_per_36 - 3) * 0.6  # Assists above/below avg
    rebounding_value = (reb_per_36 - 7) * 0.3  # Rebounds above/below avg
    turnover_penalty = (to_per_36 - 2) * -0.8  # Turnovers penalty

    obpm = scoring_value + efficiency_bonus + playmaking_value + rebounding_value + turnover_penalty

    # Defensive BPM components (harder to measure from box score alone)
    steal_value = (stl_per_36 - 1.2) * 1.2    # Steals above/below avg
    block_value = (blk_per_36 - 0.8) * 1.0    # Blocks above/below avg
    def_reb_value = (result.loc[active_games, 'defensive_rebounds'] / mins * 36 - 5) * 0.2

    # Use plus/minus as a proxy for defensive impact not captured by stats
    pm_per_36 = (result.loc[active_games, 'plus_minus'] / mins) * 36
    pm_def_proxy = (pm_per_36 - obpm) * 0.3  # What's left after offense

    dbpm = steal_value + block_value + def_reb_value + pm_def_proxy

    # Total BPM
    bpm = obpm + dbpm

    # Clamp to reasonable range (-12 to +15, with most players -5 to +8)
    bpm = np.clip(bpm, -12, 15)
    obpm = np.clip(obpm, -10, 12)
    dbpm = np.clip(dbpm, -8, 8)

    # Assign to result DataFrame
    result.loc[active_games, 'bpm'] = bpm
    result.loc[active_games, 'obpm'] = obpm
    result.loc[active_games, 'dbpm'] = dbpm

    # For DNP games, set to 0
    result['bpm'] = result['bpm'].fillna(0.0)
    result['obpm'] = result['obpm'].fillna(0.0)
    result['dbpm'] = result['dbpm'].fillna(0.0)

    logger.info("BPM calculation complete!")

    return result


def validate_bpm(df: pd.DataFrame) -> None:
    """
    Validate BPM calculations and print summary statistics.

    Args:
        df: DataFrame with BPM calculations
    """
    logger.info("=" * 80)
    logger.info("BPM VALIDATION")
    logger.info("=" * 80)

    # Filter to games with minutes > 10 for meaningful stats
    significant_games = df[df['minutes'] >= 10].copy()

    logger.info(f"Total games: {len(df):,}")
    logger.info(f"Games with 10+ minutes: {len(significant_games):,}")

    # BPM statistics
    logger.info("\nBPM Statistics (10+ minute games):")
    logger.info(f"  Mean BPM: {significant_games['bpm'].mean():.3f}")
    logger.info(f"  Median BPM: {significant_games['bpm'].median():.3f}")
    logger.info(f"  Std Dev: {significant_games['bpm'].std():.3f}")
    logger.info(f"  Min: {significant_games['bpm'].min():.3f}")
    logger.info(f"  Max: {significant_games['bpm'].max():.3f}")

    logger.info("\nOffensive BPM:")
    logger.info(f"  Mean OBPM: {significant_games['obpm'].mean():.3f}")
    logger.info(f"  Std Dev: {significant_games['obpm'].std():.3f}")

    logger.info("\nDefensive BPM:")
    logger.info(f"  Mean DBPM: {significant_games['dbpm'].mean():.3f}")
    logger.info(f"  Std Dev: {significant_games['dbpm'].std():.3f}")

    # Correlation with plus/minus
    correlation = significant_games[['bpm', 'plus_minus']].corr().iloc[0, 1]
    logger.info(f"\nCorrelation with plus/minus: {correlation:.3f}")

    # Top 20 BPM performances
    logger.info("\nTop 20 BPM Performances (Single Game, 10+ min):")
    top_20 = significant_games.nlargest(20, 'bpm')[
        ['player_name', 'team_name', 'bpm', 'obpm', 'dbpm', 'minutes', 'points', 'assists', 'rebounds', 'plus_minus']
    ]

    for idx, game in top_20.iterrows():
        logger.info(
            f"  {game['player_name']:<25} {game['team_name']:<20} "
            f"BPM: {game['bpm']:>6.1f} (O: {game['obpm']:>5.1f}, D: {game['dbpm']:>5.1f}) | "
            f"{game['points']:.0f}pts {game['assists']:.0f}ast {game['rebounds']:.0f}reb | "
            f"{game['minutes']:.0f}min +/- {game['plus_minus']:+.0f}"
        )

    # Distribution by BPM tier
    logger.info("\nBPM Distribution (10+ minute games):")
    elite = len(significant_games[significant_games['bpm'] >= 8])
    excellent = len(significant_games[(significant_games['bpm'] >= 5) & (significant_games['bpm'] < 8)])
    good = len(significant_games[(significant_games['bpm'] >= 2) & (significant_games['bpm'] < 5)])
    average = len(significant_games[(significant_games['bpm'] >= -2) & (significant_games['bpm'] < 2)])
    below = len(significant_games[(significant_games['bpm'] >= -5) & (significant_games['bpm'] < -2)])
    poor = len(significant_games[significant_games['bpm'] < -5])

    total = len(significant_games)
    logger.info(f"  Elite (8+):       {elite:>7,} ({elite/total*100:>5.1f}%)")
    logger.info(f"  Excellent (5-8):  {excellent:>7,} ({excellent/total*100:>5.1f}%)")
    logger.info(f"  Good (2-5):       {good:>7,} ({good/total*100:>5.1f}%)")
    logger.info(f"  Average (-2-2):   {average:>7,} ({average/total*100:>5.1f}%)")
    logger.info(f"  Below (-5--2):    {below:>7,} ({below/total*100:>5.1f}%)")
    logger.info(f"  Poor (<-5):       {poor:>7,} ({poor/total*100:>5.1f}%)")

    logger.info("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Calculate Box Plus/Minus for player boxscores')
    parser.add_argument('--input', default='data/raw/player_boxscores_all.csv',
                       help='Input player boxscores CSV')
    parser.add_argument('--output', default='data/raw/player_boxscores_with_bpm.csv',
                       help='Output CSV with BPM calculations')

    args = parser.parse_args()

    # Load boxscores
    logger.info(f"Loading player boxscores from {args.input}...")
    df = pd.read_csv(args.input)
    logger.info(f"Loaded {len(df):,} boxscore records")

    # Calculate BPM
    df_with_bpm = calculate_bpm(df)

    # Validate results
    validate_bpm(df_with_bpm)

    # Save results
    logger.info(f"\nSaving results to {args.output}...")
    df_with_bpm.to_csv(args.output, index=False)

    file_size_mb = os.path.getsize(args.output) / 1024 / 1024
    logger.info(f"Saved {len(df_with_bpm):,} records ({file_size_mb:.1f} MB)")

    logger.info("\nBPM calculation complete!")


if __name__ == "__main__":
    main()
