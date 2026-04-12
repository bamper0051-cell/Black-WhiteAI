"""Базовая конфигурация парсера Telegram.
Заполни значения через переменные окружения или локальный .env.
"""
import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0") or 0)
DB_PATH = os.getenv("PARSER_DB_PATH", "data/telegram.db")
