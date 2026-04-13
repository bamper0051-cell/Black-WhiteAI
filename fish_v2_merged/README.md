# 🚀 АВТОМУВИ

Бот-парсер новостей с ИИ-переписыванием и TTS-озвучкой.

## Быстрый старт (Termux)

```bash
chmod +x setup.sh
./setup.sh
python bot.py
```

## Команды бота

| Команда | Действие |
|---------|----------|
| /run | Полный цикл (парсинг + обработка) |
| /parse | Только парсинг новостей |
| /process | Обработать накопленные новости |
| /stats | Статистика |
| /test | Тест LLM подключения |
| /voices | Список русских голосов edge-tts |
| /setllm openai gpt-4o | Сменить LLM провайдера |
| /setvoice ru-RU-DmitryNeural | Сменить голос TTS |
| /help | Список команд |

## LLM провайдеры

- `openai` — GPT-4o, GPT-4o-mini
- `mistral` — mistral-small-latest и др.
- `grok` — grok-beta (x.ai)
- `gemini` — gemini-1.5-flash/pro
- `ollama` — локально (llama3.2 и др.)
- `claude` — claude-3-haiku и др.

## Смена LLM на лету

```
/setllm openai gpt-4o sk-ваш-ключ
/setllm ollama llama3.2
```

## Голоса TTS (edge-tts, без API)

- `ru-RU-DmitryNeural` — Дмитрий (муж)
- `ru-RU-SvetlanaNeural` — Светлана (жен)
- `ru-RU-DariyaNeural` — Дария (жен)

Полный список: `/voices`

## Фоновый запуск в Termux

```bash
nohup python bot.py > automuvie.log 2>&1 &
```
