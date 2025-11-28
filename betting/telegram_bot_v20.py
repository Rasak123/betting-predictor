"""
Telegram bot module for python-telegram-bot v20.x
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

try:
    from telegram import __version_info__
    if __version_info__[0] < 20:
        raise ImportError("This module requires python-telegram-bot v20.0 or higher")
    from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
    from telegram.ext import (
        Application,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters
    )
    TELEGRAM_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Telegram import error: {e}")
    logger.warning("Using placeholder classes for Telegram functionality")
    TELEGRAM_AVAILABLE = False

from .main import run_predictions, LEAGUES

async def format_prediction_message(prediction: Dict[str, Any]) -> str:
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    welcome_message = """
🤖 *Welcome to Betting Predictor Bot!* 🤖

I can help you with football match predictions. Here's what you can do:

• /predict - Get predictions for upcoming matches
• /leagues - Show supported leagues
• /help - Show this help message

You can also just type your request, like "show me predictions" or "what are the latest odds?"
"""
    await update.message.reply_text(
        welcome_message,
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    await update.message.reply_text(
        help_text,
        parse_mode='Markdown'
    )

async def get_predictions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send predictions for upcoming matches"""
    try:
        if not TELEGRAM_AVAILABLE:
            await update.message.reply_text(
                "⚠️ Bot is running in test mode. No actual Telegram connection."
            )
            return
            
        await update.message.reply_text("🔮 Generating predictions... Please wait...")
        
        # Get predictions
        predictions = run_predictions()
        
        if not predictions:
            await update.message.reply_text("❌ Could not generate any predictions at the moment.")
            return
            
        # Send each prediction as a separate message
        for pred in predictions:
            message = await format_prediction_message(pred)
            await update.message.reply_text(
                message,
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error in get_predictions: {e}")
        await update.message.reply_text("❌ An error occurred while generating predictions.")

async def get_leagues(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a list of supported leagues"""
    try:
        message = "*📋 Supported Leagues:*\n\n"
        for league_id, league in LEAGUES.items():
            message += f"• {league['name']} ({league['country']})\n"
        await update.message.reply_text(
            message,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in get_leagues: {e}")
        await update.message.reply_text("❌ Could not fetch league information.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages"""
    text = update.message.text.lower()
    
    if any(word in text for word in ['predict', 'match', 'game', 'fixture', 'bet', 'odds']):
        await get_predictions(update, context)
    elif any(word in text for word in ['league', 'leagues', 'competition']):
        await get_leagues(update, context)
    elif any(word in text for word in ['help', 'support', 'info']):
        await help_command(update, context)
    else:
        await update.message.reply_text(
            "🤔 I'm not sure what you're asking. Type /help to see what I can do!"
        )

def run_bot() -> None:
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
            
        # Create the Application and pass it your bot's token
        application = Application.builder().token(token).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("predict", get_predictions))
        application.add_handler(CommandHandler("leagues", get_leagues))
        
        # Handle text messages
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        # Log all errors
        async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
            logger.error(f'Update {update} caused error {context.error}')
            
        application.add_error_handler(error_handler)
        
        print("Bot is running. Press Ctrl+C to stop.")
        
        # Run the bot until the user presses Ctrl-C
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Error in run_bot: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    run_bot()
