import os
from dotenv import load_dotenv
import requests
from datetime import datetime, timedelta

def test_leagues():
    # Load environment variables
    load_dotenv()
    api_key = os.getenv('RAPIDAPI_KEY')
    
    # API configuration
    base_url = "https://api-football-v1.p.rapidapi.com/v3"
    headers = {
        'X-RapidAPI-Key': api_key,
        'X-RapidAPI-Host': "api-football-v1.p.rapidapi.com"
    }
    
    # Test leagues
    leagues = {
        'premier_league': {'id': 39, 'name': 'Premier League'},
        'la_liga': {'id': 140, 'name': 'La Liga'},
        'serie_a': {'id': 135, 'name': 'Serie A'},
        'bundesliga': {'id': 78, 'name': 'Bundesliga'},
        'ligue_1': {'id': 61, 'name': 'Ligue 1'}
    }
    
    # Calculate date range
    today = datetime.now()
    end_date = today + timedelta(days=7)
    from_date = today.strftime('%Y-%m-%d')
    to_date = end_date.strftime('%Y-%m-%d')
    
    print(f"\nTesting API Connection and League Data")
    print(f"API Key present: {'Yes' if api_key else 'No'}")
    print(f"API Key length: {len(api_key) if api_key else 0}")
    print(f"Date Range: {from_date} to {to_date}\n")
    
    # First, verify current leagues and seasons
    print("Checking available leagues...")
    leagues_url = f"{base_url}/leagues"
    leagues_response = requests.get(
        leagues_url,
        headers=headers,
        params={'current': 'true'}
    )
    
    if leagues_response.status_code == 200:
        leagues_data = leagues_response.json()
        print("\nActive Leagues Found:")
        for league in leagues_data.get('response', []):
            league_name = league['league']['name']
            league_id = league['league']['id']
            current_season = league['seasons'][0]['year']
            current = league['seasons'][0].get('current')
            if league_name in [l['name'] for l in leagues.values()]:
                print(f"• {league_name}")
                print(f"  ID: {league_id}")
                print(f"  Current Season: {current_season}")
                print(f"  Current: {current}")
                print(f"  Checking fixtures...")
                
                # Check fixtures for this league
                fixtures_url = f"{base_url}/fixtures"
                for season in [2023, 2024]:
                    fixtures_params = {
                        'league': league_id,
                        'from': from_date,
                        'to': to_date,
                        'season': season
                    }
                    
                    fixtures_response = requests.get(
                        fixtures_url,
                        headers=headers,
                        params=fixtures_params
                    )
                    
                    if fixtures_response.status_code == 200:
                        fixtures_data = fixtures_response.json()
                        matches = fixtures_data.get('response', [])
                        if matches:
                            print(f"    Season {season}: {len(matches)} matches found")
                            for match in matches:
                                match_date = match['fixture']['date']
                                home_team = match['teams']['home']['name']
                                away_team = match['teams']['away']['name']
                                print(f"      • {home_team} vs {away_team} on {match_date}")
                        else:
                            print(f"    Season {season}: No matches found")
                    else:
                        print(f"    Season {season}: Error {fixtures_response.status_code}")
                print()
    else:
        print(f"Error checking leagues: {leagues_response.status_code}")
        print(leagues_response.text)

if __name__ == "__main__":
    test_leagues()
