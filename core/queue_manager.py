"""
core/queue_manager.py — Task Queue
Priority queue with SQLite persistence, status tracking, retry logic.
"""
from __future__ import annotations
import uuid, time, json, sqlite3, threading, os
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Dict
from pathlib import Path
from queue import PriorityQueue

import config
from core.db_manager import TASKS_DB

DB_PATH = TASKS_DB


@dataclass
class Task:
    chat_id:    int = 0
    text:       str = ""
    files:      list = field(default_factory=list)
    agent:      str = "pythia"
    mode:       str = "auto"
    priority:   int = 5
    on_status:  Optional[Callable] = None
    task_id:    str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status:     str = "pending"     # pending → running → done → error → cancelled
    created_at: float = field(default_factory=time.time)
    started_at: float = 0
    finished_at: float = 0
    result:     Optional[dict] = None
    error:      str = ""
    retries:    int = 0
    max_retries: int = 2

    def __lt__(self, other):
        return self.priority > other.priority  # higher priority first


class TaskQueue:
    """Thread-safe priority queue with SQLite persistence."""

    def __init__(self):
        self._q = PriorityQueue()
        self._tasks: Dict[str, Task] = {}
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        with sqlite3.connect(str(DB_PATH)) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY, chat_id INTEGER, text TEXT,
                agent TEXT, mode TEXT, priority INTEGER, status TEXT,
                created_at REAL, started_at REAL, finished_at REAL,
                result TEXT, error TEXT, retries INTEGER
            )""")
            c.commit()

    def push(self, task: Task) -> str:
        with self._lock:
            self._tasks[task.task_id] = task
            self._q.put(task)
            self._persist(task)
        return task.task_id

    def pop(self, timeout: float = 1.0) -> Optional[Task]:
        try:
            task = self._q.get(timeout=timeout)
            with self._lock:
                task.status = "running"
                task.started_at = time.time()
                self._persist(task)
            return task
        except Exception:
            return None

    def complete(self, task_id: str, result: dict = None, error: str = ""):
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = "error" if error else "done"
                task.finished_at = time.time()
                task.result = result
                task.error = error
                self._persist(task)

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status in ("pending", "running"):
                task.status = "cancelled"
                task.finished_at = time.time()
                self._persist(task)
                return True
        return False

    def retry(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.retries < task.max_retries:
                task.retries += 1
                task.status = "pending"
                task.error = ""
                self._q.put(task)
                self._persist(task)
                return True
        return False

    def get(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def list_tasks(self, status: str = None, limit: int = 50) -> List[dict]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return [
            {"task_id": t.task_id, "chat_id": t.chat_id, "agent": t.agent,
             "mode": t.mode, "status": t.status, "text": t.text[:80],
             "created": t.created_at, "duration": (t.finished_at - t.started_at) if t.finished_at else 0,
             "error": t.error[:100]}
            for t in tasks[:limit]
        ]

    def stats(self) -> dict:
        tasks = list(self._tasks.values())
        return {
            "total": len(tasks),
            "pending": sum(1 for t in tasks if t.status == "pending"),
            "running": sum(1 for t in tasks if t.status == "running"),
            "done": sum(1 for t in tasks if t.status == "done"),
            "error": sum(1 for t in tasks if t.status == "error"),
            "queue_size": self._q.qsize(),
        }

    def _persist(self, task: Task):
        try:
            with sqlite3.connect(str(DB_PATH)) as c:
                c.execute("""INSERT OR REPLACE INTO tasks
                    (task_id,chat_id,text,agent,mode,priority,status,
                     created_at,started_at,finished_at,result,error,retries)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (task.task_id, task.chat_id, task.text[:500], task.agent,
                     task.mode, task.priority, task.status,
                     task.created_at, task.started_at, task.finished_at,
                     json.dumps(task.result, ensure_ascii=False, default=str) if task.result else None,
                     task.error, task.retries))
                c.commit()
        except Exception:
            pass

    def cancel_all(self) -> int:
        """Cancel all pending/running tasks."""
        cnt = 0
        with self._lock:
            for t in self._tasks.values():
                if t.status in ("pending", "running"):
                    t.status = "cancelled"
                    t.finished_at = time.time()
                    self._persist(t)
                    cnt += 1
        return cnt
