import logging
import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from .models import Team, Match, TeamStats, HeadToHeadStats, Prediction
from .api_client import FootballApiClient

class EnhancedMatchPredictor:
    """Enhanced class for predicting football match outcomes with improved statistical models"""
    
    def __init__(self):
        """Initialize the predictor"""
        self.logger = logging.getLogger(__name__)
        self.api_client = FootballApiClient()
        self.most_likely_score = (0, 0)  # Will be set during prediction
        
    def _poisson_pmf(self, k: int, mu: float) -> float:
        """Calculate Poisson probability mass function"""
        if mu == 0:
            return 0.0
        return (math.exp(-mu) * (mu ** k)) / math.factorial(k if k < 20 else 19)
        
    def _calculate_form_consistency(self, form: str) -> float:
        """Calculate form consistency from form string (e.g., 'WWLWD')"""
        if not form or len(form) < 3:
            return 0.5  # Neutral if not enough data
            
        # Count wins, draws, losses in last 5 matches
        wins = form.upper().count('W')
        draws = form.upper().count('D')
        losses = form.upper().count('L')
        
        # More consistent if all results are the same
        consistency = 1.0 - (max(wins, draws, losses) / (wins + draws + losses))
        return 0.5 + (consistency * 0.5)  # Scale to 0.5-1.0 range
        
    def calculate_expected_goals(self, home_stats: TeamStats, away_stats: TeamStats, 
                               h2h_stats: HeadToHeadStats) -> Tuple[float, float, float]:
        """Calculate expected goals for home and away teams"""
        try:
            # Calculate average goals scored/conceded per match
            home_goals_per_match = home_stats.goals_scored / max(1, home_stats.matches_played)
            away_goals_per_match = away_stats.goals_scored / max(1, away_stats.matches_played)
            
            home_goals_conceded_per_match = home_stats.goals_conceded / max(1, home_stats.matches_played)
            away_goals_conceded_per_match = away_stats.goals_conceded / max(1, away_stats.matches_played)
            
            # Calculate attack and defense strengths
            league_avg_goals = 1.5  # This should be calculated from league data
            
            home_attack_strength = home_goals_per_match / league_avg_goals
            away_attack_strength = away_goals_per_match / league_avg_goals
            
            home_defense_strength = home_goals_conceded_per_match / league_avg_goals
            away_defense_strength = away_goals_conceded_per_match / league_avg_goals
            
            # Calculate expected goals
            home_expected_goals = home_attack_strength * away_defense_strength * league_avg_goals
            away_expected_goals = away_attack_strength * home_defense_strength * league_avg_goals
            
            # Adjust for home advantage (typically around 0.3 goals)
            home_expected_goals += 0.3
            
            # Consider head-to-head results
            if h2h_stats.total_matches > 0:
                h2h_weight = min(0.2, 5 / h2h_stats.total_matches)  # More weight with more H2H matches
                
                # Calculate average goals from H2H
                h2h_home_goals = h2h_stats.goals_for / max(1, h2h_stats.home_wins + h2h_stats.draws + h2h_stats.away_wins)
                h2h_away_goals = h2h_stats.goals_against / max(1, h2h_stats.home_wins + h2h_stats.draws + h2h_stats.away_wins)
                
                # Blend with current form
                home_expected_goals = (1 - h2h_weight) * home_expected_goals + h2h_weight * h2h_home_goals
                away_expected_goals = (1 - h2h_weight) * away_expected_goals + h2h_weight * h2h_away_goals
            
            # Calculate confidence based on data quality
            confidence_factors = []
            
            # Factor 1: Number of matches played
            min_matches = 5
            matches_factor = min(1.0, (home_stats.matches_played + away_stats.matches_played) / (2 * min_matches))
            confidence_factors.append(matches_factor)
            
            # Factor 2: Head-to-head data quality
            h2h_factor = min(1.0, h2h_stats.total_matches / 5)  # Full confidence at 5+ H2H matches
            confidence_factors.append(h2h_factor)
            
            # Factor 3: Form consistency
            home_form_consistency = self._calculate_form_consistency(home_stats.form)
            away_form_consistency = self._calculate_form_consistency(away_stats.form)
            avg_form_consistency = (home_form_consistency + away_form_consistency) / 2
            confidence_factors.append(avg_form_consistency)
            
            # Calculate overall confidence - weighted average
            weights = [0.4, 0.3, 0.3]  # Matches played, H2H data, Form consistency
            confidence = sum(f * w for f, w in zip(confidence_factors, weights)) / sum(weights)
            
            return home_expected_goals, away_expected_goals, confidence
            
        except Exception as e:
            self.logger.error(f"Error calculating expected goals: {str(e)}")
            return 1.5, 1.0, 0.5  # Default values in case of error
    
    def get_team_stats(self, team_id: int, league_id: int, season: int) -> Optional[TeamStats]:
        """Get comprehensive team statistics"""
        try:
            # Get team statistics from API
            stats_data = self.api_client.get_team_statistics(team_id, league_id, season)
            
            if not stats_data or 'response' not in stats_data:
                self.logger.error(f"No stats data for team {team_id}")
                return None
                
            # Extract relevant statistics
            stats = stats_data['response']
            team_info = stats.get('team', {})
            
            # Create TeamStats object
            team_stats = TeamStats(
                team_id=team_id,
                team_name=team_info.get('name', ''),
                matches_played=stats.get('fixtures', {}).get('played', {}).get('total', 0),
                wins=stats.get('fixtures', {}).get('wins', {}).get('total', 0),
                draws=stats.get('fixtures', {}).get('draws', {}).get('total', 0),
                losses=stats.get('fixtures', {}).get('loses', {}).get('total', 0),
                goals_scored=stats.get('goals', {}).get('for', {}).get('total', {}).get('total', 0),
                goals_conceded=stats.get('goals', {}).get('against', {}).get('total', {}).get('total', 0),
                clean_sheets=stats.get('clean_sheet', {}).get('home', 0) + stats.get('clean_sheet', {}).get('away', 0),
                failed_to_score=stats.get('failed_to_score', {}).get('total', 0),
                form=stats.get('form', '')
            )
            
            return team_stats
            
        except Exception as e:
            self.logger.error(f"Error getting team stats: {str(e)}")
            return None
    
    def get_h2h_stats(self, team1_id: int, team2_id: int) -> HeadToHeadStats:
        """Get head-to-head statistics between two teams"""
        try:
            # Get head-to-head data from API
            h2h_data = self.api_client.get_head_to_head(team1_id, team2_id)
            
            if not h2h_data or 'response' not in h2h_data:
                return HeadToHeadStats()
                
            # Process head-to-head matches
            matches = h2h_data['response']
            total_matches = len(matches)
            team1_wins = 0
            team2_wins = 0
            draws = 0
            team1_goals = 0
            team2_goals = 0
            
            for match in matches:
                home_goals = match['goals']['home']
                away_goals = match['goals']['away']
                
                if match['teams']['home']['id'] == team1_id:
                    team1_goals += home_goals
                    team2_goals += away_goals
                    if home_goals > away_goals:
                        team1_wins += 1
                    elif away_goals > home_goals:
                        team2_wins += 1
                    else:
                        draws += 1
                else:
                    team1_goals += away_goals
                    team2_goals += home_goals
                    if away_goals > home_goals:
                        team1_wins += 1
                    elif home_goals > away_goals:
                        team2_wins += 1
                    else:
                        draws += 1
            
            return HeadToHeadStats(
                total_matches=total_matches,
                home_wins=team1_wins,
                away_wins=team2_wins,
                draws=draws,
                goals_for=team1_goals,
                goals_against=team2_goals
            )
            
        except Exception as e:
            self.logger.error(f"Error getting H2H stats: {str(e)}")
            return HeadToHeadStats()
    
    def calculate_expected_goals(self, home_stats: TeamStats, away_stats: TeamStats, 
                               h2h_stats: HeadToHeadStats) -> Tuple[float, float, float]:
        """Calculate expected goals for home and away teams"""
        try:
            # Calculate average goals scored/conceded per match
            home_goals_per_match = home_stats.goals_scored / max(1, home_stats.matches_played)
            away_goals_per_match = away_stats.goals_scored / max(1, away_stats.matches_played)
            
            home_goals_conceded_per_match = home_stats.goals_conceded / max(1, home_stats.matches_played)
            away_goals_conceded_per_match = away_stats.goals_conceded / max(1, away_stats.matches_played)
            
            # Calculate attack and defense strengths
            league_avg_goals = 1.5  # This should be calculated from league data
            
            home_attack_strength = home_goals_per_match / league_avg_goals
            away_attack_strength = away_goals_per_match / league_avg_goals
            
            home_defense_strength = home_goals_conceded_per_match / league_avg_goals
            away_defense_strength = away_goals_conceded_per_match / league_avg_goals
            
            # Calculate expected goals
            home_expected_goals = home_attack_strength * away_defense_strength * league_avg_goals
            away_expected_goals = away_attack_strength * home_defense_strength * league_avg_goals
            
            # Adjust for home advantage (typically around 0.3 goals)
            home_expected_goals += 0.3
            
            # Consider head-to-head results
            if h2h_stats.total_matches > 0:
                h2h_weight = min(0.2, 5 / h2h_stats.total_matches)  # More weight with more H2H matches
                
                # Calculate average goals from H2H
                h2h_home_goals = h2h_stats.goals_for / max(1, h2h_stats.home_wins + h2h_stats.draws + h2h_stats.away_wins)
                h2h_away_goals = h2h_stats.goals_against / max(1, h2h_stats.home_wins + h2h_stats.draws + h2h_stats.away_wins)
                
                # Blend with current form
                home_expected_goals = (1 - h2h_weight) * home_expected_goals + h2h_weight * h2h_home_goals
                away_expected_goals = (1 - h2h_weight) * away_expected_goals + h2h_weight * h2h_away_goals
            
            # Calculate confidence based on data quality
            confidence_factors = []
            
            # Factor 1: Number of matches played
            min_matches = 5
            matches_factor = min(1.0, (home_stats.matches_played + away_stats.matches_played) / (2 * min_matches))
            confidence_factors.append(matches_factor)
            
            # Factor 2: Head-to-head data quality
            h2h_factor = min(1.0, h2h_stats.total_matches / 5)  # Full confidence at 5+ H2H matches
            confidence_factors.append(h2h_factor)
            
            # Factor 3: Form consistency
            def calculate_form_consistency(form: str) -> float:
                if not form or len(form) < 3:
                    return 0.5  # Neutral if not enough data
                
                # Count wins, draws, losses in last 5 matches
                wins = form.upper().count('W')
                draws = form.upper().count('D')
                losses = form.upper().count('L')
                
                # More consistent if all results are the same
                consistency = 1.0 - (max(wins, draws, losses) / (wins + draws + losses))
                return 0.5 + (consistency * 0.5)  # Scale to 0.5-1.0 range
            
            home_form_consistency = calculate_form_consistency(home_stats.form)
            away_form_consistency = calculate_form_consistency(away_stats.form)
            avg_form_consistency = (home_form_consistency + away_form_consistency) / 2
            confidence_factors.append(avg_form_consistency)
            
            # Calculate overall confidence - weighted average
            weights = [0.4, 0.3, 0.3]  # Matches played, H2H data, Form consistency
            confidence = sum(f * w for f, w in zip(confidence_factors, weights)) / sum(weights)
            
            return home_expected_goals, away_expected_goals, confidence
            
        except Exception as e:
            self.logger.error(f"Error calculating expected goals: {str(e)}")
            return 1.5, 1.0, 0.5  # Default values in case of error
    
    def predict_from_stats(self, home_stats: TeamStats, away_stats: TeamStats, h2h_stats: HeadToHeadStats) -> Optional[Prediction]:
        """Predict the outcome using pre-fetched stats"""
        try:
            # Calculate expected goals
            home_goals, away_goals, confidence = self.calculate_expected_goals(home_stats, away_stats, h2h_stats)
            
            # Calculate probabilities based on expected goals
            home_win_prob = 0.0
            draw_prob = 0.0
            away_win_prob = 0.0
            
            # Simple model: use Poisson distribution to estimate probabilities
            for home in range(0, 10):
                for away in range(0, 10):
                    # Calculate probability of this scoreline
                    prob = self._poisson_pmf(home, home_goals) * self._poisson_pmf(away, away_goals)
                    
                    # Update outcome probabilities
                    if home > away:
                        home_win_prob += prob
                    elif home == away:
                        draw_prob += prob
                    else:
                        away_win_prob += prob
            
            # Normalize probabilities (they might not sum to 1 due to the limited range)
            total = home_win_prob + draw_prob + away_win_prob
            if total > 0:
                home_win_prob /= total
                draw_prob /= total
                away_win_prob /= total
            
            # Create a dummy match object (in a real scenario, this would be the actual match)
            match = Match(
                id=0,  # Dummy ID
                home_team=Team(id=0, name=home_stats.team_name),
                away_team=Team(id=1, name=away_stats.team_name),
                date=datetime.now(),
                league_id=0,  # Dummy league ID
                league_name="Test League",
                country="Test Country",
                status="NS"  # Not started
            )
            
            # Create and return prediction
            prediction = Prediction(
                match=match,
                home_win_probability=home_win_prob,
                draw_probability=draw_prob,
                away_win_probability=away_win_prob,
                predicted_home_score=home_goals,
                predicted_away_score=away_goals,
                confidence=confidence
            )
            
            return prediction
            
        except Exception as e:
            self.logger.error(f"Error predicting match: {str(e)}")
            return None
    
    def get_upcoming_matches(self, leagues: Dict[str, Dict[str, Any]], days_ahead: int = 7) -> List[Match]:
        """Get upcoming matches for specified leagues"""
        try:
            matches = []
            
            # Calculate weekend dates (Saturday and Sunday)
            today = datetime.now()
            days_until_saturday = (5 - today.weekday()) % 7  # Saturday is weekday 5
            days_until_sunday = (6 - today.weekday()) % 7    # Sunday is weekday 6
            
            saturday = today + timedelta(days=days_until_saturday if days_until_saturday > 0 else 7)
            sunday = today + timedelta(days=days_until_sunday if days_until_sunday > 0 else 8)
            
            # Format dates for API
            from_date = saturday.strftime('%Y-%m-%d')
            to_date = sunday.strftime('%Y-%m-%d')
            
            for league_key, league_info in leagues.items():
                league_id = league_info['id']
                season = league_info['season']
                
                # Log the request details
                self.logger.info(f"Fetching fixtures for {league_key} (ID: {league_id}, Season: {season}) from {from_date} to {to_date}")
                
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
    
    def predict_upcoming_matches(self, leagues: Dict[str, Dict[str, Any]], days_ahead: int = 7) -> List[Prediction]:
        """Generate predictions for upcoming matches"""
        try:
            predictions = []
            
            # Get upcoming matches
            matches = self.get_upcoming_matches(leagues, days_ahead)
            
            if not matches:
                self.logger.warning("No upcoming matches found")
                return []
            
            # Generate prediction for each match
            for match in matches:
                try:
                    # Get team statistics
                    home_stats = self.get_team_stats(match.home_team.id, match.league_id, match.season)
                    away_stats = self.get_team_stats(match.away_team.id, match.league_id, match.season)
                    
                    if not home_stats or not away_stats:
                        self.logger.warning(f"Skipping match {match.home_team.name} vs {match.away_team.name} - missing team data")
                        continue
                    
                    # Get head-to-head statistics
                    h2h_stats = self.get_h2h_stats(match.home_team.id, match.away_team.id)
                    
                    # Generate prediction
                    prediction = self.predict_from_stats(home_stats, away_stats, h2h_stats)
                    
                    if prediction:
                        predictions.append(prediction)
                    
                except Exception as e:
                    self.logger.error(f"Error predicting match {match.home_team.name} vs {match.away_team.name}: {str(e)}")
            
            return predictions
            
        except Exception as e:
            self.logger.error(f"Error predicting upcoming matches: {str(e)}")
            return []

    def predict_match(self, match: Match) -> Optional[Prediction]:
        """Predict a match using match metadata (interface used by main analyzer)"""
        try:
            season = match.season or datetime.now().year
            home_stats = self.get_team_stats(match.home_team.id, match.league_id, season)
            away_stats = self.get_team_stats(match.away_team.id, match.league_id, season)
            
            if not home_stats or not away_stats:
                self.logger.warning(
                    "Missing stats for match %s vs %s", match.home_team.name, match.away_team.name
                )
                return None
            
            h2h_stats = self.get_h2h_stats(match.home_team.id, match.away_team.id)
            prediction = self.predict_from_stats(home_stats, away_stats, h2h_stats)
            return prediction
        except Exception as e:
            self.logger.error(
                f"Error predicting match {match.home_team.name} vs {match.away_team.name}: {str(e)}"
            )
            return None
