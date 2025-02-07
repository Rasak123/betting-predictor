import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
api_key = os.getenv('RAPIDAPI_KEY')

# API endpoint
url = "https://api-football-v1.p.rapidapi.com/v3/leagues"

# Headers
headers = {
    "X-RapidAPI-Key": api_key,
    "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
}

print("Testing API connection...")
print(f"Using API Key: {api_key[:10]}...")  # Only show first 10 chars for security

try:
    response = requests.get(url, headers=headers)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        data = response.json()
        print("\nAPI connection successful!")
        print(f"Results found: {len(data.get('response', []))}")
    else:
        print("\nAPI Error:")
        print(response.text)
        
except Exception as e:
    print(f"Error: {str(e)}")
