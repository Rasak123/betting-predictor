import os
import logging
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from betting_scraper import BettingScraper
import json

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
API_KEY = os.getenv('API_KEY') or os.getenv('RAPIDAPI_KEY')
if not API_KEY:
    raise ValueError("No API key found. Set either API_KEY or RAPIDAPI_KEY in your .env file")

def test_api():
    """Test API connectivity and response"""
    base_url = "https://api-football-v1.p.rapidapi.com/v3"
    headers = {
        'x-rapidapi-host': "api-football-v1.p.rapidapi.com",
        'x-rapidapi-key': API_KEY
    }

    # Test endpoints
    endpoints = {
        'fixtures': {
            'url': f"{base_url}/fixtures",
            'params': {
                'league': '39',  # Premier League
                'season': '2024',
                'from': datetime.now().strftime("%Y-%m-%d"),
                'to': (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
                'status': 'NS'  # Only get matches that haven't started
            }
        },
        'teams': {
            'url': f"{base_url}/teams",
            'params': {
                'league': '39',
                'season': '2024'
            }
        }
    }

    for name, config in endpoints.items():
        logger.info(f"\nTesting {name} endpoint...")
        try:
            response = requests.get(
                config['url'],
                headers=headers,
                params=config['params']
            )
            
            logger.info(f"Status Code: {response.status_code}")
            logger.info(f"Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Raw API Response: {json.dumps(data, indent=2)}")
                
                if 'response' in data:
                    logger.info(f"Success! Found {len(data['response'])} {name}")
                    if name == 'fixtures':
                        for fixture in data['response'][:2]:  # Show first 2 fixtures
                            logger.info(f"Fixture: {fixture['teams']['home']['name']} vs {fixture['teams']['away']['name']}")
                else:
                    logger.error(f"Invalid response format: {data}")
            else:
                logger.error(f"Request failed: {response.text}")
                
        except Exception as e:
            logger.error(f"Error testing {name}: {str(e)}")

def test_get_matches():
    try:
        scraper = BettingScraper()
        matches = scraper.get_matches(['premier_league'])
        
        if matches:
            logger.info(f"\nFound {len(matches)} matches:")
            for match in matches:
                logger.info(f"\n{match['home_team']} vs {match['away_team']}")
                logger.info(f"Date: {match['date']}")
                logger.info(f"Status: {match['status']}")
        else:
            logger.info("\nNo matches found")
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == "__main__":
    test_api()
    test_get_matches()
