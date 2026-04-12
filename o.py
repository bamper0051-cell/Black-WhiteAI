# -*- coding: utf-8 -*-
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import types # 

# 1. Принудительно задаем конфиг клиента
client = genai.Client(
    api_key="AIzaSyBLynqQ5DD9H0IzzrX7SP0WpzC0PLAYU2w",
    http_options={'api_version': 'v1'}
)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        #
        response = client.models.generate_content(
            model="gemini-1.5-flash", 
            contents=update.message.text
        )
        
        if response.text:
            await update.message.reply_text(response.text)
        else:
            await update.message.reply_text(").")
            
    except Exception as e:
        print("Error details: {e}")
        # 404 
        await update.message.reply_text( API {e}y)

def main():
    # 
    app = Application.builder().token("8542269896:AAHvZIlxZ9pVDj-yb1yhLmjVp_pJM2fW7p4").build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("API v1...")
    app.run_polling()

if __name__ == "__main__":
    main()
