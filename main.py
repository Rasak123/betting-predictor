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

def show_bot_improvements():
    """Display the key improvements in the Telegram bot"""
    print("\n=== BETTING PREDICTOR BOT IMPROVEMENTS ===")
    print("\n1. Enhanced Message Formatting")
    print("   - Better organization with clear sections")
    print("   - Added emojis for better visual appeal")
    print("   - Improved readability with proper markdown formatting")
    
    print("\n2. Natural Language Understanding")
    print("   - Bot now understands text messages like 'show me predictions'")
    print("   - No need to use explicit commands for common requests")
    print("   - More conversational interaction")
    
    print("\n3. New /leagues Command")
    print("   - Added command to show all supported leagues")
    print("   - Now supports Premier League, La Liga, Bundesliga, Serie A, Ligue 1, and Champions League")
    
    print("\n4. Better Error Handling")
    print("   - Improved error messages and recovery")
    print("   - Progress indicators during prediction generation")
    print("   - More detailed feedback on API issues")
    
    print("\n5. Improved Prediction Display")
    print("   - More detailed confidence ratings")
    print("   - Better organization of different prediction types")
    print("   - Support for multiple prediction markets (match outcome, score, over/under, BTTS, first half)")
    
    print("\n=== EXAMPLE MESSAGE FORMAT ===")
    example = """[Trophy] *Premier League (England)*
[Ball] *Manchester United vs Liverpool*
[Calendar] Sunday, 15 May 2025 - 16:30

[Chart] *Match Prediction*
[Flag] Outcome: *Home Win*
[Numbers] Score: *2-1*
[Muscle] Confidence: 75%

[Graph] *Win Probabilities*
[House] Manchester United: 65%
[Handshake] Draw: 20%
[Bus] Liverpool: 15%

[Chart] *Over/Under*
O/U 2.5: *Over* (70%)
O/U 3.5: *Under* (65%)

[Chart] *Both Teams To Score*
BTTS: *Yes* (80%)

[Chart] *First Half*
Result: *Draw* (45%)"""
    print(example)

def main():
    """Main entry point for the application"""
    parser = argparse.ArgumentParser(description='Football Betting Predictor')
    parser.add_argument('--mode', choices=['predictions', 'bot', 'show-bot'], default='predictions',
                        help='Run mode: predictions (default), bot, or show-bot')
    args = parser.parse_args()
    
    try:
        if args.mode == 'predictions':
            logger.info("Running in predictions mode")
            run_predictions()
        elif args.mode == 'bot':
            logger.info("Running in bot mode")
            run_bot()
        elif args.mode == 'show-bot':
            show_bot_improvements()
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise

if __name__ == "__main__":
    main()
