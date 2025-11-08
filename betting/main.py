import json
import logging
from typing import Dict, List, Any
from datetime import datetime
from .predictor import MatchPredictor
from .enhanced_predictor_fixed import EnhancedMatchPredictor
from .models import Prediction

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
LEAGUES = {
    'premier_league': {
        'id': 39,
        'name': 'Premier League',
        'country': 'England',
        'season': 2024  # 2024/2025 season
    },
    'la_liga': {
        'id': 140,
        'name': 'La Liga',
        'country': 'Spain',
        'season': 2024
    },
    'bundesliga': {
        'id': 78,
        'name': 'Bundesliga',
        'country': 'Germany',
        'season': 2024
    },
    'serie_a': {
        'id': 135,
        'name': 'Serie A',
        'country': 'Italy',
        'season': 2024
    },
    'ligue_1': {
        'id': 61,
        'name': 'Ligue 1',
        'country': 'France',
        'season': 2024
    },
    'champions_league': {
        'id': 2,
        'name': 'UEFA Champions League',
        'country': 'Europe',
        'season': 2024
    }
}

def analyze_weekend_matches(leagues: Dict[str, Dict[str, Any]] = None, use_enhanced: bool = True) -> List[Dict[str, Any]]:
    """Analyze matches for the upcoming weekend across specified leagues
    
    Args:
        leagues: Dictionary of leagues to analyze
        use_enhanced: Whether to use the enhanced predictor with improved statistical models
    """
    try:
        if leagues is None:
            leagues = LEAGUES
            
        logger.info(f"Analyzing upcoming matches for {len(leagues)} leagues")
        
        # Initialize predictor - use enhanced version by default
        if use_enhanced:
            logger.info("Using enhanced predictor with improved statistical models")
            predictor = EnhancedMatchPredictor()
        else:
            logger.info("Using standard predictor")
            predictor = MatchPredictor()
        
        # Get upcoming matches
        matches = predictor.get_upcoming_matches(leagues, days_ahead=7)
        logger.info(f"Found {len(matches)} upcoming matches")
        
        if not matches:
            logger.warning("No upcoming matches found")
            return []
        
        # Make predictions for each match
        predictions = []
        for match in matches:
            try:
                logger.info(f"Analyzing match: {match.home_team.name} vs {match.away_team.name}")
                
                # Make prediction
                prediction = predictor.predict_match(match)
                if prediction:
                    predictions.append(prediction.to_dict())
                else:
                    logger.warning(f"Failed to predict match: {match.home_team.name} vs {match.away_team.name}")
                    
            except Exception as e:
                logger.error(f"Error analyzing match: {str(e)}")
                continue
        
        logger.info(f"Successfully analyzed {len(predictions)} matches")
        return predictions
        
    except Exception as e:
        logger.error(f"Error in analyze_weekend_matches: {str(e)}")
        return []

def save_predictions(predictions: List[Dict[str, Any]], output_file: str = 'predictions.json') -> bool:
    """Save predictions to a JSON file"""
    try:
        with open(output_file, 'w') as f:
            json.dump(predictions, f, indent=4)
        logger.info(f"Predictions saved to {output_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving predictions: {str(e)}")
        return False

def print_predictions_summary(predictions: List[Dict[str, Any]]) -> None:
    """Print a summary of predictions to the console"""
    if not predictions:
        print("\nNo predictions available.")
        return
        
    print("\nMatch Predictions Summary:")
    for result in predictions:
        try:
            match = result.get('match', {})
            probabilities = result.get('probabilities', {})
            score = result.get('score', {})
            over_under = result.get('over_under', {})
            btts = result.get('btts', {})
            
            print(f"\n{match.get('home_team')} vs {match.get('away_team')} ({match.get('league')})")
            print(f"Date: {match.get('date')}")
            
            # Print outcome prediction
            print(f"Predicted Outcome: {result.get('prediction')} "
                  f"(Home: {probabilities.get('home')}%, "
                  f"Draw: {probabilities.get('draw')}%, "
                  f"Away: {probabilities.get('away')}%)")
            
            # Print score prediction
            if score:
                print(f"Predicted Score: {score.get('display')} (Confidence: {result.get('confidence')}%)")
            
            # Print over/under predictions
            for threshold, ou_pred in over_under.items():
                if ou_pred:
                    print(f"Over {ou_pred.get('threshold')}: {'Yes' if ou_pred.get('prediction') else 'No'} "
                          f"(Probability: {ou_pred.get('probability')}%)")
            
            # Print BTTS prediction
            if btts:
                print(f"Both Teams To Score: {'Yes' if btts.get('prediction') else 'No'} "
                      f"(Probability: {btts.get('probability')}%)")
                
        except Exception as e:
            logger.error(f"Error printing prediction: {str(e)}")
            continue

def run_predictions(use_enhanced: bool = True) -> List[Dict[str, Any]]:
    """Run the prediction process and return results
    
    Args:
        use_enhanced: Whether to use the enhanced predictor with improved statistical models
    """
    try:
        # Analyze matches using the specified predictor
        results = analyze_weekend_matches(use_enhanced=use_enhanced)
        
        if results:
            # Save results to file
            save_predictions(results)
            
            # Print summary
            print_predictions_summary(results)
            
        return results
        
    except Exception as e:
        logger.error(f"Error running predictions: {str(e)}")
        return []
