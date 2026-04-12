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
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    if r.headers.get('content-type', '').startswith('image'):
        return _save_image(r.content, prompt), 'pollinations'
    raise Exception("Pollinations вернул не картинку: " + r.text[:200])


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

def _huggingface(prompt: str, model='stabilityai/stable-diffusion-xl-base-1.0', **kwargs):
    cfg = _get_cfg()
    api_key = (getattr(cfg, 'HF_API_KEY', '') or
               os.environ.get('HF_API_KEY', '')) if cfg else ''
    headers = {}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    url = f"https://api-inference.huggingface.co/models/{model}"
    r   = requests.post(url, headers=headers, json={'inputs': prompt}, timeout=90)
    if r.status_code == 503:
        raise Exception("Модель загружается, попробуй через 30 сек")
    r.raise_for_status()
    if r.headers.get('content-type', '').startswith('image'):
        return _save_image(r.content, prompt), 'huggingface'
    raise Exception("HuggingFace: " + r.text[:200])



# ══════════════════════════════════════════════════════════════════
#  ПРОВАЙДЕР 5: Together AI (бесплатный tier — FLUX schnell)
# ══════════════════════════════════════════════════════════════════

def _together(prompt: str, model='black-forest-labs/FLUX.1-schnell-Free',
              width=1024, height=1024, **kwargs):
    cfg = _get_cfg()
    api_key = (getattr(cfg, 'TOGETHER_API_KEY', '') or
               os.environ.get('TOGETHER_API_KEY', '')) if cfg else ''
    if not api_key:
        raise Exception("TOGETHER_API_KEY не задан (бесплатно: together.ai)")
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    body = {
        'model':   model,
        'prompt':  prompt,
        'width':   width,
        'height':  height,
        'steps':   4,
        'n':       1,
    }
    r = requests.post('https://api.together.xyz/v1/images/generations',
                      json=body, headers=headers, timeout=90)
    r.raise_for_status()
    data = r.json()
    img_url = data['data'][0].get('url') or data['data'][0].get('b64_json')
    if img_url and img_url.startswith('http'):
        img_data = requests.get(img_url, timeout=30).content
    else:
        import base64
        img_data = base64.b64decode(img_url)
    return _save_image(img_data, prompt), 'together'


# ══════════════════════════════════════════════════════════════════
#  ПРОВАЙДЕР 6: Fal.ai (быстрый FLUX, есть бесплатные кредиты)
# ══════════════════════════════════════════════════════════════════

def _fal(prompt: str, model='fal-ai/flux/schnell',
         image_size='square_hd', **kwargs):
    cfg = _get_cfg()
    api_key = (getattr(cfg, 'FAL_API_KEY', '') or
               os.environ.get('FAL_API_KEY', '')) if cfg else ''
    if not api_key:
        raise Exception("FAL_API_KEY не задан (fal.ai — есть бесплатный tier)")
    headers = {'Authorization': f'Key {api_key}', 'Content-Type': 'application/json'}
    body = {
        'prompt':     prompt,
        'image_size': image_size,
        'num_images': 1,
    }
    r = requests.post(f'https://fal.run/{model}',
                      json=body, headers=headers, timeout=90)
    r.raise_for_status()
    img_url = r.json()['images'][0]['url']
    img_data = requests.get(img_url, timeout=30).content
    return _save_image(img_data, prompt), 'fal'

# ══════════════════════════════════════════════════════════════════
#  ГЛАВНАЯ ФУНКЦИЯ
# ══════════════════════════════════════════════════════════════════

PROVIDERS = {
    'pollinations': _pollinations,
    'dalle':        _dalle,
    'stability':    _stability,
    'huggingface':  _huggingface,
    'together':     _together,
    'fal':          _fal,
}

# Порядок для 'auto' — сначала бесплатные
AUTO_ORDER = ['pollinations', 'huggingface', 'together', 'dalle', 'stability', 'fal']


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
        'pollinations': (None,              True,  '🆓 Без ключа',    'https://pollinations.ai'),
        'huggingface':  ('HF_API_KEY',      True,  '🆓 Без ключа',    'https://huggingface.co'),
        'together':     ('TOGETHER_API_KEY', False, '🆓 Бесплатный tier', 'https://together.ai'),
        'fal':          ('FAL_API_KEY',      False, '🆓 Бесплатные credits', 'https://fal.ai'),
        'dalle':        ('OPENAI_API_KEY',   False, '💳 OpenAI',       'https://platform.openai.com'),
        'stability':    ('STABILITY_API_KEY',False, '💳 Stability',    'https://platform.stability.ai'),
    }
    for pname, (key_attr, works_without_key, price, url) in checks.items():
        has_key = True
        if key_attr and cfg:
            key = getattr(cfg, key_attr, '') or os.environ.get(key_attr, '')
            has_key = bool(key)
        result.append({
            'name':             pname,
            'has_key':          has_key,
            'works_free':       works_without_key,
            'available':        works_without_key or has_key,
            'price':            price,
            'reg_url':          url,
        })
    return result
