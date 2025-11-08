import logging
import json
from datetime import datetime
from betting.enhanced_predictor import EnhancedMatchPredictor
from betting.models import Team, Match

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def test_enhanced_predictor():
    """Test the enhanced predictor with a sample match"""
    try:
        # Create a sample match
        home_team = Team(id=33, name="Manchester United", country="England")
        away_team = Team(id=40, name="Liverpool", country="England")
        
        match = Match(
            id=12345,
            league_id=39,  # Premier League
            league_name='Premier League',
            country='England',
            status='NS',  # Not Started
            home_team=home_team,
            away_team=away_team,
            date=datetime.now(),
            home_score=None,
            away_score=None
        )
        
        # Initialize the enhanced predictor
        predictor = EnhancedMatchPredictor()
        
        # Make prediction
        logger.info(f"Making prediction for {home_team.name} vs {away_team.name}")
        prediction = predictor.predict_match(match)
        
        if prediction:
            # Convert prediction to dictionary
            prediction_dict = prediction.to_dict()
            
            # Print prediction details
            print("\n=== ENHANCED PREDICTION RESULTS ===")
            print(f"Match: {prediction_dict['match']['home_team']} vs {prediction_dict['match']['away_team']}")
            print(f"League: {prediction_dict['match']['league']}")
            print("\nScore Prediction:")
            print(f"  Home: {prediction_dict['predicted_home_score']} - Away: {prediction_dict['predicted_away_score']}")
            print(f"  Confidence: {prediction_dict['confidence']}%")
            
            print("\nWin Probabilities:")
            print(f"  Home Win: {prediction_dict['home_win_probability']*100:.1f}%")
            print(f"  Draw: {prediction_dict['draw_probability']*100:.1f}%")
            print(f"  Away Win: {prediction_dict['away_win_probability']*100:.1f}%")
            
            print("\nOver/Under Predictions:")
            for threshold, ou_pred in prediction_dict['over_under_predictions'].items():
                prediction_text = "Over" if ou_pred['prediction'] else "Under"
                print(f"  O/U {threshold}: {prediction_text} ({ou_pred['probability']}%) - Expected Goals: {ou_pred['expected_goals']}")
            
            # Save prediction to file
            with open('enhanced_prediction_sample.json', 'w') as f:
                json.dump(prediction_dict, f, indent=2, default=str)
                
            print("\nPrediction saved to enhanced_prediction_sample.json")
        else:
            logger.error("Failed to make prediction")
            
    except Exception as e:
        logger.error(f"Error testing enhanced predictor: {str(e)}")
        raise

if __name__ == "__main__":
    test_enhanced_predictor()
