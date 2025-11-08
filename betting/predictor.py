import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from scipy.stats import poisson
import math
from .models import Team, Match, TeamStats, HeadToHeadStats, Prediction
from .api_client import FootballApiClient

class MatchPredictor:
    """Class for predicting football match outcomes"""
    
    def __init__(self):
        """Initialize the predictor"""
        self.logger = logging.getLogger(__name__)
        self.api_client = FootballApiClient()
        self.most_likely_score = (0, 0)  # Initialize most_likely_score

    def get_team_stats(self, team_id: int, league_id: int, season: int) -> Optional[TeamStats]:
        """Get comprehensive team statistics"""
        try:
            # Get team statistics from API
            stats_data = self.api_client.get_team_statistics(team_id, league_id, season)
            if not stats_data or 'response' not in stats_data:
                self.logger.error(f"Failed to get statistics for team {team_id}")
                return None
                
            response = stats_data['response']
            team_data = response.get('team', {})
            fixtures = response.get('fixtures', {})
            goals = response.get('goals', {})
            clean_sheet = response.get('clean_sheet', {})
            failed_to_score = response.get('failed_to_score', {})
            form = response.get('form', '')
            
            # Create team stats object
            team_stats = TeamStats(
                team_id=team_id,
                team_name=team_data.get('name', 'Unknown Team'),
                matches_played=fixtures.get('played', {}).get('total', 0),
                wins=fixtures.get('wins', {}).get('total', 0),
                draws=fixtures.get('draws', {}).get('total', 0),
                losses=fixtures.get('loses', {}).get('total', 0),
                goals_scored=goals.get('for', {}).get('total', {}).get('total', 0),
                goals_conceded=goals.get('against', {}).get('total', {}).get('total', 0),
                clean_sheets=clean_sheet.get('total', 0),
                failed_to_score=failed_to_score.get('total', 0),
                form=form
            )
            
            # Calculate averages
            team_stats.calculate_averages()
            
            return team_stats
            
        except Exception as e:
            self.logger.error(f"Error getting team stats: {e}")
            return None

    def get_h2h_stats(self, team1_id: int, team2_id: int, limit: int = 20) -> Optional[HeadToHeadStats]:
        """Get head-to-head statistics between two teams"""
        try:
            # Get head-to-head data from API
            h2h_data = self.api_client.get_head_to_head(team1_id, team2_id, limit)
            if not h2h_data or 'response' not in h2h_data:
                return None
                
            matches = h2h_data['response']
            if not matches:
                return None
                
            # Initialize counters
            team1_wins = 0
            team2_wins = 0
            draws = 0
            total_goals_team1 = 0
            total_goals_team2 = 0
            
            # Process each match
            for match in matches:
                home_goals = match['goals']['home']
                away_goals = match['goals']['away']
                
                # Determine if team1 was home or away
                if match['teams']['home']['id'] == team1_id:
                    team1_goals = home_goals
                    team2_goals = away_goals
                else:
                    team1_goals = away_goals
                    team2_goals = home_goals
                    
                # Update counters
                total_goals_team1 += team1_goals
                total_goals_team2 += team2_goals
                
                if team1_goals > team2_goals:
                    team1_wins += 1
                elif team2_goals > team1_goals:
                    team2_wins += 1
                else:
                    draws += 1
            
            # Create and return HeadToHeadStats object
            return HeadToHeadStats(
                team1_id=team1_id,
                team2_id=team2_id,
                total_matches=len(matches),
                team1_wins=team1_wins,
                team2_wins=team2_wins,
                draws=draws,
                team1_goals=total_goals_team1,
                team2_goals=total_goals_team2
            )
            
        except Exception as e:
            self.logger.error(f"Error getting H2H stats: {e}")
            return None

    def calculate_form_points(self, form_string: str) -> float:
        """Calculate form points from a form string (W/D/L)"""
        if not form_string:
            return 0.0
            
        points = 0
        weight = 1.0
        decay = 0.8  # Weight decay for older matches
        
        # Process each character in reverse (most recent first)
        for result in reversed(form_string.upper()):
            if result == 'W':
                points += 3 * weight
            elif result == 'D':
                points += 1 * weight
            # No points for losses
            
            # Apply decay for next match
            weight *= decay
            
        return points

    def predict_over_under(self, home_stats: TeamStats, away_stats: TeamStats, threshold: float = 2.5) -> Dict[str, float]:
        """Predict if the match will go over/under the goal threshold"""
        # Calculate expected goals
        home_expected = (home_stats.avg_goals_scored + away_stats.avg_goals_conceded) / 2
        away_expected = (away_stats.avg_goals_scored + home_stats.avg_goals_conceded) / 2
        
        total_expected = home_expected + away_expected
        
        # Calculate probability of over/under
        over_prob = 1.0 / (1.0 + 10 ** (-(total_expected - threshold) * 0.5))
        under_prob = 1.0 - over_prob
        
        return {
            'over': over_prob,
            'under': under_prob,
            'expected_goals': total_expected
        }

    def predict_btts(self, home_stats: TeamStats, away_stats: TeamStats) -> Dict[str, float]:
        """Predict if both teams will score"""
        # Calculate probability of both teams scoring
        home_score_prob = (home_stats.avg_goals_scored + away_stats.avg_goals_conceded) / 2
        away_score_prob = (away_stats.avg_goals_scored + home_stats.avg_goals_conceded) / 2
        
        # Convert to probability between 0 and 1
        home_score_prob = min(max(home_score_prob / 3.0, 0.1), 0.9)
        away_score_prob = min(max(away_score_prob / 3.0, 0.1), 0.9)
        
        # Calculate BTTS probability
        btts_prob = home_score_prob * away_score_prob
        
        return {
            'btts_yes': btts_prob,
            'btts_no': 1.0 - btts_prob
        }

    def predict_first_half(self, home_stats: TeamStats, away_stats: TeamStats) -> Dict[str, float]:
        """Predict first half result"""
        # Calculate expected goals for first half (approximately 45% of full match)
        home_expected = (home_stats.avg_goals_scored + away_stats.avg_goals_conceded) * 0.45
        away_expected = (away_stats.avg_goals_scored + home_stats.avg_goals_conceded) * 0.45
        
        # Calculate probabilities
        home_win = 1.0 / (1.0 + 10 ** (-(home_expected - away_expected) * 0.5))
        draw = 1.0 / (1.0 + abs(home_expected - away_expected) * 2)
        away_win = 1.0 - home_win - draw
        
        # Normalize probabilities
        total = home_win + draw + away_win
        home_win /= total
        draw /= total
        away_win /= total
        
        return {
            'home': home_win,
            'draw': draw,
            'away': away_win
        }

    def predict_score(self, home_stats: TeamStats, away_stats: TeamStats, h2h_stats: HeadToHeadStats) -> tuple[float, float, float]:
        """Predict match score based on team stats and head-to-head history"""
        # Calculate base expected goals
        home_expected_goals = (home_stats.avg_goals_scored + away_stats.avg_goals_conceded) / 2
        away_expected_goals = (away_stats.avg_goals_scored + home_stats.avg_goals_conceded) / 2
        
        # Adjust for home advantage
        home_expected_goals *= 1.1
        away_expected_goals *= 0.9
        
        # Consider form (last 5 matches)
        if home_stats.form and len(home_stats.form) >= 5:
            form_factor = calculate_form_factor(home_stats.form[-5:])
            home_expected_goals *= form_factor
            
        if away_stats.form and len(away_stats.form) >= 5:
            form_factor = calculate_form_factor(away_stats.form[-5:])
            away_expected_goals *= form_factor
        
        # Consider head-to-head history if available
        if h2h_stats and h2h_stats.total_matches > 0:
            # Calculate average goals from H2H
            h2h_home_avg = h2h_stats.team1_goals / h2h_stats.total_matches
            h2h_away_avg = h2h_stats.team2_goals / h2h_stats.total_matches
            
            # Blend current model with H2H history - H2H gets more weight if teams play often
            h2h_weight = min(0.4, 0.1 * min(h2h_stats.total_matches, 4))
            home_expected_goals = home_expected_goals * (1 - h2h_weight) + h2h_home_avg * h2h_weight
            away_expected_goals = away_expected_goals * (1 - h2h_weight) + h2h_away_avg * h2h_weight
    
        # Adjust for team motivation factors (e.g., fighting relegation, title race)
        # This would require additional data, but the framework is here
        
        # Consider defensive solidity for low-scoring predictions
        if home_stats.clean_sheets / max(1, home_stats.matches_played) > 0.4:
            away_expected_goals *= 0.9
        if away_stats.clean_sheets / max(1, away_stats.matches_played) > 0.4:
            home_expected_goals *= 0.9
        
        # Consider scoring consistency
        home_scoring_consistency = 1 - (home_stats.failed_to_score / max(1, home_stats.matches_played))
        away_scoring_consistency = 1 - (away_stats.failed_to_score / max(1, away_stats.matches_played))
        
        home_expected_goals *= max(0.8, home_scoring_consistency)
        away_expected_goals *= max(0.8, away_scoring_consistency)
        
        # Calculate most likely score using Poisson distribution
        max_goals = 5  # Consider scores up to 5-5
        max_probability = 0
        most_likely_home_score = round(home_expected_goals)
        most_likely_away_score = round(away_expected_goals)
        
        # Find the most likely exact score
        for h in range(max_goals + 1):
            for a in range(max_goals + 1):
                p_home = poisson.pmf(h, home_expected_goals)
                p_away = poisson.pmf(a, away_expected_goals)
                probability = p_home * p_away
                
                if probability > max_probability:
                    max_probability = probability
                    most_likely_home_score = h
                    most_likely_away_score = a
        
        # Calculate confidence based on multiple factors
        confidence_factors = []
        
        # Data quality factors
        if home_stats.matches_played >= 15 and away_stats.matches_played >= 15:
            confidence_factors.append(1.0)
        elif home_stats.matches_played >= 10 and away_stats.matches_played >= 10:
            confidence_factors.append(0.9)
        elif home_stats.matches_played >= 5 and away_stats.matches_played >= 5:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.5)
        
        # H2H data quality
        if h2h_stats and h2h_stats.total_matches >= 5:
            confidence_factors.append(1.0)
        elif h2h_stats and h2h_stats.total_matches >= 3:
            confidence_factors.append(0.85)
        elif h2h_stats and h2h_stats.total_matches >= 1:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.6)
        
        # Form consistency factor
        if home_stats.form and away_stats.form:
            home_form_consistency = calculate_form_consistency(home_stats.form)
            away_form_consistency = calculate_form_consistency(away_stats.form)
            avg_form_consistency = (home_form_consistency + away_form_consistency) / 2
            confidence_factors.append(avg_form_consistency)
        
        # Calculate overall confidence - weighted average
        weights = [0.4, 0.3, 0.3]  # Matches played, H2H data, Form consistency
        confidence = sum(f * w for f, w in zip(confidence_factors, weights)) / sum(weights)
        
        # Store the most likely score for reference
        self.most_likely_score = (most_likely_home_score, most_likely_away_score)
        
        return home_expected_goals, away_expected_goals, confidence

    def predict_match_outcome(self, home_stats: TeamStats, away_stats: TeamStats, h2h_stats: HeadToHeadStats) -> Dict[str, Any]:
        """Predict match outcome (home win, draw, away win)"""
        # Calculate form points
        home_form_points = self.calculate_form_points(home_stats.form)
        away_form_points = self.calculate_form_points(away_stats.form)
        
        # Calculate home advantage
        home_advantage = 0.1
        
        # Calculate win probabilities based on form
        form_total = home_form_points + away_form_points + home_advantage
        if form_total == 0:
            form_home_win_prob = 0.45  # Default with home advantage
            form_draw_prob = 0.3
            form_away_win_prob = 0.25
        else:
            form_home_win_prob = (home_form_points + home_advantage) / form_total
            form_away_win_prob = away_form_points / form_total
            form_draw_prob = 1 - form_home_win_prob - form_away_win_prob
        
        # Calculate win probabilities based on H2H
        if h2h_stats and h2h_stats.total_matches > 0:
            h2h_home_win_prob = h2h_stats.team1_wins / h2h_stats.total_matches
            h2h_away_win_prob = h2h_stats.team2_wins / h2h_stats.total_matches
            h2h_draw_prob = h2h_stats.draws / h2h_stats.total_matches
        else:
            h2h_home_win_prob = 0.45  # Default with home advantage
            h2h_draw_prob = 0.3
            h2h_away_win_prob = 0.25
        
        # Blend probabilities (form is more important than H2H)
        home_win_prob = form_home_win_prob * 0.7 + h2h_home_win_prob * 0.3
        draw_prob = form_draw_prob * 0.7 + h2h_draw_prob * 0.3
        away_win_prob = form_away_win_prob * 0.7 + h2h_away_win_prob * 0.3
        
        # Normalize probabilities
        total = home_win_prob + draw_prob + away_win_prob
        home_win_prob /= total
        draw_prob /= total
        away_win_prob /= total
        
        # Determine prediction
        probs = {'home': home_win_prob, 'draw': draw_prob, 'away': away_win_prob}
        prediction = max(probs, key=probs.get)
        confidence = max(probs.values())
        
        return {
            'prediction': prediction,
            'probabilities': {
                'home': round(home_win_prob * 100, 1),
                'draw': round(draw_prob * 100, 1),
                'away': round(away_win_prob * 100, 1)
            },
            'confidence': round(confidence * 100, 1)
        }
    
    def predict_match(self, match: Match) -> Optional[Prediction]:
        """Make a comprehensive prediction for a match"""
        try:
            self.logger.info(f"Predicting match: {match.home_team.name} vs {match.away_team.name}")
            
            # Get team statistics
            home_stats = self.get_team_stats(match.home_team.id, match.league_id, match.date.year)
            away_stats = self.get_team_stats(match.away_team.id, match.league_id, match.date.year)
            
            if not home_stats or not away_stats:
                self.logger.error("Failed to get team statistics")
                return None
            
            # Get head-to-head statistics
            h2h_stats = self.get_h2h_stats(match.home_team.id, match.away_team.id)
            
            # Predict score
            home_expected_goals, away_expected_goals, score_confidence = self.predict_score(home_stats, away_stats, h2h_stats)
            
            # Predict match outcome
            outcome_prediction = self.predict_match_outcome(home_stats, away_stats, h2h_stats)
            
            # Predict over/under
            over_under_predictions = {}
            thresholds = [1.5, 2.5, 3.5, 4.5]
            for threshold in thresholds:
                key = f"over_{str(threshold).replace('.', '_')}"
                over_under_predictions[key] = self.predict_over_under(home_stats, away_stats, threshold)
            
            # Predict BTTS
            btts_prediction = self.predict_btts(home_stats, away_stats)
            
            # Predict first half
            first_half_prediction = self.predict_first_half(home_stats, away_stats)
            
            # Create prediction object
            prediction = Prediction(
                match=match,
                home_win_probability=outcome_prediction['probabilities']['home'] / 100,
                draw_probability=outcome_prediction['probabilities']['draw'] / 100,
                away_win_probability=outcome_prediction['probabilities']['away'] / 100,
                predicted_home_score=home_expected_goals,
                predicted_away_score=away_expected_goals,
                confidence=score_confidence,
                over_under_predictions=over_under_predictions,
                btts_prediction=btts_prediction,
                first_half_prediction=first_half_prediction
            )
            
            return prediction
            
        except Exception as e:
            self.logger.error(f"Error predicting match: {str(e)}")
            return None
    
    def get_upcoming_matches(self, leagues: Dict[str, Dict[str, Any]], days_ahead: int = 7) -> List[Match]:
        """Get upcoming matches for specified leagues"""
        try:
            matches = []
            today = datetime.now().date()
            end_date = today + timedelta(days=days_ahead)
            
            for league_key, league_info in leagues.items():
                league_id = league_info['id']
                season = league_info['season']
                
                # Format dates for API
                from_date = today.strftime('%Y-%m-%d')
                to_date = end_date.strftime('%Y-%m-%d')
                
                # Get fixtures from API
                fixtures_data = self.api_client.get_fixtures(league_id, season, from_date, to_date)
                
                if not fixtures_data or 'response' not in fixtures_data:
                    self.logger.error(f"Failed to get fixtures for league {league_key}")
                    continue
                
                # Process each fixture
                for fixture_data in fixtures_data['response']:
                    match = Match.from_api(fixture_data)
                    if match:
                        matches.append(match)
            
            return matches
            
        except Exception as e:
            self.logger.error(f"Error getting upcoming matches: {str(e)}")
            return []
