import logging
import argparse
from betting.main import run_predictions
from betting.telegram_bot import run_bot

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the application"""
    parser = argparse.ArgumentParser(description='Football Betting Predictor')
    parser.add_argument('--mode', choices=['predictions', 'bot'], default='predictions',
                        help='Run mode: predictions (default) or bot')
    args = parser.parse_args()
    
    try:
        if args.mode == 'predictions':
            logger.info("Running in predictions mode")
            run_predictions()
        elif args.mode == 'bot':
            logger.info("Running in bot mode")
            run_bot()
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise

if __name__ == "__main__":
    main()
