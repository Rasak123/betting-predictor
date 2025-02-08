import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from betting_scraper import BettingScraper
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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

def get_predictions(update: Update, context: CallbackContext) -> None:
    """Send predictions for upcoming matches"""
    try:
        logger.info("Starting prediction request")
        scraper = BettingScraper()
        
        # Get matches
        matches = scraper.get_matches(['premier_league'])
        if not matches:
            logger.error("No matches found")
            update.message.reply_text("No upcoming matches found for analysis.")
            return
            
        logger.info(f"Found {len(matches)} matches")
        
        # Process each match
        predictions = []
        for match in matches:
            try:
                logger.info(f"Analyzing match: {match.get('home_team', 'Unknown')} vs {match.get('away_team', 'Unknown')}")
                
                # Validate match data
                required_fields = ['home_team', 'away_team', 'home_team_id', 'away_team_id', 'league_id', 'date']
                missing_fields = [field for field in required_fields if field not in match]
                if missing_fields:
                    logger.error(f"Match missing required fields: {missing_fields}")
                    continue
                
                # Get match analysis
                analysis = scraper.analyze_match(match)
                if not analysis:
                    logger.error(f"Failed to analyze match: {match.get('home_team')} vs {match.get('away_team')}")
                    continue
                
                # Validate analysis data
                required_analysis = ['home_form', 'away_form', 'h2h_stats', 'predictions', 'predicted_score', 'confidence']
                missing_analysis = [field for field in required_analysis if field not in analysis]
                if missing_analysis:
                    logger.error(f"Analysis missing required fields: {missing_analysis}")
                    continue
                
                predictions.append({
                    'match': match,
                    'analysis': analysis
                })
                logger.info(f"Successfully analyzed match: {match['home_team']} vs {match['away_team']}")
                
            except Exception as e:
                logger.error(f"Error processing match: {str(e)}")
                continue
        
        if not predictions:
            logger.error("No valid predictions generated")
            update.message.reply_text("Could not generate predictions for any matches. Please try again later.")
            return
        
        # Format and send predictions
        for prediction in predictions:
            try:
                formatted_text = format_prediction_message(prediction['match'], prediction['analysis'])
                if formatted_text:
                    # Split message if too long
                    if len(formatted_text) > 4096:
                        chunks = [formatted_text[i:i+4096] for i in range(0, len(formatted_text), 4096)]
                        for chunk in chunks:
                            update.message.reply_text(chunk, parse_mode='Markdown')
                    else:
                        update.message.reply_text(formatted_text, parse_mode='Markdown')
                else:
                    logger.error("Empty prediction message")
                    
            except Exception as e:
                logger.error(f"Error sending prediction: {str(e)}")
                continue
        
    except Exception as e:
        logger.error(f"Error in get_predictions: {str(e)}")
        update.message.reply_text("❌ An error occurred while getting predictions. Please try again later.")

def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    try:
        user = update.effective_user
        logger.info(f"Start command received from user {user.id}")
        update.message.reply_text(
            f"Hi {user.first_name}! 👋\n\n"
            "Welcome to the Football Betting Predictor Bot!\n\n"
            "Available commands:\n"
            "/predictions - Get predictions for upcoming matches\n"
            "/help - Show this help message"
        )
    except Exception as e:
        logger.error(f"Error in start command: {str(e)}")
        update.message.reply_text("Sorry, something went wrong. Please try again.")

def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    try:
        logger.info("Help command received")
        update.message.reply_text(
            "Available commands:\n"
            "/predictions - Get predictions for upcoming matches\n"
            "/help - Show this help message"
        )
    except Exception as e:
        logger.error(f"Error in help command: {str(e)}")
        update.message.reply_text("Sorry, something went wrong. Please try again.")

def main() -> None:
    """Main function to run the bot"""
    try:
        # Load environment variables
        load_dotenv()
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")
            
        # Create updater and dispatcher
        updater = Updater(token=token, use_context=True)
        dispatcher = updater.dispatcher
        
        # Add command handlers
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(CommandHandler("help", help_command))
        dispatcher.add_handler(CommandHandler("predictions", get_predictions))
        
        # Start the bot
        logger.info("Starting bot...")
        updater.start_polling()
        updater.idle()
        
    except Exception as e:
        logger.error(f"Error starting bot: {str(e)}")
        raise

if __name__ == '__main__':
    main()
