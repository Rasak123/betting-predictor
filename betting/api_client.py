import requests
import logging
import time
import os
from dotenv import load_dotenv

class FootballApiClient:
    """Client for interacting with the Football API"""
    
    def __init__(self):
        """Initialize the API client with credentials"""
        # Set up logging first
        self.logger = logging.getLogger(__name__)
        
        # Load environment variables from .env.local first, then .env
        load_dotenv('.env.local')  # Try loading from .env.local first
        load_dotenv()  # Fall back to .env if .env.local doesn't exist
        
        # Get API key - try multiple environment variable names for compatibility
        self.api_key = os.getenv('FOOTBALL_API_KEY') or os.getenv('RAPIDAPI_KEY') or os.getenv('API_KEY')
        
        # Log which file was loaded (for debugging)
        if os.path.exists('.env.local'):
            self.logger.info("Loaded environment variables from .env.local")
        elif os.path.exists('.env'):
            self.logger.info("Loaded environment variables from .env")
        else:
            self.logger.warning("No .env or .env.local file found")
        
        # Check if API key is available
        if not self.api_key:
            raise ValueError("No API key found. Please set FOOTBALL_API_KEY in your .env file")
            
        # For v3 API, we need to use the API-SPORTS endpoint
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {
            'x-rapidapi-host': "v3.football.api-sports.io",
            'x-rapidapi-key': self.api_key,
            'Content-Type': 'application/json'
        }
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.info("FootballApiClient initialized")
        self.logger.info(f"API Key present and length: {len(self.api_key)}")
        
        # Verify API connection on initialization
        if not self.verify_connection():
            raise ConnectionError("Could not verify API connection. Please check your API key and try again.")
    
    def verify_connection(self):
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
    
    def make_request(self, endpoint, params=None, max_retries=3):
        """Make API request with retries"""
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Making API request to {url}")
                self.logger.info(f"Params: {params}")
                
                response = requests.get(url, headers=self.headers, params=params)
                self.logger.info(f"API Response Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    if 'errors' in data and data['errors'] and len(data['errors']) > 0:
                        self.logger.error(f"API returned errors: {data['errors']}")
                        return None
                    if 'response' not in data:
                        self.logger.error(f"Invalid API response format: {data}")
                        return None
                    return data
                
                if response.status_code == 429:  # Rate limit
                    retry_after = int(response.headers.get('Retry-After', 60))
                    self.logger.warning(f"Rate limit hit. Retrying after {retry_after} seconds")
                    time.sleep(retry_after)
                    continue
                
                # Handle other error codes
                response.raise_for_status()
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request error on attempt {attempt+1}/{max_retries}: {str(e)}")
                if hasattr(e, 'response') and e.response is not None:
                    self.logger.error(f"Error Response: {e.response.text}")
                
                # Wait before retrying
                wait_time = 2 ** attempt  # Exponential backoff
                self.logger.info(f"Waiting {wait_time} seconds before retry")
                time.sleep(wait_time)
                
                if attempt == max_retries - 1:  # Last attempt
                    self.logger.error("Max retries reached. Giving up.")
                    return None
            
            except Exception as e:
                self.logger.error(f"Unexpected error: {str(e)}")
                return None
        
        return None  # Should not reach here, but just in case
    
    def get_fixtures(self, league_id, season, from_date=None, to_date=None):
        """Get fixtures for a specific league and season"""
        try:
            # Build the endpoint with query parameters
            endpoint = f'fixtures?league={league_id}&season={season}'
            
            # Ensure we always send a usable date window if none provided
            if not from_date or not to_date:
                # Default to the given season year (Aug-Dec) to pick up in-season fixtures
                from_date = f"{season}-08-01"
                to_year = season if season >= datetime.now().year else season
                to_date = f"{to_year}-12-31"
            
            # Add date filters
            endpoint += f'&from={from_date}'
            endpoint += f'&to={to_date}'
            
            # Add timezone to ensure consistent results
            endpoint += '&timezone=UTC'
            
            self.logger.info(f"Fetching fixtures with endpoint: {endpoint}")
            
            # Make the request
            response = self.make_request(endpoint)
            
            # Log the number of fixtures found for debugging
            if response and 'response' in response:
                self.logger.info(f"Found {len(response['response'])} fixtures for league {league_id}")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error in get_fixtures: {str(e)}")
            return None
    
    def get_head_to_head(self, team1_id, team2_id, last=20):
        """Get head-to-head history between two teams"""
        try:
            # For v3 API, we need to use the fixtures/headtohead endpoint with team IDs
            endpoint = f'fixtures/headtohead?h2h={team1_id}-{team2_id}&last={last}'
            
            # Make the request
            response = self.make_request(endpoint)
            
            # Log the number of head-to-head matches found for debugging
            if response and 'response' in response:
                self.logger.info(f"Found {len(response['response'])} head-to-head matches between {team1_id} and {team2_id}")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error in get_head_to_head: {str(e)}")
            return None
    
    def get_team_statistics(self, team_id, league_id, season):
        """Get team statistics for a specific season"""
        try:
            # For API v3, we need to use the teams/statistics endpoint with proper parameters
            params = {
                'team': team_id,
                'league': league_id,
                'season': season
            }
            
            # Make the request to get team statistics
            stats_response = self.make_request('teams/statistics', params)
            
            # Get team fixtures for form and recent results
            fixtures = self.make_request(f'fixtures?team={team_id}&season={season}&last=10')
            
            # Process the data into the expected format
            if stats_response and 'response' in stats_response:
                stats = stats_response['response']
                
                # Extract form from fixtures if available
                form = ''
                if fixtures and 'response' in fixtures:
                    # Get last 5 matches and determine form (W/D/L)
                    last_matches = fixtures['response'][:5]
                    for match in last_matches:
                        if match['teams']['home']['id'] == team_id:
                            if match['teams']['home']['winner'] is True:
                                form += 'W'
                            elif match['teams']['away']['winner'] is True:
                                form += 'L'
                            else:
                                form += 'D'
                        else:
                            if match['teams']['away']['winner'] is True:
                                form += 'W'
                            elif match['teams']['home']['winner'] is True:
                                form += 'L'
                            else:
                                form += 'D'
                
                # Format the response to match what the predictor expects
                result = {
                    'response': {
                        'team': stats.get('team', {}),
                        'league': stats.get('league', {}),
                        'fixtures': {
                            'played': {
                                'total': stats.get('fixtures', {}).get('played', {}).get('total', 0),
                                'home': stats.get('fixtures', {}).get('played', {}).get('home', 0),
                                'away': stats.get('fixtures', {}).get('played', {}).get('away', 0)
                            },
                            'wins': {
                                'total': stats.get('fixtures', {}).get('wins', {}).get('total', 0),
                                'home': stats.get('fixtures', {}).get('wins', {}).get('home', 0),
                                'away': stats.get('fixtures', {}).get('wins', {}).get('away', 0)
                            },
                            'draws': {
                                'total': stats.get('fixtures', {}).get('draws', {}).get('total', 0),
                                'home': stats.get('fixtures', {}).get('draws', {}).get('home', 0),
                                'away': stats.get('fixtures', {}).get('draws', {}).get('away', 0)
                            },
                            'loses': {
                                'total': stats.get('fixtures', {}).get('loses', {}).get('total', 0),
                                'home': stats.get('fixtures', {}).get('loses', {}).get('home', 0),
                                'away': stats.get('fixtures', {}).get('loses', {}).get('away', 0)
                            }
                        },
                        'goals': {
                            'for': {
                                'total': {
                                    'total': stats.get('goals', {}).get('for', {}).get('total', {}).get('total', 0),
                                    'home': stats.get('goals', {}).get('for', {}).get('total', {}).get('home', 0),
                                    'away': stats.get('goals', {}).get('for', {}).get('total', {}).get('away', 0)
                                }
                            },
                            'against': {
                                'total': {
                                    'total': stats.get('goals', {}).get('against', {}).get('total', {}).get('total', 0),
                                    'home': stats.get('goals', {}).get('against', {}).get('total', {}).get('home', 0),
                                    'away': stats.get('goals', {}).get('against', {}).get('total', {}).get('away', 0)
                                }
                            }
                        },
                        'clean_sheet': {
                            'home': stats.get('clean_sheet', {}).get('home', 0),
                            'away': stats.get('clean_sheet', {}).get('away', 0),
                            'total': stats.get('clean_sheet', {}).get('total', 0)
                        },
                        'failed_to_score': {
                            'home': stats.get('failed_to_score', {}).get('home', 0),
                            'away': stats.get('failed_to_score', {}).get('away', 0),
                            'total': stats.get('failed_to_score', {}).get('total', 0)
                        },
                        'form': form
                    }
                }
                return result
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error in get_team_statistics: {str(e)}")
            return None
    
    def get_team_fixtures(self, team_id, last=10):
        """Get last N fixtures for a team"""
        params = {
            'team': team_id,
            'last': last
        }
        
        return self.make_request('fixtures', params)
