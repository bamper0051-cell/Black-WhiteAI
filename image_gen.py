"""
image_gen.py — Генерация изображений.

Провайдеры:
  1. Pollinations (бесплатно, без ключа) — по умолчанию
  2. DALL-E (OpenAI API ключ)
  3. Stability AI (SAI ключ)
  4. Hugging Face (HF_API_KEY, бесплатно с лимитами)

Использование:
  from image_gen import generate_image
  path, provider_used = generate_image("кот на луне", provider='auto')
"""

import os
import re
import time
import tempfile
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Провайдеры и их приоритет ────────────────────────────────────────
# auto: пробуем в порядке списка, берём первый рабочий

def _get_cfg():
    try:
        import config as _cfg
        return _cfg
    except Exception:
        return None

def _safe_filename(prompt: str) -> str:
    """Безопасное имя файла из промпта."""
    s = re.sub(r'[^\w\s-]', '', prompt[:40]).strip().replace(' ', '_')
    return s or 'image'

def _save_image(data: bytes, prompt: str, ext: str = 'png') -> str:
    """Сохраняет изображение, возвращает путь."""
    out_dir = os.path.join(BASE_DIR, 'agent_projects', 'images')
    os.makedirs(out_dir, exist_ok=True)
    ts   = time.strftime('%Y%m%d_%H%M%S')
    name = '{}_{}.{}'.format(_safe_filename(prompt), ts, ext)
    path = os.path.join(out_dir, name)
    with open(path, 'wb') as f:
        f.write(data)
    return path


# ══════════════════════════════════════════════════════════════════
#  ПРОВАЙДЕР 1: Pollinations.ai (БЕСПЛАТНО, без ключа)
# ══════════════════════════════════════════════════════════════════

def _pollinations(prompt: str, width=1024, height=1024, model='flux', **kwargs):
    """
    Полностью бесплатно, без API ключа.
    Модели: flux (лучшее), turbo (быстро), flux-realism, gptimage1.
    """
    import urllib.parse
    encoded = urllib.parse.quote(prompt)
    seed    = kwargs.get('seed', int(time.time()) % 99999)
    url     = (f"https://image.pollinations.ai/prompt/{encoded}"
               f"?width={width}&height={height}&model={model}&seed={seed}"
               f"&nologo=true&enhance=true")
    for _attempt in range(3):
        try:
            r = requests.get(url, timeout=90)
            r.raise_for_status()
            ct = r.headers.get('content-type', '')
            if ct.startswith('image') or len(r.content) > 5000:
                return _save_image(r.content, prompt), 'pollinations'
            # Вернул HTML/JSON — модель занята, меняем seed
            seed = (seed + 1) % 99999
            url = (f"https://image.pollinations.ai/prompt/{encoded}"
                   f"?width={width}&height={height}&model={model}&seed={seed}"
                   f"&nologo=true&enhance=true")
        except requests.exceptions.Timeout:
            if _attempt == 2:
                raise Exception("Pollinations: timeout после 3 попыток")
    raise Exception("Pollinations вернул не картинку")


# ══════════════════════════════════════════════════════════════════
#  ПРОВАЙДЕР 2: DALL-E (OpenAI)
# ══════════════════════════════════════════════════════════════════

def _dalle(prompt: str, model='dall-e-3', size='1024x1024', quality='standard', **kwargs):
    cfg = _get_cfg()
    api_key = getattr(cfg, 'OPENAI_API_KEY', '') if cfg else ''
    if not api_key:
        raise Exception("OPENAI_API_KEY не задан")
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    body = {
        'model':   model,
        'prompt':  prompt,
        'n':       1,
        'size':    size,
        'quality': quality,
    }
    r = requests.post('https://api.openai.com/v1/images/generations',
                      json=body, headers=headers, timeout=60)
    r.raise_for_status()
    img_url = r.json()['data'][0]['url']
    img_data = requests.get(img_url, timeout=30).content
    return _save_image(img_data, prompt), 'dalle'


# ══════════════════════════════════════════════════════════════════
#  ПРОВАЙДЕР 3: Stability AI
# ══════════════════════════════════════════════════════════════════

def _stability(prompt: str, model='ultra', aspect_ratio='1:1', **kwargs):
    cfg = _get_cfg()
    api_key = (getattr(cfg, 'STABILITY_API_KEY', '') or
               os.environ.get('STABILITY_API_KEY', '')) if cfg else ''
    if not api_key:
        raise Exception("STABILITY_API_KEY не задан")
    url = f"https://api.stability.ai/v2beta/stable-image/generate/{model}"
    headers = {'Authorization': f'Bearer {api_key}', 'Accept': 'image/*'}
    files   = {
        'prompt':       (None, prompt),
        'aspect_ratio': (None, aspect_ratio),
        'output_format':(None, 'png'),
    }
    r = requests.post(url, headers=headers, files=files, timeout=60)
    r.raise_for_status()
    return _save_image(r.content, prompt), 'stability'


# ══════════════════════════════════════════════════════════════════
#  ПРОВАЙДЕР 4: Hugging Face (бесплатно с лимитами)
# ══════════════════════════════════════════════════════════════════

_HF_FREE_MODELS = [
    'black-forest-labs/FLUX.1-schnell',        # FLUX schnell, быстрый и качественный
    'stabilityai/stable-diffusion-3.5-medium', # SD 3.5 medium
    'stabilityai/stable-diffusion-3-medium-diffusers',
    'stabilityai/stable-diffusion-2-1',
]

def _huggingface(prompt: str, model=None, **kwargs):
    cfg = _get_cfg()
    api_key = (getattr(cfg, 'HF_API_KEY', '') or
               os.environ.get('HF_API_KEY', '')) if cfg else ''
    headers = {}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    models_to_try = [model] if model else _HF_FREE_MODELS
    last_err = None
    for m in models_to_try:
        url = f"https://api-inference.huggingface.co/models/{m}"
        try:
            r = requests.post(url, headers=headers, json={'inputs': prompt}, timeout=90)
            if r.status_code == 503:
                import time as _t; _t.sleep(15)
                r = requests.post(url, headers=headers, json={'inputs': prompt}, timeout=90)
            if r.status_code in (404, 410, 422):
                last_err = f"{m}: HTTP {r.status_code}"
                continue  # модель удалена — пробуем следующую
            r.raise_for_status()
            if r.headers.get('content-type', '').startswith('image'):
                return _save_image(r.content, prompt), 'huggingface'
            last_err = f"{m}: не картинка"
        except Exception as e:
            last_err = f"{m}: {e}"
            continue
    raise Exception(f"HuggingFace все модели недоступны. Последняя ошибка: {last_err}")


# ══════════════════════════════════════════════════════════════════
#  ГЛАВНАЯ ФУНКЦИЯ
# ══════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════
#  ПРОВАЙДЕР 5: Together AI (FLUX.1 — бесплатно с ключом Together)
# ══════════════════════════════════════════════════════════════════

def _together_img(prompt: str, model='black-forest-labs/FLUX.1-schnell-Free',
                  width=1024, height=1024, steps=4, **kwargs):
    cfg = _get_cfg()
    api_key = (getattr(cfg, 'TOGETHER_API_KEY', '') or
               os.environ.get('TOGETHER_API_KEY', '') or
               getattr(cfg, 'LLM_API_KEY', '')) if cfg else ''
    if not api_key:
        raise Exception("TOGETHER_API_KEY не задан")
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    body = {
        'model':  model,
        'prompt': prompt,
        'width':  width,
        'height': height,
        'steps':  steps,
        'n':      1,
        'response_format': 'b64_json',
    }
    r = requests.post('https://api.together.xyz/v1/images/generations',
                      json=body, headers=headers, timeout=60)
    r.raise_for_status()
    import base64
    b64 = r.json()['data'][0]['b64_json']
    data = base64.b64decode(b64)
    return _save_image(data, prompt, 'png'), 'together'


# ══════════════════════════════════════════════════════════════════
#  ПРОВАЙДЕР 6: Fal.ai (FLUX schnell — бесплатный тир)
# ══════════════════════════════════════════════════════════════════

def _fal_img(prompt: str, **kwargs):
    cfg = _get_cfg()
    api_key = (getattr(cfg, 'FAL_API_KEY', '') or
               os.environ.get('FAL_API_KEY', '')) if cfg else ''
    if not api_key:
        raise Exception("FAL_API_KEY не задан")
    headers = {'Authorization': f'Key {api_key}', 'Content-Type': 'application/json'}
    r = requests.post(
        'https://fal.run/fal-ai/flux/schnell',
        json={'prompt': prompt, 'image_size': 'square_hd', 'num_images': 1},
        headers=headers, timeout=60
    )
    r.raise_for_status()
    img_url = r.json()['images'][0]['url']
    img_data = requests.get(img_url, timeout=30).content
    return _save_image(img_data, prompt), 'fal'


PROVIDERS = {
    'pollinations': _pollinations,
    'together':     _together_img,
    'huggingface':  _huggingface,
    'fal':          _fal_img,
    'dalle':        _dalle,
    'stability':    _stability,
}

# Порядок для 'auto' — сначала бесплатные
AUTO_ORDER = ['pollinations', 'together', 'huggingface', 'fal', 'dalle', 'stability']


def generate_image(prompt: str,
                   provider: str = 'auto',
                   on_status=None,
                   **kwargs) -> tuple:
    """
    Генерирует изображение по промпту.
    
    Returns:
        (filepath: str, provider_used: str)
    Raises:
        Exception если ни один провайдер не сработал
    """
    def _st(m):
        if on_status:
            on_status(m)

    if provider == 'auto':
        errors = []
        for pname in AUTO_ORDER:
            try:
                _st(f"🎨 Пробую {pname}...")
                path, used = PROVIDERS[pname](prompt, **kwargs)
                _st(f"✅ Готово ({used})")
                return path, used
            except Exception as e:
                errors.append(f"{pname}: {e}")
                _st(f"⚠️ {pname} недоступен, пробую следующий...")
        raise Exception("Все провайдеры недоступны:\n" + "\n".join(errors))

    elif provider in PROVIDERS:
        _st(f"🎨 Генерирую через {provider}...")
        path, used = PROVIDERS[provider](prompt, **kwargs)
        _st(f"✅ Готово!")
        return path, used

    else:
        raise Exception(f"Неизвестный провайдер: {provider}. Доступны: {list(PROVIDERS)}")


def get_available_providers() -> list:
    """Возвращает список провайдеров и их статус (есть ключ / нет ключа)."""
    cfg = _get_cfg()
    result = []
    checks = {
        'pollinations': (None, True),  # всегда доступен
        'dalle':        ('OPENAI_API_KEY', False),
        'stability':    ('STABILITY_API_KEY', False),
        'huggingface':  ('HF_API_KEY', True),  # работает без ключа
    }
    for pname, (key_attr, works_without_key) in checks.items():
        has_key = True
        if key_attr and cfg:
            key = getattr(cfg, key_attr, '') or os.environ.get(key_attr, '')
            has_key = bool(key)
        result.append({
            'name':             pname,
            'has_key':          has_key,
            'works_free':       works_without_key,
            'available':        works_without_key or has_key,
        })
    return result
