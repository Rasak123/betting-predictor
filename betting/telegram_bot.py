import logging

# Handle Python 3.13 compatibility (imghdr module removed)
try:
    from telegram import Update, ParseMode
    from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError as e:
    # For Python 3.13+
    logging.warning(f"Telegram import error: {e}")
    logging.warning("Using placeholder classes for Telegram functionality")
    
    # Define placeholder classes
    class Update: pass
    class ParseMode: MARKDOWN = 'markdown'
    class CallbackContext: pass
    class TelegramError(Exception): pass
    class Filters: text = None
    class CommandHandler: 
        def __init__(self, *args, **kwargs): pass
    class MessageHandler:
        def __init__(self, *args, **kwargs): pass
    class Updater:
        def __init__(self, *args, **kwargs): pass
        def start_polling(self): pass
        def idle(self): pass
        
    TELEGRAM_AVAILABLE = False
import os
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional
from .main import run_predictions, LEAGUES
from datetime import datetime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def format_prediction_message(prediction: Dict[str, Any]) -> str:
    """Format prediction message for Telegram"""
    if not prediction:
        return "❌ Could not analyze match. Please try again later."
        
    try:
        match = prediction.get('match', {})
        probabilities = prediction.get('probabilities', {})
        score = prediction.get('score', {})
        over_under = prediction.get('over_under', {})
        btts = prediction.get('btts', {})
        first_half = prediction.get('first_half', {})
        
        league_name = match.get('league', 'Unknown League')
        country = match.get('country', 'Unknown Country')
        home_team = match.get('home_team', 'Unknown Home Team')
        away_team = match.get('away_team', 'Unknown Away Team')
        match_date = match.get('date', 'Unknown Date')
        
        # Try to format the date nicely
        try:
            date_obj = datetime.fromisoformat(match_date.replace('Z', '+00:00'))
            match_date = date_obj.strftime('%A, %d %B %Y - %H:%M')
        except (ValueError, TypeError, AttributeError):
            pass
        
        message = [
            f"🏆 *{league_name} ({country})*",
            f"⚽ *{home_team} vs {away_team}*",
            f"📅 {match_date}",
            f"\n📊 *Match Prediction*",
            f"🏁 Outcome: *{prediction.get('prediction', 'Unknown')}*",
            f"🔢 Score: *{score.get('display', '?-?')}*",
            f"💪 Confidence: {prediction.get('confidence', 0)}%",
            f"\n📈 *Win Probabilities*",
            f"🏠 {home_team}: {probabilities.get('home', 0)}%",
            f"🤝 Draw: {probabilities.get('draw', 0)}%",
            f"🚌 {away_team}: {probabilities.get('away', 0)}%"
        ]
        
        # Add over/under predictions
        message.append("\n📊 *Over/Under*")
        for key, ou_pred in over_under.items():
            if ou_pred:
                threshold = ou_pred.get('threshold')
                prediction_text = "Over" if ou_pred.get('prediction') else "Under"
                probability = ou_pred.get('probability', 0)
                message.append(f"O/U {threshold}: *{prediction_text}* ({probability}%)")  
        
        # Add BTTS prediction
        if btts:
            message.append("\n📊 *Both Teams To Score*")
            btts_text = "Yes" if btts.get('prediction') else "No"
            btts_prob = btts.get('probability', 0)
            message.append(f"BTTS: *{btts_text}* ({btts_prob}%)")
        
        # Add first half prediction
        if first_half:
            message.append("\n📊 *First Half*")
            fh_pred = first_half.get('prediction', 'Unknown')
            fh_conf = first_half.get('confidence', 0)
            message.append(f"Result: *{fh_pred}* ({fh_conf}%)")
        
        return "\n".join(message)
        
    except Exception as e:
        logger.error(f"Error formatting prediction message: {str(e)}")
        return "❌ Error formatting prediction message. Please try again later."

def get_predictions(update: Update, context: CallbackContext) -> None:
    """Send predictions for upcoming matches"""
    try:
        # Send initial message
        message = update.message.reply_text("⏳ Analyzing upcoming matches... This may take a minute.")
        
        # Run predictions
        predictions = run_predictions()
        
        if not predictions:
            update.message.reply_text("❌ Could not generate predictions for any matches. Please try again later.")
            return
        
        # Delete the waiting message
        try:
            context.bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)
        except TelegramError:
            pass
        
        # Send summary message
        update.message.reply_text(
            f"📊 *Found {len(predictions)} upcoming matches with predictions*\n"
            f"I'll send them one by one...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Send each prediction
        for prediction in predictions:
            try:
                formatted_text = format_prediction_message(prediction)
                if formatted_text:
                    # Split message if too long
                    if len(formatted_text) > 4096:
                        chunks = [formatted_text[i:i+4096] for i in range(0, len(formatted_text), 4096)]
                        for chunk in chunks:
                            update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
                    else:
                        update.message.reply_text(formatted_text, parse_mode=ParseMode.MARKDOWN)
                else:
                    logger.error("Empty prediction message")
                    
            except Exception as e:
                logger.error(f"Error sending prediction: {str(e)}")
                continue
        
        # Send completion message
        update.message.reply_text("✅ All predictions sent!")
        
    except Exception as e:
        logger.error(f"Error in get_predictions: {str(e)}")
        update.message.reply_text("❌ An error occurred while getting predictions. Please try again later.")

def get_leagues(update: Update, context: CallbackContext) -> None:
    """Send a list of supported leagues"""
    try:
        message = ["📋 *Supported Leagues*"]
        
        for league_key, league_info in LEAGUES.items():
            message.append(f"🏆 {league_info['name']} ({league_info['country']})")
        
        update.message.reply_text("\n".join(message), parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Error in get_leagues: {str(e)}")
        update.message.reply_text("❌ An error occurred while getting leagues. Please try again later.")

def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    try:
        user = update.effective_user
        logger.info(f"Start command received from user {user.id}")
        update.message.reply_text(
            f"Hi {user.first_name}! 👋\n\n"
            "Welcome to the Football Betting Predictor Bot!\n\n"
            "*Available commands:*\n"
            "/predictions - Get predictions for upcoming matches\n"
            "/leagues - Show supported leagues\n"
            "/help - Show this help message",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Error in start command: {str(e)}")
        update.message.reply_text("Sorry, something went wrong. Please try again.")

def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    try:
        logger.info("Help command received")
        update.message.reply_text(
            "*Available commands:*\n"
            "/predictions - Get predictions for upcoming matches\n"
            "/leagues - Show supported leagues\n"
            "/help - Show this help message",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Error in help command: {str(e)}")
        update.message.reply_text("Sorry, something went wrong. Please try again.")

def handle_text(update: Update, context: CallbackContext) -> None:
    """Handle text messages"""
    text = update.message.text.lower()
    
    if 'prediction' in text or 'predict' in text:
        get_predictions(update, context)
    elif 'league' in text:
        get_leagues(update, context)
    elif 'help' in text:
        help_command(update, context)
    else:
        update.message.reply_text(
            "I didn't understand that. Try using one of these commands:\n"
            "/predictions - Get predictions for upcoming matches\n"
            "/leagues - Show supported leagues\n"
            "/help - Show help message"
        )

def run_bot() -> None:
    """Main function to run the bot"""
    if not TELEGRAM_AVAILABLE:
        print("Telegram bot functionality is not available with your current Python version.")
        print("Please use Python 3.10-3.12 for full Telegram bot functionality.")
        print("You can still use the predictions functionality with: python main.py --mode predictions")
        return
        
    try:
        # Load environment variables
        load_dotenv()
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        
        # If no token found in environment, use the hardcoded one for testing
        if not token:
            token = '7769015532:AAHD5kETpBuZp8cRXefTOjciPOuEkJBcAF0'  # Hardcoded for testing only
            
        # Create updater and dispatcher
        updater = Updater(token=token, use_context=True)
        dispatcher = updater.dispatcher
        
        # Add command handlers
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(CommandHandler("help", help_command))
        dispatcher.add_handler(CommandHandler("predictions", get_predictions))
        dispatcher.add_handler(CommandHandler("leagues", get_leagues))
        
        # Add text handler
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
        
        # Start the bot
        logger.info("Starting bot...")
        updater.start_polling()
        updater.idle()
        
    except Exception as e:
        logger.error(f"Error starting bot: {str(e)}")
        raise
