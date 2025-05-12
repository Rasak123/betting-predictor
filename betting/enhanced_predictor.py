import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from .models import Team, Match, TeamStats, HeadToHeadStats, Prediction
from .api_client import FootballApiClient

class EnhancedMatchPredictor:
    """Enhanced class for predicting football match outcomes with improved statistical models"""
    
    def __init__(self):
        """Initialize the predictor"""
        self.logger = logging.getLogger(__name__)
        self.api_client = FootballApiClient()
        self.most_likely_score = (0, 0)  # Will be set during prediction
        
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
    
    def calculate_form_factor(self, form_string: str) -> float:
        """Calculate a form factor from recent results"""
        if not form_string:
            return 1.0
            
        # Weight recent matches more heavily with exponential decay
        total_weight = 0
        form_value = 0
        
        for i, result in enumerate(reversed(form_string)):
            weight = math.exp(-0.2 * i)  # More recent matches have higher weight
            total_weight += weight
            
            if result == 'W':
                form_value += 1.2 * weight  # Win boosts expected goals
            elif result == 'D':
                form_value += 1.0 * weight  # Draw is neutral
            elif result == 'L':
                form_value += 0.8 * weight  # Loss reduces expected goals
        
        return form_value / total_weight if total_weight > 0 else 1.0
    
    def calculate_form_consistency(self, form_string: str) -> float:
        """Calculate how consistent a team's form has been"""
        if not form_string or len(form_string) < 3:
            return 0.7  # Default medium confidence with limited data
            
        # Count transitions (changes in form)
        transitions = 0
        for i in range(1, len(form_string)):
            if form_string[i] != form_string[i-1]:
                transitions += 1
                
        # More transitions = less consistency = lower confidence
        consistency = 1.0 - (transitions / (len(form_string) - 1)) * 0.5
        return max(0.5, min(1.0, consistency))  # Bound between 0.5 and 1.0
    
    def league_avg_home_goals(self) -> float:
        """Return the average number of goals scored by home teams in the league"""
        # This would ideally be calculated from league data
        # For now, using typical values from top European leagues
        return 1.5
    
    def league_avg_away_goals(self) -> float:
        """Return the average number of goals scored by away teams in the league"""
        # This would ideally be calculated from league data
        return 1.2
    
    def league_avg_home_conceded(self) -> float:
        """Return the average number of goals conceded by home teams"""
        return 1.2
    
    def league_avg_away_conceded(self) -> float:
        """Return the average number of goals conceded by away teams"""
        return 1.5
    
    def predict_over_under(self, home_stats: TeamStats, away_stats: TeamStats, threshold: float = 2.5) -> Dict[str, Any]:
        """Predict if the match will go over/under the goal threshold using enhanced statistical analysis"""
        try:
            from scipy.stats import poisson
            use_poisson = True
        except ImportError:
            self.logger.warning("scipy not available, using simplified over/under prediction")
            use_poisson = False
            
        # Calculate expected goals with weighted factors
        home_attack_strength = home_stats.avg_goals_scored / max(0.5, self.league_avg_home_goals())
        away_defense_weakness = away_stats.avg_goals_conceded / max(0.5, self.league_avg_away_conceded())
        away_attack_strength = away_stats.avg_goals_scored / max(0.5, self.league_avg_away_goals())
        home_defense_weakness = home_stats.avg_goals_conceded / max(0.5, self.league_avg_home_conceded())
        
        # Calculate expected goals using attack strength and defense weakness
        home_expected_goals = home_attack_strength * away_defense_weakness * self.league_avg_home_goals()
        away_expected_goals = away_attack_strength * home_defense_weakness * self.league_avg_away_goals()
        
        # Apply home advantage
        home_expected_goals *= 1.2
        away_expected_goals *= 0.85
        
        # Total expected goals
        expected_goals = home_expected_goals + away_expected_goals
        
        # Calculate probability using Poisson distribution if available
        if use_poisson:
            # Calculate probability of over threshold using Poisson distribution
            over_prob = 0.0
            max_goals = 10  # Consider up to 10 goals for each team
            
            for h in range(max_goals + 1):
                for a in range(max_goals + 1):
                    if h + a > threshold:
                        p_home = poisson.pmf(h, home_expected_goals)
                        p_away = poisson.pmf(a, away_expected_goals)
                        over_prob += p_home * p_away
                        
            probability = over_prob
        else:
            # Simplified calculation if scipy is not available
            probability = 0.5  # Base probability
            
            # Adjust based on expected goals
            if expected_goals > threshold:
                probability += 0.15 * (expected_goals - threshold)
            else:
                probability -= 0.15 * (threshold - expected_goals)
        
        # Additional factors that affect over/under
        
        # Team scoring patterns
        home_scoring_rate = 1 - (home_stats.failed_to_score / max(1, home_stats.matches_played))
        away_scoring_rate = 1 - (away_stats.failed_to_score / max(1, away_stats.matches_played))
        
        # Team defensive records
        home_clean_sheet_rate = home_stats.clean_sheets / max(1, home_stats.matches_played)
        away_clean_sheet_rate = away_stats.clean_sheets / max(1, away_stats.matches_played)
        
        # Adjust probability based on these factors
        if home_scoring_rate < 0.5 and away_scoring_rate < 0.5:
            probability -= 0.1  # Both teams struggle to score
        elif home_scoring_rate > 0.8 and away_scoring_rate > 0.8:
            probability += 0.1  # Both teams score consistently
            
        if home_clean_sheet_rate > 0.4 and away_clean_sheet_rate > 0.4:
            probability -= 0.1  # Both teams have solid defense
        
        # Ensure probability is between 0 and 1
        probability = max(0.0, min(1.0, probability))
        
        # Calculate confidence based on data quality
        confidence = 0.7  # Base confidence
        
        if home_stats.matches_played >= 10 and away_stats.matches_played >= 10:
            confidence += 0.2
        elif home_stats.matches_played >= 5 and away_stats.matches_played >= 5:
            confidence += 0.1
        
        # Higher confidence when probability is far from 0.5
        confidence += min(0.2, abs(probability - 0.5) * 0.4)
        
        # Ensure confidence is between 0 and 1
        confidence = max(0.0, min(1.0, confidence))
        
        return {
            'threshold': threshold,
            'prediction': probability > 0.5,
            'probability': round(probability * 100, 1),
            'expected_goals': round(expected_goals, 2),
            'confidence': round(confidence * 100, 1)
        }
    
    def predict_score(self, home_stats: TeamStats, away_stats: TeamStats, h2h_stats: HeadToHeadStats) -> Tuple[float, float, float]:
        """Predict match score based on team stats and head-to-head history using advanced statistical models"""
        try:
            from scipy.stats import poisson
            use_poisson = True
        except ImportError:
            self.logger.warning("scipy not available, using simplified score prediction")
            use_poisson = False
            
        # Base expected goals calculation with weighted factors
        home_attack_strength = home_stats.avg_goals_scored / max(0.5, self.league_avg_home_goals())
        away_defense_weakness = away_stats.avg_goals_conceded / max(0.5, self.league_avg_away_conceded())
        away_attack_strength = away_stats.avg_goals_scored / max(0.5, self.league_avg_away_goals())
        home_defense_weakness = home_stats.avg_goals_conceded / max(0.5, self.league_avg_home_conceded())
        
        # Calculate expected goals using attack strength and defense weakness
        home_expected_goals = home_attack_strength * away_defense_weakness * self.league_avg_home_goals()
        away_expected_goals = away_attack_strength * home_defense_weakness * self.league_avg_away_goals()
        
        # Apply form adjustment - recent form matters more
        if home_stats.form and len(home_stats.form) >= 5:
            home_form_factor = self.calculate_form_factor(home_stats.form[-5:])
            home_expected_goals *= home_form_factor
        
        if away_stats.form and len(away_stats.form) >= 5:
            away_form_factor = self.calculate_form_factor(away_stats.form[-5:])
            away_expected_goals *= away_form_factor
        
        # Adjust for home advantage - typically home teams score ~35% more
        home_expected_goals *= 1.2
        away_expected_goals *= 0.85
        
        # Adjust based on H2H history with recency weighting
        if h2h_stats and h2h_stats.total_matches > 0:
            h2h_home_goals = 0
            h2h_away_goals = 0
            h2h_weights_sum = 0
            
            # Sort matches by date, most recent first
            recent_matches = sorted(
                [m for m in h2h_stats.matches if m.home_score is not None and m.away_score is not None],
                key=lambda m: m.date if m.date else datetime.min,
                reverse=True
            )
            
            # Apply recency weighting - more recent matches have higher weight
            for i, match in enumerate(recent_matches[:5]):  # Consider only last 5 H2H matches
                # Exponential decay weight - most recent match has weight 1.0
                weight = math.exp(-0.3 * i)  # Decay factor of 0.3
                
                if match.home_team.id == home_stats.team_id:
                    h2h_home_goals += match.home_score * weight
                    h2h_away_goals += match.away_score * weight
                else:
                    h2h_home_goals += match.away_score * weight
                    h2h_away_goals += match.home_score * weight
                    
                h2h_weights_sum += weight
            
            if h2h_weights_sum > 0:
                h2h_home_avg = h2h_home_goals / h2h_weights_sum
                h2h_away_avg = h2h_away_goals / h2h_weights_sum
                
                # Blend current model with H2H history - H2H gets more weight if teams play often
                h2h_weight = min(0.4, 0.1 * min(h2h_stats.total_matches, 4))
                home_expected_goals = home_expected_goals * (1 - h2h_weight) + h2h_home_avg * h2h_weight
                away_expected_goals = away_expected_goals * (1 - h2h_weight) + h2h_away_avg * h2h_weight
        
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
        
        # Calculate most likely score using Poisson distribution if available
        if use_poisson:
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
                        
            self.most_likely_score = (most_likely_home_score, most_likely_away_score)
        else:
            # Simplified calculation if scipy is not available
            self.most_likely_score = (round(home_expected_goals), round(away_expected_goals))
        
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
            home_form_consistency = self.calculate_form_consistency(home_stats.form)
            away_form_consistency = self.calculate_form_consistency(away_stats.form)
            avg_form_consistency = (home_form_consistency + away_form_consistency) / 2
            confidence_factors.append(avg_form_consistency)
        
        # Calculate overall confidence - weighted average
        weights = [0.4, 0.3, 0.3]  # Matches played, H2H data, Form consistency
        confidence = sum(f * w for f, w in zip(confidence_factors, weights)) / sum(weights)
        
        return home_expected_goals, away_expected_goals, confidence
    
    def predict_match(self, match: Match) -> Optional[Prediction]:
        """Make a comprehensive prediction for a match using enhanced statistical models"""
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
            
            # Get the most likely score from the score prediction
            most_likely_home_score, most_likely_away_score = self.most_likely_score
            
            # Predict over/under for multiple thresholds
            over_under_predictions = {}
            thresholds = [1.5, 2.5, 3.5, 4.5]
            for threshold in thresholds:
                over_under_predictions[f"{threshold}"] = self.predict_over_under(home_stats, away_stats, threshold)
            
            # Predict match outcome based on the most likely score
            if most_likely_home_score > most_likely_away_score:
                outcome = "home"
            elif most_likely_home_score < most_likely_away_score:
                outcome = "away"
            else:
                outcome = "draw"
            
            # Calculate win probabilities using Poisson if available
            try:
                from scipy.stats import poisson
                
                home_win_prob = 0.0
                draw_prob = 0.0
                away_win_prob = 0.0
                max_goals = 10
                
                for h in range(max_goals + 1):
                    for a in range(max_goals + 1):
                        p_home = poisson.pmf(h, home_expected_goals)
                        p_away = poisson.pmf(a, away_expected_goals)
                        p_score = p_home * p_away
                        
                        if h > a:
                            home_win_prob += p_score
                        elif h < a:
                            away_win_prob += p_score
                        else:
                            draw_prob += p_score
            except ImportError:
                # Simplified calculation if scipy is not available
                total_goals = home_expected_goals + away_expected_goals
                if total_goals > 0:
                    home_win_prob = home_expected_goals / total_goals * 0.6
                    away_win_prob = away_expected_goals / total_goals * 0.6
                else:
                    home_win_prob = 0.45  # Default with home advantage
                    away_win_prob = 0.25
                
                draw_prob = 1.0 - home_win_prob - away_win_prob
            
            # Create prediction object
            prediction = Prediction(
                match=match,
                home_win_probability=home_win_prob,
                draw_probability=draw_prob,
                away_win_probability=away_win_prob,
                predicted_home_score=most_likely_home_score,
                predicted_away_score=most_likely_away_score,
                confidence=score_confidence,
                over_under_predictions=over_under_predictions
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
