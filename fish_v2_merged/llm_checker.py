"""
llm_checker.py — проверяет доступность LLM-провайдеров и их моделей.
"""
import requests
import config

PROVIDERS = {
    # ── Топ-провайдеры ─────────────────────────────────────────
    'openai':      {'url': 'https://api.openai.com/v1/models',                         'key_attr': 'OPENAI_API_KEY', 'models_path': 'data[].id'},
    'anthropic':   {'url': 'https://api.anthropic.com/v1/models',                      'key_attr': 'ANTHROPIC_API_KEY', 'models_path': 'data[].id'},
    'gemini':      {'url': 'https://generativelanguage.googleapis.com/v1beta/models',   'key_attr': 'GEMINI_API_KEY', 'models_path': 'models[].name'},
    'mistral':     {'url': 'https://api.mistral.ai/v1/models',                         'key_attr': 'MISTRAL_API_KEY', 'models_path': 'data[].id'},
    'deepseek':    {'url': 'https://api.deepseek.com/v1/models',                       'key_attr': 'DEEPSEEK_API_KEY', 'models_path': 'data[].id'},
    # ── Быстрые/бесплатные ─────────────────────────────────────
    'groq':        {'url': 'https://api.groq.com/openai/v1/models',                    'key_attr': 'GROQ_API_KEY', 'models_path': 'data[].id'},
    'together':    {'url': 'https://api.together.xyz/v1/models',                       'key_attr': 'TOGETHER_API_KEY', 'models_path': 'data[].id'},
    'fireworks':   {'url': 'https://api.fireworks.ai/inference/v1/models',             'key_attr': 'FIREWORKS_API_KEY', 'models_path': 'data[].id'},
    'cerebras':    {'url': 'https://api.cerebras.ai/v1/models',                        'key_attr': 'CEREBRAS_API_KEY', 'models_path': 'data[].id'},
    'sambanova':   {'url': 'https://api.sambanova.ai/v1/models',                       'key_attr': 'SAMBANOVA_API_KEY', 'models_path': 'data[].id'},
    'novita':      {'url': 'https://api.novita.ai/v3/openai/models',                   'key_attr': 'NOVITA_API_KEY', 'models_path': 'data[].id'},
    # ── Специализированные ─────────────────────────────────────
    'xai':         {'url': 'https://api.x.ai/v1/models',                              'key_attr': 'XAI_API_KEY', 'models_path': 'data[].id'},
    'kimi':        {'url': 'https://api.moonshot.cn/v1/models',                        'key_attr': 'KIMI_API_KEY', 'models_path': 'data[].id'},
    'cohere':      {'url': 'https://api.cohere.com/v1/models',                         'key_attr': 'COHERE_API_KEY', 'models_path': 'models[].name'},
    'kluster':     {'url': 'https://api.kluster.ai/v1/models',                         'key_attr': 'KLUSTER_API_KEY', 'models_path': 'data[].id'},
    'llama':       {'url': 'https://api.llama.com/compat/v1/models',                   'key_attr': 'LLAMA_API_KEY', 'models_path': 'data[].id'},
    'perplexity':  {'url': 'https://api.perplexity.ai/models',                         'key_attr': 'PERPLEXITY_API_KEY', 'models_path': 'data[].id'},
    'openrouter':  {'url': 'https://openrouter.ai/api/v1/models',                      'key_attr': 'OPENROUTER_API_KEY', 'models_path': 'data[].id'},
    'hyperbolic':  {'url': 'https://api.hyperbolic.xyz/v1/models',                     'key_attr': 'HYPERBOLIC_API_KEY', 'models_path': 'data[].id'},
    'anyscale':    {'url': 'https://api.endpoints.anyscale.com/v1/models',             'key_attr': 'ANYSCALE_API_KEY', 'models_path': 'data[].id'},
    'nvidia':      {'url': 'https://integrate.api.nvidia.com/v1/models',               'key_attr': 'NVIDIA_API_KEY', 'models_path': 'data[].id'},
    # ── Ещё быстрые/дешёвые ───────────────────────────────────
    'lepton':      {'url': 'https://api.lepton.ai/api/v1/models',                       'key_attr': 'LEPTON_API_KEY', 'models_path': 'data[].id'},
    'deepinfra':   {'url': 'https://api.deepinfra.com/v1/openai/models',               'key_attr': 'DEEPINFRA_API_KEY', 'models_path': 'data[].id'},
    'lambda':      {'url': 'https://api.lambdalabs.com/v1/models',                     'key_attr': 'LAMBDA_API_KEY', 'models_path': 'data[].id'},
    'scaleway':    {'url': 'https://api.scaleway.ai/v1/models',                        'key_attr': 'SCALEWAY_API_KEY', 'models_path': 'data[].id'},
    'featherless': {'url': 'https://api.featherless.ai/v1/models',                     'key_attr': 'FEATHERLESS_API_KEY', 'models_path': 'data[].id'},
    'chutes':      {'url': 'https://llm.chutes.ai/v1/models',                          'key_attr': 'CHUTES_API_KEY', 'models_path': 'data[].id'},
    'neets':       {'url': 'https://api.neets.ai/v1/models',                           'key_attr': 'NEETS_API_KEY', 'models_path': 'data[].id'},
    # ── Ещё специализированные ─────────────────────────────────
    'alibaba':     {'url': 'https://dashscope.aliyuncs.com/compatible-mode/v1/models', 'key_attr': 'ALIBABA_API_KEY', 'models_path': 'data[].id'},
    'baidu':       {'url': 'https://qianfan.baidubce.com/v2/models',                   'key_attr': 'LLM_API_KEY', 'models_path': 'result[].name'},
    'zhipu':       {'url': 'https://open.bigmodel.cn/api/paas/v4/models',              'key_attr': 'ZHIPU_API_KEY', 'models_path': 'data[].id'},
    'stepfun':     {'url': 'https://api.stepfun.com/v1/models',                        'key_attr': 'STEPFUN_API_KEY', 'models_path': 'data[].id'},
    'minimax':     {'url': 'https://api.minimax.chat/v1/models',                       'key_attr': 'MINIMAX_API_KEY', 'models_path': 'data[].id'},
    'yi':          {'url': 'https://api.lingyiwanwu.com/v1/models',                    'key_attr': 'YI_API_KEY', 'models_path': 'data[].id'},
    'siliconflow': {'url': 'https://api.siliconflow.cn/v1/models',                     'key_attr': 'SILICONFLOW_API_KEY', 'models_path': 'data[].id'},
    'moonshot':    {'url': 'https://api.moonshot.ai/v1/models',                        'key_attr': 'MOONSHOT_API_KEY', 'models_path': 'data[].id'},
    'writer':      {'url': 'https://api.writer.com/v1/models',                         'key_attr': 'WRITER_API_KEY', 'models_path': 'models[].id'},
    'ai21':        {'url': 'https://api.ai21.com/studio/v1/models',                    'key_attr': 'AI21_API_KEY', 'models_path': 'data[].id'},
    'voyage':      {'url': 'https://api.voyageai.com/v1/models',                       'key_attr': 'LLM_API_KEY', 'models_path': 'data[].id'},
    'reka':        {'url': 'https://api.reka.ai/v1/models',                            'key_attr': 'REKA_API_KEY', 'models_path': 'data[].id'},
    'upstage':     {'url': 'https://api.upstage.ai/v1/models',                         'key_attr': 'UPSTAGE_API_KEY', 'models_path': 'data[].id'},
    # ── Локальные ──────────────────────────────────────────────
    'ollama':      {'url': 'http://localhost:11434/api/tags',                           'key_attr': None,          'models_path': 'models[].name'},
    'lmstudio':    {'url': 'http://localhost:1234/v1/models',                           'key_attr': None,          'models_path': 'data[].id'},
    'jan':         {'url': 'http://localhost:1337/v1/models',                           'key_attr': None,          'models_path': 'data[].id'},
    'llamacpp':    {'url': 'http://localhost:8080/v1/models',                           'key_attr': None,          'models_path': 'data[].id'},
}

# Рекомендуемые модели для каждого провайдера (если /models не работает)
RECOMMENDED = {
    # OpenAI
    'openai':      ['gpt-4.1-mini', 'gpt-4.1', 'gpt-4o', 'gpt-4o-mini', 'o4-mini', 'o3-mini'],
    # Anthropic
    'anthropic':   ['claude-3-5-haiku-latest', 'claude-3-5-sonnet-latest', 'claude-opus-4-5'],
    # Google
    'gemini':      ['gemini-2.0-flash', 'gemini-2.0-flash-lite', 'gemini-1.5-flash', 'gemini-1.5-pro'],
    # Mistral
    'mistral':     ['mistral-small-latest', 'mistral-large-latest', 'codestral-latest', 'pixtral-large-latest'],
    # DeepSeek
    'deepseek':    ['deepseek-chat', 'deepseek-reasoner', 'deepseek-coder'],
    # Groq (быстрый)
    'groq':        ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant', 'llama-4-scout-17b-16e-instruct', 'gemma2-9b-it', 'mixtral-8x7b-32768'],
    # Together AI
    'together':    ['meta-llama/Llama-3.3-70B-Instruct-Turbo', 'meta-llama/Llama-3.2-90B-Vision-Instruct-Turbo',
                    'mistralai/Mixtral-8x22B-Instruct-v0.1', 'Qwen/Qwen2.5-72B-Instruct-Turbo',
                    'deepseek-ai/DeepSeek-R1', 'google/gemma-2-27b-it'],
    # Fireworks
    'fireworks':   ['accounts/fireworks/models/llama-v3p3-70b-instruct', 'accounts/fireworks/models/deepseek-r1',
                    'accounts/fireworks/models/qwen2p5-72b-instruct', 'accounts/fireworks/models/mixtral-8x22b-instruct'],
    # Cerebras (очень быстрый)
    'cerebras':    ['llama3.1-8b', 'llama-3.3-70b', 'qwen-3-32b'],
    # SambaNova
    'sambanova':   ['Meta-Llama-3.3-70B-Instruct', 'Meta-Llama-3.1-405B-Instruct', 'Qwen2.5-72B-Instruct', 'DeepSeek-R1'],
    # Novita
    'novita':      ['meta-llama/llama-3.3-70b-instruct', 'deepseek/deepseek-r1', 'qwen/qwen2.5-72b-instruct'],
    # xAI
    'xai':         ['grok-3-mini', 'grok-3', 'grok-2-1212'],
    # Kimi / Moonshot
    'kimi':        ['moonshot-v1-8k', 'moonshot-v1-32k', 'moonshot-v1-128k'],
    # Cohere
    'cohere':      ['command-r-plus', 'command-r', 'command-a-03-2025'],
    # Kluster
    'kluster':     ['klusterai/Meta-Llama-3.3-70B-Instruct-Turbo', 'klusterai/Meta-Llama-3.1-405B-Instruct-Turbo'],
    # Meta Llama API
    'llama':       ['Llama-4-Scout-17B-16E-Instruct', 'Llama-4-Maverick-17B-128E-Instruct-FP8', 'Llama-3.3-70B-Instruct'],
    # Perplexity (поиск + LLM)
    'perplexity':  ['sonar', 'sonar-pro', 'sonar-reasoning', 'sonar-reasoning-pro', 'r1-1776'],
    # OpenRouter (агрегатор всех)
    'openrouter':  ['openai/gpt-4o-mini', 'anthropic/claude-3.5-haiku', 'google/gemini-2.0-flash-001',
                    'deepseek/deepseek-chat', 'meta-llama/llama-3.3-70b-instruct:free',
                    'mistralai/mistral-small-3.1-24b-instruct:free', 'qwen/qwen3-235b-a22b:free'],
    # Hyperbolic
    'hyperbolic':  ['meta-llama/Llama-3.3-70B-Instruct', 'deepseek-ai/DeepSeek-R1', 'Qwen/Qwen2.5-72B-Instruct'],
    # Anyscale
    'anyscale':    ['meta-llama/Llama-3-70b-chat-hf', 'mistralai/Mixtral-8x22B-Instruct-v0.1'],
    # NVIDIA NIM
    'nvidia':      ['nvidia/llama-3.1-nemotron-ultra-253b-v1', 'meta/llama-3.3-70b-instruct',
                    'deepseek-ai/deepseek-r1', 'qwen/qwen2.5-72b-instruct'],
    # ── Ещё быстрые ─────────────────────────────────────────────
    'lepton':      ['llama3-1-405b', 'llama3-1-70b', 'mixtral-8x7b'],
    'deepinfra':   ['meta-llama/Llama-3.3-70B-Instruct', 'deepseek-ai/DeepSeek-R1',
                    'Qwen/Qwen2.5-72B-Instruct', 'mistralai/Mixtral-8x22B-Instruct-v0.1',
                    'google/gemma-2-27b-it'],
    'lambda':      ['llama3.3-70b-instruct-fp8', 'llama3.1-405b-instruct-fp8', 'hermes3-405b'],
    'scaleway':    ['llama-3.3-70b-instruct', 'mistral-nemo-instruct-2407', 'qwen2.5-coder-32b-instruct'],
    'featherless': ['meta-llama/Llama-3.3-70B-Instruct', 'Qwen/Qwen2.5-72B-Instruct'],
    'chutes':      ['deepseek-ai/DeepSeek-V3-0324', 'deepseek-ai/DeepSeek-R1', 'Qwen/Qwen3-235B-A22B'],
    'neets':       ['meta-llama/llama-3-70b-instruct', 'mistralai/mixtral-8x7b-instruct-v0.1'],
    # ── Азиатские/специализированные ────────────────────────────
    'alibaba':     ['qwen-max', 'qwen-plus', 'qwen-turbo', 'qwen2.5-72b-instruct', 'qwen3-235b-a22b'],
    'baidu':       ['ernie-4.5-turbo-128k', 'ernie-4.0-8k', 'ernie-speed-128k'],
    'zhipu':       ['glm-4-plus', 'glm-4-air', 'glm-4-flash', 'glm-4-long'],
    'stepfun':     ['step-2-16k', 'step-1-256k', 'step-1-flash'],
    'minimax':     ['MiniMax-Text-01', 'abab6.5s-chat', 'abab6.5g-chat'],
    'yi':          ['yi-lightning', 'yi-large', 'yi-medium'],
    'siliconflow': ['deepseek-ai/DeepSeek-V3', 'Qwen/Qwen3-235B-A22B', 'meta-llama/Llama-3.3-70B-Instruct',
                    'THUDM/glm-4-9b-chat', 'Pro/deepseek-ai/DeepSeek-R1'],
    'moonshot':    ['moonshot-v1-auto', 'moonshot-v1-128k', 'moonshot-v1-32k'],
    'writer':      ['palmyra-x5', 'palmyra-x-004', 'palmyra-fin-32k'],
    'ai21':        ['jamba-1.5-large', 'jamba-1.5-mini', 'jamba-instruct'],
    'voyage':      ['voyage-3-large', 'voyage-3', 'voyage-code-3'],
    'reka':        ['reka-core', 'reka-flash', 'reka-edge'],
    'upstage':     ['solar-pro', 'solar-mini'],
    # Локальные
    'ollama':      [],   # динамически из /api/tags
    'lmstudio':    [],   # динамически из /v1/models
    'jan':         [],   # динамически из /v1/models
    'llamacpp':    [],   # динамически
}


def _extract_models(data, path):
    """Извлекает список моделей из JSON по пути типа 'data[].id'."""
    try:
        parts = path.split('.')
        current = data
        for part in parts:
            if part.endswith('[]'):
                key = part[:-2]
                current = current.get(key, []) if isinstance(current, dict) else current
                # current теперь список
            else:
                # достаём поле из каждого элемента списка
                if isinstance(current, list):
                    current = [item.get(part) for item in current if isinstance(item, dict)]
                else:
                    current = current.get(part, [])
        return [m for m in current if m] if isinstance(current, list) else []
    except Exception:
        return []


def _get_key_for_provider(name: str, override: str = '') -> str:
    """Возвращает API-ключ для провайдера из config."""
    if override:
        return override
    # Используем карту из llm_client (единый источник)
    try:
        from llm_client import _PROVIDER_KEY_MAP
        attr = _PROVIDER_KEY_MAP.get(name, 'LLM_API_KEY')
    except ImportError:
        attr = 'LLM_API_KEY'
    key = getattr(config, attr, '') or ''
    if not key and attr != 'LLM_API_KEY':
        key = getattr(config, 'LLM_API_KEY', '') or ''
    return key


def check_provider(name, api_key=None, timeout=8):
    """
    Проверяет один провайдер.
    Возвращает dict: {
        'name': str,
        'ok': bool,
        'models': list[str],
        'error': str | None,
        'recommended': list[str]
    }
    """
    info = PROVIDERS.get(name)
    if not info:
        return {'name': name, 'ok': False, 'models': [], 'error': 'Неизвестный провайдер',
                'recommended': RECOMMENDED.get(name, [])}

    # Ключ — из параметра или из config
    api_key = _get_key_for_provider(name, api_key or '')

    # Если ключ пустой — не тестируем, сразу сообщаем
    if not api_key and name not in ('ollama', 'lmstudio', 'jan', 'llamacpp'):
        return {'name': name, 'ok': False, 'models': [],
                'error': '🔑 нет ключа (добавь в .env)',
                'recommended': RECOMMENDED.get(name, [])}

    headers = {}
    params = {}

    if api_key:
        if name == 'gemini':
            params['key'] = api_key
        else:
            headers['Authorization'] = 'Bearer ' + api_key

    try:
        r = requests.get(info['url'], headers=headers, params=params, timeout=timeout)

        if r.status_code == 200:
            models = _extract_models(r.json(), info['models_path'])
            # Фильтруем: убираем embeddings, tts, vision-only модели
            chat_models = [m for m in models if not any(
                x in m.lower() for x in ['embed', 'whisper', 'dall-e', 'tts', 'vision',
                                          'babbage', 'davinci-00', 'search'])]
            return {
                'name': name,
                'ok': True,
                'models': chat_models[:10],  # топ-10
                'error': None,
                'recommended': RECOMMENDED.get(name, []),
            }
        elif r.status_code == 401:
            return {'name': name, 'ok': False, 'models': [],
                    'error': '401 Неверный API ключ',
                    'recommended': RECOMMENDED.get(name, [])}
        elif r.status_code == 403:
            return {'name': name, 'ok': False, 'models': [],
                    'error': '403 Доступ запрещён (ключ не тот или лимит)',
                    'recommended': RECOMMENDED.get(name, [])}
        elif r.status_code == 404:
            # Провайдер есть, но /models не поддерживает — считаем ОК если есть ключ
            if api_key:
                return {'name': name, 'ok': True, 'models': [],
                        'error': None,
                        'recommended': RECOMMENDED.get(name, [])}
            return {'name': name, 'ok': False, 'models': [],
                    'error': '404 /models endpoint не найден',
                    'recommended': RECOMMENDED.get(name, [])}
        else:
            return {'name': name, 'ok': False, 'models': [],
                    'error': 'HTTP {}'.format(r.status_code),
                    'recommended': RECOMMENDED.get(name, [])}

    except requests.exceptions.ConnectionError:
        return {'name': name, 'ok': False, 'models': [],
                'error': 'Нет соединения',
                'recommended': RECOMMENDED.get(name, [])}
    except requests.exceptions.Timeout:
        return {'name': name, 'ok': False, 'models': [],
                'error': 'Таймаут {}с'.format(timeout),
                'recommended': RECOMMENDED.get(name, [])}
    except Exception as e:
        return {'name': name, 'ok': False, 'models': [],
                'error': str(e)[:60],
                'recommended': RECOMMENDED.get(name, [])}


def check_all(providers=None, api_key=None):
    """
    Проверяет все провайдеры параллельно.
    Каждый провайдер получает свой ключ из config автоматически.
    Возвращает list[dict].
    """
    import concurrent.futures
    if providers is None:
        providers = list(PROVIDERS.keys()) + ['claude']

    # Каждый провайдер получает свой ключ из config.get_key()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(check_provider, p, _get_key_for_provider(p)): p for p in providers}
        results = []
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    # Сортируем: сначала рабочие, потом нет
    results.sort(key=lambda x: (not x['ok'], x['name']))
    return results


def format_check_results(results):
    """Форматирует результаты в HTML для Telegram."""
    lines = ['<b>🔍 Проверка LLM-провайдеров:</b>\n']

    ok_count   = sum(1 for r in results if r['ok'])
    no_key     = sum(1 for r in results if not r['ok'] and 'нет ключа' in (r['error'] or ''))
    bad_key    = sum(1 for r in results if not r['ok'] and 'нет ключа' not in (r['error'] or '') and not r['ok'])

    lines.append('🟢 Работает: {}   🔴 Ошибка: {}   🔑 Нет ключа: {}\n'.format(
        ok_count, bad_key - no_key, no_key))

    # Сначала рабочие
    for r in sorted(results, key=lambda x: (not x['ok'], 'нет ключа' in (x['error'] or ''), x['name'])):
        name = r['name']
        if r['ok']:
            models = r['models'] or r['recommended']
            lines.append('🟢 <b>{}</b>'.format(name))
            for m in (models[:3]):
                lines.append('   • <code>{}</code>'.format(m))
        elif 'нет ключа' in (r['error'] or ''):
            lines.append('🔑 <b>{}</b> — нет ключа'.format(name))
        else:
            lines.append('🔴 <b>{}</b> — {}'.format(name, r['error'] or 'недоступен'))

    lines.append('\n<i>💡 Один ключ → один провайдер. Для других добавь ключи в .env</i>')
    return '\n'.join(lines)
