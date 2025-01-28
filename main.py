import os
import requests
import psycopg2
from flask import Flask, request
from telebot import TeleBot, types
from threading import Thread
import time
from datetime import datetime

# Environment Variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"

# Bot Configuration
bot = TeleBot(TELEGRAM_BOT_TOKEN)
app = Flask(__name__)

# Allowed User IDs
AUTHORIZED_USERS = [715593260]  # Replace with your Telegram user ID

# Database Connection
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# Helper: Only allow authorized users
def is_authorized(user_id):
    return user_id in AUTHORIZED_USERS

# Routes
@app.route("/webhook", methods=["POST"])
def webhook():
    json_string = request.get_data().decode("utf-8")
    update = types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/", methods=["GET"])
def index():
    return "Bot is running!", 200

# Command: Start
@bot.message_handler(commands=["start"])
def send_welcome(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "You are not authorized to use this bot.")
        return
    bot.reply_to(message, "Welcome to Soltradingjoe_bot! Use /help for commands.")

# Command: Help
@bot.message_handler(commands=["help"])
def send_help(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "You are not authorized to use this bot.")
        return
    bot.reply_to(message, "Commands:\n/start - Start the bot\n/help - Get help\n/signals - Show recent buy/sell signals.")

# Signal Generation Logic
def fetch_meme_coins():
    url = "https://api.dexscreener.com/latest/dex/pairs/solana"
    response = requests.get(url)
    if response.status_code == 200:
        coins = response.json().get("pairs", [])
        print("Fetched coins:", coins)  # Debug: Log fetched data
        return [
            {
                "name": coin["baseToken"]["name"],
                "address": coin["baseToken"]["address"],
                "price": float(coin.get("priceUsd", 0)),
                "volume": float(coin.get("volume", 0)),
                "liquidity": float(coin.get("liquidity", 0)),
                "age": coin.get("age", "unknown"),
            }
            for coin in coins
        ]
    print("Failed to fetch data from Dexscreener:", response.status_code)  # Debug: Log failure
    return []

def store_signal(signal):
    try:
        print("Storing signal:", signal)  # Debug: Log signal being stored
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO signals (name, address, buy_price, sell_price, signal_time, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (address) DO NOTHING;
            """,
            (signal["name"], signal["address"], signal["buy_price"], signal["sell_price"], datetime.utcnow(), "pending"),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error storing signal: {e}")

def update_signal_status():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT address, sell_price FROM signals WHERE status = 'pending';")
        rows = cur.fetchall()

        for row in rows:
            address, sell_price = row
            token_data = next((coin for coin in fetch_meme_coins() if coin["address"] == address), None)

            if token_data and token_data["price"] >= sell_price:
                cur.execute(
                    "UPDATE signals SET status = 'success' WHERE address = %s;",
                    (address,),
                )
            else:
                cur.execute(
                    "UPDATE signals SET status = 'failure' WHERE address = %s AND NOW() - signal_time > interval '1 day';",
                    (address,),
                )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error updating signal status: {e}")

def generate_signals():
    coins = fetch_meme_coins()
    signals = []
    for coin in coins:
        if coin["liquidity"] > 1000 and coin["volume"] > 500:  # Lowered thresholds for testing
            buy_price = coin["price"]
            sell_price = buy_price * 1.3
            signal = {
                "name": coin["name"],
                "address": coin["address"],
                "buy_price": buy_price,
                "sell_price": sell_price,
                "reason": f"Liquidity: {coin['liquidity']}, Volume: {coin['volume']}"
            }
            signals.append(signal)
            store_signal(signal)
    return signals

def send_signals():
    while True:
        signals = generate_signals()
        if signals:
            for signal in signals:
                markup = types.InlineKeyboardMarkup()
                copy_button = types.InlineKeyboardButton(
                    text="Copy Address", callback_data=f"copy_{signal['address']}"
                )
                markup.add(copy_button)

                bot.send_message(
                    AUTHORIZED_USERS[0],
                    f"💡 Signal:\n\n"
                    f"Token: {signal['name']}\n"
                    f"Address: {signal['address']}\n"
                    f"Buy Price: ${signal['buy_price']:.4f}\n"
                    f"Sell Target: ${signal['sell_price']:.4f}\n"
                    f"Reason: {signal['reason']}",
                    reply_markup=markup
                )
        else:
            print("No signals generated at this time.")  # Debug: Log when no signals are generated
        update_signal_status()
        time.sleep(600)  # Run every 10 minutes

@bot.callback_query_handler(func=lambda call: call.data.startswith("copy_"))
def handle_copy(call):
    address = call.data.split("copy_")[1]
    bot.answer_callback_query(call.id, "Address copied!")
    bot.send_message(call.message.chat.id, f"Copied Address: {address}")

# Command: Signals
@bot.message_handler(commands=["signals"])
def show_signals(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "You are not authorized to use this bot.")
        return
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, address, buy_price, sell_price FROM signals WHERE status = 'pending';")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if rows:
        for row in rows:
            name, address, buy_price, sell_price = row
            markup = types.InlineKeyboardMarkup()
            copy_button = types.InlineKeyboardButton(
                text="Copy Address", callback_data=f"copy_{address}"
            )
            markup.add(copy_button)

            bot.send_message(
                message.chat.id,
                f"💡 Signal:\n\n"
                f"Token: {name}\n"
                f"Address: {address}\n"
                f"Buy Price: ${buy_price:.4f}\n"
                f"Sell Target: ${sell_price:.4f}\n",
                reply_markup=markup
            )
    else:
        bot.reply_to(message, "No signals found at the moment.")

# On Launch: Start Webhook and Signal Thread
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)

    # Start the signal thread
    signal_thread = Thread(target=send_signals)
    signal_thread.start()

    # Run the Flask app
    app.run(host="0.0.0.0", port=5000)
