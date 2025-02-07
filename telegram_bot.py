import logging
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.ext import Updater
from telegram import Update
from betting_scraper import BettingScraper
import os
from dotenv import load_dotenv

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_text(
        f"Hi {user.first_name}! 👋\n\n"
        "Welcome to the Premier League Betting Predictor Bot!\n\n"
        "Available commands:\n"
        "/predictions - Get predictions for upcoming matches\n"
        "/help - Show this help message"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "Available commands:\n"
        "/predictions - Get predictions for upcoming matches\n"
        "/help - Show this help message"
    )

def format_prediction(match_data):
    """Format a prediction into a readable message."""
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

async def get_predictions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send predictions when the command /predictions is issued."""
    try:
        # Send initial message
        message = await update.message.reply_text("🔄 Analyzing matches... Please wait.")
        
        # Create scraper instance
        scraper = BettingScraper()
        
        # Get predictions
        results = scraper.analyze_weekend_matches()
        
        if not results:
            await message.edit_text("No upcoming matches found for analysis.")
            return
        
        # Send each prediction as a separate message for better readability
        await message.edit_text("🎯 Here are the predictions for upcoming matches:")
        
        for match_data in results:
            formatted_prediction = format_prediction(match_data)
            await update.message.reply_text(formatted_prediction)
            
    except Exception as e:
        logger.error(f"Error getting predictions: {str(e)}")
        await update.message.reply_text(
            "Sorry, there was an error getting the predictions. Please try again later."
        )

def main():
    """Start the bot."""
    # Load environment variables
    load_dotenv()
    
    # Get bot token from environment variable
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")
    
    # Create application
    app = Application.builder().token(token).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("predictions", get_predictions))
    
    # Start the bot
    print("Starting bot...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
