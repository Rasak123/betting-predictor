import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from .models import Team, Match, TeamStats, HeadToHeadStats, Prediction
from .api_client import FootballApiClient

class MatchPredictor:
    """Class for predicting football match outcomes"""
    
    def __init__(self):
        """Initialize the predictor"""
        self.logger = logging.getLogger(__name__)
        self.api_client = FootballApiClient()
        
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
            self.logger.error(f"Error getting team stats: {str(e)}")
            return None
    
    def get_h2h_stats(self, team1_id: int, team2_id: int, limit: int = 20) -> Optional[HeadToHeadStats]:
        """Get head-to-head statistics between two teams"""
        try:
            # Get head-to-head data from API
            h2h_data = self.api_client.get_head_to_head(team1_id, team2_id, limit)
            if not h2h_data or 'response' not in h2h_data:
                self.logger.error(f"Failed to get H2H data for teams {team1_id} and {team2_id}")
                return None
                
            matches_data = h2h_data['response']
            
            # Create H2H stats object
            h2h_stats = HeadToHeadStats(
                team1_id=team1_id,
                team2_id=team2_id,
                total_matches=len(matches_data)
            )
            
            # Process each match
            total_goals = 0
            for match_data in matches_data:
                match = Match.from_api(match_data)
                if not match:
                    continue
                    
                h2h_stats.matches.append(match)
                
                # Count wins/draws
                if match.home_score is not None and match.away_score is not None:
                    total_goals += match.home_score + match.away_score
                    
                    if match.home_team.id == team1_id:
                        if match.home_score > match.away_score:
                            h2h_stats.team1_wins += 1
                        elif match.home_score < match.away_score:
                            h2h_stats.team2_wins += 1
                        else:
                            h2h_stats.draws += 1
                    else:  # team1 is away
                        if match.away_score > match.home_score:
                            h2h_stats.team1_wins += 1
                        elif match.away_score < match.home_score:
                            h2h_stats.team2_wins += 1
                        else:
                            h2h_stats.draws += 1
            
            # Calculate average goals
            if h2h_stats.total_matches > 0:
                h2h_stats.avg_goals = total_goals / h2h_stats.total_matches
                
            return h2h_stats
            
        except Exception as e:
            self.logger.error(f"Error getting H2H stats: {str(e)}")
            return None
    
    def calculate_form_points(self, form_string: str) -> float:
        """Calculate form points from a form string (W/D/L)"""
        if not form_string:
            return 0.0
            
        points = 0.0
        weight = 1.0
        total_weight = 0.0
        
        # More recent matches have higher weight
        for result in form_string:
            if result == 'W':
                points += 3.0 * weight
            elif result == 'D':
                points += 1.0 * weight
            # L gets 0 points
            
            total_weight += weight
            weight *= 0.9  # Decay factor for older matches
        
        return points / total_weight if total_weight > 0 else 0.0
    
    def predict_over_under(self, home_stats: TeamStats, away_stats: TeamStats, threshold: float = 2.5) -> Dict[str, Any]:
        """Predict if the match will go over/under the goal threshold"""
        # Calculate expected goals
        expected_goals = home_stats.avg_goals_scored + away_stats.avg_goals_conceded
        expected_goals += away_stats.avg_goals_scored + home_stats.avg_goals_conceded
        expected_goals *= 0.5  # Average of both calculations
        
        # Calculate probability
        probability = 0.5  # Base probability
        
        # Adjust based on expected goals
        if expected_goals > threshold:
            probability += 0.1 * (expected_goals - threshold)
        else:
            probability -= 0.1 * (threshold - expected_goals)
        
        # Adjust based on teams' scoring/conceding patterns
        if home_stats.failed_to_score > 0.3 * home_stats.matches_played or away_stats.failed_to_score > 0.3 * away_stats.matches_played:
            probability -= 0.1
            
        if home_stats.clean_sheets > 0.3 * home_stats.matches_played or away_stats.clean_sheets > 0.3 * away_stats.matches_played:
            probability -= 0.1
        
        # Ensure probability is between 0 and 1
        probability = max(0.0, min(1.0, probability))
        
        return {
            'threshold': threshold,
            'prediction': probability > 0.5,
            'probability': round(probability * 100, 1),
            'expected_goals': round(expected_goals, 2)
        }
    
    def predict_btts(self, home_stats: TeamStats, away_stats: TeamStats) -> Dict[str, Any]:
        """Predict if both teams will score"""
        # Base probability
        probability = 0.5
        
        # Adjust based on teams' scoring patterns
        home_scoring_rate = 1 - (home_stats.failed_to_score / home_stats.matches_played) if home_stats.matches_played > 0 else 0.5
        away_scoring_rate = 1 - (away_stats.failed_to_score / away_stats.matches_played) if away_stats.matches_played > 0 else 0.5
        
        # Adjust based on teams' defensive records
        home_conceding_rate = 1 - (home_stats.clean_sheets / home_stats.matches_played) if home_stats.matches_played > 0 else 0.5
        away_conceding_rate = 1 - (away_stats.clean_sheets / away_stats.matches_played) if away_stats.matches_played > 0 else 0.5
        
        # Calculate BTTS probability
        btts_prob = (home_scoring_rate * away_conceding_rate + away_scoring_rate * home_conceding_rate) / 2
        probability = btts_prob
        
        # Ensure probability is between 0 and 1
        probability = max(0.0, min(1.0, probability))
        
        return {
            'prediction': probability > 0.5,
            'probability': round(probability * 100, 1),
            'confidence': 'High' if abs(probability - 0.5) > 0.2 else 'Medium' if abs(probability - 0.5) > 0.1 else 'Low'
        }
    
    def predict_first_half(self, home_stats: TeamStats, away_stats: TeamStats) -> Dict[str, Any]:
        """Predict first half result"""
        # Calculate form points
        home_form_points = self.calculate_form_points(home_stats.form)
        away_form_points = self.calculate_form_points(away_stats.form)
        
        # Calculate home advantage
        home_advantage = 0.1
        
        # Calculate win probabilities
        total_points = home_form_points + away_form_points + home_advantage
        if total_points == 0:
            home_win_prob = 0.45  # Default with home advantage
            draw_prob = 0.3
            away_win_prob = 0.25
        else:
            home_win_prob = (home_form_points + home_advantage) / total_points
            away_win_prob = away_form_points / total_points
            draw_prob = 1 - home_win_prob - away_win_prob
        
        # First half tends to have more draws
        draw_prob += 0.1
        home_win_prob -= 0.05
        away_win_prob -= 0.05
        
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
    
    def predict_score(self, home_stats: TeamStats, away_stats: TeamStats, h2h_stats: HeadToHeadStats) -> Tuple[float, float, float]:
        """Predict match score based on team stats and head-to-head history"""
        # Calculate expected goals
        home_expected_goals = home_stats.avg_goals_scored * 0.6 + away_stats.avg_goals_conceded * 0.4
        away_expected_goals = away_stats.avg_goals_scored * 0.6 + home_stats.avg_goals_conceded * 0.4
        
        # Adjust for home advantage
        home_expected_goals *= 1.1
        away_expected_goals *= 0.9
        
        # Adjust based on H2H history
        if h2h_stats and h2h_stats.total_matches > 0:
            # Calculate H2H goal averages
            h2h_home_goals = 0
            h2h_away_goals = 0
            h2h_matches_count = 0
            
            for match in h2h_stats.matches:
                if match.home_score is None or match.away_score is None:
                    continue
                    
                if match.home_team.id == home_stats.team_id:
                    h2h_home_goals += match.home_score
                    h2h_away_goals += match.away_score
                else:
                    h2h_home_goals += match.away_score
                    h2h_away_goals += match.home_score
                    
                h2h_matches_count += 1
            
            if h2h_matches_count > 0:
                h2h_home_avg = h2h_home_goals / h2h_matches_count
                h2h_away_avg = h2h_away_goals / h2h_matches_count
                
                # Blend current form with H2H history
                home_expected_goals = home_expected_goals * 0.7 + h2h_home_avg * 0.3
                away_expected_goals = away_expected_goals * 0.7 + h2h_away_avg * 0.3
        
        # Calculate confidence based on data quality
        confidence_factors = []
        
        # More matches played = higher confidence
        if home_stats.matches_played >= 10 and away_stats.matches_played >= 10:
            confidence_factors.append(1.0)
        elif home_stats.matches_played >= 5 and away_stats.matches_played >= 5:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.6)
        
        # More H2H matches = higher confidence
        if h2h_stats and h2h_stats.total_matches >= 5:
            confidence_factors.append(1.0)
        elif h2h_stats and h2h_stats.total_matches >= 2:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.6)
        
        # Calculate overall confidence
        confidence = sum(confidence_factors) / len(confidence_factors)
        
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
