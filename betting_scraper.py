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
        
        # Verify API connection on initialization
        self._verify_api_connection()

    def _verify_api_connection(self):
        """Verify API connection and subscription status"""
        url = f"{self.base_url}/status"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()  # Raise an exception for bad status codes
            
            if response.status_code == 200:
                status_data = response.json()
                if status_data.get('errors'):
                    raise ValueError(f"API Error: {status_data['errors']}")
                print("API connection verified successfully")
                return True
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to connect to API: {str(e)}"
            if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 429:
                error_msg = "API rate limit exceeded. Please wait before making more requests."
            elif isinstance(e, requests.exceptions.ConnectionError):
                error_msg = "Could not connect to the API. Please check your internet connection."
            raise ConnectionError(error_msg)

    def get_premier_league_matches(self):
        """Get this week's Premier League matches"""
        url = f"{self.base_url}/fixtures"
        
        # Calculate this week's date range
        today = datetime.now()
        end_date = today + timedelta(days=7)  # Look ahead 7 days
        
        params = {
            'league': '39',
            'season': '2024',
            'from': today.strftime('%Y-%m-%d'),
            'to': end_date.strftime('%Y-%m-%d')
        }
        
        try:
            print(f"\nFetching Premier League matches from {today.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 403:
                print("\nAPI Access Error:")
                print("Your API subscription is not active. Please check:")
                print("1. You've subscribed to the API at: https://rapidapi.com/api-sports/api/api-football")
                print("2. Your API key is correct in the .env file")
                print("3. The subscription status in your RapidAPI dashboard")
                return []
                
            if response.status_code == 429:
                print("\nRate Limit Exceeded:")
                print("You've reached the API request limit. Please try again later.")
                return []
                
            response.raise_for_status()
            data = response.json()
            
            if data.get('response'):
                matches = []
                for match in data['response']:
                    matches.append({
                        'date': match['fixture']['date'].split('T')[0],
                        'time': match['fixture']['date'].split('T')[1][:5],
                        'home_team': match['teams']['home']['name'],
                        'away_team': match['teams']['away']['name'],
                        'home_team_id': match['teams']['home']['id'],
                        'away_team_id': match['teams']['away']['id'],
                        'league_round': match['league'].get('round', 'Unknown Round')
                    })
                
                # Sort matches by date and time
                matches.sort(key=lambda x: f"{x['date']} {x['time']}")
                
                if matches:
                    print(f"\nFound {len(matches)} matches this week:")
                    for match in matches:
                        print(f"{match['date']} {match['time']}: {match['home_team']} vs {match['away_team']} ({match['league_round']})")
                else:
                    print("\nNo matches scheduled for this week")
                
                return matches
            else:
                print("No matches found")
                if response.text:
                    print(f"API Response: {response.text}")
                return []
            
        except Exception as e:
            print(f"Error fetching Premier League matches: {str(e)}")
            if 'response' in locals():
                print(f"Response content: {response.text}")
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
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json().get('response', {})
        except Exception as e:
            print(f"Error getting team stats: {str(e)}")
            return {}

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
            print("No matches found for this week")
            return
            
        results = []
        print("\n⚽ Analyzing matches...")
        for match in tqdm(matches, desc="Analyzing matches", unit="match"):
            print(f"\n📊 Analyzing {match['home_team']} vs {match['away_team']} on {match['date']} at {match['time']}")
            
            # Get head-to-head data
            h2h_data = self.get_head_to_head(match['home_team_id'], match['away_team_id'])
            
            # Get team statistics
            home_stats = self.get_team_statistics(match['home_team_id'])
            away_stats = self.get_team_statistics(match['away_team_id'])
            
            # Make prediction
            prediction = self.predict_match(h2h_data, match['home_team'], match['away_team'], home_stats, away_stats)
            
            results.append({
                'date': match['date'],
                'time': match['time'],
                'home_team': match['home_team'],
                'away_team': match['away_team'],
                'prediction': prediction,
                'h2h_data': h2h_data,
                'home_stats': home_stats,
                'away_stats': away_stats
            })
            
            # Be nice to the API
            time.sleep(1)
            
        return results

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
            prediction = result['prediction']
            print(f"\n{result['home_team']} vs {result['away_team']} ({result['date']} {result['time']})")
            if isinstance(prediction, dict):
                print(f"Winner: {prediction['winner']} (Confidence: {prediction['confidence']:.1f}%)")
                print(f"Expected Goals: {result['home_team']}: {prediction['expected_goals']['home']}, {result['away_team']}: {prediction['expected_goals']['away']}")
                print(f"Predicted Score: {prediction['predicted_score']}")
                print("Reasoning:")
                for reason in prediction['reasoning']:
                    print(f"- {reason}")
            else:
                print(f"Prediction: {prediction}")

if __name__ == "__main__":
    main()
