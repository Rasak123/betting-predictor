import logging
from betting_scraper import BettingScraper
from dotenv import load_dotenv
from datetime import datetime

def get_test_date():
    """Get a date in the current Premier League season"""
    return datetime(2024, 2, 8)  # Use February 2024 for testing

def main():
    # Configure logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)

    # Initialize scraper with test date
    scraper = BettingScraper()
    
    # Test only Premier League
    league_keys = ['premier_league']
    
    try:
        logger.info("Testing Premier League matches retrieval...")
        logger.info("API Configuration:")
        logger.info(f"Base URL: {scraper.base_url}")
        logger.info(f"Headers present: {'x-rapidapi-key' in scraper.headers}")
        
        # Override current time for testing
        current_time = get_test_date()
        logger.info(f"Using test date: {current_time.strftime('%Y-%m-%d')}")
        
        matches = scraper.get_matches(league_keys)
        if matches:
            logger.info(f"Successfully found {len(matches)} Premier League matches")
            # Print matches
            logger.info("\nPremier League matches:")
            for match in matches:
                match_date = datetime.fromisoformat(match['date'].replace('Z', '+00:00'))
                logger.info(f"  {match_date.strftime('%Y-%m-%d %H:%M')} - {match['home_team']} vs {match['away_team']} (Status: {match['status']})")
        else:
            logger.warning("No Premier League matches found")
            # Print the LEAGUES dictionary for debugging
            from betting_scraper import LEAGUES
            logger.info("\nLeagues configuration:")
            logger.info(LEAGUES['premier_league'])
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)

if __name__ == "__main__":
    load_dotenv()
    main()
