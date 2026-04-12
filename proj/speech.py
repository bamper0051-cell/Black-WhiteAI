"""
BlackBugsAI — Speech Tools (TTS / STT)
Обёртка над edge-tts, ElevenLabs, Whisper.
"""
import os, asyncio, time
import config

def tts(text: str, voice: str = None, lang: str = None,
        chat_id: str = None, on_status=None) -> tuple[bool, str]:
    """
    Синтез речи. Возвращает (ok, path_or_error).
    Приоритет: ElevenLabs → edge-tts.
    """
    voice = voice or config.TTS_VOICE
    out_dir = os.path.join(config.BASE_DIR, 'agent_projects')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f'tts_{int(time.time())}.mp3')

    if on_status: on_status(f"🎙 TTS: {text[:40]}...")

    # ElevenLabs
    if config.TTS_PROVIDER == 'elevenlabs' and config.ELEVEN_API_KEY:
        try:
            import requests
            resp = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVEN_VOICE_ID}",
                headers={"xi-api-key": config.ELEVEN_API_KEY, "Content-Type": "application/json"},
                json={"text": text, "model_id": config.ELEVEN_MODEL_ID,
                      "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}},
                timeout=30
            )
            if resp.ok:
                open(out_path, 'wb').write(resp.content)
                if chat_id:
                    from telegram_client import send_document
                    send_document(out_path, caption=f"🎙 {text[:60]}", chat_id=chat_id)
                return True, out_path
        except Exception as e:
            if on_status: on_status(f"⚠️ ElevenLabs упал: {e}, пробую edge-tts...")

    # edge-tts
    try:
        import edge_tts

        async def _synth():
            comm = edge_tts.Communicate(text, voice)
            await comm.save(out_path)

        asyncio.run(_synth())
        if chat_id:
            from telegram_client import send_document
            send_document(out_path, caption=f"🎙 {text[:60]}", chat_id=chat_id)
        return True, out_path

    except Exception as e:
        return False, f"❌ TTS ошибка: {e}"


def stt(audio_path: str, lang: str = 'ru', on_status=None) -> tuple[bool, str]:
    """
    Распознавание речи (STT). Возвращает (ok, text_or_error).
    Использует Whisper (openai-whisper) если доступен.
    """
    if on_status: on_status("🎤 Распознаю речь...")
    try:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, language=lang)
        return True, result.get('text', '')
    except ImportError:
        pass

    # Fallback: Whisper через subprocess
    try:
        import subprocess
        r = subprocess.run(
            ['whisper', audio_path, '--language', lang, '--output_format', 'txt'],
            capture_output=True, text=True, timeout=120
        )
        txt_path = audio_path.rsplit('.', 1)[0] + '.txt'
        if os.path.exists(txt_path):
            return True, open(txt_path).read().strip()
        return False, "Whisper не вернул текст"
    except Exception as e:
        return False, f"❌ STT ошибка: {e}. Установи: pip install openai-whisper"
