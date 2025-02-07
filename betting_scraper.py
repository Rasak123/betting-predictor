import requests
from datetime import datetime, timedelta
import time
import os
from dotenv import load_dotenv
import json
from tqdm import tqdm
import logging

class BettingScraper:
    # Premier League configuration
    LEAGUES = {
        'premier_league': {
            'id': 39,  # Premier League ID
            'name': 'Premier League',
            'country': 'England',
            'season': 2024
        }
    }

    def __init__(self):
        """Initialize the scraper with API key"""
        load_dotenv()
        self.api_key = os.getenv('RAPIDAPI_KEY')
        if not self.api_key:
            raise ValueError("RAPIDAPI_KEY environment variable is not set. Please configure it in your environment variables.")
            
        self.base_url = "https://api-football-v1.p.rapidapi.com/v3"
        self.headers = {
            'X-RapidAPI-Key': self.api_key,
            'X-RapidAPI-Host': "api-football-v1.p.rapidapi.com"
        }
        
        # Print initialization info
        print(f"Initializing BettingScraper...")
        print(f"API Key present: {'Yes' if self.api_key else 'No'}")
        print(f"API Key length: {len(self.api_key) if self.api_key else 0}")
        
        # Verify API connection on initialization
        if not self._verify_api_connection():
            raise ConnectionError("Failed to verify API connection. Please check your API key and internet connection.")

        self.logger = logging.getLogger(__name__)

    def _verify_api_connection(self):
        """Verify API connection and subscription status"""
        url = f"{self.base_url}/timezone"  # Using timezone endpoint to verify connection
        try:
            print("Verifying API connection...")
            response = requests.get(url, headers=self.headers)
            
            # Print response details for debugging
            print(f"API Status Code: {response.status_code}")
            
            if response.status_code == 403:
                print("API Access Error: Invalid API key or subscription")
                return False
            elif response.status_code == 429:
                print("Rate Limit Error: Too many requests")
                return False
                
            response.raise_for_status()
            
            # If we get here, the connection is good
            print("API connection verified successfully")
            print(f"Requests remaining: {response.headers.get('X-RateLimit-requests-Remaining', 'Unknown')}")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"API Connection Error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Error Response: {e.response.text}")
            return False
        except Exception as e:
            print(f"Unexpected Error: {str(e)}")
            return False

    def _make_request(self, url, params=None, max_retries=3):
        """Make an API request with retries"""
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:  # Last attempt
                    self.logger.error(f"Failed to make request after {max_retries} attempts: {str(e)}")
                    raise
                self.logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                time.sleep(1)  # Wait before retrying

    def get_matches(self, league_keys, days_ahead=7):
        """
        Get matches for the specified leagues for the next N days
        Args:
            league_keys (list): List of league keys to get matches for
            days_ahead (int): Number of days ahead to get matches for, defaults to 7
        Returns:
            list: List of matches
        """
        self.logger.info(f"Getting matches for leagues: {league_keys} for next {days_ahead} days")
        
        if not isinstance(days_ahead, int) or days_ahead < 1:
            days_ahead = 7  # Default to 7 days if invalid value provided
            self.logger.warning(f"Invalid days_ahead value, using default: {days_ahead}")
            
        today = datetime.now()
        end_date = today + timedelta(days=days_ahead)
        from_date = today.strftime('%Y-%m-%d')
        to_date = end_date.strftime('%Y-%m-%d')
        
        self.logger.info(f"Date range: {from_date} to {to_date}")
        
        all_matches = []
        for league_key in league_keys:
            try:
                league_info = self.LEAGUES.get(league_key)
                if not league_info:
                    self.logger.error(f"Invalid league key: {league_key}")
                    continue
                
                self.logger.info(f"Fetching matches for league {league_key} (ID: {league_info['id']})")
                
                url = f"{self.base_url}/fixtures"
                params = {
                    'league': league_info['id'],
                    'from': from_date,
                    'to': to_date,
                    'season': league_info['season']
                }
                
                self.logger.info(f"Fetching matches for {league_info['name']} (Season {params['season']})")
                self.logger.debug(f"API Request - URL: {url}, Params: {params}")
                
                response_data = self._make_request(url, params)
                if not response_data:
                    continue
                    
                matches_data = response_data.get('response', [])
                self.logger.info(f"Found {len(matches_data)} matches for {league_key}")
                
                for match in matches_data:
                    match_data = {
                        'home_team': match['teams']['home']['name'],
                        'away_team': match['teams']['away']['name'],
                        'home_team_id': match['teams']['home']['id'],
                        'away_team_id': match['teams']['away']['id'],
                        'date': match['fixture']['date'],
                        'league': {
                            'name': league_info['name'],
                            'country': league_info['country']
                        }
                    }
                    all_matches.append(match_data)
                    
            except Exception as e:
                self.logger.error(f"Error fetching matches for {league_key}: {str(e)}")
                continue
                
        self.logger.info(f"Total matches found: {len(all_matches)}")
        return all_matches

    def get_head_to_head(self, team1_id, team2_id):
        """Get head-to-head history between two teams"""
        url = f"{self.base_url}/fixtures/headtohead"
        params = {
            'h2h': f"{team1_id}-{team2_id}",
            'last': 10  # Get last 10 matches
        }
        
        try:
            print(f"Fetching head-to-head data between teams {team1_id} and {team2_id}")
            return self._make_request(url, params)
        except Exception as e:
            print(f"Error fetching head-to-head data: {str(e)}")
            return None

    def get_team_statistics(self, team_id, season=2024):
        """Get team statistics for the current season"""
        url = f"{self.base_url}/teams/statistics"
        params = {
            'team': team_id,
            'league': self.LEAGUES['premier_league']['id'],
            'season': season
        }
        
        try:
            print(f"Fetching statistics for team {team_id}")
            response_data = self._make_request(url, params)
            if not response_data:
                return None
                
            stats = response_data.get('response', {})
            return {
                'form': stats.get('form', [])[-5:],  # Last 5 matches form
                'goals_scored': {
                    'total': stats.get('goals', {}).get('for', {}).get('total', {}).get('total', 0),
                    'average': stats.get('goals', {}).get('for', {}).get('average', {}).get('total', 0)
                },
                'goals_conceded': {
                    'total': stats.get('goals', {}).get('against', {}).get('total', {}).get('total', 0),
                    'average': stats.get('goals', {}).get('against', {}).get('average', {}).get('total', 0)
                },
                'clean_sheets': stats.get('clean_sheet', {}).get('total', 0),
                'failed_to_score': stats.get('failed_to_score', {}).get('total', 0),
                'corners': stats.get('statistics', {}).get('corners', {}).get('total', {}).get('total', 0),
                'fouls': stats.get('statistics', {}).get('fouls', {}).get('total', {}).get('total', 0)
            }
        except Exception as e:
            print(f"Error fetching team statistics: {str(e)}")
            return None

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
            print(f"Error in over/under prediction: {str(e)}")
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
            print(f"Error in BTTS prediction: {str(e)}")
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
            print(f"Error in first half prediction: {str(e)}")
            return {'prediction': 'UNKNOWN', 'confidence': 0}

    def analyze_match(self, match, h2h_data=None):
        """
        Analyze a match and provide predictions
        Args:
            match (dict): Match data including teams and fixture details
            h2h_data (dict): Head to head data between the teams
        Returns:
            dict: Match analysis and prediction
        """
        try:
            home_team = match['home_team']
            away_team = match['away_team']
            
            analysis = {
                'match': f"{home_team} vs {away_team}",
                'date': match['date'],
                'league': {
                    'name': 'Premier League',
                    'country': 'England'
                },
                'predictions': {
                    'over_under_2_5': {'prediction': 'UNKNOWN', 'confidence': 0},
                    'btts': {'prediction': 'UNKNOWN', 'confidence': 0},
                    'first_half': {'prediction': 'UNKNOWN', 'confidence': 0}
                },
                'head_to_head': [],
                'home_form': self.get_team_stats(match['home_team_id'], last_n_matches=10),
                'away_form': self.get_team_stats(match['away_team_id'], last_n_matches=10)
            }
            
            # Add head-to-head analysis if available
            if h2h_data and isinstance(h2h_data, dict) and 'response' in h2h_data:
                h2h_matches = h2h_data['response']
                if h2h_matches:
                    total_goals = 0
                    btts_count = 0
                    
                    # Process last 5 H2H matches
                    for match in h2h_matches[:5]:
                        home_goals = match['goals']['home'] or 0
                        away_goals = match['goals']['away'] or 0
                        total_goals += home_goals + away_goals
                        
                        if home_goals > 0 and away_goals > 0:
                            btts_count += 1
                            
                        # Add H2H match details
                        h2h_match = {
                            'date': match['fixture']['date'],
                            'home_team': match['teams']['home']['name'],
                            'away_team': match['teams']['away']['name'],
                            'score': f"{home_goals}-{away_goals}",
                            'winner': 'Draw' if home_goals == away_goals else (
                                match['teams']['home']['name'] if home_goals > away_goals 
                                else match['teams']['away']['name']
                            )
                        }
                        analysis['head_to_head'].append(h2h_match)
                    
                    avg_goals = total_goals / len(h2h_matches[:5])
                    btts_ratio = btts_count / len(h2h_matches[:5])
                    
                    # Over/Under prediction
                    analysis['predictions']['over_under_2_5'] = {
                        'prediction': 'OVER' if avg_goals > 2.5 else 'UNDER',
                        'confidence': min(100, round(abs(avg_goals - 2.5) * 20, 1))
                    }
                    
                    # BTTS prediction
                    analysis['predictions']['btts'] = {
                        'prediction': 'YES' if btts_ratio > 0.5 else 'NO',
                        'confidence': round(abs(btts_ratio - 0.5) * 200, 1)
                    }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing match {home_team} vs {away_team}: {str(e)}")
            return None

    def analyze_weekend_matches(self):
        """Analyze matches for the upcoming weekend across all supported leagues."""
        try:
            # Get all league keys from our LEAGUES dictionary
            league_keys = list(self.LEAGUES.keys())
            self.logger.info(f"Analyzing matches for leagues: {league_keys}")
            
            # Get matches for all leagues
            matches = self.get_matches(league_keys)
            if not matches:
                self.logger.warning("No matches found for the upcoming week")
                return []

            analyzed_matches = []
            for match in matches:
                try:
                    # Get head to head data
                    h2h_data = self.get_head_to_head(
                        match['home_team_id'],
                        match['away_team_id']
                    )

                    # Analyze the match
                    analysis = self.analyze_match(match, h2h_data)
                    if analysis:
                        analyzed_matches.append(analysis)
                except Exception as e:
                    self.logger.error(f"Error analyzing match {match['home_team']} vs {match['away_team']}: {str(e)}")
                    continue

            return analyzed_matches
        except Exception as e:
            self.logger.error(f"Error in analyze_weekend_matches: {str(e)}")
            raise

def main():
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
            print(f"\n{result['match']} ({result['date']}) in {result['league']['name']} ({result['league']['country']})")
            predictions = result['predictions']
            print(f"Over/Under 2.5: {predictions['over_under_2_5']['prediction']} (Confidence: {predictions['over_under_2_5']['confidence']:.1f}%)")
            print(f"BTTS: {predictions['btts']['prediction']} (Confidence: {predictions['btts']['confidence']:.1f}%)")
            print(f"First Half: {predictions['first_half']['prediction']} (Confidence: {predictions['first_half']['confidence']:.1f}%)")

if __name__ == "__main__":
    main()
