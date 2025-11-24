"""
ELO Visualization Engine
========================
Create compelling visualizations of NBA ELO ratings and contextual data.

Visualization Types:
- Team ELO time series (line charts)
- Season comparisons
- Travel impact scatter plots
- Rest day correlation charts
- League-wide ELO distributions
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime


class ELOVisualizer:
    """
    Create professional visualizations of NBA ELO data.
    """
    
    def __init__(self, elo_data_path: str = None, output_dir: str = "data/exports/visualizations"):
        """
        Initialize visualizer with ELO data.
        
        Args:
            elo_data_path: Path to ELO history CSV (auto-detects clean version)
            output_dir: Where to save generated plots
        """
        # Auto-detect cleaned data if no path specified
        if elo_data_path is None:
            if Path("data/exports/team_elo_history_phase_1_5_clean.csv").exists():
                elo_data_path = "data/exports/team_elo_history_phase_1_5_clean.csv"
                print("✓ Using cleaned data (All-Star games removed)")
            else:
                elo_data_path = "data/exports/team_elo_history_phase_1_5.csv"
                print("⚠ Using original data (may contain All-Star games)")
        
        self.elo_df = pd.read_csv(elo_data_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Convert date to datetime if needed
        if self.elo_df['date'].dtype == 'int64':
            self.elo_df['date'] = pd.to_datetime(self.elo_df['date'], format='%Y%m%d')
        else:
            self.elo_df['date'] = pd.to_datetime(self.elo_df['date'])
        
        # Set plotting style
        plt.style.use('seaborn-v0_8-darkgrid')
        
        print(f"✓ Loaded {len(self.elo_df):,} game records")
        print(f"✓ Output directory: {self.output_dir}")
    
    def plot_team_elo_timeseries(
        self,
        team_name: str,
        season: Optional[str] = None,
        show_context: bool = True,
        figsize: Tuple[int, int] = (14, 8)
    ) -> str:
        """
        Plot ELO rating over time for a single team.
        
        Args:
            team_name: Name of the team (e.g., "Los Angeles Lakers")
            season: Optional season filter (e.g., "2023-24")
            show_context: Whether to highlight back-to-back games
            figsize: Figure size (width, height)
        
        Returns:
            Path to saved figure
        """
        # Filter data
        team_data = self.elo_df[self.elo_df['team_name'] == team_name].copy()
        
        if season:
            team_data['season'] = team_data['date'].apply(self._get_season)
            team_data = team_data[team_data['season'] == season]
        
        if len(team_data) == 0:
            print(f"No data found for {team_name}" + (f" in {season}" if season else ""))
            return ""
        
        # Create plot
        fig, ax = plt.subplots(figsize=figsize)
        
        # Main ELO line
        ax.plot(team_data['date'], team_data['rating_after'], 
                linewidth=2, color='#1f77b4', label='ELO Rating')
        
        # Add context: back-to-back games
        if show_context and 'rest_days' in team_data.columns:
            b2b_games = team_data[team_data['rest_days'] == 0]
            if len(b2b_games) > 0:
                ax.scatter(b2b_games['date'], b2b_games['rating_after'],
                          color='red', s=100, alpha=0.6, 
                          label='Back-to-Back Game', zorder=5)
        
        # Formatting
        ax.set_title(f"{team_name} ELO Rating" + (f" - {season}" if season else ""),
                    fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('ELO Rating', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10, loc='best')
        
        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.xticks(rotation=45, ha='right')
        
        # Add baseline reference line
        ax.axhline(y=1500, color='gray', linestyle='--', alpha=0.5, linewidth=1)
        ax.text(team_data['date'].iloc[0], 1505, 'League Average (1500)', 
               fontsize=9, color='gray')
        
        # Tight layout
        plt.tight_layout()
        
        # Save
        filename = f"{team_name.replace(' ', '_')}_{season if season else 'all'}_elo.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {filepath}")
        
        plt.close()
        return str(filepath)
    
    def plot_multiple_teams(
        self,
        team_names: List[str],
        season: Optional[str] = None,
        figsize: Tuple[int, int] = (14, 8)
    ) -> str:
        """
        Plot multiple teams' ELO ratings on same chart.
        
        Args:
            team_names: List of team names
            season: Optional season filter
            figsize: Figure size
        
        Returns:
            Path to saved figure
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        colors = plt.cm.tab10(np.linspace(0, 1, len(team_names)))
        
        for i, team_name in enumerate(team_names):
            team_data = self.elo_df[self.elo_df['team_name'] == team_name].copy()
            
            if season:
                team_data['season'] = team_data['date'].apply(self._get_season)
                team_data = team_data[team_data['season'] == season]
            
            if len(team_data) > 0:
                ax.plot(team_data['date'], team_data['rating_after'],
                       linewidth=2, color=colors[i], label=team_name, alpha=0.8)
        
        # Formatting
        ax.set_title(f"ELO Rating Comparison" + (f" - {season}" if season else ""),
                    fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('ELO Rating', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9, loc='best')
        
        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.xticks(rotation=45, ha='right')
        
        # Baseline
        ax.axhline(y=1500, color='gray', linestyle='--', alpha=0.5, linewidth=1)
        
        plt.tight_layout()
        
        filename = f"comparison_{season if season else 'all'}_elo.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {filepath}")
        
        plt.close()
        return str(filepath)
    
    def plot_travel_impact(
        self,
        travel_data_path: str,
        figsize: Tuple[int, int] = (14, 8)
    ) -> str:
        """
        Visualize relationship between travel distance and performance.
        
        Args:
            travel_data_path: Path to ELO data with travel distances
            figsize: Figure size
        
        Returns:
            Path to saved figure
        """
        df = pd.read_csv(travel_data_path)
        
        # Filter out games with no travel
        df_travel = df[df['travel_distance_km'] > 0].copy()
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
        
        # Scatter: Travel distance vs ELO change
        wins = df_travel[df_travel['won'] == True]
        losses = df_travel[df_travel['won'] == False]
        
        ax1.scatter(wins['travel_distance_km'], wins['rating_change'],
                   alpha=0.3, s=20, color='green', label='Wins')
        ax1.scatter(losses['travel_distance_km'], losses['rating_change'],
                   alpha=0.3, s=20, color='red', label='Losses')
        
        ax1.set_xlabel('Travel Distance (km)', fontsize=11)
        ax1.set_ylabel('ELO Change', fontsize=11)
        ax1.set_title('Travel Distance vs ELO Change', fontsize=13, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
        
        # Bar chart: Win rate by travel bins
        df_travel['travel_bin'] = pd.cut(
            df_travel['travel_distance_km'],
            bins=[0, 500, 1000, 1500, 2000, 5000],
            labels=['0-500', '500-1000', '1000-1500', '1500-2000', '2000+']
        )
        
        win_rates = df_travel.groupby('travel_bin')['won'].agg(['mean', 'count'])
        
        bars = ax2.bar(range(len(win_rates)), win_rates['mean'], 
                      color='steelblue', alpha=0.7)
        ax2.set_xticks(range(len(win_rates)))
        ax2.set_xticklabels(win_rates.index, rotation=45, ha='right')
        ax2.set_xlabel('Travel Distance (km)', fontsize=11)
        ax2.set_ylabel('Win Rate', fontsize=11)
        ax2.set_title('Win Rate by Travel Distance', fontsize=13, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')
        ax2.axhline(y=0.5, color='red', linestyle='--', alpha=0.6, linewidth=1)
        
        # Add sample sizes on bars
        for i, (bar, count) in enumerate(zip(bars, win_rates['count'])):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                    f'n={count}', ha='center', va='bottom', fontsize=8)
        
        plt.tight_layout()
        
        filepath = self.output_dir / "travel_impact_analysis.png"
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {filepath}")
        
        plt.close()
        return str(filepath)
    
    def plot_league_distribution(
        self,
        date: Optional[str] = None,
        figsize: Tuple[int, int] = (12, 8)
    ) -> str:
        """
        Plot current ELO distribution across the league.
        
        Args:
            date: Specific date (YYYYMMDD or YYYY-MM-DD), or None for most recent
            figsize: Figure size
        
        Returns:
            Path to saved figure
        """
        # Get most recent ratings for each team
        if date:
            date_dt = pd.to_datetime(date)
            snapshot = self.elo_df[self.elo_df['date'] <= date_dt]
        else:
            snapshot = self.elo_df
        
        latest_ratings = snapshot.groupby('team_name').tail(1)
        latest_ratings = latest_ratings.sort_values('rating_after', ascending=False)
        
        fig, ax = plt.subplots(figsize=figsize)
        
        bars = ax.barh(range(len(latest_ratings)), latest_ratings['rating_after'],
                      color='steelblue', alpha=0.7)
        
        # Color code by strength
        for i, (idx, row) in enumerate(latest_ratings.iterrows()):
            if row['rating_after'] > 1600:
                bars[i].set_color('green')
            elif row['rating_after'] < 1400:
                bars[i].set_color('red')
        
        ax.set_yticks(range(len(latest_ratings)))
        ax.set_yticklabels(latest_ratings['team_name'], fontsize=9)
        ax.set_xlabel('ELO Rating', fontsize=12)
        ax.set_title('NBA Team ELO Ratings - Current Standings', 
                    fontsize=14, fontweight='bold', pad=15)
        ax.grid(True, alpha=0.3, axis='x')
        ax.axvline(x=1500, color='gray', linestyle='--', alpha=0.6, linewidth=1.5)
        
        # Add rating values on bars
        for i, (idx, row) in enumerate(latest_ratings.iterrows()):
            ax.text(row['rating_after'] + 10, i, f"{row['rating_after']:.0f}",
                   va='center', fontsize=8)
        
        plt.tight_layout()
        
        filepath = self.output_dir / "league_elo_distribution.png"
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {filepath}")
        
        plt.close()
        return str(filepath)
    
    def _get_season(self, date):
        """Convert date to NBA season string."""
        year = date.year
        month = date.month
        if month >= 10:
            return f"{year}-{str(year+1)[-2:]}"
        else:
            return f"{year-1}-{str(year)[-2:]}"


def create_sample_visualizations():
    """
    Create a set of sample visualizations to demonstrate capabilities.
    """
    print("=" * 70)
    print("ELO VISUALIZATION ENGINE - SAMPLE VISUALIZATIONS")
    print("=" * 70)
    print()
    
    # Initialize visualizer (auto-detects clean data)
    viz = ELOVisualizer()
    
    print("\n1. Creating single team ELO chart...")
    viz.plot_team_elo_timeseries("Los Angeles Lakers", season="2023-24")
    
    print("\n2. Creating multi-team comparison...")
    viz.plot_multiple_teams([
        "Los Angeles Lakers",
        "Boston Celtics",
        "Golden State Warriors"
    ], season="2023-24")
    
    print("\n3. Creating league distribution...")
    viz.plot_league_distribution()
    
    print("\n4. Creating travel impact analysis...")
    travel_clean = Path("data/exports/team_elo_with_travel_clean.csv")
    travel_original = Path("data/exports/team_elo_with_travel.csv")
    
    if travel_clean.exists():
        viz.plot_travel_impact(str(travel_clean))
    elif travel_original.exists():
        viz.plot_travel_impact(str(travel_original))
    else:
        print("   (Skipped - run travel analysis first)")
    
    print("\n" + "=" * 70)
    print("VISUALIZATION COMPLETE")
    print("=" * 70)
    print(f"\nView your charts in: data/exports/visualizations/")


if __name__ == "__main__":
    create_sample_visualizations()
