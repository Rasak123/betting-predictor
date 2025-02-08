import requests
from datetime import datetime, timedelta
import time
import os
from dotenv import load_dotenv
import json
from tqdm import tqdm
import logging

# Constants
LEAGUES = {
    'premier_league': {
        'id': 39,
        'name': 'Premier League',
        'country': 'England',
        'season': 2024  # 2024/2025 season
    }
}

class BettingScraper:
    def __init__(self):
        """Initialize the scraper with API credentials"""
        # Load environment variables
        load_dotenv()
        
        # Get API key - try both environment variable names
        self.api_key = os.getenv('API_KEY') or os.getenv('RAPIDAPI_KEY')
        if not self.api_key:
            raise ValueError("No API key found. Set either API_KEY or RAPIDAPI_KEY in your .env file")
            
        self.base_url = "https://api-football-v1.p.rapidapi.com/v3"
        self.headers = {
            'x-rapidapi-host': "api-football-v1.p.rapidapi.com",
            'x-rapidapi-key': self.api_key
        }
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.info("BettingScraper initialized")
        self.logger.info(f"API Key present and length: {len(self.api_key)}")
        
        # Verify API connection on initialization
        if not self._verify_api_connection():
            raise ConnectionError("Could not verify API connection. Please check your API key and try again.")

    def _verify_api_connection(self):
        """Verify API connection and subscription status"""
        url = f"{self.base_url}/timezone"  # Using timezone endpoint to verify connection
        try:
            self.logger.info("Verifying API connection...")
            response = requests.get(url, headers=self.headers)
            
            # Print response details for debugging
            self.logger.info(f"API Status Code: {response.status_code}")
            
            if response.status_code == 403:
                self.logger.error("API Access Error: Invalid API key or subscription")
                return False
            elif response.status_code == 429:
                self.logger.error("Rate Limit Error: Too many requests")
                return False
                
            response.raise_for_status()
            
            # If we get here, the connection is good
            self.logger.info("API connection verified successfully")
            self.logger.info(f"Requests remaining: {response.headers.get('X-RateLimit-requests-Remaining', 'Unknown')}")
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API Connection Error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                self.logger.error(f"Error Response: {e.response.text}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected Error: {str(e)}")
            return False

    def _make_request(self, url, params=None, max_retries=3):
        """Make API request with retries"""
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Making API request to {url}")
                self.logger.info(f"Params: {params}")
                
                response = requests.get(url, headers=self.headers, params=params)
                self.logger.info(f"API Response Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    if 'errors' in data:
                        self.logger.error(f"API returned errors: {data['errors']}")
                        return None
                    if 'response' not in data:
                        self.logger.error(f"Invalid API response format: {data}")
                        return None
                    return data
                elif response.status_code == 429:
                    self.logger.warning("API rate limit exceeded")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                else:
                    self.logger.error(f"API request failed with status {response.status_code}")
                    self.logger.error(f"Response: {response.text}")
                    return None
                    
            except Exception as e:
                self.logger.error(f"API request error: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None
                
        return None

    def get_matches(self, league_keys, days_ahead=7):
        """Get matches for specified leagues"""
        matches = []
        
        try:
            # Calculate date range
            today = datetime.now()
            end_date = today + timedelta(days=days_ahead)
            
            # Format dates for API
            from_date = today.strftime("%Y-%m-%d")
            to_date = end_date.strftime("%Y-%m-%d")
            
            self.logger.info(f"Searching for matches between {from_date} and {to_date}")
            self.logger.info(f"League keys: {league_keys}")
            
            for league_key in league_keys:
                if league_key not in LEAGUES:
                    self.logger.warning(f"Invalid league key: {league_key}")
                    continue
                    
                league = LEAGUES[league_key]
                self.logger.info(f"Fetching matches for {league['name']} (ID: {league['id']}, Season: {league['season']})")
                
                # Prepare API request
                url = f"{self.base_url}/fixtures"
                params = {
                    'league': str(league['id']),
                    'season': str(league['season']),
                    'from': from_date,
                    'to': to_date,
                    'timezone': 'Europe/London'
                }
                
                # Make API request
                response = self._make_request(url, params)
                if not response:
                    self.logger.error(f"No response received for {league['name']}")
                    continue
                
                # Process matches
                league_matches = response['response']
                self.logger.info(f"Found {len(league_matches)} matches for {league['name']}")
                
                for match in league_matches:
                    try:
                        fixture = match['fixture']
                        teams = match['teams']
                        league_info = match['league']
                        
                        # Log match details
                        self.logger.info(f"Processing match: {teams['home']['name']} vs {teams['away']['name']}")
                        self.logger.info(f"Match status: {fixture['status']['short']}")
                        self.logger.info(f"Match date: {fixture['date']}")
                        
                        # Validate match data
                        required_fields = {
                            'fixture': ['id', 'date', 'timestamp', 'status'],
                            'teams.home': ['id', 'name'],
                            'teams.away': ['id', 'name'],
                            'league': ['id', 'name', 'country']
                        }
                        
                        valid = True
                        for parent, fields in required_fields.items():
                            parent_obj = match
                            for part in parent.split('.'):
                                parent_obj = parent_obj.get(part, {})
                            
                            for field in fields:
                                if not parent_obj.get(field):
                                    self.logger.error(f"Missing required field: {parent}.{field}")
                                    valid = False
                                    break
                            
                            if not valid:
                                break
                                
                        if not valid:
                            continue
                        
                        match_date = datetime.strptime(fixture['date'], "%Y-%m-%dT%H:%M:%S%z")
                        match_date = match_date.replace(tzinfo=None)
                        
                        if match_date >= today:
                            match_data = {
                                'id': fixture['id'],
                                'date': fixture['date'],
                                'timestamp': fixture['timestamp'],
                                'home_team': teams['home']['name'],
                                'away_team': teams['away']['name'],
                                'home_team_id': teams['home']['id'],
                                'away_team_id': teams['away']['id'],
                                'league': league_info['name'],
                                'league_id': league_info['id'],
                                'country': league_info['country'],
                                'status': fixture['status']['short']
                            }
                            matches.append(match_data)
                            self.logger.info(f"Added match: {match_data['home_team']} vs {match_data['away_team']}")
                        else:
                            self.logger.info(f"Skipping match - before current date")
                            
                    except Exception as e:
                        self.logger.error(f"Error processing match: {str(e)}")
                        self.logger.error(f"Match data: {match}")
                        continue
                
                time.sleep(1)  # Rate limiting
                
        except Exception as e:
            self.logger.error(f"Error in get_matches: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            
        if not matches:
            self.logger.warning("No matches found")
            self.logger.info(f"Search parameters: dates {from_date} to {to_date}, leagues: {league_keys}")
        else:
            self.logger.info(f"Total matches found: {len(matches)}")
            
        return matches

    def get_head_to_head(self, team1_id, team2_id):
        """Get head-to-head history between two teams"""
        url = f"{self.base_url}/fixtures/headtohead"
        params = {
            'h2h': f"{team1_id}-{team2_id}",
            'last': 10  # Get last 10 matches
        }
        
        try:
            self.logger.info(f"Fetching head-to-head data between teams {team1_id} and {team2_id}")
            return self._make_request(url, params)
        except Exception as e:
            self.logger.error(f"Error fetching head-to-head data: {str(e)}")
            return None

    def get_team_statistics(self, team_id, league_id, season):
        """Get team statistics for a specific season"""
        try:
            url = f"{self.base_url}/teams/statistics"
            params = {
                'team': str(team_id),
                'league': str(league_id),
                'season': str(season)
            }
            
            self.logger.info(f"Getting team stats for team {team_id} in league {league_id} season {season}")
            response = self._make_request(url, params)
            
            if not response or 'response' not in response:
                self.logger.error(f"Invalid response for team stats: {response}")
                return None
                
            stats = response['response']
            if not stats:
                self.logger.error("No team statistics found")
                return None
                
            # Validate required fields
            required_fields = ['goals', 'clean_sheet', 'failed_to_score']
            for field in required_fields:
                if field not in stats:
                    self.logger.error(f"Missing required field in team stats: {field}")
                    return None
                    
            # Validate goals data
            goals = stats['goals']
            if not goals or 'for' not in goals or 'against' not in goals:
                self.logger.error("Invalid goals data in team stats")
                return None
                
            # Ensure all required nested fields exist
            for goal_type in ['for', 'against']:
                if not all(key in goals[goal_type] for key in ['total', 'average']):
                    self.logger.error(f"Missing goals {goal_type} data")
                    return None
                if not all(key in goals[goal_type]['total'] for key in ['home', 'away']):
                    self.logger.error(f"Missing home/away goals {goal_type} data")
                    return None
                if not all(key in goals[goal_type]['average'] for key in ['home', 'away']):
                    self.logger.error(f"Missing home/away average goals {goal_type} data")
                    return None
                    
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting team statistics: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def get_h2h_matches(self, team1_id, team2_id, limit=20):
        """Get head-to-head match history"""
        url = f"{self.base_url}/fixtures/headtohead"
        params = {
            'h2h': f"{team1_id}-{team2_id}",
            'last': str(limit)
        }
        
        response = self._make_request(url, params)
        if not response or 'response' not in response:
            return []
            
        return response['response']

    def get_team_stats(self, team_id, last_n_matches=10):
        """Get team statistics from last N matches"""
        url = f"{self.base_url}/fixtures"
        params = {
            'team': team_id,
            'last': last_n_matches,
            'status': 'FT'  # Only finished matches
        }
        
        response_data = self._make_request(url, params)
        if not response_data:
            return None
            
        matches = response_data.get('response', [])
        form_data = []
        
        for match in matches:
            is_home = match['teams']['home']['id'] == team_id
            team_score = match['goals']['home'] if is_home else match['goals']['away']
            opponent_score = match['goals']['away'] if is_home else match['goals']['home']
            opponent_name = match['teams']['away']['name'] if is_home else match['teams']['home']['name']
            
            result = 'W' if team_score > opponent_score else ('L' if team_score < opponent_score else 'D')
            
            match_data = {
                'date': match['fixture']['date'],
                'opponent': opponent_name,
                'score': f"{team_score}-{opponent_score}",
                'result': result,
                'venue': 'Home' if is_home else 'Away'
            }
            form_data.append(match_data)
            
        return form_data

    def predict_match(self, h2h_data, home_team, away_team, home_stats, away_stats):
        """Make a prediction based on head-to-head history, current form, and team statistics"""
        try:
            if not h2h_data or len(h2h_data) == 0:
                return "Insufficient data for prediction"
                
            # Analyze last 5 matches
            recent_matches = h2h_data[:5]
            home_wins = 0
            away_wins = 0
            draws = 0
            goals_scored = {'home': 0, 'away': 0}
            
            for match in recent_matches:
                if not match['score']:
                    continue
                    
                try:
                    home_score, away_score = map(int, match['score'].split('-'))
                    goals_scored['home'] += home_score
                    goals_scored['away'] += away_score
                    
                    if home_score > away_score:
                        home_wins += 1
                    elif away_score > home_score:
                        away_wins += 1
                    else:
                        draws += 1
                except (ValueError, TypeError):
                    continue
            
            num_matches = len(recent_matches)
            if num_matches == 0:
                return "Insufficient valid match data for prediction"
                
            # Calculate form points (W=3, D=1, L=0)
            def calculate_form_points(form_string):
                points = 0
                for result in form_string:
                    if result == 'W': points += 3
                    elif result == 'D': points += 1
                return points
                
            home_form_points = calculate_form_points(home_stats['form']) if home_stats else 0
            away_form_points = calculate_form_points(away_stats['form']) if away_stats else 0
            
            # Consider home advantage
            home_advantage = 1.2
            
            # Calculate predicted goals using current season stats and h2h history
            predicted_home_goals = (
                (float(home_stats['goals_scored']['average']) * 2 +  # Current season scoring rate (weighted double)
                 goals_scored['home'] / num_matches) * home_advantage  # H2H scoring rate
            ) / 3  # Average of both factors
            
            predicted_away_goals = (
                (float(away_stats['goals_scored']['average']) * 2 +  # Current season scoring rate (weighted double)
                 goals_scored['away'] / num_matches)  # H2H scoring rate
            ) / 3  # Average of both factors
            
            prediction = {
                'winner': None,
                'confidence': 0,
                'expected_goals': {
                    'home': round(predicted_home_goals, 1),
                    'away': round(predicted_away_goals, 1)
                },
                'predicted_score': None,
                'reasoning': []
            }
            
            # Calculate win probability based on multiple factors
            home_strength = (
                (home_form_points / 15) * 0.3 +  # Current form (30% weight)
                (home_wins / num_matches) * 0.3 +  # H2H record (30% weight)
                (float(home_stats['goals_scored']['average']) / 
                 (float(home_stats['goals_scored']['average']) + float(away_stats['goals_scored']['average']))) * 0.2 +  # Scoring ability (20% weight)
                (float(away_stats['goals_conceded']['average']) / 
                 (float(home_stats['goals_conceded']['average']) + float(away_stats['goals_conceded']['average']))) * 0.2  # Defensive ability (20% weight)
            ) if home_stats and away_stats else 0.5
            
            # Add home advantage
            home_strength *= home_advantage
            
            # Determine winner and confidence
            if home_strength > 0.55:  # Threshold for home win prediction
                prediction['winner'] = home_team
                prediction['confidence'] = round(home_strength * 100)
            elif home_strength < 0.45:  # Threshold for away win prediction
                prediction['winner'] = away_team
                prediction['confidence'] = round((1 - home_strength) * 100)
            else:
                prediction['winner'] = 'Draw'
                prediction['confidence'] = round((1 - abs(0.5 - home_strength)) * 100)
            
            # Predict final score (rounded to nearest whole number)
            prediction['predicted_score'] = f"{round(predicted_home_goals)}-{round(predicted_away_goals)}"
            
            # Build detailed reasoning
            if home_stats and away_stats:
                prediction['reasoning'].extend([
                    f"Current form (last 5): {home_team}: {home_stats['form']}, {away_team}: {away_stats['form']}",
                    f"Season goals scored per game: {home_team}: {float(home_stats['goals_scored']['average']):.1f}, {away_team}: {float(away_stats['goals_scored']['average']):.1f}",
                    f"Season goals conceded per game: {home_team}: {float(home_stats['goals_conceded']['average']):.1f}, {away_team}: {float(away_stats['goals_conceded']['average']):.1f}",
                    f"H2H Record (last {num_matches}): {home_team} wins: {home_wins}, {away_team} wins: {away_wins}, Draws: {draws}"
                ])
            
            return prediction
            
        except Exception as e:
            self.logger.error(f"Error predicting match: {str(e)}")
            return None

    def predict_over_under(self, home_stats, away_stats, threshold=2.5):
        """Predict if the match will go over/under the goal threshold"""
        try:
            # Calculate average goals
            home_scored = float(home_stats.get('goals', {}).get('for', {}).get('average', {}).get('total', 0))
            home_conceded = float(home_stats.get('goals', {}).get('against', {}).get('average', {}).get('total', 0))
            away_scored = float(away_stats.get('goals', {}).get('for', {}).get('average', {}).get('total', 0))
            away_conceded = float(away_stats.get('goals', {}).get('against', {}).get('average', {}).get('total', 0))
            
            # Predicted goals for this match
            expected_goals = (home_scored + away_conceded + away_scored + home_conceded) / 2
            
            return {
                'prediction': 'OVER' if expected_goals > threshold else 'UNDER',
                'confidence': abs(expected_goals - threshold) / threshold * 100,
                'expected_goals': round(expected_goals, 2)
            }
        except Exception as e:
            self.logger.error(f"Error in over/under prediction: {str(e)}")
            return {'prediction': 'UNKNOWN', 'confidence': 0, 'expected_goals': 0}

    def predict_btts(self, home_stats, away_stats):
        """Predict if both teams will score"""
        try:
            # Get BTTS percentages from recent matches
            home_btts = float(home_stats.get('goals', {}).get('both_teams_score', {}).get('percentage', 0))
            away_btts = float(away_stats.get('goals', {}).get('both_teams_score', {}).get('percentage', 0))
            
            # Average BTTS probability
            btts_probability = (home_btts + away_btts) / 2
            
            return {
                'prediction': 'YES' if btts_probability > 50 else 'NO',
                'confidence': btts_probability if btts_probability > 50 else 100 - btts_probability
            }
        except Exception as e:
            self.logger.error(f"Error in BTTS prediction: {str(e)}")
            return {'prediction': 'UNKNOWN', 'confidence': 0}

    def predict_first_half(self, home_stats, away_stats):
        """Predict first half result"""
        try:
            # Get first half goals
            home_first_half = float(home_stats.get('goals', {}).get('for', {}).get('minute', {}).get('0-45', {}).get('percentage', 0))
            away_first_half = float(away_stats.get('goals', {}).get('for', {}).get('minute', {}).get('0-45', {}).get('percentage', 0))
            
            # Compare first half scoring tendencies
            prediction = 'HOME' if home_first_half > away_first_half else 'AWAY'
            confidence = abs(home_first_half - away_first_half)
            
            return {
                'prediction': prediction,
                'confidence': confidence,
                'home_first_half_goals': home_first_half,
                'away_first_half_goals': away_first_half
            }
        except Exception as e:
            self.logger.error(f"Error in first half prediction: {str(e)}")
            return {'prediction': 'UNKNOWN', 'confidence': 0}

    def calculate_form_points(self, form_data):
        """Calculate form points from recent matches"""
        if not form_data:
            return 0
            
        points = 0
        for match in form_data:
            if match['result'] == 'W':
                points += 3
            elif match['result'] == 'D':
                points += 1
                
        # Convert to a score out of 10
        max_points = len(form_data) * 3
        return round((points / max_points) * 10, 1)

    def predict_score(self, home_form, away_form, h2h_matches):
        """Predict match score based on form and head-to-head"""
        try:
            # Calculate average goals
            home_goals = 0
            away_goals = 0
            h2h_home_goals = 0
            h2h_away_goals = 0
            
            # Calculate from recent form
            for match in home_form or []:
                goals = int(match['score'].split('-')[0])
                home_goals += goals
            
            for match in away_form or []:
                goals = int(match['score'].split('-')[0])
                away_goals += goals
                
            # Calculate from H2H
            if h2h_matches:
                for match in h2h_matches[:5]:  # Last 5 H2H matches
                    h2h_home_goals += match['goals']['home'] or 0
                    h2h_away_goals += match['goals']['away'] or 0
                    
                # Weight H2H more heavily
                home_avg = ((home_goals / len(home_form) if home_form else 1.5) + 
                          (2 * h2h_home_goals / len(h2h_matches[:5]) if h2h_matches else 1.5)) / 3
                away_avg = ((away_goals / len(away_form) if away_form else 1.5) + 
                          (2 * h2h_away_goals / len(h2h_matches[:5]) if h2h_matches else 1.5)) / 3
            else:
                home_avg = home_goals / len(home_form) if home_form else 1.5
                away_avg = away_goals / len(away_form) if away_form else 1.5
            
            # Round to nearest 0.5 for more realistic scores
            predicted_home = round(home_avg * 2) / 2
            predicted_away = round(away_avg * 2) / 2
            
            return {
                'home_score': int(predicted_home),
                'away_score': int(predicted_away),
                'confidence': min(100, round((1 - abs(predicted_home - int(predicted_home)) - 
                                           abs(predicted_away - int(predicted_away))) * 100))
            }
            
        except Exception as e:
            self.logger.error(f"Error predicting score: {str(e)}")
            return {'home_score': 1, 'away_score': 1, 'confidence': 0}

    def predict_winner(self, home_form, away_form, h2h_matches):
        """Predict match winner based on form and head-to-head"""
        try:
            # Calculate form points (out of 10)
            home_form_points = self.calculate_form_points(home_form)
            away_form_points = self.calculate_form_points(away_form)
            
            # Calculate H2H points
            h2h_points = {'home': 0, 'away': 0}
            if h2h_matches:
                for match in h2h_matches[:5]:  # Last 5 H2H matches
                    home_goals = match['goals']['home'] or 0
                    away_goals = match['goals']['away'] or 0
                    if home_goals > away_goals:
                        h2h_points['home'] += 2
                    elif away_goals > home_goals:
                        h2h_points['away'] += 2
                    else:
                        h2h_points['home'] += 1
                        h2h_points['away'] += 1
                        
                # Convert H2H points to score out of 10
                max_h2h_points = len(h2h_matches[:5]) * 2
                h2h_home_points = (h2h_points['home'] / max_h2h_points) * 10
                h2h_away_points = (h2h_points['away'] / max_h2h_points) * 10
                
                # Combine form and H2H (60% form, 40% H2H)
                home_score = (0.6 * home_form_points) + (0.4 * h2h_home_points)
                away_score = (0.6 * away_form_points) + (0.4 * h2h_away_points)
            else:
                # Use only form if no H2H data
                home_score = home_form_points
                away_score = away_form_points
            
            # Calculate win probability
            total_points = home_score + away_score
            if total_points == 0:
                home_prob = away_prob = 0.33
                draw_prob = 0.34
            else:
                home_prob = home_score / total_points * 0.8  # 80% of probability split between teams
                away_prob = away_score / total_points * 0.8
                draw_prob = 0.2  # 20% chance of draw
                
            # Determine prediction
            probs = [
                ('HOME', home_prob),
                ('DRAW', draw_prob),
                ('AWAY', away_prob)
            ]
            prediction = max(probs, key=lambda x: x[1])
            
            return {
                'prediction': prediction[0],
                'probabilities': {
                    'home': round(home_prob * 100, 1),
                    'draw': round(draw_prob * 100, 1),
                    'away': round(away_prob * 100, 1)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error predicting winner: {str(e)}")
            return {'prediction': 'UNKNOWN', 'probabilities': {'home': 0, 'draw': 0, 'away': 0}}

    def analyze_match(self, match):
        """Perform deep analysis of a match"""
        try:
            # Validate match data
            required_match_fields = ['home_team_id', 'away_team_id', 'league_id']
            for field in required_match_fields:
                if field not in match:
                    self.logger.error(f"Missing required field in match data: {field}")
                    return None
            
            # Get team statistics
            home_stats = self.get_team_statistics(match['home_team_id'], match['league_id'], LEAGUES['premier_league']['season'])
            away_stats = self.get_team_statistics(match['away_team_id'], match['league_id'], LEAGUES['premier_league']['season'])
            
            if not home_stats or not away_stats:
                self.logger.error("Could not get team statistics")
                return None
            
            # Analyze home team performance
            try:
                home_form = {
                    'goals_scored': home_stats['goals']['for']['total']['home'] or 0,
                    'goals_conceded': home_stats['goals']['against']['total']['home'] or 0,
                    'clean_sheets': home_stats['clean_sheet']['home'] or 0,
                    'failed_to_score': home_stats['failed_to_score']['home'] or 0,
                    'avg_goals_scored': round(float(home_stats['goals']['for']['average']['home'] or 0), 2),
                    'avg_goals_conceded': round(float(home_stats['goals']['against']['average']['home'] or 0), 2)
                }
            except (KeyError, TypeError) as e:
                self.logger.error(f"Error processing home team stats: {str(e)}")
                return None
            
            # Analyze away team performance
            try:
                away_form = {
                    'goals_scored': away_stats['goals']['for']['total']['away'] or 0,
                    'goals_conceded': away_stats['goals']['against']['total']['away'] or 0,
                    'clean_sheets': away_stats['clean_sheet']['away'] or 0,
                    'failed_to_score': away_stats['failed_to_score']['away'] or 0,
                    'avg_goals_scored': round(float(away_stats['goals']['for']['average']['away'] or 0), 2),
                    'avg_goals_conceded': round(float(away_stats['goals']['against']['average']['away'] or 0), 2)
                }
            except (KeyError, TypeError) as e:
                self.logger.error(f"Error processing away team stats: {str(e)}")
                return None
            
            # Analyze H2H history
            h2h_stats = {
                'total_matches': 0,
                'home_wins': 0,
                'away_wins': 0,
                'draws': 0,
                'over_1_5': 0,
                'over_4_5': 0,
                'home_won_half': 0
            }
            
            h2h_matches = self.get_h2h_matches(match['home_team_id'], match['away_team_id'])
            if h2h_matches:
                for h2h in h2h_matches:
                    home_score = h2h['goals']['home']
                    away_score = h2h['goals']['away']
                    total_goals = home_score + away_score
                    
                    if home_score > away_score:
                        h2h_stats['home_wins'] += 1
                    elif away_score > home_score:
                        h2h_stats['away_wins'] += 1
                    else:
                        h2h_stats['draws'] += 1
                        
                    if total_goals > 1.5:
                        h2h_stats['over_1_5'] += 1
                    if total_goals > 4.5:
                        h2h_stats['over_4_5'] += 1
                        
                    # Check if home team won either half
                    try:
                        if h2h['score'] and h2h['score']['halftime'] and h2h['score']['fulltime']:
                            ht_home = h2h['score']['halftime']['home'] or 0
                            ht_away = h2h['score']['halftime']['away'] or 0
                            ft_home = h2h['score']['fulltime']['home'] or 0
                            ft_away = h2h['score']['fulltime']['away'] or 0
                            
                            # Check first half
                            if ht_home > ht_away:
                                h2h_stats['home_won_half'] += 1
                            # Check second half
                            elif (ft_home - ht_home) > (ft_away - ht_away):
                                h2h_stats['home_won_half'] += 1
                    except (KeyError, TypeError):
                        self.logger.warning("Missing score data in H2H match")
                        continue
                
                h2h_stats['total_matches'] = len(h2h_matches)
            
            # Calculate prediction confidence
            confidence_factors = {
                'recent_form': 0.35,  # Increased since we removed corners
                'h2h_history': 0.3,   # Increased since we removed corners
                'goals_scored': 0.2,
                'defense': 0.15
            }
            
            # Calculate form-based confidence
            home_form_score = (home_form['avg_goals_scored'] * 2 - home_form['avg_goals_conceded']) * 10
            away_form_score = (away_form['avg_goals_scored'] * 2 - away_form['avg_goals_conceded']) * 10
            
            # Calculate H2H-based confidence
            h2h_ratio = h2h_stats['home_wins'] / max(1, h2h_stats['total_matches'])
            
            # Combined confidence calculation
            confidence = (
                (home_form_score * confidence_factors['recent_form']) +
                (h2h_ratio * 100 * confidence_factors['h2h_history']) +
                (home_form['avg_goals_scored'] * 10 * confidence_factors['goals_scored']) +
                ((1 - home_form['avg_goals_conceded']/3) * 100 * confidence_factors['defense'])
            )
            
            # Cap confidence between 0 and 100
            confidence = max(0, min(100, confidence))
            
            # Make predictions
            predicted_home_goals = round((home_form['avg_goals_scored'] + away_form['avg_goals_conceded']) / 2)
            predicted_away_goals = round((away_form['avg_goals_scored'] + home_form['avg_goals_conceded']) / 2)
            
            # Predict over/under
            total_predicted_goals = predicted_home_goals + predicted_away_goals
            over_1_5_prob = (h2h_stats['over_1_5'] / h2h_stats['total_matches']) * 100
            over_4_5_prob = (h2h_stats['over_4_5'] / h2h_stats['total_matches']) * 100
            
            # Predict home team winning either half
            home_half_win_prob = (h2h_stats['home_won_half'] / h2h_stats['total_matches']) * 100
            
            return {
                'home_form': home_form,
                'away_form': away_form,
                'h2h_stats': h2h_stats,
                'confidence': round(confidence, 2),
                'predicted_score': {
                    'home': predicted_home_goals,
                    'away': predicted_away_goals
                },
                'predictions': {
                    'over_1_5': {
                        'probability': round(over_1_5_prob, 2),
                        'prediction': over_1_5_prob > 60
                    },
                    'over_4_5': {
                        'probability': round(over_4_5_prob, 2),
                        'prediction': over_4_5_prob > 50
                    },
                    'home_win_either_half': {
                        'probability': round(home_half_win_prob, 2),
                        'prediction': home_half_win_prob > 50
                    }
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing match: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def analyze_weekend_matches(self):
        """Analyze matches for the upcoming weekend across all supported leagues."""
        try:
            # Get all league keys from our LEAGUES dictionary
            league_keys = list(LEAGUES.keys())
            self.logger.info(f"Analyzing matches for leagues: {league_keys}")
            
            # Get matches for all leagues
            matches = self.get_matches(league_keys)
            if not matches:
                self.logger.warning("No matches found for analysis")
                return []
                
            self.logger.info(f"Found {len(matches)} matches to analyze")
            
            # Analyze each match
            predictions = []
            for match in matches:
                try:
                    self.logger.info(f"Analyzing match: {match['home_team']} vs {match['away_team']}")
                    
                    # Analyze match
                    prediction = self.analyze_match(match)
                    if prediction:
                        predictions.append(prediction)
                    else:
                        self.logger.warning(f"Failed to analyze match: {match['home_team']} vs {match['away_team']}")
                        
                except Exception as e:
                    self.logger.error(f"Error analyzing match: {str(e)}")
                    continue
            
            self.logger.info(f"Successfully analyzed {len(predictions)} matches")
            return predictions
            
        except Exception as e:
            self.logger.error(f"Error in analyze_weekend_matches: {str(e)}")
            return []

def main():
    try:
        scraper = BettingScraper()
        results = scraper.analyze_weekend_matches()
        
        if results:
            # Save results to a JSON file
            output_file = 'predictions.json'
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=4)
            print(f"\nPredictions saved to {output_file}")
            
            # Print summary
            print("\nMatch Predictions Summary:")
            for result in results:
                try:
                    print(f"\n{result['home_team']} vs {result['away_team']} ({result['league']})")
                    predictions = result['predictions']
                    
                    # Print predictions with error handling
                    try:
                        print(f"Over/Under 2.5: {predictions['over_1_5']['prediction']} (Confidence: {predictions['over_1_5']['probability']:.1f}%)")
                    except (KeyError, TypeError):
                        print("Over/Under 2.5: Not available")
                        
                    try:
                        print(f"BTTS: {predictions['btts']['prediction']} (Confidence: {predictions['btts']['confidence']:.1f}%)")
                    except (KeyError, TypeError):
                        print("BTTS: Not available")
                        
                    try:
                        print(f"First Half: {predictions['first_half']['prediction']} (Confidence: {predictions['first_half']['confidence']:.1f}%)")
                    except (KeyError, TypeError):
                        print("First Half: Not available")
                        
                    try:
                        outcome = predictions['match_outcome']
                        if isinstance(outcome, dict) and 'prediction' in outcome:
                            print(f"Match Outcome: {outcome['prediction']} (Confidence: {outcome['probabilities'].get(outcome['prediction'].lower(), 0):.1f}%)")
                        else:
                            print("Match Outcome: Not available")
                    except (KeyError, TypeError, AttributeError):
                        print("Match Outcome: Not available")
                        
                    try:
                        score = predictions['score']
                        if isinstance(score, dict) and 'home_score' in score:
                            print(f"Score: {score['home_score']}-{score['away_score']} (Confidence: {score['confidence']:.1f}%)")
                        else:
                            print("Score: Not available")
                    except (KeyError, TypeError):
                        print("Score: Not available")
                        
                except Exception as e:
                    print(f"Error printing match result: {str(e)}")
                    continue
        else:
            print("\nNo predictions available.")
            
    except Exception as e:
        print(f"\nError running predictions: {str(e)}")
        raise

if __name__ == "__main__":
    main()
