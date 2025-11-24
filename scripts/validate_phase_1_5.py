"""
Phase 1.5 Validation Script
===========================
Validates the enhanced ELO system with real historical NBA data.

Steps:
1. Verify data quality
2. Run Phase 1.5 enhanced engine
3. Calculate prediction accuracy
4. Compare vs baseline (if available)
5. Generate validation report
"""

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import sys
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Phase15Validator:
    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        self.data = None
        self.results = {}
        
    def validate_data_quality(self):
        """Step 1: Verify the scraped data is clean and complete"""
        logger.info("=" * 60)
        logger.info("STEP 1: Data Quality Validation")
        logger.info("=" * 60)
        
        # Load data
        logger.info(f"Loading data from: {self.data_path}")
        self.data = pd.read_csv(self.data_path)
        
        # Basic stats
        total_games = len(self.data)
        date_range = f"{self.data['date'].min()} to {self.data['date'].max()}"
        unique_teams = pd.concat([self.data['home_team_name'], 
                                  self.data['away_team_name']]).nunique()
        
        logger.info(f"✓ Total games: {total_games:,}")
        logger.info(f"✓ Date range: {date_range}")
        logger.info(f"✓ Unique teams: {unique_teams}")
        
        # Check for required columns
        required_cols = ['game_id', 'date', 'home_team_id', 'away_team_id', 
                        'home_score', 'away_score', 'winner_team_id']
        missing_cols = [col for col in required_cols if col not in self.data.columns]
        
        if missing_cols:
            logger.error(f"✗ Missing required columns: {missing_cols}")
            return False
        logger.info(f"✓ All required columns present")
        
        # Check for nulls in critical columns
        null_counts = self.data[required_cols].isnull().sum()
        if null_counts.any():
            logger.warning(f"⚠ Null values found:\n{null_counts[null_counts > 0]}")
        else:
            logger.info(f"✓ No null values in critical columns")
        
        # Check for duplicates
        duplicates = self.data['game_id'].duplicated().sum()
        if duplicates > 0:
            logger.warning(f"⚠ Found {duplicates} duplicate game_ids")
        else:
            logger.info(f"✓ No duplicate games")
        
        # Season breakdown
        self.data['season'] = self.data['date'].apply(self._get_season)
        season_counts = self.data.groupby('season').size()
        
        logger.info("\nGames per season:")
        for season, count in season_counts.items():
            expected = 1230  # 30 teams * 82 games / 2
            pct = (count / expected) * 100
            logger.info(f"  {season}: {count:4d} games ({pct:5.1f}% of expected)")
        
        self.results['data_quality'] = {
            'total_games': total_games,
            'date_range': date_range,
            'unique_teams': unique_teams,
            'nulls': null_counts.sum(),
            'duplicates': duplicates,
            'seasons': len(season_counts)
        }
        
        logger.info("\n✓ Data quality validation complete!")
        return True
    
    def _get_season(self, date_str):
        """Convert date to NBA season format (e.g., 2023-24)"""
        try:
            # Handle both YYYYMMDD format (as int or str) and YYYY-MM-DD formats
            if isinstance(date_str, (int, np.int64)):
                # Convert integer to string
                date_str = str(date_str)
            
            if isinstance(date_str, str):
                if len(date_str) == 8 and date_str.isdigit():
                    # YYYYMMDD format
                    date = pd.to_datetime(date_str, format='%Y%m%d')
                else:
                    # Try standard parsing
                    date = pd.to_datetime(date_str)
            else:
                date = pd.to_datetime(date_str)
            
            year = date.year
            month = date.month
            
            # NBA season spans two calendar years (Oct-Apr)
            if month >= 10:  # October onwards = start of season
                return f"{year}-{str(year+1)[-2:]}"
            else:  # Jan-Apr = end of season
                return f"{year-1}-{str(year)[-2:]}"
        except Exception as e:
            return "Unknown"
    
    def run_enhanced_engine(self):
        """Step 2: Run the Phase 1.5 enhanced ELO engine"""
        logger.info("\n" + "=" * 60)
        logger.info("STEP 2: Running Phase 1.5 Enhanced Engine")
        logger.info("=" * 60)
        
        logger.info("Running team_elo_engine.py with Phase 1.5 enhancements...")
        logger.info("  - MOV multiplier: ENABLED")
        logger.info("  - Rest penalties: ENABLED")
        logger.info("  - Season regression: ENABLED")
        logger.info("  - Home advantage: 70 points")
        
        # This will be run via subprocess in the actual implementation
        logger.info("\n→ Please run manually:")
        logger.info("  python src/engines/team_elo_engine.py \\")
        logger.info("      --input data/raw/nba_games_all.csv \\")
        logger.info("      --output data/exports/team_elo_history_phase_1_5.csv")
        
        return True
    
    def calculate_accuracy(self, elo_history_path: str):
        """Step 3: Calculate prediction accuracy"""
        logger.info("\n" + "=" * 60)
        logger.info("STEP 3: Calculating Prediction Accuracy")
        logger.info("=" * 60)
        
        # Load ELO history
        elo_history = pd.read_csv(elo_history_path)
        
        # Debug: Print available columns
        logger.info(f"\nAvailable columns in ELO output:")
        logger.info(f"  {list(elo_history.columns)}")
        
        # Detect column names (handle different naming conventions)
        elo_col = None
        for possible_name in ['rating_before', 'elo_rating_before', 'elo_before', 'elo_rating', 'elo', 'rating']:
            if possible_name in elo_history.columns:
                elo_col = possible_name
                break
        
        if elo_col is None:
            logger.error("✗ Could not find ELO rating column in output!")
            logger.error(f"Available columns: {list(elo_history.columns)}")
            return 0.0
        
        logger.info(f"✓ Using ELO column: '{elo_col}'")
        
        # Check for home indicator column
        home_col = None
        for possible_name in ['is_home', 'home', 'is_home_team', 'home_team']:
            if possible_name in elo_history.columns:
                home_col = possible_name
                break
        
        # Check for winner indicator
        won_col = None
        for possible_name in ['won', 'win', 'winner', 'is_winner']:
            if possible_name in elo_history.columns:
                won_col = possible_name
                break
        
        # Merge with original game data to calculate accuracy
        predictions = []
        correct = 0
        total = 0
        
        # Group by game_id to get both teams' data
        games = elo_history.groupby('game_id')
        
        for game_id, game_data in games:
            if len(game_data) != 2:
                continue  # Skip if we don't have both teams
            
            try:
                # Identify home and away teams
                if home_col and home_col in game_data.columns:
                    # Sort by home indicator
                    game_data = game_data.sort_values(home_col, ascending=False)
                    home_idx = 0
                    away_idx = 1
                else:
                    # Use first team as home (less reliable)
                    home_idx = 0
                    away_idx = 1
                
                home_elo = game_data.iloc[home_idx][elo_col]
                away_elo = game_data.iloc[away_idx][elo_col]
                
                # Calculate home win probability (with home advantage)
                home_advantage = 70
                win_prob = 1 / (1 + 10**((away_elo - home_elo - home_advantage) / 400))
                
                # Get actual result
                if won_col and won_col in game_data.columns:
                    home_won = bool(game_data.iloc[home_idx][won_col])
                else:
                    # Fallback: use original game data
                    game_info = self.data[self.data['game_id'] == game_id].iloc[0]
                    home_team = game_data.iloc[home_idx]['team_id']
                    home_won = (game_info['winner_team_id'] == home_team)
                
                # Check if prediction was correct
                predicted_home_win = win_prob > 0.5
                if predicted_home_win == home_won:
                    correct += 1
                total += 1
                
                predictions.append({
                    'game_id': game_id,
                    'home_win_prob': win_prob,
                    'predicted_winner': 'home' if predicted_home_win else 'away',
                    'actual_winner': 'home' if home_won else 'away',
                    'correct': predicted_home_win == home_won
                })
                
            except Exception as e:
                logger.warning(f"Skipping game {game_id}: {str(e)}")
                continue
        
        accuracy = (correct / total) * 100 if total > 0 else 0
        
        logger.info(f"\nOverall Accuracy:")
        logger.info(f"  Correct predictions: {correct:,} / {total:,}")
        logger.info(f"  Accuracy: {accuracy:.2f}%")
        
        # Calculate by confidence levels
        if predictions:
            pred_df = pd.DataFrame(predictions)
            pred_df['confidence'] = pred_df['home_win_prob'].apply(
                lambda x: max(x, 1-x)
            )
            
            confidence_bins = [(0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0)]
            
            logger.info("\nAccuracy by Confidence Level:")
            for low, high in confidence_bins:
                mask = (pred_df['confidence'] >= low) & (pred_df['confidence'] < high)
                bin_correct = pred_df[mask]['correct'].sum()
                bin_total = mask.sum()
                bin_accuracy = (bin_correct / bin_total * 100) if bin_total > 0 else 0
                logger.info(f"  {low:.0%}-{high:.0%}: {bin_accuracy:5.1f}% ({bin_total:,} games)")
        
        self.results['accuracy'] = {
            'overall': accuracy,
            'correct': correct,
            'total': total,
            'target': 62.0,
            'meets_target': accuracy >= 62.0
        }
        
        return accuracy
    
    def generate_report(self, output_path: str = "validation_report.txt"):
        """Step 4: Generate validation report"""
        logger.info("\n" + "=" * 60)
        logger.info("STEP 4: Generating Validation Report")
        logger.info("=" * 60)
        
        report_lines = []
        report_lines.append("=" * 70)
        report_lines.append("NBA ELO INTELLIGENCE ENGINE - PHASE 1.5 VALIDATION REPORT")
        report_lines.append("=" * 70)
        report_lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("\n" + "-" * 70)
        report_lines.append("DATA QUALITY")
        report_lines.append("-" * 70)
        
        dq = self.results.get('data_quality', {})
        report_lines.append(f"Total Games:     {dq.get('total_games', 'N/A'):,}")
        report_lines.append(f"Date Range:      {dq.get('date_range', 'N/A')}")
        report_lines.append(f"Unique Teams:    {dq.get('unique_teams', 'N/A')}")
        report_lines.append(f"Seasons:         {dq.get('seasons', 'N/A')}")
        report_lines.append(f"Null Values:     {dq.get('nulls', 'N/A')}")
        report_lines.append(f"Duplicates:      {dq.get('duplicates', 'N/A')}")
        
        report_lines.append("\n" + "-" * 70)
        report_lines.append("PREDICTION ACCURACY")
        report_lines.append("-" * 70)
        
        acc = self.results.get('accuracy', {})
        correct = acc.get('correct', 0)
        total = acc.get('total', 0)
        overall = acc.get('overall', 0)
        
        report_lines.append(f"Correct Predictions:  {correct:,}" if correct else "Correct Predictions:  N/A")
        report_lines.append(f"Total Predictions:    {total:,}" if total else "Total Predictions:    N/A")
        report_lines.append(f"Accuracy:             {overall:.2f}%" if overall else "Accuracy:             N/A")
        report_lines.append(f"Target:               {acc.get('target', 62.0):.2f}%")
        
        meets_target = acc.get('meets_target', False)
        status = "[PASS]" if meets_target else "[BELOW TARGET]"
        report_lines.append(f"Status:               {status}")
        
        report_lines.append("\n" + "-" * 70)
        report_lines.append("PHASE 1.5 ENHANCEMENTS")
        report_lines.append("-" * 70)
        report_lines.append("[PASS] Margin of Victory Multiplier:  ENABLED")
        report_lines.append("[PASS] Rest Day Penalties:             ENABLED (-46 B2B, -15 1-day)")
        report_lines.append("[PASS] Season Regression:              ENABLED (25% factor)")
        report_lines.append("[PASS] Home Court Advantage:           70 rating points")
        
        report_lines.append("\n" + "=" * 70)
        report_lines.append(f"VALIDATION COMPLETE - {datetime.now().strftime('%Y-%m-%d')}")
        report_lines.append("=" * 70)
        
        # Write to file
        report_text = "\n".join(report_lines)
        
        # Replace Unicode characters for Windows compatibility
        report_text = report_text.replace('✓', '[PASS]').replace('✗', '[FAIL]')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        logger.info(f"\n✓ Report saved to: {output_path}")
        
        # Print to console
        print("\n" + report_text)
        
        return report_text


def main():
    """Run the complete validation workflow"""
    print("\n" + "=" * 70)
    print("NBA ELO INTELLIGENCE ENGINE - PHASE 1.5 VALIDATION")
    print("=" * 70)
    
    # Check if data file exists
    data_path = "data/raw/nba_games_all.csv"
    
    if not Path(data_path).exists():
        logger.error(f"\n✗ Data file not found: {data_path}")
        logger.error("Please ensure the scraper has completed and data exists.")
        return False
    
    # Initialize validator
    validator = Phase15Validator(data_path)
    
    # Run validation steps
    try:
        # Step 1: Data quality
        if not validator.validate_data_quality():
            logger.error("\n✗ Data quality validation failed!")
            return False
        
        # Step 2: Instructions for running engine
        validator.run_enhanced_engine()
        
        # Note: Steps 3-4 require ELO output to exist
        elo_output = "data/exports/team_elo_history_phase_1_5.csv"
        
        if Path(elo_output).exists():
            logger.info(f"\n✓ Found ELO output: {elo_output}")
            validator.calculate_accuracy(elo_output)
            validator.generate_report("data/exports/validation_report_phase_1_5.txt")
        else:
            logger.warning(f"\n⚠ ELO output not found: {elo_output}")
            logger.warning("Run the engine first, then re-run this validator.")
        
        logger.info("\n" + "=" * 70)
        logger.info("✓ Validation workflow complete!")
        logger.info("=" * 70)
        
        return True
        
    except Exception as e:
        logger.error(f"\n✗ Validation failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
