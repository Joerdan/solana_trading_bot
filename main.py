
import os
import requests
from solana.rpc.api import Client
from telebot import TeleBot
from flask import Flask

# Configuration (Environment Variables)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
WALLET_PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY")
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

# Ensure sensitive variables are set
if not TELEGRAM_BOT_TOKEN or not DATABASE_URL or not WALLET_PRIVATE_KEY:
    raise EnvironmentError("Missing required environment variables. Please set TELEGRAM_BOT_TOKEN, DATABASE_URL, and WALLET_PRIVATE_KEY.")

# Solana Client
solana_client = Client(SOLANA_RPC_URL)

# Telegram Bot
bot = TeleBot(TELEGRAM_BOT_TOKEN)

# Flask App
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

if __name__ == "__main__":
    from threading import Thread

    # Start Flask app in a thread
    flask_thread = Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": 5000})
    flask_thread.start()

    # Start Telegram bot polling
    bot.polling()
