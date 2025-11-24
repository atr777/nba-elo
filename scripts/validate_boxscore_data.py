"""
Box Score Data Validator
=========================
Validate player box score data quality before Phase 3 Player ELO implementation

USAGE:
    python validate_boxscore_data.py player_boxscores_all.csv
"""

import pandas as pd
import sys
from pathlib import Path


class BoxScoreValidator:
    """Validate box score data structure and quality"""
    
    def __init__(self, csv_path):
        """Load and validate box score data"""
        self.csv_path = csv_path
        self.df = None
        self.issues = []
        self.warnings = []
        
    def load_data(self):
        """Load CSV file"""
        try:
            self.df = pd.read_csv(self.csv_path)
            print(f"✓ Loaded {len(self.df):,} records from {self.csv_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to load file: {e}")
            return False
    
    def check_required_columns(self):
        """Verify all required columns exist"""
        required = [
            'game_id', 'player_id', 'player_name',
            'team_id', 'team_name', 'minutes', 'starter'
        ]
        
        missing = [col for col in required if col not in self.df.columns]
        
        if missing:
            self.issues.append(f"Missing required columns: {missing}")
            return False
        
        print(f"✓ All required columns present")
        return True
    
    def check_data_types(self):
        """Validate data types"""
        checks = []
        
        # Minutes should be numeric
        if not pd.api.types.is_numeric_dtype(self.df['minutes']):
            self.issues.append("'minutes' column is not numeric")
            checks.append(False)
        else:
            checks.append(True)
        
        # Starter should be boolean
        if self.df['starter'].dtype not in ['bool', 'object']:
            self.warnings.append("'starter' column may not be boolean")
        else:
            checks.append(True)
        
        if all(checks):
            print(f"✓ Data types look correct")
        
        return all(checks)
    
    def check_missing_values(self):
        """Check for missing values"""
        missing = self.df.isnull().sum()
        problematic = missing[missing > 0]
        
        if len(problematic) > 0:
            print(f"\n⚠️  Missing values found:")
            for col, count in problematic.items():
                pct = (count / len(self.df)) * 100
                print(f"  - {col}: {count:,} ({pct:.2f}%)")
                
                if col in ['game_id', 'player_id', 'team_id']:
                    self.issues.append(f"Critical column '{col}' has missing values")
                else:
                    self.warnings.append(f"Column '{col}' has {count} missing values")
        else:
            print(f"✓ No missing values")
        
        return len(problematic) == 0
    
    def check_minutes_distribution(self):
        """Validate minutes played distribution"""
        minutes = self.df[self.df['minutes'] > 0]['minutes']
        
        stats = {
            'min': minutes.min(),
            'max': minutes.max(),
            'mean': minutes.mean(),
            'median': minutes.median()
        }
        
        print(f"\n📊 Minutes distribution:")
        print(f"  Min: {stats['min']:.1f}")
        print(f"  Max: {stats['max']:.1f}")
        print(f"  Mean: {stats['mean']:.1f}")
        print(f"  Median: {stats['median']:.1f}")
        
        # Sanity checks
        if stats['max'] > 60:
            self.warnings.append(f"Max minutes ({stats['max']:.1f}) exceeds 60 (OT games?)")
        
        if stats['mean'] < 15 or stats['mean'] > 35:
            self.warnings.append(f"Average minutes ({stats['mean']:.1f}) seems unusual")
        
        return True
    
    def check_game_coverage(self):
        """Analyze game-level statistics"""
        game_stats = self.df.groupby('game_id').agg({
            'player_id': 'count',
            'team_id': 'nunique',
            'minutes': 'sum'
        }).rename(columns={'player_id': 'players_count'})
        
        print(f"\n📊 Per-game statistics:")
        print(f"  Total games: {len(game_stats):,}")
        print(f"  Avg players per game: {game_stats['players_count'].mean():.1f}")
        print(f"  Avg teams per game: {game_stats['team_id'].mean():.1f}")
        print(f"  Avg total minutes: {game_stats['minutes'].mean():.1f}")
        
        # Sanity checks
        if game_stats['team_id'].min() < 2:
            self.issues.append("Some games have fewer than 2 teams")
        
        if game_stats['players_count'].mean() < 15:
            self.warnings.append(f"Average players per game ({game_stats['players_count'].mean():.1f}) seems low")
        
        # Expected total minutes: ~240 per team × 2 teams = ~480
        expected_minutes = 480
        avg_minutes = game_stats['minutes'].mean()
        if abs(avg_minutes - expected_minutes) > 100:
            self.warnings.append(
                f"Average game minutes ({avg_minutes:.1f}) differs significantly from expected ({expected_minutes})"
            )
        
        return True
    
    def check_player_consistency(self):
        """Check player-level consistency"""
        player_stats = self.df.groupby('player_id').agg({
            'game_id': 'nunique',
            'team_id': 'nunique',
            'player_name': 'nunique'
        }).rename(columns={
            'game_id': 'games_played',
            'team_id': 'teams_count',
            'player_name': 'name_variations'
        })
        
        print(f"\n📊 Player statistics:")
        print(f"  Total unique players: {len(player_stats):,}")
        print(f"  Avg games per player: {player_stats['games_played'].mean():.1f}")
        print(f"  Max games per player: {player_stats['games_played'].max()}")
        
        # Check for players with multiple teams (trades)
        multi_team = player_stats[player_stats['teams_count'] > 1]
        print(f"  Players with multiple teams: {len(multi_team)} (trades)")
        
        # Check for inconsistent names
        name_issues = player_stats[player_stats['name_variations'] > 1]
        if len(name_issues) > 0:
            self.warnings.append(
                f"{len(name_issues)} players have inconsistent name spellings"
            )
        
        return True
    
    def check_starter_distribution(self):
        """Validate starter flags"""
        if 'starter' not in self.df.columns:
            return True
        
        starters_per_game = self.df[self.df['starter'] == True].groupby('game_id').size()
        
        print(f"\n📊 Starter distribution:")
        print(f"  Total starter records: {self.df['starter'].sum():,}")
        print(f"  Avg starters per game: {starters_per_game.mean():.1f}")
        print(f"  Expected: ~10 (5 per team)")
        
        if starters_per_game.mean() < 8 or starters_per_game.mean() > 12:
            self.warnings.append(
                f"Average starters per game ({starters_per_game.mean():.1f}) seems unusual"
            )
        
        return True
    
    def run_all_checks(self):
        """Run all validation checks"""
        print("="*70)
        print("BOX SCORE DATA VALIDATION")
        print("="*70)
        print(f"File: {self.csv_path}\n")
        
        if not self.load_data():
            return False
        
        print(f"\nRunning validation checks...\n")
        
        self.check_required_columns()
        self.check_data_types()
        self.check_missing_values()
        self.check_minutes_distribution()
        self.check_game_coverage()
        self.check_player_consistency()
        self.check_starter_distribution()
        
        # Summary
        print("\n" + "="*70)
        print("VALIDATION SUMMARY")
        print("="*70)
        
        if self.issues:
            print(f"\n❌ CRITICAL ISSUES ({len(self.issues)}):")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        if not self.issues and not self.warnings:
            print(f"\n✅ ALL CHECKS PASSED!")
            print(f"\nData is ready for Phase 3 Player ELO implementation.")
        elif not self.issues:
            print(f"\n✅ NO CRITICAL ISSUES")
            print(f"\nData can be used but review warnings above.")
        else:
            print(f"\n❌ VALIDATION FAILED")
            print(f"\nPlease fix critical issues before proceeding.")
        
        return len(self.issues) == 0


def main():
    """Main execution"""
    if len(sys.argv) < 2:
        print("Usage: python validate_boxscore_data.py <player_boxscores.csv>")
        print("\nExample:")
        print("  python validate_boxscore_data.py player_boxscores_all.csv")
        print("  python validate_boxscore_data.py mock_player_boxscores.csv")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    
    if not Path(csv_path).exists():
        print(f"❌ File not found: {csv_path}")
        sys.exit(1)
    
    validator = BoxScoreValidator(csv_path)
    success = validator.run_all_checks()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
