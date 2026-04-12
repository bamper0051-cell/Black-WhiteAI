import telebot
from app.parsers.telegram_parser import TelegramParser

API_TOKEN = 'YOUR_BOT_TOKEN'

bot = telebot.TeleBot(API_TOKEN)
parser = TelegramParser()

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Telegram Parser Bot Started!")

if __name__ == "__main__":
    bot.polling()
