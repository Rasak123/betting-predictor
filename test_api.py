import requests
import os
from dotenv import load_dotenv

def test_api_connection():
    # Load environment variables
    load_dotenv()
    api_key = os.getenv('RAPIDAPI_KEY')
    
    print(f"\nTesting API Connection...")
    print(f"API Key present: {'Yes' if api_key else 'No'}")
    print(f"API Key length: {len(api_key) if api_key else 0}")
    
    # API endpoint for status check
    url = "https://api-football-v1.p.rapidapi.com/v3/timezone"  # Using a simple endpoint to test connection
    
    headers = {
        'X-RapidAPI-Key': api_key,
        'X-RapidAPI-Host': "api-football-v1.p.rapidapi.com"
    }
    
    try:
        print("\nMaking API request...")
        response = requests.get(url, headers=headers)
        
        print(f"\nResponse Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print("\nAPI Response Data:")
            print(f"Account: {data.get('response', {}).get('account', {}).get('email', 'Unknown')}")
            print(f"Requests Today: {data.get('response', {}).get('requests', {}).get('current', 'Unknown')}")
            print(f"Requests Limit: {data.get('response', {}).get('requests', {}).get('limit_day', 'Unknown')}")
            return True
        elif response.status_code == 403:
            print("\nError: Invalid API key or subscription inactive")
            return False
        elif response.status_code == 429:
            print("\nError: Rate limit exceeded")
            return False
        else:
            print(f"\nUnexpected status code: {response.status_code}")
            print(f"Response content: {response.text}")
            return False
            
    except Exception as e:
        print(f"\nError testing API: {str(e)}")
        return False

if __name__ == "__main__":
    test_api_connection()
