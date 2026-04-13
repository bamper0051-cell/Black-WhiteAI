import os, sys

PROVIDERS = {
    '1': ('openai',   'gpt-4o-mini',              'https://platform.openai.com/api-keys'),
    '2': ('mistral',  'mistral-small-latest',      'https://console.mistral.ai/'),
    '3': ('grok',     'grok-beta',                 'https://console.x.ai/'),
    '4': ('gemini',   'gemini-1.5-flash',          'https://aistudio.google.com/'),
    '5': ('ollama',   'llama3.2',                  'локальный, ключ не нужен'),
    '6': ('claude',   'claude-3-haiku-20240307',   'https://console.anthropic.com/'),
}

VOICES = {
    '1': ('ru-RU-DmitryNeural',   '🇷🇺 Дмитрий (муж)'),
    '2': ('ru-RU-SvetlanaNeural', '🇷🇺 Светлана (жен)'),
    '3': ('ru-RU-DariyaNeural',   '🇷🇺 Дария (жен, живее)'),
    '4': ('en-US-GuyNeural',      '🇺🇸 Guy (англ, муж)'),
}

def choose(options: dict, prompt: str) -> str:
    print(f"\n{prompt}")
    for k, v in options.items():
        label = v[1] if isinstance(v, tuple) else v
        print(f"  {k}. {label}")
    while True:
        c = input("Выбор: ").strip()
        if c in options:
            return c
        print("  ❌ Неверный выбор")

def main():
    print("\n" + "="*40)
    print("  ⚙️  АВТОМУВИ — Мастер настройки")
    print("="*40)

    token = input("\n🤖 Telegram Bot Token: ").strip()
    chat_id = input("💬 Telegram Chat ID: ").strip()

    c = choose(
        {k: f"{v[0]} ({v[1]})" for k, v in PROVIDERS.items()},
        "🧠 Выбери LLM провайдера:"
    )
    provider, model, key_url = PROVIDERS[c]

    api_key = ''
    if provider != 'ollama':
        print(f"  🔗 Получить ключ: {key_url}")
        api_key = input(f"  🔑 API Key для {provider}: ").strip()

    custom_model = input(f"  📦 Модель [{model}] (Enter = оставить): ").strip()
    if custom_model:
        model = custom_model

    ollama_url = 'http://localhost:11434'
    if provider == 'ollama':
        u = input(f"  🌐 Ollama URL [{ollama_url}]: ").strip()
        if u:
            ollama_url = u

    c = choose(
        {k: v[1] for k, v in VOICES.items()},
        "🎙️  Выбери голос TTS (edge-tts, без API):"
    )
    voice = VOICES[c][0]

    interval = input("\n⏰ Интервал парсинга в часах [12]: ").strip() or '12'

    env = f"""TELEGRAM_BOT_TOKEN={token}
TELEGRAM_CHAT_ID={chat_id}

LLM_PROVIDER={provider}
LLM_MODEL={model}
LLM_API_KEY={api_key}
OLLAMA_BASE_URL={ollama_url}

TTS_VOICE={voice}
PARSE_INTERVAL_HOURS={interval}
"""
    with open('.env', 'w') as f:
        f.write(env)

    print("\n✅ .env сохранён!")
    print(f"   Провайдер: {provider} / {model}")
    print(f"   Голос: {voice}")
    print(f"   Интервал: {interval}ч")
    print("\n🚀 Запуск: python bot.py")

if __name__ == '__main__':
    main()
