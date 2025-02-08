import logging
from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes
from betting_scraper import BettingScraper
import os
from dotenv import load_dotenv
import pytz

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
            "Welcome to the Football Betting Predictor Bot!\n\n"
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

def format_prediction(prediction):
    """Format a prediction for Telegram message"""
    try:
        if not prediction or not isinstance(prediction, dict):
            return "Invalid prediction data"
            
        match_info = prediction.get('match', 'Unknown Match')
        date = prediction.get('date', 'Unknown Date')
        league_info = prediction.get('league', {'name': 'Unknown League', 'country': 'Unknown Country'})
        predictions = prediction.get('predictions', {})
        h2h = prediction.get('head_to_head', [])
        home_form = prediction.get('home_form', [])
        away_form = prediction.get('away_form', [])
        
        # Format main match info
        formatted_text = (
            f"🏆 *{league_info['name']}* ({league_info['country']})\n"
            f"⚽ {match_info}\n"
            f"📅 {date}\n\n"
        )
        
        # Format head-to-head history
        formatted_text += "*Head-to-Head (Last 5):*\n"
        if h2h:
            for match in h2h:
                formatted_text += f"• {match['date'][:10]}: {match['home_team']} {match['score']} {match['away_team']}\n"
        else:
            formatted_text += "No recent head-to-head matches\n"
        formatted_text += "\n"
        
        # Format home team form
        team_name = match_info.split(" vs ")[0]
        formatted_text += f"*{team_name} Form (Last 10):*\n"
        if home_form:
            for match in home_form:
                result_emoji = "✅" if match['result'] == 'W' else ("❌" if match['result'] == 'L' else "⚪")
                formatted_text += f"• {match['date'][:10]} ({match['venue']}): vs {match['opponent']} {match['score']} {result_emoji}\n"
        else:
            formatted_text += "No recent form data available\n"
        formatted_text += "\n"
        
        # Format away team form
        team_name = match_info.split(" vs ")[1]
        formatted_text += f"*{team_name} Form (Last 10):*\n"
        if away_form:
            for match in away_form:
                result_emoji = "✅" if match['result'] == 'W' else ("❌" if match['result'] == 'L' else "⚪")
                formatted_text += f"• {match['date'][:10]} ({match['venue']}): vs {match['opponent']} {match['score']} {result_emoji}\n"
        else:
            formatted_text += "No recent form data available\n"
        formatted_text += "\n"
        
        # Format match outcome and score predictions
        match_outcome = predictions.get('match_outcome', {})
        score = predictions.get('score', {})
        if match_outcome and score:
            formatted_text += (
                f"*Match Prediction:*\n"
                f"🎯 Predicted Winner: {match_outcome.get('prediction', 'UNKNOWN')}\n"
                f"   Home Win: {match_outcome.get('probabilities', {}).get('home', 0)}%\n"
                f"   Draw: {match_outcome.get('probabilities', {}).get('draw', 0)}%\n"
                f"   Away Win: {match_outcome.get('probabilities', {}).get('away', 0)}%\n\n"
                f"📊 Predicted Score: {score.get('home_score', 0)}-{score.get('away_score', 0)}\n"
                f"   Confidence: {score.get('confidence', 0)}%\n\n"
            )
        
        # Format other predictions
        formatted_text += (
            f"*Other Predictions:*\n"
            f"📈 Over/Under 2.5: {predictions.get('over_under_2_5', {}).get('prediction', 'UNKNOWN')}\n"
            f"   Confidence: {predictions.get('over_under_2_5', {}).get('confidence', 0):.1f}%\n\n"
            f"🎯 BTTS: {predictions.get('btts', {}).get('prediction', 'UNKNOWN')}\n"
            f"   Confidence: {predictions.get('btts', {}).get('confidence', 0):.1f}%\n\n"
            f"⏱ First Half: {predictions.get('first_half', {}).get('prediction', 'UNKNOWN')}\n"
            f"   Confidence: {predictions.get('first_half', {}).get('confidence', 0):.1f}%\n"
            f"{'➖' * 20}\n"
        )
        
        return formatted_text
        
    except Exception as e:
        logging.error(f"Error formatting prediction: {str(e)}")
        return "Error formatting prediction data"

async def get_predictions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send predictions for upcoming matches"""
    try:
        # Send initial message
        message = await update.message.reply_text("🔄 Analyzing matches... Please wait.")
        
        try:
            # Initialize scraper
            scraper = BettingScraper()
            
            # Get predictions
            logger.info("Getting weekend match predictions")
            predictions = scraper.analyze_weekend_matches()
            
            if not predictions:
                await message.edit_text("❌ No matches found for analysis.\nThis could be because:\n1. There are no upcoming Premier League matches in the next 7 days\n2. The API data hasn't been updated yet\n\nPlease try again later.")
                return
                
            # Format and send each prediction
            for prediction in predictions:
                try:
                    formatted_text = format_prediction(prediction)
                    if len(formatted_text) > 4096:  # Telegram message limit
                        # Split message if too long
                        chunks = [formatted_text[i:i+4096] for i in range(0, len(formatted_text), 4096)]
                        for chunk in chunks:
                            await context.bot.send_message(
                                chat_id=update.effective_chat.id,
                                text=chunk,
                                parse_mode='Markdown'
                            )
                    else:
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=formatted_text,
                            parse_mode='Markdown'
                        )
                except Exception as e:
                    logger.error(f"Error formatting/sending prediction: {str(e)}")
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="❌ Error formatting this prediction. Skipping to next match..."
                    )
                    continue
                    
            # Delete the "analyzing" message
            await message.delete()
            
        except Exception as e:
            logger.error(f"Error getting predictions: {str(e)}")
            error_msg = (
                "❌ Error getting predictions.\n\n"
                "Possible issues:\n"
                "1. API rate limit exceeded\n"
                "2. Network connection problem\n"
                "3. Invalid API key\n\n"
                "Please try again in a few minutes."
            )
            await message.edit_text(error_msg)
            
    except Exception as e:
        logger.error(f"Critical error in get_predictions: {str(e)}")
        error_msg = (
            "❌ A critical error occurred.\n\n"
            "Please check:\n"
            "1. Your API key is valid\n"
            "2. You have sufficient API credits\n"
            "3. The bot has proper permissions\n\n"
            "Try again in a few minutes."
        )
        try:
            await update.message.reply_text(error_msg)
        except Exception as msg_error:
            logger.error(f"Error sending error message: {str(msg_error)}")

def main() -> None:
    """Main function to run the bot"""
    try:
        # Configure logging first
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('bot.log')
            ]
        )
        logger = logging.getLogger(__name__)
        
        # Load environment variables
        load_dotenv()
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")
            
        rapidapi_key = os.getenv('RAPIDAPI_KEY')
        if not rapidapi_key:
            raise ValueError("RAPIDAPI_KEY not found in environment variables")
            
        logger.info("Starting Telegram bot...")
        logger.info(f"Telegram token present: {'Yes' if token else 'No'}")
        logger.info(f"RapidAPI key present: {'Yes' if rapidapi_key else 'No'}")
        
        # Test API connection
        try:
            scraper = BettingScraper()
            logger.info("Successfully initialized BettingScraper")
        except Exception as e:
            logger.error(f"Failed to initialize BettingScraper: {str(e)}")
            raise
        
        # Create application and pass it bot's token
        application = Application.builder().token(token).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("predictions", get_predictions))
        
        # Start the bot
        logger.info("Bot is starting...")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Critical error starting bot: {str(e)}")
        raise

if __name__ == "__main__":
    main()
