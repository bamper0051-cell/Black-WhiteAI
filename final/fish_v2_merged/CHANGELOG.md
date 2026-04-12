# АВТОМУВИ v2.2 — Changelog

## Новые модули
- `image_gen.py` — генерация картинок (Pollinations бесплатно, DALL-E, Stability AI, HuggingFace)
- `msg_sender.py` — отправка сообщений, рассылка, отложенная отправка
- `updater.py` — диагностика зависимостей, обновление пакетов
- `bot_tools.py` — инструменты бота для агента-кодера
- `file_manager.py` — файловый менеджер в Telegram

## Исправленные ошибки
- 409 Conflict — умная обработка, не спамит ошибками
- list index out of range в format_check_results
- BUTTON_DATA_INVALID (FileManager) — кэш путей вместо длинных callback_data
- Дублирование обработчиков
- Синтаксические ошибки в f-strings

## Улучшения интерфейса
- Главное меню: +Генерация картинок, +Отправить сообщение, +Обновление
- LLM меню: приоритет бесплатным провайдерам, кнопка "Все провайдеры"
- Агент-кодер: меню выбора режима (код/ревью/fix/sandbox/инструменты)
- ИИ-чат: кнопки поиска, файлов, смены роли

## Бесплатные LLM (без оплаты)
- Groq: llama-3.3-70b-versatile (groq.com)
- Gemini: gemini-2.0-flash (aistudio.google.com)
- OpenRouter: множество :free моделей (openrouter.ai)
- Cerebras: llama3.1-8b сверхбыстрый (cloud.cerebras.ai)
- SambaNova: Llama-3.3-70B (cloud.sambanova.ai)

## Генерация картинок
- Pollinations: ПОЛНОСТЬЮ БЕСПЛАТНО, без ключа
- DALL-E 3: нужен OPENAI_API_KEY
- Stability AI: нужен STABILITY_API_KEY
- HuggingFace: бесплатно с HF_API_KEY

## Установка
```bash
pip install yt-dlp edge-tts requests flask python-dotenv --break-system-packages
# Для конвертации аудио:
pkg install ffmpeg
```
