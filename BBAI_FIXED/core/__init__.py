"""
BlackBugsAI Core Architecture v3.0

Pipeline: User → Bot → Gateway → Queue → Workers → Agents → Tools → Memory → DB
                                    ↓
                                 Observer (SMITH)
                                    ↓
                                 Admin Panel
"""
from core.gateway import Gateway
from core.queue_manager import TaskQueue, Task
from core.worker_pool import WorkerPool
from core.agent_base import AgentBase, AgentResult
from core.tool_registry import ToolRegistry
from core.memory_store import MemoryStore
from core.observer import Observer

__all__ = [
    'Gateway', 'TaskQueue', 'Task', 'WorkerPool',
    'AgentBase', 'AgentResult', 'ToolRegistry',
    'MemoryStore', 'Observer',
]
