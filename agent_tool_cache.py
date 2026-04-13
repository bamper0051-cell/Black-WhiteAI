"""
BlackBugsAI — Agent Tool Cache
Хранилище сгенерированных инструментов (код, метаданные).
"""
import json
import os
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'tool_cache')
os.makedirs(CACHE_DIR, exist_ok=True)

def _hash_name(name: str) -> str:
    return hashlib.md5(name.encode()).hexdigest()

def save_tool(name: str, code: str, language: str, metadata: Dict[str, Any] = None) -> str:
    """Сохраняет инструмент в кэш. Возвращает путь к файлу."""
    safe = _hash_name(name)
    path = os.path.join(CACHE_DIR, f"{safe}.json")
    data = {
        'name': name,
        'code': code,
        'language': language,
        'created': datetime.now().isoformat(),
        'metadata': metadata or {},
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    return path

def get_tool(name: str) -> Optional[Dict[str, Any]]:
    """Возвращает данные инструмента по имени, если есть."""
    safe = _hash_name(name)
    path = os.path.join(CACHE_DIR, f"{safe}.json")
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def list_tools() -> list:
    """Возвращает список имён всех закэшированных инструментов."""
    tools = []
    for fname in os.listdir(CACHE_DIR):
        if fname.endswith('.json'):
            try:
                with open(os.path.join(CACHE_DIR, fname), 'r') as f:
                    data = json.load(f)
                    tools.append(data['name'])
            except:
                pass
    return tools
