"""
Telegram bot module compatible with Python 3.13.
This version removes the dependency on the deprecated imghdr module.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Import Telegram modules with compatibility handling
try:
    from telegram import Update, ParseMode
    from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Telegram import error: {e}")
    logger.warning("Using placeholder classes for Telegram functionality")
    
    # Define placeholder classes
    class Update: pass
    class ParseMode: 
        MARKDOWN = 'markdown'
        HTML = 'html'
    class CallbackContext: 
        def __init__(self, *args, **kwargs):
            self.args = args[1] if len(args) > 1 else []
    class TelegramError(Exception): pass
    class Filters: 
        text = None
        @staticmethod
        def text_filter(update):
            return True
        text = type('text', (), {'__call__': text_filter})()
    class CommandHandler: 
        def __init__(self, *args, **kwargs): 
            self.command = args[0] if args else None
            self.callback = args[1] if len(args) > 1 else None
    class MessageHandler:
        def __init__(self, *args, **kwargs):
            self.filters = args[0] if args else None
            self.callback = args[1] if len(args) > 1 else None
    class Updater:
        def __init__(self, *args, **kwargs): 
            self.token = args[0] if args else None
        def start_polling(self): 
            logger.info("Bot started in test mode (no actual Telegram connection)")
        def idle(self): 
            logger.info("Bot idle")
        def dispatcher(self):
            return self
        def add_handler(self, *args, **kwargs):
            logger.info(f"Added handler: {args[0].__class__.__name__}")
    
    TELEGRAM_AVAILABLE = False

from .main import run_predictions, LEAGUES

def format_prediction_message(prediction: Dict[str, Any]) -> str:
    """Format prediction message for Telegram"""
    try:
        match = prediction.get('match', {})
        home_team = match.get('home_team', 'Home')
        away_team = match.get('away_team', 'Away')
        league = match.get('league', 'Unknown League')
        country = match.get('country', '')
        
        # Format the main message
        message = f"*{home_team} vs {away_team}*\n"
        message += f"*{league}* • {country}\n\n"
        
        # Add probabilities
        probs = prediction.get('probabilities', {})
        message += "*Probabilities:*\n"
        message += f"🏠 {home_team}: {probs.get('home', 0):.1f}%\n"
        message += f"🤝 Draw: {probs.get('draw', 0):.1f}%\n"
        message += f"✈️ {away_team}: {probs.get('away', 0):.1f}%\n\n"
        
        # Add predicted score
        message += f"*Predicted Score:* {prediction.get('prediction', 'N/A')}\n"
        
        # Add confidence
        message += f"*Confidence:* {prediction.get('confidence', 0):.1f}%"
        
        return message
    except Exception as e:
        logger.error(f"Error formatting prediction: {e}")
        return "Error formatting prediction. Please try again later."

def get_predictions(update: Update, context: CallbackContext):
    """Send predictions for upcoming matches"""
    try:
        if not TELEGRAM_AVAILABLE:
            update.message.reply_text(
                "⚠️ Bot is running in test mode. No actual Telegram connection."
            )
            return
            
        update.message.reply_text("🔮 Generating predictions... Please wait...")
        
        # Get predictions
        predictions = run_predictions()
        
        if not predictions:
            update.message.reply_text("❌ Could not generate any predictions at the moment.")
            return
            
        # Send each prediction as a separate message
        for pred in predictions:
            message = format_prediction_message(pred)
            update.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN
            )
            
    except Exception as e:
        logger.error(f"Error in get_predictions: {e}")
        update.message.reply_text("❌ An error occurred while generating predictions.")

def get_leagues(update: Update, context: CallbackContext):
    """Send a list of supported leagues"""
    try:
        message = "*📋 Supported Leagues:*\n\n"
        for league_id, league in LEAGUES.items():
            message += f"• {league['name']} ({league['country']})\n"
        update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Error in get_leagues: {e}")
        update.message.reply_text("❌ Could not fetch league information.")

def start(update: Update, context: CallbackContext):
    """Send a message when the command /start is issued."""
    welcome_message = """
🤖 *Welcome to Betting Predictor Bot!* 🤖

I can help you with football match predictions. Here's what you can do:

• /predict - Get predictions for upcoming matches
• /leagues - Show supported leagues
• /help - Show this help message

You can also just type your request, like "show me predictions" or "what are the latest odds?"
"""
    update.message.reply_text(
        welcome_message,
        parse_mode=ParseMode.MARKDOWN
    )

def help_command(update: Update, context: CallbackContext):
    """Send a message when the command /help is issued."""
    help_text = """
📚 *Available Commands:*

/start - Start the bot and see welcome message
/predict - Get predictions for upcoming matches
/leagues - Show supported leagues
/help - Show this help message

💡 *Tip:* You can also type natural language requests like:
• "Show me predictions"
• "What are today's matches?"
• "Predictions for Premier League"
"""
    update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN
    )

def handle_text(update: Update, context: CallbackContext):
    """Handle text messages"""
    text = update.message.text.lower()
    
    if any(word in text for word in ['predict', 'match', 'game', 'fixture', 'bet', 'odds']):
        get_predictions(update, context)
    elif any(word in text for word in ['league', 'leagues', 'competition']):
        get_leagues(update, context)
    elif any(word in text for word in ['help', 'support', 'info']):
        help_command(update, context)
    else:
        update.message.reply_text(
            "🤔 I'm not sure what you're asking. Type /help to see what I can do!"
        )

def run_bot():
    """Run the Telegram bot"""
    try:
        # Load environment variables
        load_dotenv()
        
        # Get bot token from environment variables
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        
        if not token:
            logger.error("No TELEGRAM_BOT_TOKEN found in environment variables")
            print("Error: No TELEGRAM_BOT_TOKEN found in environment variables")
            return
            
        if not TELEGRAM_AVAILABLE:
            logger.warning("Running in test mode - no actual Telegram connection")
            print("Running in test mode - no actual Telegram connection")
            return
            
        # Create the Updater and pass it your bot's token
        updater = Updater(token)
        
        # Get the dispatcher to register handlers
        dp = updater.dispatcher
        
        # Register command handlers
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("help", help_command))
        dp.add_handler(CommandHandler("predict", get_predictions))
        dp.add_handler(CommandHandler("leagues", get_leagues))
        
        # Handle text messages
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
        
        # Log all errors
        def error(update: Update, context: CallbackContext):
            logger.warning(f'Update {update} caused error {context.error}')
            
        dp.add_error_handler(error)
        
        # Start the Bot
        updater.start_polling()
        
        logger.info("Bot is running. Press Ctrl+C to stop.")
        print("Bot is running. Press Ctrl+C to stop.")
        
        # Run the bot until you press Ctrl-C
        updater.idle()
        
    except Exception as e:
        logger.error(f"Error in run_bot: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    run_bot()
