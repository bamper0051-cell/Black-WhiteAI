"""
model_discovery.py — автоматическое обнаружение всех доступных моделей у провайдеров.

Запуск вручную:  python model_discovery.py
Из бота:        /discover  или кнопка в меню LLM → 🔄 Обновить модели

Результат сохраняется в models_cache.json и используется при выборе модели.
"""

import json
import os
import time
import requests
import concurrent.futures
import config

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models_cache.json')
CACHE_TTL  = 3600 * 6   # обновляем не чаще раза в 6 часов

# ════════════════════════════════════════════════════════════
#  ФИЛЬТРАЦИЯ — что НЕ показываем
# ════════════════════════════════════════════════════════════
_SKIP_KEYWORDS = [
    'embed', 'embedding', 'whisper', 'dall-e', 'tts', 'speech',
    'realtime', 'transcri', 'audio', 'vision-only', 'image-',
    'babbage', 'davinci-00', 'search-', 'instruct-search',
    'moderat', 'guard', 'shield',
]

def _is_chat_model(model_id: str) -> bool:
    m = model_id.lower()
    return not any(kw in m for kw in _SKIP_KEYWORDS)


# ════════════════════════════════════════════════════════════
#  FETCHERS — один на провайдера
# ════════════════════════════════════════════════════════════

def _openai_compat_fetch(base_url: str, api_key: str = '', timeout: int = 10) -> list[str]:
    """Универсальный fetcher для OpenAI-совместимых /v1/models."""
    headers = {'Authorization': 'Bearer ' + api_key} if api_key else {}
    try:
        r = requests.get(base_url.rstrip('/') + '/models',
                         headers=headers, timeout=timeout)
        if r.status_code == 200:
            data = r.json().get('data', r.json().get('models', []))
            ids = []
            for item in data:
                mid = item.get('id') or item.get('name') or ''
                if mid and _is_chat_model(mid):
                    ids.append(mid)
            return sorted(ids)
    except Exception:
        pass
    return []


def _openrouter_fetch(api_key: str = '', timeout: int = 15) -> dict:
    """OpenRouter: возвращает {model_id: {free, ctx, name}}."""
    headers = {}
    if api_key:
        headers['Authorization'] = 'Bearer ' + api_key
    try:
        r = requests.get('https://openrouter.ai/api/v1/models',
                          headers=headers, timeout=timeout)
        if r.status_code == 200:
            result = {}
            for m in r.json().get('data', []):
                mid  = m.get('id', '')
                if not mid or not _is_chat_model(mid):
                    continue
                pricing = m.get('pricing', {})
                is_free = (float(pricing.get('prompt', 1) or 1) == 0 and
                           float(pricing.get('completion', 1) or 1) == 0)
                result[mid] = {
                    'name':    m.get('name', mid),
                    'ctx':     m.get('context_length', 0),
                    'free':    is_free,
                    'prompt_price': pricing.get('prompt', '?'),
                }
            return result
    except Exception:
        pass
    return {}


def _gemini_fetch(api_key: str = '', timeout: int = 10) -> list[str]:
    try:
        url = 'https://generativelanguage.googleapis.com/v1beta/models'
        r = requests.get(url, params={'key': api_key}, timeout=timeout)
        if r.status_code == 200:
            return [
                m['name'].replace('models/', '')
                for m in r.json().get('models', [])
                if 'generateContent' in m.get('supportedGenerationMethods', [])
                and _is_chat_model(m.get('name', ''))
            ]
    except Exception:
        pass
    return []


def _ollama_fetch(timeout: int = 5) -> list[str]:
    try:
        r = requests.get('http://localhost:11434/api/tags', timeout=timeout)
        if r.status_code == 200:
            return [m['name'] for m in r.json().get('models', [])]
    except Exception:
        pass
    return []


def _local_server_fetch(port: int, timeout: int = 3) -> list[str]:
    try:
        r = requests.get(f'http://localhost:{port}/v1/models', timeout=timeout)
        if r.status_code == 200:
            return [m['id'] for m in r.json().get('data', []) if _is_chat_model(m.get('id', ''))]
    except Exception:
        pass
    return []


# ════════════════════════════════════════════════════════════
#  ГЛАВНАЯ ФУНКЦИЯ
# ════════════════════════════════════════════════════════════

# Провайдеры с OpenAI-совместимым /v1/models
_COMPAT_PROVIDERS = {
    'openai':      'https://api.openai.com/v1',
    'mistral':     'https://api.mistral.ai/v1',
    'deepseek':    'https://api.deepseek.com/v1',
    'groq':        'https://api.groq.com/openai/v1',
    'together':    'https://api.together.xyz/v1',
    'fireworks':   'https://api.fireworks.ai/inference/v1',
    'cerebras':    'https://api.cerebras.ai/v1',
    'sambanova':   'https://api.sambanova.ai/v1',
    'novita':      'https://api.novita.ai/v3/openai',
    'xai':         'https://api.x.ai/v1',
    'kimi':        'https://api.moonshot.cn/v1',
    'cohere':      'https://api.cohere.com/compatibility/v1',
    'kluster':     'https://api.kluster.ai/v1',
    'llama':       'https://api.llama.com/compat/v1',
    'perplexity':  'https://api.perplexity.ai',
    'hyperbolic':  'https://api.hyperbolic.xyz/v1',
    'deepinfra':   'https://api.deepinfra.com/v1/openai',
    'lambda':      'https://api.lambdalabs.com/v1',
    'lepton':      'https://api.lepton.ai/api/v1',
    'scaleway':    'https://api.scaleway.ai/v1',
    'featherless': 'https://api.featherless.ai/v1',
    'chutes':      'https://llm.chutes.ai/v1',
    'alibaba':     'https://dashscope.aliyuncs.com/compatible-mode/v1',
    'zhipu':       'https://open.bigmodel.cn/api/paas/v4',
    'stepfun':     'https://api.stepfun.com/v1',
    'siliconflow': 'https://api.siliconflow.cn/v1',
    'yi':          'https://api.lingyiwanwu.com/v1',
    'ai21':        'https://api.ai21.com/studio/v1',
    'reka':        'https://api.reka.ai/v1',
    'upstage':     'https://api.upstage.ai/v1',
    'nvidia':      'https://integrate.api.nvidia.com/v1',
    'writer':      'https://api.writer.com/v1',
    'anthropic':   'https://api.anthropic.com/v1',
}


def discover_all(api_key: str = None, on_progress=None) -> dict:
    """
    Опрашивает все провайдеры и возвращает dict:
    {
        'openai':      {'models': ['gpt-4o', ...], 'ok': True,  'count': N},
        'openrouter':  {'models': {'id': {free, ctx}}, 'ok': True, 'free_count': N},
        ...
        '_updated_at': timestamp,
    }
    """
    if api_key is None:
        api_key = getattr(config, 'LLM_API_KEY', '') or ''

    result = {}

    # ── OpenRouter — отдельно, богатые метаданные ─────────────
    if on_progress:
        on_progress("🔍 OpenRouter...")
    or_data = _openrouter_fetch(api_key)
    free_count = sum(1 for m in or_data.values() if m['free'])
    result['openrouter'] = {
        'models':     or_data,
        'ok':         bool(or_data),
        'count':      len(or_data),
        'free_count': free_count,
    }

    # ── OpenAI-compat провайдеры — параллельно ─────────────────
    def fetch_one(name_url):
        name, base = name_url
        models = _openai_compat_fetch(base, api_key)
        return name, models

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(fetch_one, item): item[0]
                   for item in _COMPAT_PROVIDERS.items()}
        for f in concurrent.futures.as_completed(futures):
            name, models = f.result()
            result[name] = {'models': models, 'ok': bool(models), 'count': len(models)}
            if on_progress and models:
                on_progress("✅ {} — {} моделей".format(name, len(models)))

    # ── Gemini ────────────────────────────────────────────────
    gemini_key = getattr(config, 'GEMINI_API_KEY', '') or api_key
    models = _gemini_fetch(gemini_key)
    result['gemini'] = {'models': models, 'ok': bool(models), 'count': len(models)}

    # ── Локальные ─────────────────────────────────────────────
    result['ollama']   = {'models': _ollama_fetch(),              'ok': False, 'count': 0}
    result['lmstudio'] = {'models': _local_server_fetch(1234),    'ok': False, 'count': 0}
    result['jan']      = {'models': _local_server_fetch(1337),    'ok': False, 'count': 0}
    result['llamacpp'] = {'models': _local_server_fetch(8080),    'ok': False, 'count': 0}
    for name in ('ollama', 'lmstudio', 'jan', 'llamacpp'):
        result[name]['ok']    = bool(result[name]['models'])
        result[name]['count'] = len(result[name]['models'])

    result['_updated_at'] = time.time()
    return result


# ════════════════════════════════════════════════════════════
#  КЭШ
# ════════════════════════════════════════════════════════════

def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                data = json.load(f)
            if time.time() - data.get('_updated_at', 0) < CACHE_TTL:
                return data
        except Exception:
            pass
    return {}


def save_cache(data: dict):
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_models(provider: str, api_key: str = None, use_cache: bool = True) -> list[str]:
    """Возвращает список моделей для провайдера (из кэша или живой запрос)."""
    cache = load_cache() if use_cache else {}
    if provider in cache:
        entry = cache[provider]
        models = entry.get('models', [])
        if isinstance(models, dict):  # OpenRouter
            return sorted(models.keys())
        return models

    # Живой запрос
    if api_key is None:
        api_key = getattr(config, 'LLM_API_KEY', '') or ''

    if provider == 'openrouter':
        data = _openrouter_fetch(api_key)
        return sorted(data.keys())
    if provider == 'gemini':
        return _gemini_fetch(getattr(config, 'GEMINI_API_KEY', '') or api_key)
    if provider == 'ollama':
        return _ollama_fetch()
    if provider in _COMPAT_PROVIDERS:
        return _openai_compat_fetch(_COMPAT_PROVIDERS[provider], api_key)
    return []


def get_free_openrouter(api_key: str = None, use_cache: bool = True) -> list[str]:
    """Возвращает список бесплатных моделей OpenRouter."""
    cache = load_cache() if use_cache else {}
    or_entry = cache.get('openrouter', {})
    models = or_entry.get('models', {})
    if not models:
        models = _openrouter_fetch(api_key or getattr(config, 'LLM_API_KEY', ''))
    if isinstance(models, dict):
        return sorted(mid for mid, info in models.items() if info.get('free'))
    return []


def format_discovery_report(data: dict) -> str:
    """HTML-отчёт для Telegram."""
    lines = ['<b>🔍 Доступные модели по провайдерам:</b>\n']

    ok_total = sum(1 for k, v in data.items()
                   if not k.startswith('_') and isinstance(v, dict) and v.get('ok'))
    lines.append('✅ Активных провайдеров: {}\n'.format(ok_total))

    # OpenRouter отдельно — показываем free count
    or_entry = data.get('openrouter', {})
    if or_entry.get('ok'):
        lines.append('🟢 <b>openrouter</b> — {} моделей ({} бесплатных)'.format(
            or_entry.get('count', 0), or_entry.get('free_count', 0)))

    # Остальные
    for name, entry in sorted(data.items()):
        if name in ('openrouter', '_updated_at') or not isinstance(entry, dict):
            continue
        if entry.get('ok'):
            models = entry.get('models', [])
            if isinstance(models, list) and models:
                top = models[:3]
                lines.append('\n🟢 <b>{}</b> — {} моделей'.format(name, entry['count']))
                for m in top:
                    lines.append('   • <code>{}</code>'.format(m))
                if len(models) > 3:
                    lines.append('   <i>...и ещё {}</i>'.format(len(models) - 3))
        else:
            lines.append('🔴 <b>{}</b>'.format(name))

    ts = data.get('_updated_at', 0)
    if ts:
        lines.append('\n<i>Обновлено: {}</i>'.format(
            time.strftime('%H:%M:%S', time.localtime(ts))))

    return '\n'.join(lines)


# ════════════════════════════════════════════════════════════
#  CLI — запуск напрямую
# ════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys

    api_key = sys.argv[1] if len(sys.argv) > 1 else getattr(config, 'LLM_API_KEY', '')

    print("🔍 Обнаруживаю модели...\n")

    def progress(msg):
        print(" ", msg)

    data = discover_all(api_key, on_progress=progress)
    save_cache(data)

    print("\n" + "="*50)
    print("ИТОГ:")
    print("="*50)

    for name, entry in sorted(data.items()):
        if name.startswith('_') or not isinstance(entry, dict):
            continue
        if entry.get('ok'):
            extra = ""
            if name == 'openrouter':
                extra = " ({} free)".format(entry.get('free_count', 0))
            print(f"  ✅ {name}: {entry['count']} моделей{extra}")
        else:
            print(f"  ❌ {name}")

    # Показываем бесплатные OpenRouter
    or_models = data.get('openrouter', {}).get('models', {})
    if or_models:
        free = [mid for mid, info in or_models.items() if info.get('free')]
        print(f"\n🆓 Бесплатные OpenRouter ({len(free)}):")
        for m in sorted(free):
            ctx = or_models[m].get('ctx', 0)
            print(f"   {m}  (ctx: {ctx:,})")

    print(f"\nКэш сохранён: {CACHE_FILE}")


# ════════════════════════════════════════════════════════════
#  COMPATIBILITY LAYER — функции которые ждёт bot.py
# ════════════════════════════════════════════════════════════

_or_cache = {}  # {key_hash: (timestamp, models_dict)}

def get_openrouter_models_cached(api_key: str = '', force: bool = False):
    """
    Возвращает (models_list, error_str | None).
    models_list — список dict: {id, name, ctx, free, price}
    Кэш 6 часов. force=True — принудительное обновление.
    """
    cache = load_cache()
    or_entry = cache.get('openrouter', {})
    models_dict = or_entry.get('models', {})

    if models_dict and not force:
        return _dict_to_list(models_dict), None

    # Живой запрос
    models_dict = _openrouter_fetch(api_key)
    if not models_dict:
        return [], "Не удалось получить модели (проверь ключ и соединение)"

    # Обновляем кэш
    cache['openrouter'] = {
        'models':     models_dict,
        'ok':         True,
        'count':      len(models_dict),
        'free_count': sum(1 for m in models_dict.values() if m.get('free')),
    }
    cache['_updated_at'] = time.time()
    save_cache(cache)

    return _dict_to_list(models_dict), None


def _dict_to_list(models_dict: dict) -> list:
    """Конвертирует {id: info} → [{id, name, ctx, free, price}]."""
    result = []
    for mid, info in models_dict.items():
        result.append({
            'id':    mid,
            'name':  info.get('name', mid),
            'ctx':   info.get('ctx', 0),
            'free':  info.get('free', False),
            'price': info.get('prompt_price', '?'),
        })
    return sorted(result, key=lambda x: (not x['free'], x['id']))


def fetch_ollama_models() -> tuple:
    """Возвращает (models_list, error | None). models_list: [{id, name}]."""
    names = _ollama_fetch()
    if not names:
        return [], "Ollama не запущена"
    return [{'id': n, 'name': n} for n in names], None


def fetch_any_provider_models(base_url: str, api_key: str, provider: str) -> tuple:
    """Возвращает (models_list, error | None). models_list: [{id}]."""
    models = _openai_compat_fetch(base_url, api_key)
    if not models:
        return [], "Нет моделей или нет доступа"
    return [{'id': m} for m in models], None


def format_models_summary(models: list, title: str = "Модели") -> str:
    """HTML-сводка по списку моделей."""
    total = len(models)
    free  = sum(1 for m in models if m.get('free'))
    lines = [f"<b>{title}</b>"]
    lines.append(f"Всего: {total}" + (f"  |  🆓 Бесплатных: {free}" if free else ""))
    return "\n".join(lines)


def format_free_models_keyboard(models: list, page: int = 0, page_size: int = 8):
    """
    Возвращает (free_models_on_page, has_next, has_prev).
    Используется в _show_models_page в bot.py.
    """
    free = [m for m in models if m.get('free')]
    start = page * page_size
    end   = start + page_size
    return free[start:end], end < len(free), page > 0
