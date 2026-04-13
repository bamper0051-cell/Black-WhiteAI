import os
from dotenv import load_dotenv, set_key

# Всегда ищем .env рядом с этим файлом, не зависит от cwd
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, '.env')

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
    def ENV_PATH(self):             return ENV_PATH
    @property
    def TELEGRAM_BOT_TOKEN(self):   return get('TELEGRAM_BOT_TOKEN', '')
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
    # ── API ключи провайдеров ─────────────────────────────────
    # Логика: специфичный ключ → LLM_API_KEY как fallback
    @property
    def OPENAI_API_KEY(self):       return get('OPENAI_API_KEY')      or self.LLM_API_KEY
    @property
    def ANTHROPIC_API_KEY(self):    return get('ANTHROPIC_API_KEY')   or self.LLM_API_KEY
    @property
    def GEMINI_API_KEY(self):       return get('GEMINI_API_KEY')      or ''
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
            'openai':       'OPENAI_API_KEY',
            'mistral':      'MISTRAL_API_KEY',
            'groq':         'GROQ_API_KEY',
            'deepseek':     'DEEPSEEK_API_KEY',
            'claude':       'ANTHROPIC_API_KEY',
            'anthropic':    'ANTHROPIC_API_KEY',
            'openrouter':   'OPENROUTER_API_KEY',
            'xai':          'XAI_API_KEY',
            'grok':         'XAI_API_KEY',
            'gemini':       'GEMINI_API_KEY',
            'together':     'TOGETHER_API_KEY',
            'cerebras':     'CEREBRAS_API_KEY',
            'sambanova':    'SAMBANOVA_API_KEY',
            'fireworks':    'FIREWORKS_API_KEY',
            'novita':       'NOVITA_API_KEY',
            'deepinfra':    'DEEPINFRA_API_KEY',
            'kimi':         'KIMI_API_KEY',
            'cohere':       'COHERE_API_KEY',
            'perplexity':   'PERPLEXITY_API_KEY',
            'hyperbolic':   'HYPERBOLIC_API_KEY',
            'nvidia':       'NVIDIA_API_KEY',
            'huggingface':  'HF_API_KEY',
            'hf':           'HF_API_KEY',
            'stability':    'STABILITY_API_KEY',
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

    def set_key(self, provider: str, key_value: str) -> bool:
        """Устанавливает API ключ для провайдера. Возвращает True если провайдер известен."""
        key_map = {
            'openai':     'OPENAI_API_KEY',
            'anthropic':  'ANTHROPIC_API_KEY',
            'claude':     'ANTHROPIC_API_KEY',
            'gemini':     'GEMINI_API_KEY',
            'groq':       'GROQ_API_KEY',
            'mistral':    'MISTRAL_API_KEY',
            'deepseek':   'DEEPSEEK_API_KEY',
            'openrouter': 'OPENROUTER_API_KEY',
            'together':   'TOGETHER_API_KEY',
            'cerebras':   'CEREBRAS_API_KEY',
            'sambanova':  'SAMBANOVA_API_KEY',
            'xai':        'XAI_API_KEY',
            'kimi':       'KIMI_API_KEY',
            'cohere':     'COHERE_API_KEY',
            'stability':  'STABILITY_API_KEY',
            'huggingface':'HF_API_KEY',
            'hf':         'HF_API_KEY',
            'perplexity': 'PERPLEXITY_API_KEY',
            'nvidia':     'NVIDIA_API_KEY',
        }
        env_key = key_map.get(provider.lower(), 'LLM_API_KEY')
        _set_env(env_key, key_value.strip())
        return provider.lower() in key_map

    def __setattr__(self, key, value):
        """Fallback setattr — на случай если @property.setter не сработал."""
        _set_env(key, str(value))

import sys
sys.modules[__name__] = _Config()
