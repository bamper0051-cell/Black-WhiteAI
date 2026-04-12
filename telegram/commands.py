"""
BlackBugsAI — Command handlers
Обработка текстовых команд и сообщений.
Импортируется из bot.py как telegram.commands
"""
# Этот модуль содержит логику команд перенесённую из bot.py
# В следующей версии handle_text будет разбита на:
#   /start /menu /help → commands.start_handler
#   /chat /code       → commands.agent_handler  
#   /admin            → commands.admin_handler
#   обычный текст     → commands.message_handler

# Пока используется bot.py напрямую.
# Шаг 5 в процессе выполнения.
