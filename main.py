import logging
import argparse
from betting.main import run_predictions

# Handle Python 3.13 compatibility issues
try:
    from betting.telegram_bot import run_bot
except ImportError as e:
    if 'imghdr' in str(e):
        logging.warning("Telegram bot functionality not available due to Python 3.13 compatibility issues.")
        # Define a placeholder function
        def run_bot():
            print("Telegram bot functionality is not available with Python 3.13.")
            print("Please use Python 3.10-3.12 for full functionality.")

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
