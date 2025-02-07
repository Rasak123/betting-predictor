import requests
from datetime import datetime, timedelta
import time
import os
from dotenv import load_dotenv
import json
from tqdm import tqdm

class BettingScraper:
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
        
        # Premier League ID in API-Football
        self.premier_league_id = 39
        
        # Print initialization info
        print(f"Initializing BettingScraper...")
        print(f"API Key present: {'Yes' if self.api_key else 'No'}")
        print(f"API Key length: {len(self.api_key) if self.api_key else 0}")
        
        # Verify API connection on initialization
        if not self._verify_api_connection():
            raise ConnectionError("Failed to verify API connection. Please check your API key and internet connection.")

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

    def get_premier_league_matches(self):
        """Get this week's Premier League matches"""
        # Calculate date range for this week
        today = datetime.now()
        end_date = today + timedelta(days=7)
        
        # Format dates for API
        from_date = today.strftime('%Y-%m-%d')
        to_date = end_date.strftime('%Y-%m-%d')
        
        url = f"{self.base_url}/fixtures"
        params = {
            'league': self.premier_league_id,
            'from': from_date,
            'to': to_date,
            'season': 2023  # Current season
        }
        
        try:
            print(f"Fetching matches from {from_date} to {to_date}")
            response = requests.get(url, headers=self.headers, params=params)
            
            # Handle specific API errors
            if response.status_code == 403:
                print("API Access Error: Your API key might be invalid or subscription inactive")
                return []
            elif response.status_code == 429:
                print("Rate Limit Error: Too many requests. Please wait before trying again")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            if 'response' in data:
                matches = data['response']
                print(f"Found {len(matches)} matches")
                return matches
            elif 'errors' in data:
                print(f"API Error: {data['errors']}")
                return []
            else:
                print(f"Unexpected API response format: {data}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"Request Error: {str(e)}")
            return []
        except ValueError as e:
            print(f"JSON Parsing Error: {str(e)}")
            return []
        except Exception as e:
            print(f"Unexpected Error: {str(e)}")
            return []

    def get_head_to_head(self, team1_id, team2_id):
        """Get head-to-head history between two teams"""
        url = f"{self.base_url}/fixtures/headtohead"
        params = {
            'h2h': f"{team1_id}-{team2_id}",
            'last': 10  # Get last 10 matches
        }
        
        try:
            print(f"Fetching head-to-head data between teams {team1_id} and {team2_id}")
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get('response'):
                h2h_matches = []
                for match in data['response']:
                    # Determine scores relative to team1
                    if match['teams']['home']['id'] == team1_id:
                        team1_score = match['goals']['home'] or 0
                        team2_score = match['goals']['away'] or 0
                    else:
                        team1_score = match['goals']['away'] or 0
                        team2_score = match['goals']['home'] or 0
                    
                    h2h_matches.append({
                        'date': match['fixture']['date'].split('T')[0],
                        'score': f"{team1_score}-{team2_score}",
                        'competition': match['league']['name']
                    })
                return h2h_matches
            else:
                print("No head-to-head matches found")
                if 'response' in locals():
                    print(f"Response content: {response.text}")
                return []
            
        except Exception as e:
            print(f"Error fetching head-to-head data: {str(e)}")
            if 'response' in locals():
                print(f"Response content: {response.text}")
            return None

    def get_team_statistics(self, team_id, season=2024):
        """Get team statistics for the current season"""
        url = f"{self.base_url}/teams/statistics"
        params = {
            'team': team_id,
            'league': self.premier_league_id,
            'season': season
        }
        
        try:
            print(f"Fetching statistics for team {team_id}")
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get('response'):
                stats = data['response']
                return {
                    'form': stats['form'][-5:],  # Last 5 matches form
                    'goals_scored': {
                        'total': stats['goals']['for']['total']['total'],
                        'average': stats['goals']['for']['average']['total']
                    },
                    'goals_conceded': {
                        'total': stats['goals']['against']['total']['total'],
                        'average': stats['goals']['against']['average']['total']
                    },
                    'clean_sheets': stats['clean_sheet']['total'],
                    'failed_to_score': stats['failed_to_score']['total'],
                    'corners': stats.get('statistics', {}).get('corners', {}).get('total', {}).get('total', 0),
                    'fouls': stats.get('statistics', {}).get('fouls', {}).get('total', {}).get('total', 0)
                }
            return None
            
        except Exception as e:
            print(f"Error fetching team statistics: {str(e)}")
            return None

    def get_team_stats(self, team_id, last_n_matches=10):
        """Get team statistics from last N matches"""
        url = f"{self.base_url}/teams/statistics"
        params = {
            'team': team_id,
            'league': self.premier_league_id,
            'season': 2023,
            'last': last_n_matches
        }
        
        try:
            print(f"Fetching stats for team {team_id}")
            response = requests.get(url, headers=self.headers, params=params)
            
            # Handle specific API errors
            if response.status_code == 403:
                print("API Access Error: Your API key might be invalid or subscription inactive")
                return {}
            elif response.status_code == 429:
                print("Rate Limit Error: Too many requests. Please wait before trying again")
                return {}
            
            response.raise_for_status()
            data = response.json()
            
            if 'response' in data:
                return data['response']
            elif 'errors' in data:
                print(f"API Error: {data['errors']}")
                return {}
            else:
                print(f"Unexpected API response format: {data}")
                return {}
                
        except requests.exceptions.RequestException as e:
            print(f"Request Error: {str(e)}")
            return {}
        except ValueError as e:
            print(f"JSON Parsing Error: {str(e)}")
            return {}
        except Exception as e:
            print(f"Unexpected Error: {str(e)}")
            return {}

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

    def analyze_match(self, match):
        """Enhanced match analysis with additional predictions"""
        try:
            home_team = match['teams']['home']
            away_team = match['teams']['away']
            
            # Get detailed stats for both teams
            home_stats = self.get_team_stats(home_team['id'])
            away_stats = self.get_team_stats(away_team['id'])
            
            # Generate all predictions
            over_under = self.predict_over_under(home_stats, away_stats)
            btts = self.predict_btts(home_stats, away_stats)
            first_half = self.predict_first_half(home_stats, away_stats)
            
            return {
                'match': f"{home_team['name']} vs {away_team['name']}",
                'date': match['fixture']['date'],
                'predictions': {
                    'over_under_2_5': over_under,
                    'btts': btts,
                    'first_half': first_half
                }
            }
        except Exception as e:
            print(f"Error analyzing match: {str(e)}")
            return None

    def analyze_weekend_matches(self):
        """Analyze all Premier League matches for this week"""
        matches = self.get_premier_league_matches()
        if not matches:
            return []

        predictions = []
        for match in tqdm(matches, desc="Analyzing matches", unit="match"):
            prediction = self.analyze_match(match)
            if prediction:
                predictions.append(prediction)

        return predictions

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
            prediction = result['predictions']
            print(f"\n{result['match']} ({result['date']})")
            print(f"Over/Under 2.5: {prediction['over_under_2_5']['prediction']} (Confidence: {prediction['over_under_2_5']['confidence']:.1f}%)")
            print(f"BTTS: {prediction['btts']['prediction']} (Confidence: {prediction['btts']['confidence']:.1f}%)")
            print(f"First Half: {prediction['first_half']['prediction']} (Confidence: {prediction['first_half']['confidence']:.1f}%)")

if __name__ == "__main__":
    main()
