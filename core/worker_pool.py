"""
core/worker_pool.py — Worker Pool
Thread pool: pulls Tasks from Queue → instantiates Agent → runs → reports result.
"""
from __future__ import annotations
import threading, time, traceback, os, signal
from typing import Optional, Callable, Dict
from core.queue_manager import TaskQueue, Task

MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "4"))


class WorkerPool:
    """Thread pool that processes tasks from the queue."""

    def __init__(self, queue: TaskQueue, agent_factory: Callable,
                 observer=None, max_workers: int = MAX_WORKERS):
        self._queue = queue
        self._factory = agent_factory  # (agent_name, mode) → AgentBase instance
        self._observer = observer
        self._max = max_workers
        self._workers: Dict[str, threading.Thread] = {}
        self._active_tasks: Dict[str, Task] = {}
        self._running = False
        self._lock = threading.Lock()

    def start(self):
        if self._running:
            return
        self._running = True
        for i in range(self._max):
            t = threading.Thread(target=self._worker_loop, daemon=True,
                                 name=f"worker-{i}")
            t.start()
            self._workers[f"worker-{i}"] = t
        print(f"  ⚙️ WorkerPool: {self._max} workers started", flush=True)

    def stop(self):
        self._running = False

    def _worker_loop(self):
        name = threading.current_thread().name
        while self._running:
            task = self._queue.pop(timeout=1.0)
            if not task:
                continue

            with self._lock:
                self._active_tasks[task.task_id] = task

            try:
                if self._observer:
                    self._observer.on_task_start(task)

                # Create agent instance
                agent = self._factory(task.agent, task.mode)
                if not agent:
                    raise RuntimeError(f"Unknown agent: {task.agent}")

                # Run agent
                result = agent.execute(
                    task=task.text,
                    chat_id=task.chat_id,
                    files=task.files,
                    mode=task.mode,
                    on_status=task.on_status,
                )

                # Complete
                self._queue.complete(task.task_id, result=result.to_dict())

                if self._observer:
                    self._observer.on_task_done(task, result)

            except Exception as exc:
                err = traceback.format_exc()
                self._queue.complete(task.task_id, error=str(exc))

                if self._observer:
                    self._observer.on_task_error(task, err)

                # Retry logic
                if task.retries < task.max_retries:
                    self._queue.retry(task.task_id)

            finally:
                with self._lock:
                    self._active_tasks.pop(task.task_id, None)

    def active_tasks(self) -> list:
        with self._lock:
            return [
                {"task_id": t.task_id, "agent": t.agent, "chat_id": t.chat_id,
                 "text": t.text[:60], "running_for": time.time() - t.started_at}
                for t in self._active_tasks.values()
            ]

    def kill_all(self) -> int:
        """Cancel all active + pending tasks."""
        cnt = self._queue.cancel_all()
        # Kill sandbox child processes
        killed = 0
        try:
            from pathlib import Path
            for p in Path("/proc").iterdir():
                if not p.name.isdigit():
                    continue
                try:
                    cmd = (p / "cmdline").read_bytes().decode('utf-8', errors='replace')
                    if '_runner.py' in cmd or '_sandbox_' in cmd:
                        os.kill(int(p.name), signal.SIGKILL)
                        killed += 1
                except Exception:
                    pass
        except Exception:
            pass
        return cnt + killed

    def stats(self) -> dict:
        return {
            "workers": self._max,
            "running": self._running,
            "active_tasks": len(self._active_tasks),
            **self._queue.stats(),
        }
