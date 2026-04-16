"""
BlackBugsAI Core Architecture v3.0

Pipeline: User → Bot → Gateway → Queue → Workers → Agents → Tools → Memory → DB
                                    ↓
                                 Observer (SMITH)
                                    ↓
                                 Admin Panel

NOTE: No eager imports here — each module imports exactly what it needs.
      Eager package-level imports cause cascade failures when any one
      dependency (e.g. config, dotenv, bcrypt) is unavailable at import time.
      Use direct submodule imports instead:
        from core.gateway      import Gateway
        from core.queue_manager import TaskQueue, Task
        from core import tool_registry as TR   # submodule access works fine
"""

__all__ = [
    'Gateway', 'TaskQueue', 'Task', 'WorkerPool',
    'AgentBase', 'AgentResult', 'ToolRegistry',
    'MemoryStore', 'Observer',
]
