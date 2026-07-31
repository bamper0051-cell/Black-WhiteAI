import os
from dotenv import load_dotenv, set_key

# Всегда ищем .env рядом с этим файлом, не зависит от cwd
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, '.env')
# DATA_DIR — отдельная папка для БД (монтируется как volume в Docker)
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

def _load():
    load_dotenv(dotenv_path=ENV_PATH, override=True)

_load()

def get(key, default=''):
    return os.environ.get(key, default)

def _set_env(key, value):
    """Пишет в .env и сразу в os.environ (runtime-изменение)."""
    os.environ[key] = str(value)
    if os.path.exists(ENV_PATH):
        set_key(ENV_PATH, key, str(value))

class _Config:
    # ── Read-only (из env) ────────────────────────────────────
    @property
    def BASE_DIR(self):             return BASE_DIR
    @property
    def DATA_DIR(self):             return DATA_DIR
    @property
    def ENV_PATH(self):             return ENV_PATH
    @property
    def TELEGRAM_BOT_TOKEN(self):   return get('TELEGRAM_BOT_TOKEN', '') or get('BOT_TOKEN', '')
    @property
    def TELEGRAM_CHAT_ID(self):     return get('TELEGRAM_CHAT_ID', '')
    @property
    def OLLAMA_BASE_URL(self):      return get('OLLAMA_BASE_URL', 'http://localhost:11434')
    @property
    def ELEVEN_API_KEY(self):       return get('ELEVEN_API_KEY', '')
    @property
    def ELEVEN_VOICE_ID(self):      return get('ELEVEN_VOICE_ID', '')
    @property
    def ELEVEN_MODEL_ID(self):      return get('ELEVEN_MODEL_ID', 'eleven_multilingual_v2').strip()
    @property
    def PARSE_INTERVAL_HOURS(self): return int(get('PARSE_INTERVAL_HOURS', '12'))
    @property
    def GEMINI_API_KEY(self):       return get('GEMINI_API_KEY', '')
    @GEMINI_API_KEY.setter
    def GEMINI_API_KEY(self, v):    _set_env('GEMINI_API_KEY', v)

    # ── Ключи по провайдерам (опционально) ───────────────────
    # ── API ключи провайдеров ─────────────────────────────────
    # Логика: специфичный ключ → LLM_API_KEY как fallback
    @property
    def OPENAI_API_KEY(self):       return get('OPENAI_API_KEY')      or self.LLM_API_KEY
    @property
    def ANTHROPIC_API_KEY(self):    return get('ANTHROPIC_API_KEY')   or self.LLM_API_KEY
    @property
    def MISTRAL_API_KEY(self):      return get('MISTRAL_API_KEY')     or self.LLM_API_KEY
    @property
    def DEEPSEEK_API_KEY(self):     return get('DEEPSEEK_API_KEY')    or self.LLM_API_KEY
    @property
    def GROQ_API_KEY(self):         return get('GROQ_API_KEY')        or self.LLM_API_KEY
    @property
    def TOGETHER_API_KEY(self):     return get('TOGETHER_API_KEY')    or self.LLM_API_KEY
    @property
    def FIREWORKS_API_KEY(self):    return get('FIREWORKS_API_KEY')   or self.LLM_API_KEY
    @property
    def CEREBRAS_API_KEY(self):     return get('CEREBRAS_API_KEY')    or self.LLM_API_KEY
    @property
    def SAMBANOVA_API_KEY(self):    return get('SAMBANOVA_API_KEY')   or self.LLM_API_KEY
    @property
    def NOVITA_API_KEY(self):       return get('NOVITA_API_KEY')      or self.LLM_API_KEY
    @property
    def DEEPINFRA_API_KEY(self):    return get('DEEPINFRA_API_KEY')   or self.LLM_API_KEY
    @property
    def LAMBDA_API_KEY(self):       return get('LAMBDA_API_KEY')      or self.LLM_API_KEY
    @property
    def LEPTON_API_KEY(self):       return get('LEPTON_API_KEY')      or self.LLM_API_KEY
    @property
    def SCALEWAY_API_KEY(self):     return get('SCALEWAY_API_KEY')    or self.LLM_API_KEY
    @property
    def FEATHERLESS_API_KEY(self):  return get('FEATHERLESS_API_KEY') or self.LLM_API_KEY
    @property
    def CHUTES_API_KEY(self):       return get('CHUTES_API_KEY')      or self.LLM_API_KEY
    @property
    def NEETS_API_KEY(self):        return get('NEETS_API_KEY')       or self.LLM_API_KEY
    @property
    def XAI_API_KEY(self):          return get('XAI_API_KEY')         or self.LLM_API_KEY
    @property
    def OPENROUTER_API_KEY(self):   return get('OPENROUTER_API_KEY')  or self.LLM_API_KEY
    @property
    def KIMI_API_KEY(self):         return get('KIMI_API_KEY')        or self.LLM_API_KEY
    @property
    def COHERE_API_KEY(self):       return get('COHERE_API_KEY')      or self.LLM_API_KEY
    @property
    def KLUSTER_API_KEY(self):      return get('KLUSTER_API_KEY')     or self.LLM_API_KEY
    @property
    def LLAMA_API_KEY(self):        return get('LLAMA_API_KEY')       or self.LLM_API_KEY
    @property
    def PERPLEXITY_API_KEY(self):   return get('PERPLEXITY_API_KEY')  or self.LLM_API_KEY
    @property
    def HYPERBOLIC_API_KEY(self):   return get('HYPERBOLIC_API_KEY')  or self.LLM_API_KEY
    @property
    def ANYSCALE_API_KEY(self):     return get('ANYSCALE_API_KEY')    or self.LLM_API_KEY
    @property
    def NVIDIA_API_KEY(self):       return get('NVIDIA_API_KEY')      or self.LLM_API_KEY
    @property
    def ALIBABA_API_KEY(self):      return get('ALIBABA_API_KEY')     or self.LLM_API_KEY
    @property
    def ZHIPU_API_KEY(self):        return get('ZHIPU_API_KEY')       or self.LLM_API_KEY
    @property
    def STEPFUN_API_KEY(self):      return get('STEPFUN_API_KEY')     or self.LLM_API_KEY
    @property
    def SILICONFLOW_API_KEY(self):  return get('SILICONFLOW_API_KEY') or self.LLM_API_KEY
    @property
    def YI_API_KEY(self):           return get('YI_API_KEY')          or self.LLM_API_KEY
    @property
    def MOONSHOT_API_KEY(self):     return get('MOONSHOT_API_KEY')    or self.LLM_API_KEY
    @property
    def MINIMAX_API_KEY(self):      return get('MINIMAX_API_KEY')     or self.LLM_API_KEY
    @property
    def WRITER_API_KEY(self):       return get('WRITER_API_KEY')      or self.LLM_API_KEY
    @property
    def AI21_API_KEY(self):         return get('AI21_API_KEY')        or self.LLM_API_KEY
    @property
    def REKA_API_KEY(self):         return get('REKA_API_KEY')        or self.LLM_API_KEY
    @property
    def UPSTAGE_API_KEY(self):      return get('UPSTAGE_API_KEY')     or self.LLM_API_KEY

    def get_key(self, provider: str) -> str:
        """Возвращает ключ для конкретного провайдера."""
        mapping = {
            'openai':     'OPENAI_API_KEY',
            'mistral':    'MISTRAL_API_KEY',
            'groq':       'GROQ_API_KEY',
            'deepseek':   'DEEPSEEK_API_KEY',
            'claude':     'ANTHROPIC_API_KEY',
            'anthropic':  'ANTHROPIC_API_KEY',
            'openrouter': 'OPENROUTER_API_KEY',
            'xai':        'XAI_API_KEY',
            'grok':       'XAI_API_KEY',
            'gemini':     'GEMINI_API_KEY',
        }
        attr = mapping.get(provider.lower())
        if attr:
            specific = get(attr, '')
            if specific:
                return specific
        return self.LLM_API_KEY  # fallback

    # ── Settable properties (runtime + .env) ─────────────────
    @property
    def LLM_PROVIDER(self):         return get('LLM_PROVIDER', 'openai').lower().strip()
    @LLM_PROVIDER.setter
    def LLM_PROVIDER(self, v):      _set_env('LLM_PROVIDER', v)

    @property
    def LLM_MODEL(self):            return get('LLM_MODEL', 'gpt-4o-mini').strip()
    @LLM_MODEL.setter
    def LLM_MODEL(self, v):         _set_env('LLM_MODEL', v)

    @property
    def LLM_API_KEY(self):          return get('LLM_API_KEY', '')
    @LLM_API_KEY.setter
    def LLM_API_KEY(self, v):       _set_env('LLM_API_KEY', v)

    # ── Специализированные провайдеры ─────────────────────────
    # Если не заданы — фоллбэк на основной LLM
    @property
    def CODE_PROVIDER(self):
        return get('CODE_PROVIDER', '') or self.LLM_PROVIDER
    @CODE_PROVIDER.setter
    def CODE_PROVIDER(self, v):     _set_env('CODE_PROVIDER', v)

    @property
    def CODE_MODEL(self):
        return get('CODE_MODEL', '') or self.LLM_MODEL
    @CODE_MODEL.setter
    def CODE_MODEL(self, v):        _set_env('CODE_MODEL', v)

    @property
    def AGENT_PROVIDER(self):
        return get('AGENT_PROVIDER', '') or self.LLM_PROVIDER
    @AGENT_PROVIDER.setter
    def AGENT_PROVIDER(self, v):    _set_env('AGENT_PROVIDER', v)

    @property
    def AGENT_MODEL(self):
        return get('AGENT_MODEL', '') or self.LLM_MODEL
    @AGENT_MODEL.setter
    def AGENT_MODEL(self, v):       _set_env('AGENT_MODEL', v)

    @property
    def IMAGE_PROVIDER(self):
        return get('IMAGE_PROVIDER', 'auto').lower().strip()
    @IMAGE_PROVIDER.setter
    def IMAGE_PROVIDER(self, v):    _set_env('IMAGE_PROVIDER', v)

    @property
    def HF_API_KEY(self):           return get('HF_API_KEY', '') or self.LLM_API_KEY
    @HF_API_KEY.setter
    def HF_API_KEY(self, v):        _set_env('HF_API_KEY', v)

    @property
    def DEEPGRAM_API_KEY(self):     return get('DEEPGRAM_API_KEY', '') or self.LLM_API_KEY
    @property
    def STABILITY_API_KEY(self):    return get('STABILITY_API_KEY', '')

    @property
    def TTS_PROVIDER(self):         return get('TTS_PROVIDER', 'edge').lower().strip()
    @TTS_PROVIDER.setter
    def TTS_PROVIDER(self, v):      _set_env('TTS_PROVIDER', v)

    @property
    def TTS_VOICE(self):            return get('TTS_VOICE', 'ru-RU-DmitryNeural')
    @TTS_VOICE.setter
    def TTS_VOICE(self, v):         _set_env('TTS_VOICE', v)

    def reload(self):
        _load()
        print(f"  🔄 Config reloaded: {self.LLM_PROVIDER} / {self.LLM_MODEL}", flush=True)

    def set_llm(self, provider: str, model: str, api_key: str = ''):
        """Удобный метод: меняет провайдер + модель + ключ одним вызовом."""
        self.LLM_PROVIDER = provider.lower().strip()
        self.LLM_MODEL    = model.strip()
        if api_key:
            self.LLM_API_KEY = api_key.strip()
        print(f"  ✅ LLM: {self.LLM_PROVIDER} / {self.LLM_MODEL}", flush=True)

    # ════════════════════════════════════════════════════════════
    #  BlackBugsAI — Brand / Proxy / Billing / Plans
    # ════════════════════════════════════════════════════════════

    BRAND = {
        'name':    'BlackBugsAI',
        'tagline': 'Autonomous AI Agent Platform',
        'version': '1.0.0',
        'emoji':   '🖤🐛',
        'url':     'https://blackbugsai.com',
        'support': '@blackbugsai_support',
    }

    # ── Proxy / Tor ──────────────────────────────────────────────
    @property
    def PROXY(self) -> dict:
        return {
            'enabled':  get('PROXY_ENABLED', '').lower() == 'true',
            'url':      get('PROXY_URL', ''),
            'tor':      get('TOR_ENABLED', '').lower() == 'true',
            'tor_port': int(get('TOR_PORT', '9050')),
            'rotate':   get('PROXY_ROTATE', '').lower() == 'true',
        }

    @property
    def PROXY_ENABLED(self) -> bool:
        return get('PROXY_ENABLED', '').lower() == 'true'

    # ── Admin Web ────────────────────────────────────────────────
    @property
    def ADMIN_WEB_PORT(self) -> int:
        return int(get('ADMIN_WEB_PORT', '8080'))

    @property
    def ADMIN_WEB_TOKEN(self) -> str:
        return get('ADMIN_WEB_TOKEN', 'changeme_secret_token')

    # ── Auth / JWT ───────────────────────────────────────────────
    @property
    def JWT_SECRET(self) -> str:
        return get('JWT_SECRET', 'change_me_in_production')

    @property
    def JWT_EXPIRE_HOURS(self) -> int:
        return int(get('JWT_EXPIRE_HOURS', '24'))

    # ── Billing ──────────────────────────────────────────────────
    @property
    def BILLING_ENABLED(self) -> bool:
        return get('BILLING_ENABLED', 'false').lower() == 'true'

    @property
    def BILLING_PROVIDER(self) -> str:
        return get('BILLING_PROVIDER', 'telegram_stars')

    # ── Plans ────────────────────────────────────────────────────
    PLANS = {
        'free': {
            'name':           '🆓 Free',
            'price':          0,
            'tasks_per_day':  10,
            'tools':          ['tts', 'pollinations_image', 'web_search',
                               'python_sandbox', 'chat', 'fetch_url'],
            'file_mb':        10,
            'agent_rounds':   3,
            'history_msgs':   20,
        },
        'pro': {
            'name':           '⭐ Pro',
            'price':          9.99,
            'tasks_per_day':  100,
            'tools':          ['*'],
            'file_mb':        500,
            'agent_rounds':   10,
            'history_msgs':   50,
        },
        'business': {
            'name':           '🚀 Business',
            'price':          49.99,
            'tasks_per_day':  -1,
            'tools':          ['*'],
            'file_mb':        -1,
            'agent_rounds':   20,
            'history_msgs':   100,
            'api_access':     True,
            'white_label':    True,
        },
        'enterprise': {
            'name':           '🏢 Enterprise',
            'price':          0,
            'tasks_per_day':  -1,
            'tools':          ['*'],
            'file_mb':        -1,
            'agent_rounds':   -1,
            'history_msgs':   200,
            'dedicated':      True,
            'sla':            True,
        },
    }

    # ── Sandbox ──────────────────────────────────────────────────
    @property
    def SANDBOX(self) -> dict:
        return {
            'timeout_default': int(get('SANDBOX_TIMEOUT', '30')),
            'timeout_max':     int(get('SANDBOX_TIMEOUT_MAX', '300')),
            'docker_enabled':  get('DOCKER_SANDBOX', '').lower() == 'true',
        }

    # ── Queue ────────────────────────────────────────────────────
    @property
    def QUEUE_WORKERS(self) -> int:
        return int(get('QUEUE_WORKERS', '2'))

    @property
    def REDIS_URL(self) -> str:
        return get('REDIS_URL', '')

    def get_plan(self, plan_name: str) -> dict:
        """Возвращает конфиг тарифного плана."""
        return self.PLANS.get(plan_name, self.PLANS['free'])

    def plan_allows_tool(self, plan_name: str, tool_name: str) -> bool:
        """Проверяет доступность инструмента для тарифа."""
        plan = self.get_plan(plan_name)
        allowed = plan.get('tools', [])
        return '*' in allowed or tool_name in allowed

    def startup_banner(self) -> str:
        """ASCII-баннер при запуске."""
        b = self.BRAND
        lines = [
            "",
            "  ██████╗ ██╗      █████╗  ██████╗██╗  ██╗██████╗ ██╗   ██╗ ██████╗ ███████╗",
            "  ██╔══██╗██║     ██╔══██╗██╔════╝██║ ██╔╝██╔══██╗██║   ██║██╔════╝ ██╔════╝",
            "  ██████╔╝██║     ███████║██║     █████╔╝ ██████╔╝██║   ██║██║  ███╗███████╗ ",
            "  ██╔══██╗██║     ██╔══██║██║     ██╔═██╗ ██╔══██╗██║   ██║██║   ██║╚════██║",
            "  ██████╔╝███████╗██║  ██║╚██████╗██║  ██╗██████╔╝╚██████╔╝╚██████╔╝███████║",
            "  ╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═════╝  ╚═════╝  ╚═════╝╚══════╝",
            "",
            f"  {b['emoji']}  {b['name']} — {b['tagline']}  v{b['version']}",
            "",
        ]
        return "\n".join(lines)

    def __setattr__(self, key, value):
        """Fallback setattr — на случай если @property.setter не сработал."""
        _set_env(key, str(value))

import sys
sys.modules[__name__] = _Config()
