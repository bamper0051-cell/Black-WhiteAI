"""
core/gateway.py — Message Gateway
Routes: User message → detect agent/mode → create Task → push to Queue
"""
from __future__ import annotations
import re, time, os
from typing import Optional, Callable, Dict, List
from dataclasses import dataclass

# Lazy imports to avoid circular deps
_queue = None
_observer = None


@dataclass
class RouteResult:
    agent: str
    mode: str
    priority: int = 5
    reason: str = ""


# ── Keywords for agent detection ──────────────────────────────────────────────

_AGENT_KEYWORDS = {
    "neo":      (["agent neo", "нео", "/neo"], 10),
    "matrix":   (["agent matrix", "матрикс", "/matrix", "pentest", "пентест", "nmap", "nuclei", "sqlmap"], 10),
    "smith":    (["agent smith", "смит", "/smith", "агент_смит"], 10),
    "tanker":   (["tanker", "танкер", "/tanker", "red team", "атака"], 8),
    "anderson": (["anderson", "андерсон", "/anderson", "vuln", "уязвимост"], 8),
    "pythia":   (["pythia", "пифия", "/pythia"], 8),
    "operator": (["operator", "оператор", "/operator", "оркестр"], 9),
    # morpheus is in ALLIANCE_REGISTRY but NOT yet in agents/ AGENT_MAP.
    # Keyword routing disabled to prevent Unknown agent errors in worker_pool.
    # Re-enable when agents/morpheus.py is registered.
    # "morpheus": (["morpheus", "морфеус", "/morpheus", "обучи", "объясни", "learn"], 7),
}

# Alliance: full agent registry for /alliance command
ALLIANCE_REGISTRY = {
    "neo":      {"emoji": "🟢", "name": "NEO",      "desc": "Автономный агент, self-tool gen, sandbox, OSINT",  "access": ["god", "owner"]},
    "matrix":   {"emoji": "🟥", "name": "MATRIX",   "desc": "Универсал: Coder + OSINT + Pentester + тулы",      "access": ["god", "owner"]},
    "smith":    {"emoji": "🕶",  "name": "SMITH",    "desc": "Генератор шаблонов, ботов, проектов",              "access": ["god", "owner", "adm"]},
    "pythia":   {"emoji": "💻", "name": "PYTHIA",   "desc": "Кодер: quick/project/review/sandbox/autofix",      "access": ["*"]},
    "anderson": {"emoji": "🔍", "name": "ANDERSON", "desc": "Анализ уязвимостей, code fix, VulnSage",           "access": ["*"]},
    "tanker":   {"emoji": "🚛", "name": "TANKER",   "desc": "Парсинг, веб-скрапинг, мониторинг",                "access": ["*"]},
    "operator": {"emoji": "🎛", "name": "OPERATOR", "desc": "Системные задачи, оркестрация, планирование",      "access": ["god", "owner"]},
    "morpheus": {"emoji": "🟣", "name": "MORPHEUS", "desc": "Обучение, объяснения, анализ данных",              "access": ["*"]},
}

_MODE_KEYWORDS = {
    "code":    ["код", "напиши", "скрипт", "python", "программ", "функци", "класс", "модуль"],
    "osint":   ["osint", "username", "sherlock", "профиль", "найди человека", "whois", "dns"],
    "pentest": ["сканируй", "scan", "nmap", "pentest", "пентест", "уязвимост", "exploit", "порт"],
    "project": ["проект", "project", "структур", "scaffold", "несколько файлов"],
    "review":  ["ревью", "review", "проверь код", "найди ошибки", "анализ кода"],
    "sandbox": ["запусти", "execute", "sandbox", "выполни"],
    "test":    ["тест", "test", "pytest", "coverage"],
}


class Gateway:
    """Routes incoming tasks to appropriate agent and queue."""

    def __init__(self, queue=None, observer=None):
        self._queue = queue
        self._observer = observer
        self._overrides: Dict[int, str] = {}  # chat_id → forced agent

    def set_agent(self, chat_id: int, agent: str):
        """Force specific agent for chat."""
        self._overrides[chat_id] = agent

    def clear_agent(self, chat_id: int):
        self._overrides.pop(chat_id, None)

    def route(self, chat_id: int, text: str, files: list = None,
              privilege: str = "user", forced_agent: str = "") -> RouteResult:
        """Detect which agent should handle this task."""
        text_lower = text.lower().strip()

        # 1. Explicit override
        if forced_agent:
            return RouteResult(agent=forced_agent, mode=self._detect_mode(text_lower),
                               reason="explicit")

        # 2. Chat-level override
        if chat_id in self._overrides:
            return RouteResult(agent=self._overrides[chat_id],
                               mode=self._detect_mode(text_lower), reason="session")

        # 3. Keyword detection
        best_agent = "pythia"  # default
        best_score = 0
        for agent, (keywords, priority) in _AGENT_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    if priority > best_score:
                        best_agent = agent
                        best_score = priority
                    break

        # 4. Access control
        restricted = {"neo": ["god", "owner"], "matrix": ["god", "owner"],
                      "smith": ["god", "owner", "adm"], "operator": ["god", "owner"]}
        if best_agent in restricted and privilege not in restricted[best_agent]:
            if privilege in ("vip", "adm"):
                best_agent = "pythia"
            else:
                best_agent = "tanker"  # public agent

        mode = self._detect_mode(text_lower)
        return RouteResult(agent=best_agent, mode=mode, priority=best_score or 5,
                           reason="auto")

    def _detect_mode(self, text: str) -> str:
        scores = {}
        for mode, keywords in _MODE_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    scores[mode] = scores.get(mode, 0) + 1
        if scores:
            return max(scores, key=scores.get)
        return "auto"

    def alliance_info(self, privilege: str = "user") -> List[dict]:
        """Return list of agents accessible to the given privilege level."""
        result = []
        for key, info in ALLIANCE_REGISTRY.items():
            allowed = info["access"]
            if "*" in allowed or privilege in allowed:
                result.append({"id": key, **info, "available": True})
            else:
                result.append({"id": key, **info, "available": False})
        return result

    def submit(self, chat_id: int, text: str, files: list = None,
               privilege: str = "user", forced_agent: str = "",
               on_status: Callable = None) -> Optional[str]:
        """Route and submit task to queue. Returns task_id."""
        route = self.route(chat_id, text, files, privilege, forced_agent)

        if self._queue:
            from core.queue_manager import Task
            task = Task(
                chat_id=chat_id, text=text, files=files or [],
                agent=route.agent, mode=route.mode,
                priority=route.priority, on_status=on_status,
            )
            self._queue.push(task)
            if self._observer:
                self._observer.on_task_submitted(task)
            return task.task_id
        return None
