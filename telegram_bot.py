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
    match_info = prediction['match']
    date = prediction['date']
    league_info = prediction['league']
    predictions = prediction['predictions']
    h2h = prediction['head_to_head']
    home_form = prediction['home_form']
    away_form = prediction['away_form']
    
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
    if 'match_outcome' in predictions and 'score' in predictions:
        outcome = predictions['match_outcome']
        score = predictions['score']
        formatted_text += (
            f"*Match Prediction:*\n"
            f"🎯 Predicted Winner: {outcome['prediction']}\n"
            f"   Home Win: {outcome['probabilities']['home']}%\n"
            f"   Draw: {outcome['probabilities']['draw']}%\n"
            f"   Away Win: {outcome['probabilities']['away']}%\n\n"
            f"📊 Predicted Score: {score['home_score']}-{score['away_score']}\n"
            f"   Confidence: {score['confidence']}%\n\n"
        )
    
    # Format other predictions
    formatted_text += (
        f"*Other Predictions:*\n"
        f"📈 Over/Under 2.5: {predictions['over_under_2_5']['prediction']}\n"
        f"   Confidence: {predictions['over_under_2_5']['confidence']:.1f}%\n\n"
        f"🎯 BTTS: {predictions['btts']['prediction']}\n"
        f"   Confidence: {predictions['btts']['confidence']:.1f}%\n\n"
        f"⏱ First Half: {predictions['first_half']['prediction']}\n"
        f"   Confidence: {predictions['first_half']['confidence']:.1f}%\n"
        f"{'➖' * 20}\n"
    )
    
    return formatted_text

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
            "This may take a moment while I analyze matches from multiple leagues."
        )
        
        try:
            # Initialize scraper
            scraper = BettingScraper()
            logger.info("BettingScraper initialized")
            
            await status_message.edit_text(
                "✅ System initialized\n"
                "🔄 Fetching and analyzing matches from:\n"
                "• Premier League 🏴󠁧󠁢󠁥󠁮󠁧󠁿\n"
                "• La Liga 🇪🇸\n"
                "• Serie A 🇮🇹\n"
                "• Bundesliga 🇩🇪\n"
                "• Ligue 1 🇫🇷\n"
                "• Eredivisie 🇳🇱\n"
                "• Primeira Liga 🇵🇹"
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
            
            # Group predictions by league
            league_predictions = {}
            for prediction in predictions:
                league_name = prediction['league']['name']
                if league_name not in league_predictions:
                    league_predictions[league_name] = []
                league_predictions[league_name].append(prediction)
            
            # Format predictions by league
            formatted_messages = []
            for league_name, league_preds in league_predictions.items():
                formatted_predictions = []
                for prediction in league_preds:
                    try:
                        formatted_text = format_prediction(prediction)
                        formatted_predictions.append(formatted_text)
                    except Exception as format_error:
                        logger.error(f"Error formatting prediction: {str(format_error)}")
                        continue
                
                if formatted_predictions:
                    league_message = "\n".join(formatted_predictions)
                    formatted_messages.append(league_message)
            
            if not formatted_messages:
                await status_message.edit_text(
                    "❌ Error formatting predictions.\n"
                    "This might be due to unexpected data format.\n"
                    "The development team has been notified."
                )
                return
            
            # Delete status message
            await status_message.delete()
            
            # Send predictions in chunks if needed
            intro_message = "🎯 *Football Predictions*\n\n"
            current_message = intro_message
            
            for message in formatted_messages:
                if len(current_message + message) > 4000:  # Telegram message limit
                    await update.message.reply_text(current_message, parse_mode='Markdown')
                    current_message = message
                else:
                    current_message += message
            
            if current_message:
                await update.message.reply_text(current_message, parse_mode='Markdown')
                
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
    # Load environment variables
    load_dotenv()
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")

    # Configure logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)

    logger.info("Starting bot with configuration:")
    logger.info(f"- TELEGRAM_BOT_TOKEN: {'*' * len(token)}")
    logger.info(f"- RAPIDAPI_KEY: {'*' * len(os.getenv('RAPIDAPI_KEY', ''))}")

    try:
        # Build application with minimal configuration
        builder = ApplicationBuilder()
        builder.token(token)
        builder.concurrent_updates(True)
        builder.job_queue(None)  # Explicitly disable job queue
        application = builder.build()

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("predictions", get_predictions))

        # Start the bot
        logger.info("Starting bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    main()
