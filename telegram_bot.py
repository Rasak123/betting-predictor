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
        predictions = match_data['predictions']
        
        # Format Over/Under prediction
        over_under = predictions['over_under_2_5']
        over_under_text = (
            f"Over/Under 2.5: {over_under['prediction']}\n"
            f"Expected Goals: {over_under['expected_goals']}\n"
            f"Confidence: {over_under['confidence']:.1f}%"
        )
        
        # Format BTTS prediction
        btts = predictions['btts']
        btts_text = (
            f"Both Teams to Score: {btts['prediction']}\n"
            f"Confidence: {btts['confidence']:.1f}%"
        )
        
        # Format First Half prediction
        first_half = predictions['first_half']
        first_half_text = (
            f"First Half Stronger Team: {first_half['prediction']}\n"
            f"Confidence: {first_half['confidence']:.1f}%"
        )
        
        # Combine all predictions
        message = (
            f"🏆 {match_data['match']}\n"
            f"📅 {match_data['date']}\n\n"
            f"📊 PREDICTIONS:\n\n"
            f"⚽ {over_under_text}\n\n"
            f"🎯 {btts_text}\n\n"
            f"⏱ {first_half_text}\n"
            f"\n-------------------\n"
        )
        
        return message
    except Exception as e:
        logger.error(f"Error formatting prediction: {str(e)}")
        return "Error formatting prediction data"

async def get_predictions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send predictions when the command /predictions is issued."""
    try:
        # Log the start of prediction retrieval
        logger.info("Starting to get predictions")
        user = update.effective_user
        logger.info(f"User {user.id} requested predictions")
        
        # Send initial message
        status_message = await update.message.reply_text(
            "🔄 Initializing prediction system...\n"
            "This may take a moment while I analyze the matches."
        )
        
        try:
            # Initialize scraper
            scraper = BettingScraper()
            logger.info("BettingScraper initialized")
            
            await status_message.edit_text(
                "✅ System initialized\n"
                "🔄 Fetching and analyzing matches..."
            )
            
            # Get and analyze matches
            predictions = scraper.analyze_weekend_matches()
            logger.info(f"Retrieved {len(predictions) if predictions else 0} predictions")
            
            if not predictions:
                await status_message.edit_text(
                    "ℹ️ No matches found for the upcoming week.\n"
                    "This could be because:\n"
                    "• There are no scheduled matches\n"
                    "• The API service is temporarily unavailable\n"
                    "Please try again later."
                )
                return
            
            await status_message.edit_text(
                f"✅ Found {len(predictions)} matches\n"
                "🔄 Formatting predictions..."
            )
            
            # Format all predictions
            formatted_predictions = []
            for prediction in predictions:
                try:
                    formatted_text = format_prediction(prediction)
                    formatted_predictions.append(formatted_text)
                except Exception as format_error:
                    logger.error(f"Error formatting prediction: {str(format_error)}")
                    continue
            
            if not formatted_predictions:
                await status_message.edit_text(
                    "❌ Error formatting predictions.\n"
                    "This might be due to unexpected data format.\n"
                    "The development team has been notified."
                )
                return
            
            # Split predictions into chunks if too long
            message = "🎯 *Premier League Predictions*\n\n" + "\n".join(formatted_predictions)
            
            # Delete status message
            await status_message.delete()
            
            # Send predictions
            await update.message.reply_text(message, parse_mode='Markdown')
            logger.info("Successfully sent predictions")
            
        except ValueError as ve:
            error_msg = (
                "❌ Configuration Error\n"
                "The bot is not properly configured.\n"
                f"Details: {str(ve)}"
            )
            await status_message.edit_text(error_msg)
            logger.error(f"Configuration error: {str(ve)}")
            
        except ConnectionError as ce:
            error_msg = (
                "❌ API Connection Error\n"
                "Could not connect to the prediction service.\n"
                "This might be due to:\n"
                "• Invalid API key\n"
                "• API service is down\n"
                "• Rate limit exceeded\n"
                "Please try again later."
            )
            await status_message.edit_text(error_msg)
            logger.error(f"Connection error: {str(ce)}")
            
        except Exception as e:
            error_msg = (
                "❌ Unexpected Error\n"
                "An error occurred while processing your request.\n"
                "The development team has been notified.\n"
                "Please try again later."
            )
            await status_message.edit_text(error_msg)
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            
    except Exception as e:
        logger.error(f"Critical error in get_predictions: {str(e)}", exc_info=True)
        try:
            await update.message.reply_text(
                "❌ Critical Error\n"
                "A critical error occurred while processing your request.\n"
                "Please try again later."
            )
        except Exception as msg_error:
            logger.error(f"Error sending error message: {str(msg_error)}")

def main() -> None:
    """Start the bot."""
    try:
        # Load environment variables
        load_dotenv()
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        api_key = os.getenv('RAPIDAPI_KEY')

        # Validate environment variables
        if not token:
            logger.error("TELEGRAM_BOT_TOKEN environment variable is not set")
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")
        if not api_key:
            logger.error("RAPIDAPI_KEY environment variable is not set")
            raise ValueError("RAPIDAPI_KEY environment variable is not set")

        logger.info("Starting bot with configuration:")
        logger.info(f"- TELEGRAM_BOT_TOKEN: {'*' * len(token)}")
        logger.info(f"- RAPIDAPI_KEY: {'*' * len(api_key)}")

        # Create the Application and pass it your bot's token
        application = Application.builder().token(token).build()

        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("predictions", get_predictions))

        # Log successful setup
        logger.info("Bot handlers configured successfully")

        # Start the Bot
        logger.info("Starting bot polling...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

    except ValueError as ve:
        logger.error(f"Configuration error: {str(ve)}")
        raise
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    main()
