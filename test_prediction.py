import logging
from betting.enhanced_predictor_fixed import EnhancedMatchPredictor
from betting.models import TeamStats, HeadToHeadStats

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_prediction():
    try:
        logger.info("Testing prediction functionality...")
        predictor = EnhancedMatchPredictor()
        
        # Example match data
        home_stats = TeamStats(
            team_id=1,
            team_name="Home Team",
            form="WWLWD",
            goals_scored=15,
            goals_conceded=8,
            clean_sheets=5,
            failed_to_score=2
        )
        
        away_stats = TeamStats(
            team_id=2,
            team_name="Away Team",
            form="LDWDL",
            goals_scored=10,
            goals_conceded=12,
            clean_sheets=3,
            failed_to_score=3
        )
        
        h2h_stats = HeadToHeadStats(
            total_matches=5,
            home_wins=2,
            away_wins=1,
            draws=2,
            goals_for=8,
            goals_against=6
        )
        
        logger.info("Generating prediction...")
        prediction = predictor.predict_match(home_stats, away_stats, h2h_stats)
        
        if prediction:
            logger.info("Prediction successful!")
            logger.info(f"Predicted outcome: {prediction.predicted_outcome}")
            logger.info(f"Predicted score: {prediction.predicted_score}")
            logger.info(f"Home win probability: {prediction.home_win_probability*100:.1f}%")
            logger.info(f"Draw probability: {prediction.draw_probability*100:.1f}%")
            logger.info(f"Away win probability: {prediction.away_win_probability*100:.1f}%")
            logger.info(f"Confidence: {prediction.confidence*100:.1f}%")
        else:
            logger.error("Failed to generate prediction (returned None)")
            
    except Exception as e:
        logger.error(f"Error during prediction test: {str(e)}", exc_info=True)

if __name__ == "__main__":
    test_prediction()
