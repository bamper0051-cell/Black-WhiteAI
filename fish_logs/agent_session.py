# -*- coding: utf-8 -*-
"""
agent_session.py — Управление агент-сессиями AGENT_SMITH.

Экспортирует ВСЕ символы которые нужны bot.py:
  Константы:    STAGE_WAIT_FILES, STAGE_EXECUTING, STAGE_DONE
  Функции:      create_session, get_session, close_session, has_active_session
                execute_pipeline, analyze_task
                is_ready_trigger, is_cancel_trigger
                detect_file_type

Объект AgentSession:
  .task, .stage, .files, .output_dir
  .add_file(path, name, ftype)
  .touch()
"""

import logging
import os
import time
import zipfile
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable

logger = logging.getLogger(__name__)

# ─── Константы стадий ────────────────────────────────────────────────────────

STAGE_IDLE       = 'idle'
STAGE_WAIT_FILES = 'wait_files'
STAGE_ANALYZING  = 'analyzing'
STAGE_EXECUTING  = 'executing'
STAGE_DONE       = 'done'
STAGE_CANCELLED  = 'cancelled'

# ─── Триггеры ────────────────────────────────────────────────────────────────

_READY_TRIGGERS = {
    'готово', 'go', 'start', 'старт', 'запуск', 'запустить',
    'поехали', 'давай', 'выполни', 'run', 'ok', 'ок', 'да',
}

_CANCEL_TRIGGERS = {
    'отмена', 'стоп', 'stop', 'cancel', 'отменить', 'хватит',
    'нет', 'выход', 'quit', '/end', '/стоп', '/cancel',
}

def is_ready_trigger(text: str) -> bool:
    """True если текст означает «запустить задачу»."""
    return (text or '').strip().lower() in _READY_TRIGGERS

def is_cancel_trigger(text: str) -> bool:
    """True если текст означает «отменить»."""
    return (text or '').strip().lower() in _CANCEL_TRIGGERS


# ─── Определение типа файла ───────────────────────────────────────────────────

def detect_file_type(filename: str) -> str:
    """Возвращает тип файла: 'code' | 'image' | 'document' | 'archive' | 'other'"""
    ext = Path(filename).suffix.lower()
    if ext in ('.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs', '.rb', '.php'):
        return 'code'
    if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'):
        return 'image'
    if ext in ('.pdf', '.docx', '.doc', '.xlsx', '.xls', '.txt', '.md', '.csv'):
        return 'document'
    if ext in ('.zip', '.tar', '.gz', '.rar', '.7z'):
        return 'archive'
    return 'other'


# ─── Объект сессии ───────────────────────────────────────────────────────────

@dataclass
class AgentSession:
    chat_id: int
    task: str = ""
    stage: str = STAGE_IDLE
    files: List[Dict] = field(default_factory=list)
    output_dir: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.output_dir:
            self.output_dir = tempfile.mkdtemp(prefix=f"agent_{self.chat_id}_")
        os.makedirs(self.output_dir, exist_ok=True)

    def add_file(self, path: str, name: str = '', ftype: str = '') -> None:
        """Добавляет файл в контекст сессии."""
        if not name:
            name = os.path.basename(path)
        if not ftype:
            ftype = detect_file_type(name)
        self.files.append({'path': path, 'name': name, 'type': ftype})
        self.touch()
        logger.debug("File added to session %d: %s", self.chat_id, name)

    def touch(self) -> None:
        """Обновляет timestamp."""
        self.updated_at = time.time()

    @property
    def file_paths(self) -> List[str]:
        return [f['path'] for f in self.files]


# ─── Хранилище сессий ────────────────────────────────────────────────────────

_sessions: Dict[int, AgentSession] = {}


def create_session(chat_id) -> AgentSession:
    """Создаёт новую агент-сессию."""
    cid = int(chat_id)
    sess = AgentSession(chat_id=cid)
    _sessions[cid] = sess
    logger.info("AgentSession created: chat_id=%s output_dir=%s", cid, sess.output_dir)
    return sess


def get_session(chat_id) -> Optional[AgentSession]:
    """Возвращает сессию или None."""
    return _sessions.get(int(chat_id))


def close_session(chat_id) -> None:
    """Закрывает и удаляет сессию."""
    cid = int(chat_id)
    sess = _sessions.pop(cid, None)
    if sess:
        sess.stage = STAGE_CANCELLED
        logger.info("AgentSession closed: chat_id=%s", cid)


def has_active_session(chat_id) -> bool:
    """True если есть активная сессия (не idle и не cancelled)."""
    sess = _sessions.get(int(chat_id))
    return bool(sess and sess.stage not in (STAGE_IDLE, STAGE_CANCELLED, STAGE_DONE))


# ─── Анализ задачи ────────────────────────────────────────────────────────────

def analyze_task(sess: AgentSession, on_status: Callable = None) -> Dict:
    """
    Анализирует задачу: определяет тип, необходимые инструменты, риски.
    Возвращает dict с результатами анализа.
    """
    if on_status:
        on_status("🧠 Анализирую задачу...")

    try:
        from agent_utils import detect_task_type
        task_type = detect_task_type(sess.task)
    except Exception:
        task_type = 'script'

    analysis = {
        'task_type': task_type,
        'has_files': len(sess.files) > 0,
        'file_types': list({f['type'] for f in sess.files}),
        'estimated_steps': 3 if task_type == 'project' else 2,
    }

    if on_status:
        on_status(f"📋 Тип: {task_type}, файлов: {len(sess.files)}")

    return analysis


# ─── Выполнение pipeline ─────────────────────────────────────────────────────

def execute_pipeline(
    sess: AgentSession,
    on_status: Callable = None,
    llm_caller: Callable = None,
) -> Dict[str, Any]:
    """
    Синхронное выполнение задачи из сессии.

    Аргументы:
        sess: AgentSession с заполненными .task и .files
        on_status: функция для статус-сообщений (text) -> None
        llm_caller: callable(prompt, system, max_tokens) -> str

    Возвращает:
        {
          'ok': bool,
          'artifacts': [{'path': str, 'name': str}],
          'zip_path': str | None,
          'errors': [str],
          'text': str,
        }
    """
    if on_status is None:
        on_status = lambda m: None

    sess.stage = STAGE_EXECUTING
    sess.touch()

    result: Dict[str, Any] = {
        'ok': False,
        'artifacts': [],
        'zip_path': None,
        'errors': [],
        'text': '',
    }

    workspace = Path(sess.output_dir)

    try:
        on_status(f"🚀 Запускаю: {sess.task[:80]}...")

        # Передаём файлы сессии в code_agent_run
        def _on_status(m): on_status(m)

        # Используем code_agent_run из chat_agent
        from chat_agent import code_agent_run
        agent_result = code_agent_run(
            sess.chat_id,
            sess.task,
            on_status=_on_status,
        )

        result['ok'] = agent_result.get('success', False)
        result['errors'] = agent_result.get('errors', [])
        result['text'] = agent_result.get('text', '')

        # Собираем артефакты
        for fp in agent_result.get('files', []):
            if os.path.exists(str(fp)):
                result['artifacts'].append({
                    'path': str(fp),
                    'name': os.path.basename(str(fp)),
                })

        if agent_result.get('zip_path') and os.path.exists(str(agent_result['zip_path'])):
            result['zip_path'] = str(agent_result['zip_path'])

        # Если zip не создан — создаём сами
        if not result['zip_path']:
            zip_path = _pack_workspace(workspace, sess.chat_id)
            if zip_path:
                result['zip_path'] = zip_path
                result['artifacts'].append({
                    'path': zip_path,
                    'name': os.path.basename(zip_path),
                })

    except Exception as exc:
        logger.exception("execute_pipeline error for chat %d: %s", sess.chat_id, exc)
        result['errors'].append(str(exc))
        result['ok'] = False
        # Пытаемся собрать хоть что-то
        try:
            _write_error_output(workspace, str(exc))
            zip_path = _pack_workspace(workspace, sess.chat_id)
            if zip_path:
                result['zip_path'] = zip_path
        except Exception:
            pass

    finally:
        sess.stage = STAGE_DONE
        sess.touch()
        on_status("✅ Готово" if result['ok'] else "⚠️ Завершено с ошибками")

    return result


# ─── Вспомогательные ─────────────────────────────────────────────────────────

def _pack_workspace(workspace: Path, chat_id) -> Optional[str]:
    """Упаковывает workspace в zip. Возвращает путь или None."""
    try:
        from agent_utils import pack_artifacts
        zp = pack_artifacts(workspace, zip_name=f"result_{chat_id}.zip")
        return str(zp)
    except Exception:
        pass
    try:
        files = [p for p in workspace.rglob("*") if p.is_file() and "__pycache__" not in str(p)]
        if not files:
            return None
        zip_path = workspace.parent / f"result_{chat_id}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fp in files:
                zf.write(fp, fp.relative_to(workspace.parent))
        return str(zip_path)
    except Exception as e:
        logger.error("_pack_workspace error: %s", e)
        return None


def _write_error_output(workspace: Path, error: str) -> None:
    try:
        from agent_utils import save_output
        save_output(workspace, stderr=error)
    except Exception:
        (workspace / "output.txt").write_text(f"ERROR:\n{error}", encoding="utf-8")


# ─── pipeline.py совместимость ────────────────────────────────────────────────
# bot.py строки 329-332: from pipeline import run_pipeline
# Оригинальный run_pipeline обрабатывал новости (возвращал int).
# Добавим в pipeline.py алиас — здесь даём заглушку на случай
# если кто-то импортирует из agent_session.

def run_pipeline_news() -> int:
    """Заглушка для совместимости. Оригинальный run_pipeline обрабатывал новости."""
    try:
        from pipeline import run_pipeline as _rp
        return _rp() or 0
    except Exception:
        return 0
