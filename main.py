import os
import sys
import threading

# ── Configuration from environment ───────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', os.environ.get('BOT_TOKEN', ''))
ADMIN_ID = os.environ.get('ADMIN_ID', '')

def _start_server():
    """Start the Flask admin web server in a background thread."""
    try:
        from admin_web import start_admin_web
        start_admin_web()
        print("✅ Admin web server started", flush=True)
    except Exception as e:
        print(f"⚠️  Admin web server failed to start: {e}", flush=True)

def _start_bot():
    """Start the Telegram bot."""
    # Try to use the full bot.py if available
    try:
        from bot import main as bot_main
        bot_main()
        return
    except ImportError:
        pass

    # Fallback: simple bot using TELEGRAM_TOKEN
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == 'YOUR_BOT_TOKEN':
        print("⚠️  TELEGRAM_TOKEN not set. Set it via environment variable TELEGRAM_TOKEN.", flush=True)
        print("    Example: export TELEGRAM_TOKEN=123456:ABC-DEF...", flush=True)
        # Keep the process alive so the server stays up
        import time
        while True:
            time.sleep(60)
        return

    try:
        import telebot
        bot = telebot.TeleBot(TELEGRAM_TOKEN)

        @bot.message_handler(commands=['start'])
        def start(message):
            bot.reply_to(message, "🤖 BlackBugsAI Bot Started!\n\nSend any message to interact.")

        print(f"✅ Telegram bot started (admin_id={ADMIN_ID or 'not set'})", flush=True)
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ Telegram bot failed: {e}", flush=True)

if __name__ == "__main__":
    print("🚀 Starting BlackBugsAI...", flush=True)

    # Start admin web server first (in background thread)
    server_thread = threading.Thread(target=_start_server, daemon=True)
    server_thread.start()

    # Give the server a moment to bind
    import time
    time.sleep(1)

    # Start the bot (blocking)
    _start_bot()
