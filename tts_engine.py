"""
tts_engine.py — синтез речи через edge-tts или ElevenLabs.

Новое: учитывает TTS_LANGUAGE из .env для выбора локали edge-tts.
Профили персонажей обновлены под все языки через config.TTS_VOICE.
"""
import asyncio
import os
import json
import re
import config

OUTPUT_DIR = os.path.join(config.BASE_DIR, 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ══════════════════════════════════════════════════════════════
#  EDGE-TTS
# ══════════════════════════════════════════════════════════════

# Параметры скорости/тона для каждого стиля (не зависят от языка).
# Голос берётся из config.TTS_VOICE — так что смена языка меняет голос
# автоматически через .env/UI, не трогая этот файл.
СТИЛИ_EDGE: dict = {
    'anchor':  {'rate': '+8%',  'pitch': '+3Hz'},
    'troll':   {'rate': '+0%',  'pitch': '+0Hz'},
    'critic':  {'rate': '-8%',  'pitch': '-2Hz'},
    'drunk':   {'rate': '-20%', 'pitch': '-4Hz'},
    'grandma': {'rate': '-25%', 'pitch': '-6Hz'},
    'hype':    {'rate': '+20%', 'pitch': '+5Hz'},
    'custom':  {'rate': '+0%',  'pitch': '+0Hz'},
}

def _get_style() -> str:
    return os.environ.get('REWRITE_STYLE', 'troll').lower().strip()

def _edge_voice_params() -> dict:
    """Возвращает voice, rate, pitch для текущего стиля."""
    style = _get_style()
    params = СТИЛИ_EDGE.get(style, {'rate': '+0%', 'pitch': '+0Hz'})
    return {
        'voice': config.TTS_VOICE,   # берётся из .env, меняется через UI
        'rate':  params['rate'],
        'pitch': params['pitch'],
    }

async def _edge_synthesize(text: str, path: str):
    import edge_tts
    p = _edge_voice_params()
    com = edge_tts.Communicate(text, p['voice'], rate=p['rate'], pitch=p['pitch'])
    await com.save(path)

async def _edge_list_all_voices():
    import edge_tts
    return await edge_tts.list_voices()

def list_russian_voices() -> list:
    """Список голосов edge-tts с текущей локалью (для /voices)."""
    all_voices = asyncio.run(_edge_list_all_voices())
    lang_key = os.environ.get('TTS_LANGUAGE', 'ru').lower()
    return [v for v in all_voices if v.get('Locale', '').lower().startswith(lang_key)]


# ══════════════════════════════════════════════════════════════
#  ELEVENLABS
# ══════════════════════════════════════════════════════════════

def _eleven_headers():
    if not config.ELEVEN_API_KEY:
        raise RuntimeError("ELEVEN_API_KEY не задан в .env")
    return {
        "xi-api-key":   config.ELEVEN_API_KEY,
        "Content-Type": "application/json",
        "Accept":       "audio/mpeg",
    }

def eleven_list_voices() -> list:
    """Возвращает список голосов ElevenLabs."""
    import requests
    r = requests.get(
        "https://api.elevenlabs.io/v1/voices",
        headers={"xi-api-key": config.ELEVEN_API_KEY}
    )
    r.raise_for_status()
    out = []
    for v in r.json().get("voices", []):
        out.append({
            "name":     v.get("name", ""),
            "voice_id": v.get("voice_id", ""),
            "category": v.get("category", ""),
        })
    return out

def _eleven_voice_id() -> str:
    vid = (config.ELEVEN_VOICE_ID or "").strip()
    if vid:
        return vid
    # Фолбэк: если вдруг voice_id записали в TTS_VOICE
    cand = (config.TTS_VOICE or "").strip()
    if re.fullmatch(r"[A-Za-z0-9]{10,}", cand or ""):
        return cand
    raise RuntimeError(
        "ELEVEN_VOICE_ID не задан. /voices → скопируй voice_id → нажми 🎙 Сменить голос"
    )

def _eleven_payload(text: str) -> dict:
    return {
        "text":     text,
        "model_id": config.ELEVEN_MODEL_ID,
        "voice_settings": {
            "stability":        0.5,
            "similarity_boost": 0.75
        }
    }

def _eleven_synthesize(text: str, path: str):
    import requests
    voice_id = _eleven_voice_id()
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    r = requests.post(
        url,
        headers=_eleven_headers(),
        data=json.dumps(_eleven_payload(text)).encode("utf-8")
    )
    r.raise_for_status()
    with open(path, "wb") as f:
        f.write(r.content)


# ══════════════════════════════════════════════════════════════
#  ПУБЛИЧНЫЙ API
# ══════════════════════════════════════════════════════════════

def synthesize(text: str, filename: str) -> str:
    """Синтезирует речь и сохраняет MP3. Используется в pipeline.py."""
    path = os.path.join(OUTPUT_DIR, filename)
    provider = (config.TTS_PROVIDER or "edge").lower().strip()

    if provider in ("eleven", "elevenlabs", "11labs"):
        _eleven_synthesize(text, path)
    else:
        asyncio.run(_edge_synthesize(text, path))

    return path
