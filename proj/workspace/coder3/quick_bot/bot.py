import os
import telebot

TOKEN = os.getenv("BOT_TOKEN", "")
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

@bot.message_handler(commands=["start", "help"])
def start(message):
    bot.reply_to(message, "<b>Привет.</b> Я шаблонный бот от AGENT_CODER3")

if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("BOT_TOKEN is empty")
    bot.infinity_polling()
