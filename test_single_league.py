import logging
from betting_scraper import BettingScraper
from dotenv import load_dotenv
from datetime import datetime

def main():
    # Configure logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)

    # Initialize scraper
    scraper = BettingScraper()
    
    # Test only Premier League
    league_keys = ['premier_league']
    
    try:
        logger.info("Testing Premier League matches retrieval...")
        logger.info("API Configuration:")
        logger.info(f"Base URL: {scraper.base_url}")
        logger.info(f"Headers present: {'x-rapidapi-key' in scraper.headers}")
        
        matches = scraper.get_matches(league_keys)
        if matches:
            logger.info(f"Successfully found {len(matches)} Premier League matches")
            # Print matches
            logger.info("\nPremier League matches:")
            for match in matches:
                match_date = datetime.fromisoformat(match['date'].replace('Z', '+00:00'))
                logger.info(f"  {match_date.strftime('%Y-%m-%d %H:%M')} - {match['home_team']} vs {match['away_team']} (Status: {match['status']})")
                
                # Get match analysis
                analysis = scraper.analyze_match(match)
                if analysis:
                    logger.info("\nMatch Analysis:")
                    logger.info(f"Predicted Score: {analysis['predicted_score']['home']}-{analysis['predicted_score']['away']}")
                    logger.info(f"Confidence: {analysis['confidence']}%")
                    logger.info("\nPredictions:")
                    logger.info(f"Over 1.5 Goals: {'✅' if analysis['predictions']['over_1_5']['prediction'] else '❌'} ({analysis['predictions']['over_1_5']['probability']}%)")
                    logger.info(f"Over 4.5 Goals: {'✅' if analysis['predictions']['over_4_5']['prediction'] else '❌'} ({analysis['predictions']['over_4_5']['probability']}%)")
                    logger.info(f"Home Win Either Half: {'✅' if analysis['predictions']['home_win_either_half']['prediction'] else '❌'} ({analysis['predictions']['home_win_either_half']['probability']}%)")
                    logger.info("\n" + "="*50)
                else:
                    logger.warning("Could not analyze match")
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
