"""
core/memory_store.py — Unified Memory Store
Wraps agent_memory.py for cross-agent memory access.
"""
from __future__ import annotations
from typing import Optional


class MemoryStore:
    """Static interface to agent memory — all agents share this."""

    @staticmethod
    def build_context(chat_id: str, task: str) -> str:
        try:
            from agent_memory import AgentMemory
            return AgentMemory(chat_id).build_context(task)
        except Exception:
            return ""

    @staticmethod
    def after_task(chat_id: str, task: str, tools_used: list,
                   result: str, status: str, duration: float):
        try:
            from agent_memory import AgentMemory
            AgentMemory(chat_id).after_task(
                task=task, tools_used=tools_used,
                result=result, status=status, duration=duration)
        except Exception:
            pass

    @staticmethod
    def get_user_memory(chat_id: str, key: str) -> Optional[str]:
        try:
            from agent_memory import get_user_memory
            return get_user_memory(chat_id, key)
        except Exception:
            return None

    @staticmethod
    def set_user_memory(chat_id: str, key: str, value: str):
        try:
            from agent_memory import set_user_memory
            set_user_memory(chat_id, key, value)
        except Exception:
            pass
