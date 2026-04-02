"""
bootstrap.py — BlackBugsAI Platform Bootstrap v3.0
Initializes: Gateway → Queue → WorkerPool → Observer → Agents → Tools

Usage in bot.py:
    from bootstrap import platform
    platform.start()
    task_id = platform.submit(chat_id, text, files, privilege)
    platform.stop_all()
"""
from __future__ import annotations
import threading, time, os
from typing import Optional, Callable

import config


class Platform:
    """Main platform singleton — wires everything together."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._started = False
        return cls._instance

    def __init__(self):
        if self._started:
            return
        self._queue = None
        self._gateway = None
        self._pool = None
        self._observer = None

    def start(self):
        """Initialize and start all subsystems."""
        if self._started:
            return
        print("═══════════════════════════════════════════", flush=True)
        print("  BlackBugsAI Platform v3.0 — Starting...", flush=True)
        print("═══════════════════════════════════════════", flush=True)

        # 1. Observer
        from core.observer import Observer
        self._observer = Observer()
        print("  ✅ Observer", flush=True)

        # 2. Task Queue
        from core.queue_manager import TaskQueue
        self._queue = TaskQueue()
        print("  ✅ TaskQueue", flush=True)

        # 3. Gateway
        from core.gateway import Gateway
        self._gateway = Gateway(queue=self._queue, observer=self._observer)
        print("  ✅ Gateway", flush=True)

        # 4. Worker Pool
        from core.worker_pool import WorkerPool
        from agents import create_agent
        self._pool = WorkerPool(
            queue=self._queue,
            agent_factory=create_agent,
            observer=self._observer,
        )
        self._pool.start()
        print("  ✅ WorkerPool", flush=True)

        # 5. Tool warmup (background)
        def _warmup():
            time.sleep(3)
            try:
                from core.tool_registry import warmup
                r = warmup(on_status=lambda m: print(f"  {m}", flush=True))
                print(f"  ✅ Tools: +{r.get('registered',0)} registered", flush=True)
            except Exception as e:
                print(f"  ⚠️ Tool warmup: {e}", flush=True)
        threading.Thread(target=_warmup, daemon=True, name="warmup").start()

        self._started = True
        print("  ✅ Platform ready", flush=True)
        print("═══════════════════════════════════════════", flush=True)

    # ── Public API ────────────────────────────────────────────────────────────

    def submit(self, chat_id: int, text: str, files: list = None,
               privilege: str = "user", forced_agent: str = "",
               on_status: Callable = None) -> Optional[str]:
        """Submit task through gateway → queue → workers."""
        if not self._started:
            self.start()
        return self._gateway.submit(
            chat_id, text, files, privilege, forced_agent, on_status)

    def route(self, chat_id: int, text: str, privilege: str = "user"):
        """Just detect which agent would handle this (no execution)."""
        if self._gateway:
            return self._gateway.route(chat_id, text, privilege=privilege)
        return None

    def set_agent(self, chat_id: int, agent: str):
        """Force specific agent for a chat session."""
        if self._gateway:
            self._gateway.set_agent(chat_id, agent)

    def clear_agent(self, chat_id: int):
        if self._gateway:
            self._gateway.clear_agent(chat_id)

    def stop_all(self) -> int:
        """Stop all running tasks and processes."""
        killed = 0
        if self._pool:
            killed += self._pool.kill_all()
        if self._queue:
            killed += self._queue.cancel_all()
        return killed

    # ── Getters for admin panel ───────────────────────────────────────────────

    @property
    def queue(self):
        return self._queue

    @property
    def gateway(self):
        return self._gateway

    @property
    def pool(self):
        return self._pool

    @property
    def observer(self):
        return self._observer

    def stats(self) -> dict:
        """Full platform stats for admin panel."""
        from core.tool_registry import stats as tool_stats
        from agents import AGENT_INFO
        s = {"platform": "v3.0", "started": self._started}
        if self._pool:
            s["workers"] = self._pool.stats()
        if self._queue:
            s["queue"] = self._queue.stats()
        if self._observer:
            s["observer"] = self._observer.get_stats()
        s["tools"] = tool_stats()
        s["agents"] = AGENT_INFO
        return s


# Singleton
platform = Platform()
