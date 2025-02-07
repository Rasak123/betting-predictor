import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from betting_scraper import BettingScraper
import os
from dotenv import load_dotenv

# Enable detailed logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    try:
        user = update.effective_user
        logger.info(f"Start command received from user {user.id}")
        await update.message.reply_text(
            f"Hi {user.first_name}! 👋\n\n"
            "Welcome to the Premier League Betting Predictor Bot!\n\n"
            "Available commands:\n"
            "/predictions - Get predictions for upcoming matches\n"
            "/help - Show this help message"
        )
    except Exception as e:
        logger.error(f"Error in start command: {str(e)}")
        await update.message.reply_text("Sorry, something went wrong. Please try again.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    try:
        logger.info("Help command received")
        await update.message.reply_text(
            "Available commands:\n"
            "/predictions - Get predictions for upcoming matches\n"
            "/help - Show this help message"
        )
    except Exception as e:
        logger.error(f"Error in help command: {str(e)}")
        await update.message.reply_text("Sorry, something went wrong. Please try again.")

def format_prediction(match_data):
    """Format a prediction into a readable message."""
    try:
        prediction = match_data['prediction']
        
        message = [
            f"🏟️ {match_data['home_team']} vs {match_data['away_team']}",
            f"📅 {match_data['date']} {match_data['time']}",
            f"\n🏆 Predicted Winner: {prediction['winner']}",
            f"📊 Confidence: {prediction['confidence']:.1f}%",
            f"⚽ Predicted Score: {prediction['predicted_score']}",
            "\n📈 Analysis:",
        ]
        
        for reason in prediction['reasoning']:
            message.append(f"• {reason}")
        
        return "\n".join(message)
    except Exception as e:
        logger.error(f"Error formatting prediction: {str(e)}")
        return "Error formatting prediction"

async def get_predictions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send predictions when the command /predictions is issued."""
    try:
        logger.info("Predictions command received")
        
        # Send initial message
        message = await update.message.reply_text("🔄 Analyzing matches... Please wait.")
        
        # Create scraper instance
        scraper = BettingScraper()
        logger.info("Created BettingScraper instance")
        
        # Get predictions
        logger.info("Getting predictions...")
        results = scraper.analyze_weekend_matches()
        
        if not results:
            logger.warning("No matches found")
            await message.edit_text("No upcoming matches found for analysis.")
            return
        
        # Send each prediction as a separate message
        await message.edit_text("🎯 Here are the predictions for upcoming matches:")
        logger.info(f"Found {len(results)} matches")
        
        for match_data in results:
            formatted_prediction = format_prediction(match_data)
            await update.message.reply_text(formatted_prediction)
            
    except Exception as e:
        logger.error(f"Error getting predictions: {str(e)}")
        await update.message.reply_text(
            "Sorry, there was an error getting the predictions. Please try again later."
        )

def main() -> None:
    """Start the bot."""
    try:
        # Load environment variables
        load_dotenv()
        logger.info("Loaded environment variables")
        
        # Get bot token
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            logger.error("TELEGRAM_BOT_TOKEN not found")
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")
        
        logger.info("Bot token found")
        
        # Create application
        app = Application.builder().token(token).build()
        logger.info("Created application")
        
        # Add handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("predictions", get_predictions))
        logger.info("Added command handlers")
        
        # Start the Bot
        logger.info("Starting bot...")
        app.run_polling()
        logger.info("Bot is running")
        
    except Exception as e:
        logger.error(f"Critical error in main: {str(e)}")
        raise

if __name__ == '__main__':
    main()
