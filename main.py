import os
from flask import Flask, request
from telebot import TeleBot, types

# Load environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"

# Initialize the bot and Flask app
bot = TeleBot(TELEGRAM_BOT_TOKEN)
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    """Handles incoming updates from Telegram."""
    json_string = request.get_data().decode("utf-8")
    update = types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/", methods=["GET"])
def index():
    """Health check route."""
    return "Bot is running!", 200

# Define a simple command handler
@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(message, "Welcome to Soltradingjoe_bot! How can I assist you today?")

@bot.message_handler(commands=["help"])
def send_help(message):
    bot.reply_to(message, "Here are the commands you can use:\n/start - Start the bot\n/help - Get help")

if __name__ == "__main__":
    # Remove any previous webhooks and set a new one
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)

    # Run the Flask app
    app.run(host="0.0.0.0", port=5000)
