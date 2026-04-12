"""
core/session.py — Управление сессиями пользователей.

Каждая сессия:
  - История чата (в памяти + JSON на диске)
  - Настройки LLM-провайдера
  - Путь к файлам/проектам пользователя
  - Состояние агента (текущий инструмент, wait_state)
"""

import os
import json
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger('session')

DATA_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "users")
MAX_HISTORY = 20   # максимум сообщений в контексте


# ── Структура сессии ──────────────────────────────────────────────

@dataclass
class UserSession:
    user_id:      int
    # LLM настройки (персональные, переопределяют глобальные)
    llm_provider: str = ''
    llm_model:    str = ''
    # История чата
    history:      List[Dict] = field(default_factory=list)
    # Состояние ожидания (для multi-step диалогов)
    wait_state:   str = ''
    wait_data:    Dict = field(default_factory=dict)
    # Режим (chat / agent / gen)
    mode:         str = 'chat'
    # Метаданные
    last_active:  float = field(default_factory=time.time)
    # Sandbox Docker container ID (если запущен)
    container_id: str = ''

    @property
    def user_dir(self) -> str:
        d = os.path.join(DATA_DIR, str(self.user_id))
        os.makedirs(d, exist_ok=True)
        return d

    @property
    def projects_dir(self) -> str:
        d = os.path.join(self.user_dir, 'projects')
        os.makedirs(d, exist_ok=True)
        return d

    @property
    def files_dir(self) -> str:
        d = os.path.join(self.user_dir, 'files')
        os.makedirs(d, exist_ok=True)
        return d

    @property
    def sandbox_dir(self) -> str:
        d = os.path.join(self.user_dir, 'sandbox')
        os.makedirs(d, exist_ok=True)
        return d

    def add_message(self, role: str, content: str):
        """Добавляет сообщение в историю."""
        self.history.append({'role': role, 'content': content})
        # Обрезаем историю (оставляем последние MAX_HISTORY)
        if len(self.history) > MAX_HISTORY:
            # Всегда оставляем system-сообщения
            system = [m for m in self.history if m['role'] == 'system']
            other  = [m for m in self.history if m['role'] != 'system']
            other  = other[-(MAX_HISTORY - len(system)):]
            self.history = system + other
        self.last_active = time.time()

    def get_context(self, system_prompt: str = '') -> List[Dict]:
        """Возвращает историю для передачи в LLM."""
        msgs = []
        if system_prompt:
            msgs.append({'role': 'system', 'content': system_prompt})
        # Убираем старые system-сообщения из истории
        msgs += [m for m in self.history if m['role'] != 'system']
        return msgs

    def clear_history(self):
        self.history = []
        logger.info(f'[session] История очищена: {self.user_id}')

    def set_wait(self, state: str, data: Dict = None):
        self.wait_state = state
        self.wait_data  = data or {}

    def clear_wait(self):
        self.wait_state = ''
        self.wait_data  = {}

    def save(self):
        """Сохраняет сессию на диск."""
        path = os.path.join(self.user_dir, 'session.json')
        data = {
            'user_id':      self.user_id,
            'llm_provider': self.llm_provider,
            'llm_model':    self.llm_model,
            'history':      self.history,
            'mode':         self.mode,
            'last_active':  self.last_active,
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, user_id: int) -> 'UserSession':
        """Загружает сессию с диска (или создаёт новую)."""
        path = os.path.join(DATA_DIR, str(user_id), 'session.json')
        sess = cls(user_id=user_id)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                sess.llm_provider = data.get('llm_provider', '')
                sess.llm_model    = data.get('llm_model', '')
                sess.history      = data.get('history', [])
                sess.mode         = data.get('mode', 'chat')
                sess.last_active  = data.get('last_active', time.time())
            except Exception as e:
                logger.warning(f'[session] Ошибка загрузки {user_id}: {e}')
        return sess


# ── Менеджер сессий (in-memory кэш) ──────────────────────────────

class SessionManager:
    """
    Singleton менеджер сессий.
    Держит активные сессии в памяти, сохраняет на диск при изменениях.
    """

    def __init__(self):
        self._sessions: Dict[int, UserSession] = {}
        self._last_save: Dict[int, float] = {}
        self._save_interval = 60  # секунд между сохранениями

    def get(self, user_id: int) -> UserSession:
        """Возвращает сессию (загружает если нет в памяти)."""
        if user_id not in self._sessions:
            self._sessions[user_id] = UserSession.load(user_id)
            logger.debug(f'[session] Загружена: {user_id}')
        sess = self._sessions[user_id]
        sess.last_active = time.time()
        return sess

    def save(self, user_id: int, force: bool = False):
        """Сохраняет сессию на диск (с дебаунсом)."""
        now = time.time()
        last = self._last_save.get(user_id, 0)
        if force or (now - last > self._save_interval):
            if user_id in self._sessions:
                self._sessions[user_id].save()
                self._last_save[user_id] = now

    def save_all(self):
        """Сохраняет все активные сессии."""
        for uid in list(self._sessions.keys()):
            self.save(uid, force=True)

    def clear(self, user_id: int):
        """Очищает сессию из памяти."""
        if user_id in self._sessions:
            self.save(user_id, force=True)
            del self._sessions[user_id]

    def active_count(self) -> int:
        return len(self._sessions)

    def get_user_dir(self, user_id: int) -> str:
        return self.get(user_id).user_dir

    def get_projects_dir(self, user_id: int) -> str:
        return self.get(user_id).projects_dir


# Глобальный экземпляр
sessions = SessionManager()
