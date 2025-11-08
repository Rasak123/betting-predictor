import requests
import logging
import time
import os
from dotenv import load_dotenv

class FootballApiClient:
    """Client for interacting with the Football API"""
    
    def __init__(self):
        """Initialize the API client with credentials"""
        # Load environment variables
        load_dotenv()
        
        # Get API key - try multiple environment variable names for compatibility
        self.api_key = os.getenv('FOOTBALL_API_KEY') or os.getenv('RAPIDAPI_KEY') or os.getenv('API_KEY')
        
        # Check if API key is available
        if not self.api_key:
            raise ValueError("No API key found. Please set FOOTBALL_API_KEY in your .env file")
            
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
        params = {
            'league': league_id,
            'season': season
        }
        
        if from_date:
            params['from'] = from_date
        
        if to_date:
            params['to'] = to_date
        
        return self.make_request('fixtures', params)
    
    def get_head_to_head(self, team1_id, team2_id, last=20):
        """Get head-to-head history between two teams"""
        params = {
            'h2h': f"{team1_id}-{team2_id}",
            'last': last
        }
        
        return self.make_request('fixtures/headtohead', params)
    
    def get_team_statistics(self, team_id, league_id, season):
        """Get team statistics for a specific season"""
        params = {
            'team': team_id,
            'league': league_id,
            'season': season
        }
        
        return self.make_request('teams/statistics', params)
    
    def get_team_fixtures(self, team_id, last=10):
        """Get last N fixtures for a team"""
        params = {
            'team': team_id,
            'last': last
        }
        
        return self.make_request('fixtures', params)
