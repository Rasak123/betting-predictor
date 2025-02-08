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
        
        home_form_stats = prediction.get('home_form_stats', {})
        away_form_stats = prediction.get('away_form_stats', {})
        h2h_stats = prediction.get('h2h_stats', {})
        predicted_score = prediction.get('predicted_score', {})
        confidence = prediction.get('confidence', 0)
        
        # Format main match info
        formatted_text = (
            f"🏆 *{league_info['name']}* ({league_info['country']})\n"
            f"⚽ {match_info}\n"
            f"📅 {date}\n\n"
        )
        
        # Format home team statistics
        home_stats = (
            f"🏠 Home Team Form:\n"
            f"   • Avg Goals Scored: {home_form_stats.get('avg_goals_scored', 0)}\n"
            f"   • Avg Goals Conceded: {home_form_stats.get('avg_goals_conceded', 0)}\n"
            f"   • Clean Sheets: {home_form_stats.get('clean_sheets', 0)}\n"
            f"   • Failed to Score: {home_form_stats.get('failed_to_score', 0)}"
        )
        
        # Format away team statistics
        away_stats = (
            f"🚌 Away Team Form:\n"
            f"   • Avg Goals Scored: {away_form_stats.get('avg_goals_scored', 0)}\n"
            f"   • Avg Goals Conceded: {away_form_stats.get('avg_goals_conceded', 0)}\n"
            f"   • Clean Sheets: {away_form_stats.get('clean_sheets', 0)}\n"
            f"   • Failed to Score: {away_form_stats.get('failed_to_score', 0)}"
        )
        
        # Format head-to-head statistics
        h2h = (
            f"📊 Head-to-Head Stats (Last {h2h_stats.get('total_matches', 0)} matches):\n"
            f"   • Home Wins: {h2h_stats.get('home_wins', 0)}\n"
            f"   • Away Wins: {h2h_stats.get('away_wins', 0)}\n"
            f"   • Draws: {h2h_stats.get('draws', 0)}\n"
            f"   • Over 1.5 Goals: {h2h_stats.get('over_1_5', 0)}\n"
            f"   • Over 4.5 Goals: {h2h_stats.get('over_4_5', 0)}\n"
            f"   • Home Team Won Either Half: {h2h_stats.get('home_won_half', 0)}"
        )
        
        # Format predictions
        predictions_text = (
            f"🎯 Predictions:\n"
            f"   • Predicted Score: {predicted_score.get('home', 0)}-{predicted_score.get('away', 0)}\n"
            f"   • Over 1.5 Goals: {'✅' if predictions.get('over_1_5', {}).get('prediction', False) else '❌'} ({predictions.get('over_1_5', {}).get('probability', 0)}%)\n"
            f"   • Over 4.5 Goals: {'✅' if predictions.get('over_4_5', {}).get('prediction', False) else '❌'} ({predictions.get('over_4_5', {}).get('probability', 0)}%)\n"
            f"   • Home Team to Win Either Half: {'✅' if predictions.get('home_win_either_half', {}).get('prediction', False) else '❌'} ({predictions.get('home_win_either_half', {}).get('probability', 0)}%)\n"
            f"   • Most Corners: {predictions.get('most_corners', {}).get('team', '')} ({predictions.get('most_corners', {}).get('probability', 0)}%)"
        )
        
        # Format confidence explanation
        confidence_explanation = (
            f"🎲 Prediction Confidence: {confidence}%\n"
            f"Confidence factors:\n"
            f"   • Recent Form (30%)\n"
            f"   • H2H History (25%)\n"
            f"   • Goals Scored (20%)\n"
            f"   • Defense (15%)\n"
            f"   • Home Advantage (10%)"
        )
        
        # Combine all sections
        formatted_text += (
            f"{home_stats}\n\n"
            f"{away_stats}\n\n"
            f"{h2h}\n\n"
            f"{predictions_text}\n\n"
            f"{confidence_explanation}"
        )
        
        return formatted_text
        
    except Exception as e:
        logging.error(f"Error formatting prediction: {str(e)}")
        return "Error formatting prediction data"

def format_prediction_message(match, analysis):
    """Format prediction message for Telegram"""
    if not match or not analysis:
        return "❌ Could not analyze match. Please try again later."
        
    try:
        league_name = match.get('league', 'Unknown League')
        country = match.get('country', 'Unknown Country')
        home_team = match.get('home_team', 'Unknown Home Team')
        away_team = match.get('away_team', 'Unknown Away Team')
        match_date = match.get('date', 'Unknown Date')
        
        home_form = analysis.get('home_form', {})
        away_form = analysis.get('away_form', {})
        h2h = analysis.get('h2h_stats', {})
        predictions = analysis.get('predictions', {})
        predicted_score = analysis.get('predicted_score', {'home': 0, 'away': 0})
        confidence = analysis.get('confidence', 0)
        
        message = [
            f"🏆 *{league_name} ({country})*",
            f"⚽ *{home_team} vs {away_team}*",
            f"📅 {match_date}",
            f"\n📊 *Team Statistics*",
            f"\n🏠 *{home_team}*",
            f"⚽ Goals Scored (avg): {home_form.get('avg_goals_scored', 0)}",
            f"🥅 Goals Conceded (avg): {home_form.get('avg_goals_conceded', 0)}",
            f"🛡️ Clean Sheets: {home_form.get('clean_sheets', 0)}",
            f"❌ Failed to Score: {home_form.get('failed_to_score', 0)}",
            f"\n🚌 *{away_team}*",
            f"⚽ Goals Scored (avg): {away_form.get('avg_goals_scored', 0)}",
            f"🥅 Goals Conceded (avg): {away_form.get('avg_goals_conceded', 0)}",
            f"🛡️ Clean Sheets: {away_form.get('clean_sheets', 0)}",
            f"❌ Failed to Score: {away_form.get('failed_to_score', 0)}",
            f"\n🤝 *Head to Head (Last {h2h.get('total_matches', 0)} matches)*",
            f"🏠 Home Wins: {h2h.get('home_wins', 0)}",
            f"🚌 Away Wins: {h2h.get('away_wins', 0)}",
            f"🤝 Draws: {h2h.get('draws', 0)}",
            f"\n📈 *Predictions*",
            f"🎯 Predicted Score: {predicted_score['home']} - {predicted_score['away']}",
            f"💪 Confidence: {confidence}%"
        ]
        
        # Add additional predictions if available
        if predictions:
            message.append("\n📊 *Additional Predictions*")
            over_1_5 = predictions.get('over_1_5', {})
            over_4_5 = predictions.get('over_4_5', {})
            home_half = predictions.get('home_win_either_half', {})
            
            if over_1_5:
                message.append(f"Over 1.5 Goals: {'✅' if over_1_5.get('prediction') else '❌'} ({over_1_5.get('probability', 0)}%)")
            if over_4_5:
                message.append(f"Over 4.5 Goals: {'✅' if over_4_5.get('prediction') else '❌'} ({over_4_5.get('probability', 0)}%)")
            if home_half:
                message.append(f"Home Win Either Half: {'✅' if home_half.get('prediction') else '❌'} ({home_half.get('probability', 0)}%)")
        
        return "\n".join(message)
        
    except Exception as e:
        logger.error(f"Error formatting prediction message: {str(e)}")
        return "❌ Error formatting prediction message. Please try again later."

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
                    match = prediction.get('match', {})
                    analysis = prediction.get('analysis', {})
                    formatted_text = format_prediction_message(match, analysis)
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
