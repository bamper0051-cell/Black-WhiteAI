"""
Application configuration — persisted in JSON under user's AppData.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _config_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path.home() / ".config"
    p = base / "BlackBugsAI"
    p.mkdir(parents=True, exist_ok=True)
    return p


CONFIG_PATH = _config_dir() / "config.json"
MODELS_DIR = _config_dir() / "models"
DB_PATH = _config_dir() / "history.db"
LOGS_DIR = _config_dir() / "logs"

MODELS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

_DEFAULTS: dict[str, Any] = {
    # Provider
    "provider": "local",  # local | openai | anthropic | gemini | mistral | groq | ollama
    "openai_api_key": "",
    "anthropic_api_key": "",
    "gemini_api_key": "",
    "mistral_api_key": "",
    "groq_api_key": "",
    "ollama_base_url": "http://localhost:11434",
    "openai_base_url": "https://api.openai.com/v1",
    # Model selection
    "selected_model_path": "",
    "selected_api_model": "gpt-4o-mini",
    # LLM params
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40,
    "max_tokens": 2048,
    "context_length": 4096,
    "n_gpu_layers": -1,       # -1 = auto (all layers to GPU if possible)
    "n_threads": 0,           # 0 = auto
    "repeat_penalty": 1.1,
    # UI
    "theme": "dark",
    "font_size": 13,
    "code_font_size": 13,
    # API server
    "api_server_enabled": False,
    "api_server_port": 8765,
    # Telegram
    "telegram_bot_token": "",
    "telegram_enabled": False,
    # Sandbox
    "sandbox_enabled": True,
    "sandbox_timeout": 15,
    # System prompt
    "system_prompt": "You are BlackBugsAI — a helpful AI assistant. Be concise and clear.",
}


class Config:
    def __init__(self) -> None:
        self._data: dict[str, Any] = dict(_DEFAULTS)
        self.load()

    def load(self) -> None:
        if CONFIG_PATH.exists():
            try:
                saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                self._data.update(saved)
            except Exception:
                pass

    def save(self) -> None:
        CONFIG_PATH.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default if default is not None else _DEFAULTS.get(key))

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)


# Global singleton
config = Config()
