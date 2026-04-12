"""
core/observer.py — Observer (SMITH pattern)
Monitors all agent activity: logging, security audit, auto-fix suggestions.
Feeds data to Admin Panel.
"""
from __future__ import annotations
import time, json, threading, sqlite3, os
from pathlib import Path
from typing import Optional, List, Dict
from collections import deque
import config

LOG_DB = Path(config.DATA_DIR) / "observer.db"
_MAX_BUFFER = 500


class Observer:
    """Singleton observer — watches all agent/task activity."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._events: deque = deque(maxlen=_MAX_BUFFER)
        self._stats = {
            "tasks_total": 0, "tasks_ok": 0, "tasks_error": 0,
            "tools_generated": 0, "agents_active": set(),
        }
        self._init_db()

    def _init_db(self):
        try:
            os.makedirs(os.path.dirname(LOG_DB), exist_ok=True)
            with sqlite3.connect(str(LOG_DB)) as c:
                c.execute("""CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL, type TEXT, agent TEXT, chat_id TEXT,
                    task TEXT, data TEXT
                )""")
                c.commit()
        except Exception:
            pass

    def _log(self, event_type: str, agent: str = "", chat_id: str = "",
             task: str = "", data: dict = None):
        event = {
            "ts": time.time(), "type": event_type, "agent": agent,
            "chat_id": str(chat_id), "task": task[:200],
            "data": data or {},
        }
        self._events.append(event)
        try:
            with sqlite3.connect(str(LOG_DB)) as c:
                c.execute("INSERT INTO events (ts,type,agent,chat_id,task,data) VALUES (?,?,?,?,?,?)",
                    (event["ts"], event_type, agent, str(chat_id), task[:200],
                     json.dumps(data or {}, ensure_ascii=False, default=str)))
                c.commit()
        except Exception:
            pass

    # ── Event handlers ────────────────────────────────────────────────────────

    def on_task_submitted(self, task):
        self._stats["tasks_total"] += 1
        self._stats["agents_active"].add(task.agent)
        self._log("submitted", task.agent, task.chat_id, task.text)

    def on_task_start(self, task):
        self._log("start", task.agent, task.chat_id, task.text)

    def on_task_done(self, task, result):
        self._stats["tasks_ok"] += 1
        self._stats["agents_active"].discard(task.agent)
        data = {"duration": result.duration, "mode": result.mode,
                "files": len(result.files), "tools_generated": result.generated_tools}
        if result.generated_tools:
            self._stats["tools_generated"] += len(result.generated_tools)
        self._log("done", task.agent, task.chat_id, task.text, data)

    def on_task_error(self, task, error: str):
        self._stats["tasks_error"] += 1
        self._stats["agents_active"].discard(task.agent)
        self._log("error", task.agent, task.chat_id, task.text, {"error": error[:500]})

    def on_tool_generated(self, tool_name: str, agent: str):
        self._stats["tools_generated"] += 1
        self._log("tool_gen", agent, data={"tool": tool_name})

    # ── Query ─────────────────────────────────────────────────────────────────

    def recent_events(self, limit: int = 50, event_type: str = None) -> List[dict]:
        events = list(self._events)
        if event_type:
            events = [e for e in events if e["type"] == event_type]
        return list(reversed(events[-limit:]))

    def get_stats(self) -> dict:
        return {
            "tasks_total": self._stats["tasks_total"],
            "tasks_ok": self._stats["tasks_ok"],
            "tasks_error": self._stats["tasks_error"],
            "tools_generated": self._stats["tools_generated"],
            "agents_active": list(self._stats["agents_active"]),
            "events_buffered": len(self._events),
        }

    def agent_history(self, agent: str, limit: int = 20) -> List[dict]:
        return [e for e in list(self._events) if e.get("agent") == agent][-limit:]
