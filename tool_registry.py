"""
BlackBugsAI — Tool Registry (Marketplace Core)
Каждый инструмент: name, description, schema, permissions, cost, sandbox_level
"""
from __future__ import annotations
import time, json, threading
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Optional
from enum import IntEnum

class SandboxLevel(IntEnum):
    NONE      = 0   # без изоляции (только для admin/owner)
    SAFE      = 1   # только чтение, нет сети
    STANDARD  = 2   # ограниченная сеть, ограниченная ФС
    FULL      = 3   # полная изоляция Docker

class ToolPerm(IntEnum):
    ALL    = 0   # все пользователи
    VIP    = 1   # vip+
    ADMIN  = 2   # admin+
    OWNER  = 3   # только owner

@dataclass
class ToolSpec:
    name:          str
    description:   str
    category:      str                     # media | code | system | network | productivity | bot
    fn:            Callable                # функция-обработчик
    input_schema:  dict      = field(default_factory=dict)
    output_schema: dict      = field(default_factory=dict)
    permission:    ToolPerm  = ToolPerm.ALL
    sandbox:       SandboxLevel = SandboxLevel.STANDARD
    timeout:       int       = 60          # секунд
    cost:          int       = 0           # условных кредитов
    tags:          list      = field(default_factory=list)
    enabled:       bool      = True
    # Статистика
    calls_total:   int       = 0
    calls_ok:      int       = 0
    calls_fail:    int       = 0
    last_used:     float     = 0.0

    @property
    def stability(self) -> float:
        """Рейтинг стабильности 0-100%"""
        if self.calls_total == 0: return 100.0
        return round(self.calls_ok / self.calls_total * 100, 1)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop('fn')
        d['permission'] = self.permission.name
        d['sandbox'] = self.sandbox.name
        d['stability'] = self.stability
        return d


class ToolRegistry:
    """Реестр инструментов — синглтон"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._tools: dict[str, ToolSpec] = {}
                    cls._instance._run_log: list[dict] = []
        return cls._instance

    def register(self, spec: ToolSpec):
        self._tools[spec.name] = spec

    def get(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def all(self, category: str = None, enabled_only: bool = True) -> list[ToolSpec]:
        tools = list(self._tools.values())
        if enabled_only: tools = [t for t in tools if t.enabled]
        if category:     tools = [t for t in tools if t.category == category]
        return sorted(tools, key=lambda t: t.name)

    def categories(self) -> list[str]:
        return sorted(set(t.category for t in self._tools.values()))

    def execute(self, name: str, args: Any,
                chat_id: str = None,
                on_status: Callable = None,
                user_role: str = 'user') -> tuple[bool, str]:
        """Выполнить инструмент с логированием и проверкой прав."""
        spec = self.get(name)
        if not spec:
            return False, f"❌ Инструмент '{name}' не найден"
        if not spec.enabled:
            return False, f"⏸ Инструмент '{name}' отключён"

        # Проверка прав
        role_order = ['user','vip','admin','owner']
        user_level = role_order.index(user_role) if user_role in role_order else 0
        if user_level < int(spec.permission):
            return False, f"🚫 Нет доступа к '{name}' (требуется {spec.permission.name})"

        start = time.time()
        spec.calls_total += 1
        spec.last_used = start

        entry = {
            'tool': name, 'chat_id': str(chat_id or ''),
            'ts': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'args_preview': str(args)[:100],
        }

        try:
            result = spec.fn(args, chat_id=chat_id, on_status=on_status)
            elapsed = round(time.time() - start, 2)
            spec.calls_ok += 1
            entry.update({'ok': True, 'elapsed': elapsed, 'result': str(result)[:200]})
            self._run_log.append(entry)
            if len(self._run_log) > 2000: self._run_log.pop(0)
            return True, str(result)
        except Exception as e:
            import traceback
            spec.calls_fail += 1
            err = f"❌ {name}: {e}\n{traceback.format_exc()[-300:]}"
            entry.update({'ok': False, 'error': str(e)[:200]})
            self._run_log.append(entry)
            if len(self._run_log) > 2000: self._run_log.pop(0)
            return False, err

    def run_log(self, n: int = 50) -> list[dict]:
        return self._run_log[-n:]

    def stats(self) -> dict:
        tools = list(self._tools.values())
        return {
            'total': len(tools),
            'enabled': sum(1 for t in tools if t.enabled),
            'categories': self.categories(),
            'calls_today': len([l for l in self._run_log
                                 if l['ts'][:10] == time.strftime('%Y-%m-%d')]),
        }


# Глобальный реестр
registry = ToolRegistry()


def tool(name: str, description: str, category: str = 'general', **kwargs):
    """Декоратор для регистрации инструмента."""
    def decorator(fn: Callable):
        spec = ToolSpec(name=name, description=description,
                        category=category, fn=fn, **kwargs)
        registry.register(spec)
        return fn
    return decorator
