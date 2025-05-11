# Betting Match Predictor

A comprehensive football match prediction system that uses statistical analysis to predict match outcomes, scores, and other betting markets.

## Setup

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

### Getting Your Telegram Bot Token

1. Open Telegram and search for "@BotFather"
2. Start a chat with BotFather and send `/newbot`
3. Follow the instructions to create your bot
4. Copy the API token provided by BotFather
5. Add the token to your `.env` file as `TELEGRAM_BOT_TOKEN`

## Usage

1. Open `betting_scraper.py` and replace `YOUR_BETTING_WEBSITE_URL` with the actual betting website URL you want to scrape.

2. Modify the `parse_matches` method to match the HTML structure of your target website. You'll need to:
   - Update the CSS selectors to match the website's HTML structure
   - Adjust the data extraction logic based on the website's layout

3. Run the script:
```bash
python betting_scraper.py
```

### Running the Telegram Bot
```bash
python telegram_bot.py
```

### Telegram Bot Commands
- `/start` - Start the bot and see available commands
- `/predictions` - Get predictions for upcoming matches
- `/help` - Show help message

## Project Structure

The project has been organized into a modular structure for better maintainability:

```
betting/
  ├── __init__.py         # Package initialization
  ├── api_client.py       # Football API client
  ├── models.py           # Data models for teams, matches, predictions
  ├── predictor.py        # Match prediction algorithms
  ├── main.py             # Main prediction functionality
  └── telegram_bot.py     # Telegram bot implementation
main.py                   # Application entry point
requirements.txt          # Project dependencies
```

## Features

- Modular, maintainable code structure
- Statistical analysis of team performance and head-to-head records
- Multiple prediction markets (match outcome, score, over/under, BTTS, first half)
- Confidence ratings for predictions
- Enhanced Telegram bot with natural language understanding
- Support for multiple football leagues
- Comprehensive error handling and logging

## Important Notes

- Make sure to check the website's robots.txt and terms of service before scraping
- Consider implementing additional delays between requests to be respectful to the website
- Some betting websites may have anti-scraping measures in place
- This is a basic implementation that you'll need to customize based on your specific needs

## Customization

You can extend this script by:
1. Adding more data fields to collect
2. Implementing prediction algorithms
3. Adding database storage
4. Creating a user interface
5. Adding historical data analysis

## Deployment

### Option 1: Railway.app (Recommended)

1. Create a [Railway.app](https://railway.app) account
2. Install Railway CLI:
```bash
npm i -g @railway/cli
```

3. Login to Railway:
```bash
railway login
```

4. Create a new project:
```bash
railway init
```

5. Add environment variables in Railway dashboard:
- `RAPIDAPI_KEY`
- `TELEGRAM_BOT_TOKEN`

6. Deploy:
```bash
railway up
```

### Option 2: Heroku

1. Install [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
2. Login to Heroku:
```bash
heroku login
```

3. Create a new app:
```bash
heroku create your-app-name
```

4. Set environment variables:
```bash
heroku config:set RAPIDAPI_KEY=your_rapidapi_key
heroku config:set TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

5. Deploy:
```bash
git push heroku main
```

### Option 3: DigitalOcean

1. Create a DigitalOcean account
2. Create a new Droplet (Ubuntu)
3. SSH into your Droplet
4. Install dependencies:
```bash
sudo apt update
sudo apt install python3-pip python3-venv
```

5. Clone your repository
6. Set up environment variables
7. Create a systemd service for automatic startup

## Usage

Once deployed, interact with the bot on Telegram:
1. `/start` - Start the bot
2. `/predictions` - Get match predictions
3. `/help` - Show help message
