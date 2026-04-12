import time
import requests as req
import config

# ── Retry helper ──────────────────────────────────────────────

def _retry(fn, retries=3, delay=5):
    last_err = None
    for i in range(retries):
        try:
            return fn()
        except Exception as e:
            last_err = e
            msg = str(e)
            if '429' in msg or 'Too Many Requests' in msg:
                wait = delay * (2 ** i)
                print("  ⏳ Rate limit, жду {}с...".format(wait))
                time.sleep(wait)
            else:
                raise
    raise last_err

# ── Основной вызов ────────────────────────────────────────────

# Все OpenAI-совместимые провайдеры: алиас -> base_url
_OPENAI_COMPAT = {
    # ── Топ ─────────────────────────────
    'openai':     'https://api.openai.com/v1',
    'mistral':    'https://api.mistral.ai/v1',
    'deepseek':   'https://api.deepseek.com/v1',
    # ── Быстрые/бесплатные ──────────────
    'groq':       'https://api.groq.com/openai/v1',
    'together':   'https://api.together.xyz/v1',
    'fireworks':  'https://api.fireworks.ai/inference/v1',
    'cerebras':   'https://api.cerebras.ai/v1',
    'sambanova':  'https://api.sambanova.ai/v1',
    'novita':     'https://api.novita.ai/v3/openai',
    # ── Специализированные ──────────────
    'xai':        'https://api.x.ai/v1',
    'grok':       'https://api.x.ai/v1',
    'kimi':       'https://api.moonshot.cn/v1',
    'cohere':     'https://api.cohere.com/compatibility/v1',
    'kluster':    'https://api.kluster.ai/v1',
    'llama':      'https://api.llama.com/compat/v1',
    'perplexity': 'https://api.perplexity.ai',
    'openrouter': 'https://openrouter.ai/api/v1',
    'hyperbolic': 'https://api.hyperbolic.xyz/v1',
    'anyscale':   'https://api.endpoints.anyscale.com/v1',
    'nvidia':     'https://integrate.api.nvidia.com/v1',
    # ── Локальные ────────────────────────
    'lmstudio':   'http://localhost:1234/v1',
    'jan':        'http://localhost:1337/v1',
}

def call_llm(prompt, system='', max_tokens=1200):
    p = config.LLM_PROVIDER.lower().strip()

    # OpenAI-совместимые провайдеры — один обработчик для всех
    if p in _OPENAI_COMPAT:
        base = _OPENAI_COMPAT[p]
        return _retry(lambda: _openai_compat(prompt, system, base, max_tokens))

    # Специфичные провайдеры
    if p == 'ollama':
        return _retry(lambda: _ollama(prompt, system, max_tokens))
    if p == 'gemini':
        return _retry(lambda: _gemini(prompt, system, max_tokens))
    if p == 'claude':
        return _retry(lambda: _claude(prompt, system, max_tokens))

    providers = list(_OPENAI_COMPAT.keys()) + ['ollama', 'gemini', 'claude']
    raise ValueError(
        "Неизвестный провайдер: '{}'\nДоступные: {}".format(p, ' | '.join(providers))
    )


# ════════════════════════════════════════════════════════════
#  call_llm_full — как call_llm, но возвращает (text, is_truncated)
#  is_truncated=True если LLM остановилась по лимиту токенов
# ════════════════════════════════════════════════════════════

def call_llm_full(prompt, system='', max_tokens=1200):
    """
    Как call_llm, но возвращает кортеж (text: str, is_truncated: bool).
    is_truncated=True когда finish_reason == 'length' (LLM обрезало по лимиту).
    """
    p = config.LLM_PROVIDER.lower().strip()

    if p in _OPENAI_COMPAT:
        base = _OPENAI_COMPAT[p]
        return _retry(lambda: _openai_compat_full(prompt, system, base, max_tokens))

    if p == 'gemini':
        return _retry(lambda: _gemini_full(prompt, system, max_tokens))

    # Для ollama и claude — нет надёжного finish_reason в простом виде, обрезаем эвристикой
    text = call_llm(prompt, system, max_tokens)
    truncated = _heuristic_truncated(text)
    return text, truncated


def _heuristic_truncated(text: str) -> bool:
    """Эвристика: код/текст оборван если нет финального закрывающего маркера."""
    t = text.strip()
    # Открытый блок кода без закрытия
    if t.count('```') % 2 != 0:
        return True
    # Последняя строка не похожа на завершение (нет '', ''', end-of-block)
    last = t.split('\n')[-1].strip() if t else ''
    open_endings = ('(', ',', '{', '[', ':', '\\', 'def', 'class', 'return', 'import')
    if last.endswith(open_endings) or (last and not last.endswith((')', '}', ']', '"""', "'''", '`', '"', "'", ';'))):
        # Дополнительная проверка — обрыв примерно в конце лимита
        if len(t) > 3000:
            return True
    return False


def _openai_compat_full(prompt, system, base_url, max_tokens=1200):
    messages = []
    if system:
        messages.append({'role': 'system', 'content': system})
    messages.append({'role': 'user', 'content': prompt})

    api_key = _get_provider_key(config.LLM_PROVIDER.lower().strip())
    r = req.post(
        '{}/chat/completions'.format(base_url),
        json={'model': config.LLM_MODEL, 'messages': messages, 'max_tokens': max_tokens},
        headers={
            'Authorization': 'Bearer {}'.format(api_key),
            'Content-Type': 'application/json',
        },
        timeout=90
    )
    if r.status_code == 429:
        raise Exception("429 Too Many Requests: {}".format(r.text[:200]))
    if r.status_code == 401:
        raise Exception("401 Unauthorized — нет ключа для {} в .env".format(config.LLM_PROVIDER))
    r.raise_for_status()
    data = r.json()
    text = data['choices'][0]['message']['content'].strip()
    finish = data['choices'][0].get('finish_reason', 'stop')
    return text, (finish == 'length')


def _gemini_full(prompt, system, max_tokens=1200):
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "{}:generateContent?key={}".format(config.LLM_MODEL, config.GEMINI_API_KEY)
    )
    full_prompt = "{}\n\n{}".format(system, prompt) if system else prompt
    body = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens}
    }
    r = req.post(url, json=body, timeout=60)
    r.raise_for_status()
    data = r.json()
    text = data['candidates'][0]['content']['parts'][0]['text'].strip()
    reason = data['candidates'][0].get('finishReason', 'STOP')
    return text, (reason == 'MAX_TOKENS')



# Маппинг провайдер → название атрибута config с ключом
_PROVIDER_KEY_MAP = {
    'openai':      'OPENAI_API_KEY',
    'anthropic':   'ANTHROPIC_API_KEY',
    'claude':      'ANTHROPIC_API_KEY',
    'gemini':      'GEMINI_API_KEY',
    'mistral':     'MISTRAL_API_KEY',
    'deepseek':    'DEEPSEEK_API_KEY',
    'groq':        'GROQ_API_KEY',
    'together':    'TOGETHER_API_KEY',
    'fireworks':   'FIREWORKS_API_KEY',
    'cerebras':    'CEREBRAS_API_KEY',
    'sambanova':   'SAMBANOVA_API_KEY',
    'novita':      'NOVITA_API_KEY',
    'deepinfra':   'DEEPINFRA_API_KEY',
    'lambda':      'LAMBDA_API_KEY',
    'lepton':      'LEPTON_API_KEY',
    'scaleway':    'SCALEWAY_API_KEY',
    'featherless': 'FEATHERLESS_API_KEY',
    'chutes':      'CHUTES_API_KEY',
    'neets':       'NEETS_API_KEY',
    'xai':         'XAI_API_KEY',
    'grok':        'XAI_API_KEY',
    'openrouter':  'OPENROUTER_API_KEY',
    'kimi':        'KIMI_API_KEY',
    'cohere':      'COHERE_API_KEY',
    'kluster':     'KLUSTER_API_KEY',
    'llama':       'LLAMA_API_KEY',
    'perplexity':  'PERPLEXITY_API_KEY',
    'hyperbolic':  'HYPERBOLIC_API_KEY',
    'anyscale':    'ANYSCALE_API_KEY',
    'nvidia':      'NVIDIA_API_KEY',
    'alibaba':     'ALIBABA_API_KEY',
    'zhipu':       'ZHIPU_API_KEY',
    'stepfun':     'STEPFUN_API_KEY',
    'siliconflow': 'SILICONFLOW_API_KEY',
    'yi':          'YI_API_KEY',
    'moonshot':    'MOONSHOT_API_KEY',
    'minimax':     'MINIMAX_API_KEY',
    'writer':      'WRITER_API_KEY',
    'ai21':        'AI21_API_KEY',
    'reka':        'REKA_API_KEY',
    'upstage':     'UPSTAGE_API_KEY',
}

def _get_provider_key(provider: str) -> str:
    """Возвращает API ключ для конкретного провайдера из config."""
    attr = _PROVIDER_KEY_MAP.get(provider, 'LLM_API_KEY')
    key = getattr(config, attr, '') or ''
    if not key and attr != 'LLM_API_KEY':
        key = getattr(config, 'LLM_API_KEY', '') or ''
    return key


def _openai_compat(prompt, system, base_url, max_tokens=1200):
    messages = []
    if system:
        messages.append({'role': 'system', 'content': system})
    messages.append({'role': 'user', 'content': prompt})

    # Берём ключ специфичный для текущего провайдера
    api_key = _get_provider_key(config.LLM_PROVIDER.lower().strip())

    r = req.post(
        '{}/chat/completions'.format(base_url),
        json={'model': config.LLM_MODEL, 'messages': messages, 'max_tokens': max_tokens},
        headers={
            'Authorization': 'Bearer {}'.format(api_key),
            'Content-Type': 'application/json',
        },
        timeout=60
    )
    if r.status_code == 429:
        raise Exception("429 Too Many Requests: {}".format(r.text[:200]))
    if r.status_code == 401:
        raise Exception("401 Unauthorized — нет ключа для {} в .env".format(
            config.LLM_PROVIDER))
    r.raise_for_status()
    return r.json()['choices'][0]['message']['content'].strip()


def _ollama(prompt, system, max_tokens=1200):
    messages = []
    if system:
        messages.append({'role': 'system', 'content': system})
    messages.append({'role': 'user', 'content': prompt})

    r = req.post(
        '{}/api/chat'.format(config.OLLAMA_BASE_URL),
        json={'model': config.LLM_MODEL, 'messages': messages, 'stream': False, 'options': {'num_predict': max_tokens}},
        timeout=120
    )
    r.raise_for_status()
    return r.json()['message']['content'].strip()


def _gemini(prompt, system, max_tokens=1200):
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "{}:generateContent?key={}".format(config.LLM_MODEL, config.GEMINI_API_KEY)
    )
    full_prompt = "{}\n\n{}".format(system, prompt) if system else prompt
    body = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens}
    }
    r = req.post(url, json=body, timeout=60)
    if r.status_code == 400:
        raise Exception("Gemini 400: {}".format(r.text[:300]))
    r.raise_for_status()
    return r.json()['candidates'][0]['content']['parts'][0]['text'].strip()


def _claude(prompt, system, max_tokens=1200):
    body = {
        'model': config.LLM_MODEL,
        'max_tokens': max_tokens,
        'messages': [{'role': 'user', 'content': prompt}]
    }
    if system:
        body['system'] = system

    r = req.post(
        'https://api.anthropic.com/v1/messages',
        json=body,
        headers={
            'x-api-key': config.ANTHROPIC_API_KEY,
            'anthropic-version': '2023-06-01',
            'Content-Type': 'application/json',
        },
        timeout=60
    )
    if r.status_code == 401:
        raise Exception("401 Unauthorized — проверь LLM_API_KEY")
    r.raise_for_status()
    return r.json()['content'][0]['text'].strip()


# ── Тест ─────────────────────────────────────────────────────

def test_connection():
    try:
        result = call_llm("Скажи только 'ОК'.", "Ты тестовый ассистент.")
        return True, result
    except Exception as e:
        return False, str(e)


# ── Авто-чек доступных провайдеров ───────────────────────────

import threading

def check_provider(provider, model, api_key, base_url=None):
    """
    Быстрый тест одного провайдера. Возвращает (ok: bool, latency_ms: int, error: str).
    Таймаут 10 секунд — не ждём долго.
    """
    import time
    start = time.time()
    try:
        if not api_key and provider not in ('ollama',):
            return False, 0, "нет API ключа"

        if base_url is None:
            base_url = _OPENAI_COMPAT.get(provider)

        if provider == 'ollama':
            # Ollama: просто проверяем /api/tags
            import requests as _r
            ollama_url = (base_url or 'http://localhost:11434').replace('/api/chat', '')
            r = _r.get('{}/api/tags'.format(ollama_url), timeout=5)
            r.raise_for_status()
            models = [m['name'] for m in r.json().get('models', [])]
            ms = int((time.time() - start) * 1000)
            return True, ms, "модели: {}".format(', '.join(models[:5]) or 'нет')

        elif provider == 'gemini':
            import requests as _r
            url = ("https://generativelanguage.googleapis.com/v1beta/models/"
                   "{}:generateContent?key={}".format(model, api_key))
            body = {"contents": [{"parts": [{"text": "hi"}]}],
                    "generationConfig": {"maxOutputTokens": 5}}
            r = _r.post(url, json=body, timeout=10)
            if r.status_code == 401:
                return False, 0, "неверный ключ"
            if r.status_code == 403:
                return False, 0, "доступ запрещён"
            r.raise_for_status()
            ms = int((time.time() - start) * 1000)
            return True, ms, "OK"

        elif provider == 'claude':
            import requests as _r
            r = _r.post('https://api.anthropic.com/v1/messages',
                json={'model': model, 'max_tokens': 5,
                      'messages': [{'role': 'user', 'content': 'hi'}]},
                headers={'x-api-key': api_key,
                         'anthropic-version': '2023-06-01'},
                timeout=10)
            if r.status_code == 401:
                return False, 0, "неверный ключ"
            r.raise_for_status()
            ms = int((time.time() - start) * 1000)
            return True, ms, "OK"

        elif base_url:
            # OpenAI-совместимые
            import requests as _r
            r = _r.post('{}/chat/completions'.format(base_url),
                json={'model': model,
                      'messages': [{'role': 'user', 'content': 'hi'}],
                      'max_tokens': 5},
                headers={'Authorization': 'Bearer {}'.format(api_key),
                         'Content-Type': 'application/json'},
                timeout=10)
            if r.status_code == 401:
                return False, 0, "неверный ключ"
            if r.status_code == 403:
                return False, 0, "доступ запрещён / нет подписки"
            if r.status_code == 429:
                return False, 0, "rate limit"
            if r.status_code == 404:
                return False, 0, "модель не найдена: {}".format(model)
            r.raise_for_status()
            ms = int((time.time() - start) * 1000)
            return True, ms, "OK"
        else:
            return False, 0, "неизвестный провайдер"

    except Exception as e:
        ms = int((time.time() - start) * 1000)
        msg = str(e)
        if 'timeout' in msg.lower() or 'timed out' in msg.lower():
            return False, ms, "таймаут"
        if 'connection' in msg.lower():
            return False, ms, "нет соединения"
        return False, ms, msg[:80]


# Дефолтные модели для каждого провайдера при чеке
_CHECK_PRESETS = {
    'openai':   ('gpt-4o-mini',                    None),
    'mistral':  ('mistral-small-latest',           None),
    'groq':     ('llama-3.3-70b-versatile',        None),
    'deepseek': ('deepseek-chat',                  None),
    'xai':      ('grok-3-mini',                    None),
    'kimi':     ('moonshot-v1-8k',                 None),
    'llama':    ('Llama-4-Scout-17B-16E-Instruct', None),
    'cohere':   ('command-r-plus',                 None),
    'kluster':  ('klusterai/Meta-Llama-3.3-70B-Instruct-Turbo', None),
    'gemini':   ('gemini-2.0-flash',               None),
    'claude':   ('claude-3-haiku-20240307',        None),
    'ollama':   ('',                               None),
}


def check_all_providers(env_vars):
    """
    Параллельно тестирует все провайдеры у которых есть ключи в env_vars.
    env_vars — dict с переменными окружения (из os.environ или config).

    Возвращает list of dict:
      {provider, model, ok, latency_ms, error, has_key}
    """
    results = []
    lock = threading.Lock()
    threads = []

    def _test(provider, model, api_key, base_url):
        ok, ms, err = check_provider(provider, model, api_key, base_url)
        with lock:
            results.append({
                'provider': provider,
                'model': model,
                'ok': ok,
                'latency_ms': ms,
                'error': err,
                'has_key': bool(api_key) or provider == 'ollama',
            })

    for provider, (model, _) in _CHECK_PRESETS.items():
        # Ищем ключ в env_vars
        key_names = [
            'LLM_API_KEY',
            '{}_API_KEY'.format(provider.upper()),
            'OPENAI_API_KEY', 'MISTRAL_API_KEY', 'GROQ_API_KEY',
            'DEEPSEEK_API_KEY', 'ANTHROPIC_API_KEY', 'GEMINI_API_KEY',
            'XAI_API_KEY', 'KIMI_API_KEY',
        ]
        api_key = ''
        for kn in key_names:
            v = env_vars.get(kn, '')
            if v and len(v) > 8:
                # Для текущего провайдера ключ LLM_API_KEY первичен
                if kn == 'LLM_API_KEY' and env_vars.get('LLM_PROVIDER', '').lower() == provider:
                    api_key = v
                    break
                elif kn != 'LLM_API_KEY':
                    api_key = v
                    break

        # Ollama всегда проверяем
        if provider != 'ollama' and not api_key:
            continue  # нет ключа — пропускаем

        base_url = _OPENAI_COMPAT.get(provider)
        t = threading.Thread(
            target=_test,
            args=(provider, model, api_key, base_url),
            daemon=True
        )
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=15)

    results.sort(key=lambda x: (not x['ok'], x['provider']))
    return results


def format_check_results(results):
    """Форматирует результаты чека для Telegram (HTML)."""
    if not results:
        return (
            "⚠️ <b>Нет настроенных провайдеров</b>\n\n"
            "Добавь API ключи в .env или через меню 🧠 LLM настройки.\n"
            "Ollama: убедись что запущен на localhost:11434."
        )

    lines = ["🔍 <b>Доступные LLM провайдеры:</b>\n"]
    ok_count = sum(1 for r in results if r['ok'])

    for r in results:
        if r['ok']:
            icon = "✅"
            ms = r.get('latency_ms')
            detail = "{}ms".format(ms) if ms else "OK"
        else:
            icon = "❌"
            detail = r.get('error') or 'недоступен'
            if not r.get('has_key', True):
                detail = "нет ключа"

        provider = r.get('provider') or r.get('name', '?')
        model = r.get('model') or ''
        if not model:
            models_list = r.get('models') or []
            model = models_list[0] if models_list else ''
        if isinstance(model, list):
            model = model[0] if model else ''
        lines.append("{} <b>{}</b> — <code>{}</code>\n   {}".format(
            icon, provider, model, detail
        ))

    lines.append("\n<i>Работает: {}/{}</i>".format(ok_count, len(results)))
    return "\n".join(lines)
