"""
core/tools/registry.py — Реестр инструментов AI-агента.

Каждый инструмент:
  - name: строка-идентификатор
  - description: что делает (для LLM)
  - execute(user_id, args, session) → str результат

Агент может:
  1. Использовать существующий инструмент
  2. Написать код и запустить в sandbox (CodeTool)
  3. Создать нового бота (BotFactory)
  4. Вернуть инструкцию если ничего не подходит
"""

import logging
from typing import Dict, Callable, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger('tools')


@dataclass
class ToolDef:
    name:        str
    description: str
    examples:    List[str]
    execute:     Callable


class ToolRegistry:
    """Реестр всех доступных инструментов."""

    def __init__(self):
        self._tools: Dict[str, ToolDef] = {}

    def register(self, name: str, description: str,
                 examples: List[str], fn: Callable):
        self._tools[name] = ToolDef(
            name=name, description=description,
            examples=examples, execute=fn
        )
        logger.debug(f'[tools] Зарегистрирован: {name}')

    def get(self, name: str) -> Optional[ToolDef]:
        return self._tools.get(name)

    def all_tools(self) -> List[ToolDef]:
        return list(self._tools.values())

    def tools_prompt(self) -> str:
        """Описание всех инструментов для системного промпта агента."""
        lines = ["Доступные инструменты:"]
        for t in self._tools.values():
            ex = '; '.join(t.examples[:2])
            lines.append(f"  - {t.name}: {t.description} (пример: {ex})")
        return '\n'.join(lines)

    def tool_names(self) -> List[str]:
        return list(self._tools.keys())


# Глобальный реестр
registry = ToolRegistry()
