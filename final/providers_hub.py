"""
providers_hub.py — Центральный реестр всех провайдеров по категориям.

Категории:
  LLM_CHAT      — чат / ассистент (текст)
  LLM_CODER     — кодирование (предпочтительные модели)
  LLM_AGENT     — агенты / инструменты (function calling, long context)
  IMAGE         — генерация изображений
  TTS           — синтез речи
  TUNNEL        — туннели для Flask (bore, serveo, ngrok, cloudflared)

Использование:
  from providers_hub import hub
  active = hub.active_providers('LLM_CHAT')
  result = hub.call_best('LLM_CHAT', prompt='Привет')
"""

import os
import requests
import threading
import time
import config

def _set_env_hub(key, value):
    """Записывает переменную в .env и os.environ, совместимо с sys.modules подменой config."""
    import os, sys
    os.environ[str(key)] = str(value)
    # Ищем оригинальный модуль config до подмены через sys.modules trick
    cfg = sys.modules.get('config')
    env_path = getattr(cfg, '_ENV_PATH', None) or getattr(cfg, 'ENV_PATH', None)
    if env_path is None:
        import pathlib
        env_path = str(pathlib.Path(__file__).parent / '.env')
    try:
        from dotenv import set_key
        set_key(env_path, str(key), str(value))
    except Exception:
        pass


# ════════════════════════════════════════════════════════════════════
#  РЕЕСТР ПРОВАЙДЕРОВ ПО КАТЕГОРИЯМ
# ════════════════════════════════════════════════════════════════════

# LLM-провайдеры: общий чат / ассистент
LLM_CHAT_PROVIDERS = [
    ('groq',        'llama-3.3-70b-versatile',              'GROQ_API_KEY',        'https://api.groq.com/openai/v1'),
    ('cerebras',    'llama-3.3-70b',                        'CEREBRAS_API_KEY',    'https://api.cerebras.ai/v1'),
    ('sambanova',   'Meta-Llama-3.3-70B-Instruct',          'SAMBANOVA_API_KEY',   'https://api.sambanova.ai/v1'),
    ('gemini',      'gemini-2.0-flash',                     'GEMINI_API_KEY',      None),
    ('openrouter',  'meta-llama/llama-3.3-70b-instruct:free','OPENROUTER_API_KEY', 'https://openrouter.ai/api/v1'),
    ('mistral',     'mistral-small-latest',                 'MISTRAL_API_KEY',     'https://api.mistral.ai/v1'),
    ('deepseek',    'deepseek-chat',                        'DEEPSEEK_API_KEY',    'https://api.deepseek.com/v1'),
    ('openai',      'gpt-4o-mini',                          'OPENAI_API_KEY',      'https://api.openai.com/v1'),
    ('xai',         'grok-3-mini',                          'XAI_API_KEY',         'https://api.x.ai/v1'),
    ('together',    'meta-llama/Llama-3.3-70B-Instruct-Turbo','TOGETHER_API_KEY',  'https://api.together.xyz/v1'),
    ('novita',      'meta-llama/llama-3.3-70b-instruct',   'NOVITA_API_KEY',      'https://api.novita.ai/v3/openai'),
    ('deepinfra',   'meta-llama/Llama-3.3-70B-Instruct',   'DEEPINFRA_API_KEY',   'https://api.deepinfra.com/v1/openai'),
    ('chutes',      'deepseek-ai/DeepSeek-V3-0324',        'CHUTES_API_KEY',      'https://llm.chutes.ai/v1'),
    ('perplexity',  'sonar',                                'PERPLEXITY_API_KEY',  'https://api.perplexity.ai/v1'),
    ('cohere',      'command-r-plus',                       'COHERE_API_KEY',      'https://api.cohere.com/v1'),
    ('ollama',      'llama3.2',                             None,                  None),
]

# LLM для кодирования — предпочтительные модели-кодеры
LLM_CODER_PROVIDERS = [
    ('deepseek',    'deepseek-chat',                        'DEEPSEEK_API_KEY',    'https://api.deepseek.com/v1'),
    ('groq',        'llama-3.3-70b-versatile',              'GROQ_API_KEY',        'https://api.groq.com/openai/v1'),
    ('openrouter',  'deepseek/deepseek-r1:free',            'OPENROUTER_API_KEY',  'https://openrouter.ai/api/v1'),
    ('cerebras',    'qwen-3-32b',                           'CEREBRAS_API_KEY',    'https://api.cerebras.ai/v1'),
    ('mistral',     'codestral-latest',                     'MISTRAL_API_KEY',     'https://api.mistral.ai/v1'),
    ('openai',      'gpt-4.1-mini',                         'OPENAI_API_KEY',      'https://api.openai.com/v1'),
    ('together',    'deepseek-ai/DeepSeek-R1',              'TOGETHER_API_KEY',    'https://api.together.xyz/v1'),
    ('novita',      'deepseek/deepseek-r1',                 'NOVITA_API_KEY',      'https://api.novita.ai/v3/openai'),
    ('deepinfra',   'deepseek-ai/DeepSeek-R1',              'DEEPINFRA_API_KEY',   'https://api.deepinfra.com/v1/openai'),
    ('chutes',      'deepseek-ai/DeepSeek-R1',              'CHUTES_API_KEY',      'https://llm.chutes.ai/v1'),
    ('ollama',      'codellama',                            None,                  None),
]

# LLM для агентов — длинный контекст, function calling
LLM_AGENT_PROVIDERS = [
    ('gemini',      'gemini-2.0-flash',                     'GEMINI_API_KEY',      None),
    ('openai',      'gpt-4o-mini',                          'OPENAI_API_KEY',      'https://api.openai.com/v1'),
    ('groq',        'llama-3.3-70b-versatile',              'GROQ_API_KEY',        'https://api.groq.com/openai/v1'),
    ('deepseek',    'deepseek-chat',                        'DEEPSEEK_API_KEY',    'https://api.deepseek.com/v1'),
    ('openrouter',  'google/gemini-2.0-flash-001',          'OPENROUTER_API_KEY',  'https://openrouter.ai/api/v1'),
    ('mistral',     'mistral-small-latest',                 'MISTRAL_API_KEY',     'https://api.mistral.ai/v1'),
    ('cerebras',    'llama-3.3-70b',                        'CEREBRAS_API_KEY',    'https://api.cerebras.ai/v1'),
    ('ollama',      'llama3.2',                             None,                  None),
]

# Провайдеры генерации изображений
IMAGE_PROVIDERS = [
    # (имя, requires_key, env_key, описание)
    ('pollinations', False, None,               'Бесплатно без ключа'),
    ('huggingface',  True,  'HF_API_KEY',       'HF Inference API'),
    ('openai',       True,  'OPENAI_API_KEY',   'DALL-E 3'),
    ('stability',    True,  'STABILITY_API_KEY','Stability AI SDXL'),
    ('together',     True,  'TOGETHER_API_KEY', 'FLUX / SD via Together'),
    ('novita',       True,  'NOVITA_API_KEY',   'SDXL / FLUX'),
    ('deepinfra',    True,  'DEEPINFRA_API_KEY','SD / FLUX'),
]

# TTS провайдеры
TTS_PROVIDERS = [
    # (имя, requires_key, env_key, описание)
    ('edge',        False, None,              'edge-tts бесплатно (Microsoft)'),
    ('elevenlabs',  True,  'ELEVEN_API_KEY',  'ElevenLabs высокое качество'),
    ('openai',      True,  'OPENAI_API_KEY',  'OpenAI TTS-1 / TTS-1-HD'),
    ('google',      True,  'GEMINI_API_KEY',  'Google Cloud TTS'),
    ('deepgram',    True,  'DEEPGRAM_API_KEY','Deepgram Nova-2'),
]

# Туннели
TUNNEL_PROVIDERS = [
    # (имя, binary, install_cmd, протокол, описание)
    ('bore',        'bore',       'cargo install bore-cli',      'http',  'Rust, бесплатно, bore.pub'),
    ('serveo',      'ssh',        'pkg install openssh',         'https', 'SSH → serveo.net, бесплатно'),
    ('ngrok',       'ngrok',      'pkg install ngrok',           'https', 'ngrok.com, требует токен'),
    ('cloudflared', 'cloudflared','pkg install cloudflared',     'https', 'Cloudflare Tunnel'),
    ('localtunnel', 'lt',         'npm install -g localtunnel',  'https', 'localtunnel.me, npm'),
]


# ════════════════════════════════════════════════════════════════════
#  ХАБ — класс для работы с провайдерами
# ════════════════════════════════════════════════════════════════════

class ProvidersHub:
    """Центральный управляющий класс для всех провайдеров."""

    def __init__(self):
        self._cache = {}          # 'category:name' → {'ok': bool, 'ms': int, 'ts': float}
        self._lock  = threading.Lock()

    # ── Хелперы ───────────────────────────────────────────────────

    def _key_value(self, env_key: str) -> str:
        if not env_key:
            return 'no_key_needed'
        return os.environ.get(env_key, '') or getattr(config, env_key, '') or ''

    def _has_key(self, env_key) -> bool:
        if not env_key:
            return True   # не требует ключа
        return bool(self._key_value(env_key))

    # ── LLM ───────────────────────────────────────────────────────

    def active_llm(self, category: str = 'LLM_CHAT') -> list:
        """Возвращает список (name, model, base_url) для провайдеров у которых есть ключ."""
        tables = {
            'LLM_CHAT':  LLM_CHAT_PROVIDERS,
            'LLM_CODER': LLM_CODER_PROVIDERS,
            'LLM_AGENT': LLM_AGENT_PROVIDERS,
        }
        result = []
        for name, model, env_key, base_url in tables.get(category, LLM_CHAT_PROVIDERS):
            if self._has_key(env_key):
                result.append({'name': name, 'model': model,
                               'base_url': base_url, 'key': self._key_value(env_key)})
        return result

    def best_llm(self, category: str = 'LLM_CHAT'):
        """Возвращает первого доступного провайдера с ключом."""
        active = self.active_llm(category)
        return active[0] if active else None

    def call_best_llm(self, prompt: str, system: str = '',
                      category: str = 'LLM_CHAT',
                      max_tokens: int = 1200) -> str:
        """Вызывает лучший доступный LLM для категории с авто-фоллбэком."""
        from llm_client import _openai_compat_ex, _gemini_ex, _get_provider_key
        from llm_checker import RECOMMENDED

        active = self.active_llm(category)
        if not active:
            raise RuntimeError(f"Нет доступных провайдеров для {category}")

        last_err = None
        for p in active:
            try:
                name     = p['name']
                model    = p['model']
                api_key  = p['key']
                base_url = p['base_url']

                if name == 'gemini':
                    from llm_client import _gemini_ex
                    return _gemini_ex(prompt, system, model, api_key, max_tokens)
                elif name == 'ollama':
                    import requests as _req
                    messages = []
                    if system:
                        messages.append({'role': 'system', 'content': system})
                    messages.append({'role': 'user', 'content': prompt})
                    r = _req.post(f"{getattr(config, 'OLLAMA_BASE_URL', 'http://localhost:11434')}/api/chat",
                                  json={'model': model, 'messages': messages, 'stream': False},
                                  timeout=60)
                    r.raise_for_status()
                    return r.json()['message']['content'].strip()
                elif base_url:
                    from llm_client import _openai_compat_ex
                    return _openai_compat_ex(prompt, system, base_url, model, api_key, max_tokens)
                else:
                    raise ValueError(f"Нет base_url для {name}")
            except Exception as e:
                last_err = e
                err_s = str(e)
                if '401' in err_s or 'Unauthorized' in err_s:
                    continue  # плохой ключ → следующий
                continue

        raise RuntimeError(f"Все провайдеры [{category}] недоступны. Последняя ошибка: {last_err}")

    # ── Изображения ───────────────────────────────────────────────

    def active_image(self) -> list:
        """Список доступных провайдеров для генерации картинок."""
        result = []
        for name, needs_key, env_key, desc in IMAGE_PROVIDERS:
            if not needs_key or self._has_key(env_key):
                result.append({'name': name, 'env_key': env_key, 'desc': desc})
        return result

    def image_status(self) -> dict:
        """Возвращает статус каждого image-провайдера."""
        status = {}
        for name, needs_key, env_key, desc in IMAGE_PROVIDERS:
            has = not needs_key or self._has_key(env_key)
            status[name] = {
                'available': has,
                'needs_key': needs_key,
                'env_key':   env_key,
                'desc':      desc,
            }
        return status

    # ── TTS ───────────────────────────────────────────────────────

    def active_tts(self) -> list:
        """Список доступных TTS провайдеров."""
        result = []
        for name, needs_key, env_key, desc in TTS_PROVIDERS:
            if not needs_key or self._has_key(env_key):
                result.append({'name': name, 'env_key': env_key, 'desc': desc})
        return result

    def tts_status(self) -> dict:
        """Возвращает статус каждого TTS провайдера."""
        status = {}
        for name, needs_key, env_key, desc in TTS_PROVIDERS:
            has = not needs_key or self._has_key(env_key)
            status[name] = {
                'available': has,
                'needs_key': needs_key,
                'env_key':   env_key,
                'desc':      desc,
            }
        return status

    # ── Туннели ───────────────────────────────────────────────────

    def tunnel_status(self) -> dict:
        """Проверяет наличие бинарников туннелей в PATH."""
        import shutil
        status = {}
        for name, binary, install_cmd, proto, desc in TUNNEL_PROVIDERS:
            found = bool(shutil.which(binary))
            status[name] = {
                'installed': found,
                'binary':    binary,
                'install':   install_cmd,
                'proto':     proto,
                'desc':      desc,
            }
        return status

    def best_tunnel(self) -> str:
        """Возвращает имя лучшего доступного туннеля."""
        import shutil
        for name, binary, _, proto, _ in TUNNEL_PROVIDERS:
            if shutil.which(binary):
                # serveo работает через ssh — всегда доступен на Android
                return name
        return None

    # ── Авто-сбор (scan) ──────────────────────────────────────────

    def scan_all(self) -> dict:
        """
        Сканирует все провайдеры по всем категориям.
        Возвращает структурированный отчёт.
        """
        report = {
            'llm_chat':  self.active_llm('LLM_CHAT'),
            'llm_coder': self.active_llm('LLM_CODER'),
            'llm_agent': self.active_llm('LLM_AGENT'),
            'image':     self.active_image(),
            'tts':       self.active_tts(),
            'tunnels':   self.tunnel_status(),
        }
        return report

    def format_scan_report(self) -> str:
        """Форматирует отчёт для Telegram."""
        r = self.scan_all()

        def _fmt_llm(lst, label):
            if not lst:
                return f"<b>{label}:</b> ❌ нет провайдеров\n"
            names = ', '.join(f"<code>{p['name']}</code>" for p in lst[:5])
            return f"<b>{label}:</b> ✅ {len(lst)} [{names}]\n"

        def _fmt_simple(lst, label):
            if not lst:
                return f"<b>{label}:</b> ❌ нет\n"
            names = ', '.join(f"<code>{p['name']}</code>" for p in lst)
            return f"<b>{label}:</b> ✅ {len(lst)} [{names}]\n"

        def _fmt_tunnels(d):
            parts = []
            for name, info in d.items():
                icon = '✅' if info['installed'] else '❌'
                parts.append(f"{icon} {name}")
            return "<b>Туннели:</b> " + "  ".join(parts) + "\n"

        lines = ["🔍 <b>Авто-скан провайдеров:</b>\n\n"]
        lines.append(_fmt_llm(r['llm_chat'],  '💬 Чат/Ассистент'))
        lines.append(_fmt_llm(r['llm_coder'], '💻 Кодер'))
        lines.append(_fmt_llm(r['llm_agent'], '🤖 Агент'))
        lines.append(_fmt_simple(r['image'],  '🎨 Фото'))
        lines.append(_fmt_simple(r['tts'],    '🎙 TTS'))
        lines.append(_fmt_tunnels(r['tunnels']))

        # Советы по недостающим
        tips = []
        if not r['llm_chat']:
            tips.append("Добавь ключ: /menu → 🧠 LLM → 🔑 Добавить ключ")
        if len(r['image']) < 2:
            tips.append("Для фото: добавь HF_API_KEY (бесплатно на huggingface.co)")
        if not any(t['installed'] for t in r['tunnels'].values()):
            tips.append("Для туннеля: <code>pkg install openssh</code> (serveo)")
        if tips:
            lines.append("\n💡 <b>Советы:</b>\n" + "\n".join(f"• {t}" for t in tips))

        return "".join(lines)

    def auto_configure(self) -> dict:
        """
        Авто-конфигурация: устанавливает лучшие провайдеры в config.
        Возвращает dict с примёнёнными изменениями.
        """
        changes = {}

        # Лучший LLM для чата
        best_chat = self.best_llm('LLM_CHAT')
        if best_chat and best_chat['name'] != config.LLM_PROVIDER:
            config.LLM_PROVIDER = best_chat['name']
            config.LLM_MODEL    = best_chat['model']
            changes['LLM']      = f"{best_chat['name']} / {best_chat['model']}"

        # Лучший TTS
        tts_list = self.active_tts()
        if tts_list:
            best_tts = tts_list[0]['name']
            if best_tts != config.TTS_PROVIDER:
                config.TTS_PROVIDER = best_tts
                changes['TTS'] = best_tts

        # Лучший LLM_CODER в .env
        best_coder = self.best_llm('LLM_CODER')
        if best_coder:
            _set_env_hub('CODE_PROVIDER',  best_coder['name'])
            _set_env_hub('CODE_MODEL',     best_coder['model'])
            changes['CODE'] = f"{best_coder['name']} / {best_coder['model']}"

        # Лучший LLM_AGENT в .env
        best_agent = self.best_llm('LLM_AGENT')
        if best_agent:
            _set_env_hub('AGENT_PROVIDER', best_agent['name'])
            _set_env_hub('AGENT_MODEL',    best_agent['model'])
            changes['AGENT'] = f"{best_agent['name']} / {best_agent['model']}"

        return changes


# Глобальный экземпляр
hub = ProvidersHub()
