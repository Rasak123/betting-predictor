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
    
    # Test with all top 5 leagues
    league_keys = ['premier_league', 'la_liga', 'bundesliga', 'serie_a', 'ligue_1']
    
    try:
        matches = scraper.get_matches(league_keys)
        if matches:
            logger.info(f"Successfully found {len(matches)} matches")
            # Group matches by league
            matches_by_league = {}
            for match in matches:
                league = match['league']
                if league not in matches_by_league:
                    matches_by_league[league] = []
                matches_by_league[league].append(match)
            
            # Print matches by league
            for league, league_matches in matches_by_league.items():
                logger.info(f"\n{league} matches ({len(league_matches)}):")
                for match in league_matches:
                    match_date = datetime.fromisoformat(match['date'].replace('Z', '+00:00'))
                    logger.info(f"  {match_date.strftime('%Y-%m-%d %H:%M')} - {match['home_team']} vs {match['away_team']}")
        else:
            logger.warning("No matches found")
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)

if __name__ == "__main__":
    load_dotenv()
    main()
