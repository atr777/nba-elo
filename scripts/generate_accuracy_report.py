"""
Generate accuracy reports for ELO predictions with adjusted player ratings.

Reports:
1. Overall accuracy across all historical games
2. Last 5 days accuracy (most recent performance)
"""

import pandas as pd
import sys
from datetime import datetime, timedelta

# Fix encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 80)
print("ELO MODEL ACCURACY REPORT")
print("With Player Rating Adjustments (0.80x rim protectors, 1.10x scorers)")
print("=" * 80)

# Load predictions data
predictions_df = pd.read_csv('data/exports/enhanced_features_predictions.csv')

# Convert date to datetime
predictions_df['date'] = pd.to_datetime(predictions_df['date'], format='%Y%m%d')

print(f"\nTotal games with predictions: {len(predictions_df)}")

# OVERALL ACCURACY
print("\n" + "=" * 80)
print("OVERALL ACCURACY (All Games)")
print("=" * 80)

total_games = len(predictions_df)
correct_predictions = predictions_df['correct'].sum()
overall_accuracy = (correct_predictions / total_games) * 100

print(f"\nTotal Games Analyzed: {total_games:,}")
print(f"Correct Predictions: {correct_predictions:,}")
print(f"Overall Accuracy: {overall_accuracy:.2f}%")

# Get date range
min_date = predictions_df['date'].min()
max_date = predictions_df['date'].max()
print(f"\nDate Range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")
print(f"Duration: {(max_date - min_date).days} days")

# Calculate average win probability for correct vs incorrect predictions
correct_df = predictions_df[predictions_df['correct'] == True]
incorrect_df = predictions_df[predictions_df['correct'] == False]

avg_prob_correct = correct_df['home_prob'].mean() if len(correct_df) > 0 else 0
avg_prob_incorrect = incorrect_df['home_prob'].mean() if len(incorrect_df) > 0 else 0

print(f"\nAverage confidence (win probability):")
print(f"  Correct predictions: {avg_prob_correct:.1%}")
print(f"  Incorrect predictions: {abs(1 - avg_prob_incorrect):.1%}")

# LAST 5 DAYS ACCURACY
print("\n" + "=" * 80)
print("LAST 5 DAYS ACCURACY (Recent Performance)")
print("=" * 80)

# Calculate cutoff date (5 days ago from most recent game)
cutoff_date = max_date - timedelta(days=5)
recent_df = predictions_df[predictions_df['date'] >= cutoff_date].copy()

print(f"\nDate Range: {cutoff_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")

if len(recent_df) > 0:
    recent_total = len(recent_df)
    recent_correct = recent_df['correct'].sum()
    recent_accuracy = (recent_correct / recent_total) * 100

    print(f"\nTotal Games Analyzed: {recent_total}")
    print(f"Correct Predictions: {recent_correct}")
    print(f"Accuracy: {recent_accuracy:.2f}%")

    # Compare to overall
    diff = recent_accuracy - overall_accuracy
    trend = "better" if diff > 0 else "worse"
    print(f"\nComparison to overall: {diff:+.2f}% ({trend})")
else:
    print("\nNo games found in the last 5 days")

# ACCURACY BY CONFIDENCE LEVEL
print("\n" + "=" * 80)
print("ACCURACY BY CONFIDENCE LEVEL")
print("=" * 80)

# Calculate confidence as the probability of the predicted winner
predictions_df['confidence'] = predictions_df.apply(
    lambda row: row['home_prob'] if row['prediction'] else (1 - row['home_prob']),
    axis=1
)

# Create bins
bins = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]
labels = ['50-55%', '55-60%', '60-65%', '65-70%', '70-75%', '75-80%', '80-85%', '85-90%', '90-95%', '95-100%']

predictions_df['confidence_bin'] = pd.cut(
    predictions_df['confidence'],
    bins=bins,
    labels=labels,
    include_lowest=True
)

print("\n{:>12} | {:>8} | {:>10}".format("Confidence", "Games", "Accuracy"))
print("-" * 40)

for label in labels:
    bin_df = predictions_df[predictions_df['confidence_bin'] == label]
    if len(bin_df) > 0:
        bin_accuracy = (bin_df['correct'].sum() / len(bin_df)) * 100
        print("{:>12} | {:>8} | {:>9.2f}%".format(label, len(bin_df), bin_accuracy))

# ACCURACY BY SEASON
print("\n" + "=" * 80)
print("ACCURACY BY SEASON (Last 5 Seasons)")
print("=" * 80)

# Extract season (assuming season changes in October)
predictions_df['year'] = predictions_df['date'].dt.year
predictions_df['month'] = predictions_df['date'].dt.month

# Season is the year in which it started (Oct-Sep)
predictions_df['season'] = predictions_df.apply(
    lambda row: row['year'] if row['month'] >= 10 else row['year'] - 1,
    axis=1
)

# Get last 5 seasons
recent_seasons = sorted(predictions_df['season'].unique())[-5:]

print("\n{:>10} | {:>8} | {:>10}".format("Season", "Games", "Accuracy"))
print("-" * 40)

for season in recent_seasons:
    season_df = predictions_df[predictions_df['season'] == season]
    if len(season_df) > 0:
        season_accuracy = (season_df['correct'].sum() / len(season_df)) * 100
        season_label = f"{season}-{str(season+1)[-2:]}"
        print("{:>10} | {:>8} | {:>9.2f}%".format(season_label, len(season_df), season_accuracy))

# LAST 30 DAYS TREND
print("\n" + "=" * 80)
print("ACCURACY TREND (Last 30 Days)")
print("=" * 80)

cutoff_30_days = max_date - timedelta(days=30)
last_30_days = predictions_df[predictions_df['date'] >= cutoff_30_days].copy()

if len(last_30_days) > 0:
    # Group by week
    last_30_days['week'] = last_30_days['date'].dt.to_period('W')
    weekly_accuracy = last_30_days.groupby('week').agg({
        'correct': ['sum', 'count']
    })
    weekly_accuracy.columns = ['correct', 'total']
    weekly_accuracy['accuracy'] = (weekly_accuracy['correct'] / weekly_accuracy['total']) * 100

    print("\n{:>15} | {:>8} | {:>10}".format("Week", "Games", "Accuracy"))
    print("-" * 45)

    for week, row in weekly_accuracy.tail(4).iterrows():
        week_str = f"{week.start_time.strftime('%m/%d')}-{week.end_time.strftime('%m/%d')}"
        print("{:>15} | {:>8} | {:>9.2f}%".format(
            week_str,
            int(row['total']),
            row['accuracy']
        ))

# SUMMARY
print("\n" + "=" * 80)
print("SUMMARY & RECOMMENDATIONS")
print("=" * 80)

print("\nModel Performance:")
print(f"  - Overall accuracy: {overall_accuracy:.2f}%")
if len(recent_df) > 0:
    print(f"  - Recent accuracy (5 days): {recent_accuracy:.2f}%")
    print(f"  - Trend: {trend} than overall by {abs(diff):.2f}%")

# Confidence calibration
high_conf = predictions_df[predictions_df['confidence'] >= 0.7]
if len(high_conf) > 0:
    high_conf_accuracy = (high_conf['correct'].sum() / len(high_conf)) * 100
    print(f"  - Accuracy on high-confidence picks (>=70%): {high_conf_accuracy:.2f}%")

print("\nPlayer Rating Adjustments Applied:")
print("  - Rim Protectors (0.80x): Rudy Gobert, Jarrett Allen, etc.")
print("  - Elite Scorers (1.10x): Stephen Curry, Kevin Durant, etc.")

print("\nNote:")
print("  This accuracy report is based on the enhanced ELO model with form,")
print("  rest, and margin of victory adjustments. The player rating adjustments")
print("  improve the quality of individual player impact calculations.")

print("\n" + "=" * 80)
print("REPORT COMPLETE")
print("=" * 80)
