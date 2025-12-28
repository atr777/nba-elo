"""
Betting Analyzer - Low-Risk Bet Recommendations
================================================

Analyzes games using our ELO model, injury data, and historical performance
to identify the safest betting opportunities.

Risk Categories:
- VERY LOW RISK: 75%+ win probability, strong confidence
- LOW RISK: 65-75% win probability, good confidence
- MODERATE RISK: 55-65% win probability
- HIGH RISK: <55% win probability (not recommended)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from pathlib import Path


class BettingAnalyzer:
    """Analyzes games to identify low-risk betting opportunities."""

    # Risk thresholds
    VERY_LOW_RISK_THRESHOLD = 0.75
    LOW_RISK_THRESHOLD = 0.65
    MODERATE_RISK_THRESHOLD = 0.55

    # Minimum confidence required to recommend a bet
    MIN_CONFIDENCE_THRESHOLD = 0.60

    def __init__(self):
        """Initialize the betting analyzer."""
        self.predictions = []
        self.injury_data = {}

    def analyze_game(self, prediction: Dict) -> Dict:
        """
        Analyze a single game prediction for betting opportunities.

        Args:
            prediction: Game prediction with probabilities and metadata

        Returns:
            Betting analysis with risk rating and recommendations
        """
        home_prob = prediction['predicted_home_prob']
        away_prob = prediction['predicted_away_prob']

        # Determine recommended bet
        if home_prob > away_prob:
            recommended_team = prediction['home_team_name']
            win_probability = home_prob
            recommended_side = 'home'
        else:
            recommended_team = prediction['away_team_name']
            win_probability = away_prob
            recommended_side = 'away'

        # Calculate risk level
        risk_level = self._calculate_risk_level(win_probability)

        # Calculate expected value (simplified)
        # Assumes American odds based on probability
        implied_odds = self._probability_to_american_odds(win_probability)

        # Calculate confidence score (0-100)
        confidence_score = int(win_probability * 100)

        # Determine if bet should be recommended
        should_recommend = (
            win_probability >= self.MIN_CONFIDENCE_THRESHOLD and
            risk_level in ['VERY LOW RISK', 'LOW RISK']
        )

        analysis = {
            'game_id': prediction.get('game_id'),
            'date': prediction.get('date'),
            'matchup': f"{prediction['away_team_name']} @ {prediction['home_team_name']}",
            'home_team': prediction['home_team_name'],
            'away_team': prediction['away_team_name'],
            'recommended_team': recommended_team,
            'recommended_side': recommended_side,
            'win_probability': win_probability,
            'confidence_score': confidence_score,
            'risk_level': risk_level,
            'should_recommend': should_recommend,
            'implied_odds': implied_odds,
            'home_prob': home_prob,
            'away_prob': away_prob,
            'prob_spread': abs(home_prob - away_prob),  # Higher = more confident
        }

        return analysis

    def _calculate_risk_level(self, win_probability: float) -> str:
        """Calculate risk level based on win probability."""
        if win_probability >= self.VERY_LOW_RISK_THRESHOLD:
            return 'VERY LOW RISK'
        elif win_probability >= self.LOW_RISK_THRESHOLD:
            return 'LOW RISK'
        elif win_probability >= self.MODERATE_RISK_THRESHOLD:
            return 'MODERATE RISK'
        else:
            return 'HIGH RISK'

    def _probability_to_american_odds(self, probability: float) -> int:
        """
        Convert win probability to American odds format.

        Args:
            probability: Win probability (0-1)

        Returns:
            American odds (negative for favorites)
        """
        if probability >= 0.5:
            # Favorite (negative odds)
            odds = -(probability / (1 - probability)) * 100
        else:
            # Underdog (positive odds)
            odds = ((1 - probability) / probability) * 100

        return int(odds)

    def get_daily_recommendations(
        self,
        predictions: List[Dict],
        max_recommendations: int = 5,
        risk_levels: List[str] = None
    ) -> List[Dict]:
        """
        Get recommended bets for the day, sorted by confidence.

        Args:
            predictions: List of game predictions
            max_recommendations: Maximum number of bets to recommend
            risk_levels: Filter by risk levels (default: VERY LOW and LOW only)

        Returns:
            List of recommended bets, sorted by confidence
        """
        if risk_levels is None:
            risk_levels = ['VERY LOW RISK', 'LOW RISK']

        # Analyze all games
        analyses = [self.analyze_game(pred) for pred in predictions]

        # Filter to only recommended bets
        recommended = [
            a for a in analyses
            if a['should_recommend'] and a['risk_level'] in risk_levels
        ]

        # Sort by win probability (highest first)
        recommended.sort(key=lambda x: x['win_probability'], reverse=True)

        # Limit to max recommendations
        return recommended[:max_recommendations]

    def calculate_parlay_probability(self, bets: List[Dict]) -> Dict:
        """
        Calculate probability and risk for a parlay bet.

        Args:
            bets: List of individual bet analyses

        Returns:
            Parlay analysis with combined probability and risk
        """
        if not bets:
            return None

        # Calculate combined probability (product of individual probabilities)
        combined_prob = np.prod([bet['win_probability'] for bet in bets])

        # Calculate combined odds
        combined_odds = 1
        for bet in bets:
            # Convert to decimal odds first
            if bet['implied_odds'] < 0:
                decimal_odds = 1 + (100 / abs(bet['implied_odds']))
            else:
                decimal_odds = 1 + (bet['implied_odds'] / 100)
            combined_odds *= decimal_odds

        # Convert back to American odds
        if combined_odds >= 2:
            american_odds = int((combined_odds - 1) * 100)
        else:
            american_odds = int(-100 / (combined_odds - 1))

        risk_level = self._calculate_risk_level(combined_prob)

        return {
            'num_bets': len(bets),
            'combined_probability': combined_prob,
            'confidence_score': int(combined_prob * 100),
            'risk_level': risk_level,
            'combined_odds': american_odds,
            'individual_bets': [
                {
                    'team': bet['recommended_team'],
                    'matchup': bet['matchup'],
                    'probability': bet['win_probability']
                }
                for bet in bets
            ]
        }

    def generate_betting_report(self, predictions: List[Dict]) -> Dict:
        """
        Generate a comprehensive betting report for the day.

        Args:
            predictions: List of game predictions

        Returns:
            Report with recommendations, statistics, and insights
        """
        analyses = [self.analyze_game(pred) for pred in predictions]

        # Get recommendations by risk level
        very_low_risk = [a for a in analyses if a['risk_level'] == 'VERY LOW RISK']
        low_risk = [a for a in analyses if a['risk_level'] == 'LOW RISK']
        moderate_risk = [a for a in analyses if a['risk_level'] == 'MODERATE RISK']

        # Sort each group by probability
        very_low_risk.sort(key=lambda x: x['win_probability'], reverse=True)
        low_risk.sort(key=lambda x: x['win_probability'], reverse=True)
        moderate_risk.sort(key=lambda x: x['win_probability'], reverse=True)

        # Calculate statistics
        total_games = len(analyses)
        total_recommended = len([a for a in analyses if a['should_recommend']])
        avg_confidence = np.mean([a['confidence_score'] for a in analyses]) if analyses else 0

        # Find best parlay opportunities (2-3 very low risk bets)
        best_parlays = []
        if len(very_low_risk) >= 2:
            # 2-leg parlay
            two_leg = self.calculate_parlay_probability(very_low_risk[:2])
            if two_leg:
                best_parlays.append(two_leg)

        if len(very_low_risk) >= 3:
            # 3-leg parlay
            three_leg = self.calculate_parlay_probability(very_low_risk[:3])
            if three_leg:
                best_parlays.append(three_leg)

        report = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'total_games': total_games,
            'total_recommended': total_recommended,
            'avg_confidence': avg_confidence,
            'very_low_risk_bets': very_low_risk,
            'low_risk_bets': low_risk,
            'moderate_risk_bets': moderate_risk,
            'top_5_recommendations': (very_low_risk + low_risk)[:5],
            'best_parlays': best_parlays,
            'statistics': {
                'very_low_risk_count': len(very_low_risk),
                'low_risk_count': len(low_risk),
                'moderate_risk_count': len(moderate_risk),
                'high_risk_count': len(analyses) - len(very_low_risk) - len(low_risk) - len(moderate_risk)
            }
        }

        return report
