"""Утилита подготовки структуры проекта parser.

Изначально этот файл был недописан и ломал импорт/компиляцию.
Оставлен как безопасный генератор-заготовка.
"""
from pathlib import Path

PROJECT_ROOT = Path("telegram_parser_project")
DIRECTORIES = [
    "app",
    "app/parsers",
    "app/models",
    "data",
    "utils",
    "logs",
]

FILES = {
    "README.md": "# Telegram Parser Project\nParser for chats, groups, channels and users in Telegram\n",
    "requirements.txt": "pyTelegramBotAPI\nbeautifulsoup4\nrequests\n",
    "app/__init__.py": "",
    "app/main.py": (
        "import os\n"
        "import telebot\n\n"
        "API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')\n"
        "bot = telebot.TeleBot(API_TOKEN) if API_TOKEN else None\n\n"
        "@bot.message_handler(commands=['start'])\n"
        "def start(message):\n"
        "    bot.reply_to(message, 'Telegram Parser Bot Started!')\n\n"
        "if __name__ == '__main__':\n"
        "    if not bot:\n"
        "        raise SystemExit('Set TELEGRAM_BOT_TOKEN first')\n"
        "    bot.polling()\n"
    ),
    "app/parsers/__init__.py": "",
    "app/parsers/telegram_parser.py": (
        "class TelegramParser:\n"
        "    def parse(self, source: str) -> dict:\n"
        "        return {'source': source, 'status': 'stub'}\n"
    ),
}


def scaffold_project(root: Path = PROJECT_ROOT) -> Path:
    root.mkdir(exist_ok=True)
    for rel in DIRECTORIES:
        (root / rel).mkdir(parents=True, exist_ok=True)
    for rel, content in FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
    return root


if __name__ == '__main__':
    created = scaffold_project()
    print(f'Created parser scaffold at: {created.resolve()}')
