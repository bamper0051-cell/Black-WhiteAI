"""
core/agent_brain.py — Agent Intelligence Layer
Делает агентов умнее через 5 механизмов:

1. REFLEXION    — агент критикует свой ответ и переделывает если плохо
2. DELEGATION   — агент может вызвать другого агента как инструмент
3. GRAPH        — выполнение через граф состояний с ветвлением и памятью
4. FEEDBACK     — сбор оценок пользователя, агент учится избегать ошибок
5. LINTING      — агент-кодер прогоняет ruff перед отдачей кода

Подключается к AgentBase без переписывания существующего кода:
    from core.agent_brain import BrainMixin
    class AgentNeo(BrainMixin, AgentBase):
        ...

Или оборачивает execute() напрямую:
    result = Brain.run(agent, task, chat_id, ...)
"""
from __future__ import annotations

import ast
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import config
from core.db_manager import BRAIN_DB

# ── Хранилище обратной связи ──────────────────────────────────────────────────
_BRAIN_DB = BRAIN_DB


def _db():
    os.makedirs(_BRAIN_DB.parent, exist_ok=True)
    conn = sqlite3.connect(str(_BRAIN_DB))
    conn.execute("""CREATE TABLE IF NOT EXISTS feedback (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        ts        REAL,
        chat_id   TEXT,
        agent     TEXT,
        task      TEXT,
        answer    TEXT,
        score     INTEGER,   -- 1=👍  -1=👎  0=нейтрально
        comment   TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS reflexion_log (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        ts        REAL,
        agent     TEXT,
        task      TEXT,
        attempt   INTEGER,
        critique  TEXT,
        improved  INTEGER    -- 0/1
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS agent_graph_runs (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        ts        REAL,
        agent     TEXT,
        chat_id   TEXT,
        task      TEXT,
        nodes     TEXT,      -- JSON list of visited nodes
        final_ok  INTEGER
    )""")
    conn.commit()
    return conn


# ══════════════════════════════════════════════════════════════════════════════
#  1. REFLEXION — самокритика и улучшение ответа
# ══════════════════════════════════════════════════════════════════════════════

REFLEXION_CRITIC_SYSTEM = """Ты — строгий критик AI-агента.
Тебе дают задачу и ответ агента. Оцени ответ по критериям:
1. Полнота (все требования выполнены?)
2. Корректность (нет логических ошибок?)
3. Качество кода (если есть код — синтаксис верный, нет мусора?)
4. Ясность (ответ понятен пользователю?)

Верни JSON:
{
  "score": 1-10,
  "issues": ["список проблем"],
  "verdict": "ok" | "retry",
  "improvement_hint": "что исправить"
}

Если score >= 7 — verdict = "ok".
Отвечай ТОЛЬКО JSON, без markdown.
"""

REFLEXION_IMPROVE_SYSTEM = """Ты AI-агент. Улучши свой предыдущий ответ на основе критики.
Устрани все указанные проблемы. Будь конкретен и лаконичен.
"""


class Reflexion:
    """
    Reflexion loop: execute → critique → improve → repeat.

    Пример:
        result = Reflexion.run(
            llm_fn=agent.llm,
            task="напиши сортировку пузырьком",
            initial_answer="...",
            max_rounds=2,
        )
    """

    @staticmethod
    def critique(llm_fn: Callable, task: str, answer: str) -> dict:
        """Запросить LLM-критику ответа."""
        prompt = (
            f"ЗАДАЧА:\n{task[:500]}\n\n"
            f"ОТВЕТ АГЕНТА:\n{answer[:2000]}\n\n"
            f"Оцени ответ и верни JSON."
        )
        raw = llm_fn(prompt, REFLEXION_CRITIC_SYSTEM, max_tokens=800)
        raw = re.sub(r"```json\s*|\s*```", "", raw).strip()
        try:
            return json.loads(raw)
        except Exception:
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group())
                except Exception:
                    pass
        return {"score": 5, "issues": [], "verdict": "ok", "improvement_hint": ""}

    @staticmethod
    def improve(llm_fn: Callable, task: str, answer: str,
                critique: dict, system: str = "") -> str:
        """Попросить LLM улучшить ответ на основе критики."""
        hint = critique.get("improvement_hint", "")
        issues = "\n".join(f"- {i}" for i in critique.get("issues", []))
        prompt = (
            f"ИСХОДНАЯ ЗАДАЧА:\n{task[:400]}\n\n"
            f"МОЙ ПРЕДЫДУЩИЙ ОТВЕТ:\n{answer[:1500]}\n\n"
            f"ПРОБЛЕМЫ (score={critique.get('score')}/10):\n{issues}\n\n"
            f"ЧТО ИСПРАВИТЬ: {hint}\n\n"
            f"Напиши улучшенную версию:"
        )
        return llm_fn(prompt, system or REFLEXION_IMPROVE_SYSTEM, max_tokens=3000)

    @classmethod
    def run(
        cls,
        llm_fn: Callable,
        task: str,
        initial_answer: str,
        agent_name: str = "agent",
        system: str = "",
        max_rounds: int = 2,
        min_score: int = 7,
        on_status: Optional[Callable] = None,
    ) -> Tuple[str, List[dict]]:
        """
        Запускает reflexion loop.
        Returns: (final_answer, critique_history)
        """
        answer = initial_answer
        history = []

        for attempt in range(max_rounds):
            if on_status:
                on_status(f"🔍 Reflexion {attempt+1}/{max_rounds}: анализирую ответ...")

            critique = cls.critique(llm_fn, task, answer)
            score = critique.get("score", 5)
            verdict = critique.get("verdict", "ok")
            history.append({"attempt": attempt, "score": score, "critique": critique})

            # Логируем в БД
            try:
                with _db() as db:
                    db.execute(
                        "INSERT INTO reflexion_log (ts,agent,task,attempt,critique,improved) VALUES (?,?,?,?,?,?)",
                        (time.time(), agent_name, task[:200], attempt,
                         json.dumps(critique, ensure_ascii=False), 0)
                    )
            except Exception:
                pass

            if verdict == "ok" or score >= min_score:
                if on_status:
                    on_status(f"✅ Reflexion: ответ принят (score={score}/10)")
                break

            if on_status:
                issues = critique.get("issues", [])
                on_status(f"⚠️ Reflexion score={score}/10 — улучшаю: {'; '.join(issues[:2])}")

            improved = cls.improve(llm_fn, task, answer, critique, system)
            if improved and len(improved) > 50:
                answer = improved
                # Обновляем improved=1 в логе
                try:
                    with _db() as db:
                        db.execute(
                            "UPDATE reflexion_log SET improved=1 WHERE agent=? AND attempt=? ORDER BY id DESC LIMIT 1",
                            (agent_name, attempt)
                        )
                except Exception:
                    pass

        return answer, history


# ══════════════════════════════════════════════════════════════════════════════
#  2. DELEGATION — агент вызывает другого агента
# ══════════════════════════════════════════════════════════════════════════════

class Delegation:
    """
    Позволяет агенту делегировать подзадачу другому агенту.

    Пример:
        result = Delegation.call(
            from_agent="neo",
            to_agent="matrix",
            subtask="просканируй порты 192.168.1.1",
            chat_id=chat_id,
        )
    """

    # Реестр делегирования: что умеет каждый агент
    AGENT_SKILLS = {
        "neo":      ["код", "python", "скрипт", "автоматизация", "github", "файл"],
        "matrix":   ["pentest", "nmap", "osint", "сканирование", "безопасность", "порт"],
        "smith":    ["анализ кода", "ревью", "autofix", "рефакторинг", "тест"],
        "morpheus": ["apt", "docker", "установи", "systemctl", "root", "сервер"],
        "anderson": ["уязвимост", "cve", "exploit", "патч"],
        "pythia":   ["анализ", "данные", "статистика", "предсказание"],
        "operator": ["оркестрация", "сложная задача", "несколько агентов"],
    }

    @classmethod
    def find_best_agent(cls, subtask: str, exclude: str = "") -> Optional[str]:
        """Определить лучшего агента для подзадачи по ключевым словам."""
        task_low = subtask.lower()
        scores: Dict[str, int] = {}
        for agent, skills in cls.AGENT_SKILLS.items():
            if agent == exclude:
                continue
            score = sum(1 for skill in skills if skill in task_low)
            if score > 0:
                scores[agent] = score
        return max(scores, key=scores.get) if scores else None

    @classmethod
    def call(
        cls,
        from_agent: str,
        to_agent: str,
        subtask: str,
        chat_id: int,
        files: list = None,
        on_status: Optional[Callable] = None,
    ) -> dict:
        """
        Вызвать агента to_agent с подзадачей.
        Returns: {"ok": bool, "answer": str, "files": list, "agent": str}
        """
        if on_status:
            on_status(f"🤝 {from_agent.upper()} → {to_agent.upper()}: делегирую подзадачу...")

        try:
            from agents import create_agent, AGENT_MAP
            if to_agent not in AGENT_MAP:
                return {"ok": False, "answer": f"Агент {to_agent} не найден", "files": [], "agent": to_agent}

            agent = create_agent(to_agent)
            if not agent:
                return {"ok": False, "answer": f"Не удалось создать {to_agent}", "files": [], "agent": to_agent}

            result = agent.execute(subtask, chat_id, files=files, on_status=on_status)
            return {
                "ok": result.ok,
                "answer": result.answer,
                "files": result.files,
                "agent": to_agent,
                "zip_path": result.zip_path,
            }
        except Exception as e:
            return {"ok": False, "answer": f"Ошибка делегирования: {e}", "files": [], "agent": to_agent}

    @classmethod
    def auto_delegate(
        cls,
        from_agent: str,
        task: str,
        chat_id: int,
        llm_fn: Callable,
        on_status: Optional[Callable] = None,
    ) -> Optional[dict]:
        """
        LLM решает нужно ли делегирование и кому.
        Returns: dict с результатом или None если делегирование не нужно.
        """
        # Сначала быстрая проверка по ключевым словам
        best = cls.find_best_agent(task, exclude=from_agent)
        if not best:
            return None

        # Проверяем через LLM нужно ли делегировать
        check_prompt = (
            f"Ты агент {from_agent.upper()}. Тебе пришла задача:\n{task[:300]}\n\n"
            f"Можешь ли ты решить её сам, или лучше делегировать агенту {best.upper()}?\n"
            f"Ответь ТОЛЬКО одним словом: 'сам' или 'делегировать'."
        )
        try:
            decision = llm_fn(check_prompt, max_tokens=10).strip().lower()
            if "делегировать" in decision or "delegat" in decision:
                if on_status:
                    on_status(f"🔀 Делегирую задачу агенту {best.upper()}...")
                return cls.call(from_agent, best, task, chat_id, on_status=on_status)
        except Exception:
            pass
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  3. GRAPH — граф состояний выполнения задачи
# ══════════════════════════════════════════════════════════════════════════════

class NodeStatus(Enum):
    PENDING  = "pending"
    RUNNING  = "running"
    DONE     = "done"
    FAILED   = "failed"
    SKIPPED  = "skipped"


@dataclass
class GraphNode:
    """Узел графа выполнения."""
    name:       str
    fn:         Callable                    # fn(state) -> state
    on_success: Optional[str] = None       # имя следующего узла
    on_failure: Optional[str] = None       # имя узла при ошибке
    condition:  Optional[Callable] = None  # condition(state) -> bool
    retry:      int = 0                    # кол-во повторов при ошибке
    status:     NodeStatus = field(default=NodeStatus.PENDING, init=False)
    output:     Any = field(default=None, init=False)
    error:      str = field(default="", init=False)


@dataclass
class GraphState:
    """Состояние графа — передаётся между узлами."""
    task:       str
    chat_id:    int
    agent:      str = ""
    answer:     str = ""
    files:      List[str] = field(default_factory=list)
    memory:     Dict[str, Any] = field(default_factory=dict)
    errors:     List[str] = field(default_factory=list)
    visited:    List[str] = field(default_factory=list)
    ok:         bool = True
    metadata:   Dict[str, Any] = field(default_factory=dict)


class AgentGraph:
    """
    Граф выполнения задачи.
    Узлы — этапы обработки. Рёбра — условные переходы.

    Пример:
        graph = AgentGraph("my_pipeline")
        graph.add_node(GraphNode("plan",    plan_fn,    on_success="execute"))
        graph.add_node(GraphNode("execute", execute_fn, on_success="reflect", on_failure="fix"))
        graph.add_node(GraphNode("reflect", reflect_fn, on_success="done"))
        graph.add_node(GraphNode("fix",     fix_fn,     on_success="execute"))
        graph.add_node(GraphNode("done",    done_fn))
        result = graph.run(state, start="plan")
    """

    def __init__(self, name: str = "graph"):
        self.name = name
        self._nodes: Dict[str, GraphNode] = {}
        self._on_status: Optional[Callable] = None

    def add_node(self, node: GraphNode) -> "AgentGraph":
        self._nodes[node.name] = node
        return self  # для chain: graph.add_node(...).add_node(...)

    def run(
        self,
        state: GraphState,
        start: str,
        on_status: Optional[Callable] = None,
        max_steps: int = 20,
    ) -> GraphState:
        """Запустить граф начиная с узла start."""
        self._on_status = on_status
        current = start
        steps = 0

        while current and steps < max_steps:
            node = self._nodes.get(current)
            if not node:
                state.errors.append(f"Узел {current!r} не найден в графе")
                state.ok = False
                break

            # Проверяем условие входа в узел
            if node.condition and not node.condition(state):
                if on_status:
                    on_status(f"⏭️ [{current}] пропускаю (условие не выполнено)")
                node.status = NodeStatus.SKIPPED
                current = node.on_success
                continue

            if on_status:
                on_status(f"▶️ [{current}] выполняю...")

            node.status = NodeStatus.RUNNING
            state.visited.append(current)

            # Выполняем с retry
            success = False
            for attempt in range(node.retry + 1):
                try:
                    new_state = node.fn(state)
                    if new_state is not None:
                        state = new_state
                    node.output = state.answer
                    node.status = NodeStatus.DONE
                    success = True
                    break
                except Exception as e:
                    node.error = str(e)
                    if attempt < node.retry:
                        if on_status:
                            on_status(f"⚠️ [{current}] retry {attempt+1}/{node.retry}: {e}")
                        time.sleep(0.5)

            if success:
                current = node.on_success
            else:
                node.status = NodeStatus.FAILED
                state.errors.append(f"[{current}] {node.error}")
                if on_status:
                    on_status(f"❌ [{current}] ошибка: {node.error[:100]}")
                current = node.on_failure
                if not current:
                    state.ok = False
                    break

            steps += 1

        # Логируем граф-ран
        try:
            with _db() as db:
                db.execute(
                    "INSERT INTO agent_graph_runs (ts,agent,chat_id,task,nodes,final_ok) VALUES (?,?,?,?,?,?)",
                    (time.time(), state.agent, str(state.chat_id),
                     state.task[:200], json.dumps(state.visited), int(state.ok))
                )
        except Exception:
            pass

        return state


# ══════════════════════════════════════════════════════════════════════════════
#  4. FEEDBACK — оценки пользователя, агент учится на ошибках
# ══════════════════════════════════════════════════════════════════════════════

class FeedbackStore:
    """
    Сбор и анализ оценок пользователя.
    Используется для:
    - отображения "рейтинга агентов" в админ-панели
    - формирования "anti-patterns" — чего агенту делать не стоит
    - персонализации ответов под конкретного пользователя
    """

    @staticmethod
    def save(chat_id: str, agent: str, task: str, answer: str,
             score: int, comment: str = "") -> bool:
        """Сохранить оценку. score: 1=👍, -1=👎, 0=нейтрально."""
        try:
            with _db() as db:
                db.execute(
                    "INSERT INTO feedback (ts,chat_id,agent,task,answer,score,comment) VALUES (?,?,?,?,?,?,?)",
                    (time.time(), str(chat_id), agent, task[:300],
                     answer[:1000], score, comment[:500])
                )
            return True
        except Exception:
            return False

    @staticmethod
    def get_agent_stats(agent: str) -> dict:
        """Статистика по агенту."""
        try:
            with _db() as db:
                rows = db.execute(
                    "SELECT score, COUNT(*) FROM feedback WHERE agent=? GROUP BY score",
                    (agent,)
                ).fetchall()
                stats = {"likes": 0, "dislikes": 0, "neutral": 0, "total": 0}
                for score, count in rows:
                    stats["total"] += count
                    if score == 1:
                        stats["likes"] = count
                    elif score == -1:
                        stats["dislikes"] = count
                    else:
                        stats["neutral"] = count
                stats["rating"] = (
                    round((stats["likes"] / stats["total"]) * 100)
                    if stats["total"] > 0 else 0
                )
                return stats
        except Exception:
            return {"likes": 0, "dislikes": 0, "neutral": 0, "total": 0, "rating": 0}

    @staticmethod
    def get_anti_patterns(agent: str, limit: int = 5) -> List[str]:
        """
        Получить паттерны плохих ответов (для инжекта в system prompt).
        Возвращает задачи с 👎 которых надо избегать.
        """
        try:
            with _db() as db:
                rows = db.execute(
                    "SELECT task, comment FROM feedback WHERE agent=? AND score=-1 ORDER BY ts DESC LIMIT ?",
                    (agent, limit)
                ).fetchall()
                patterns = []
                for task, comment in rows:
                    hint = f"Задача: '{task[:80]}'"
                    if comment:
                        hint += f" → проблема: {comment[:100]}"
                    patterns.append(hint)
                return patterns
        except Exception:
            return []

    @staticmethod
    def build_system_prompt_addon(agent: str) -> str:
        """
        Добавка к system prompt на основе накопленного фидбека.
        Инжектируется в начало каждого LLM-вызова.
        """
        anti = FeedbackStore.get_anti_patterns(agent)
        if not anti:
            return ""
        lines = "\n".join(f"  - {p}" for p in anti)
        return (
            f"\n⚠️ НА ОСНОВЕ ПРОШЛЫХ ОШИБОК — избегай следующих паттернов:\n{lines}\n"
        )

    @staticmethod
    def all_stats() -> List[dict]:
        """Статистика по всем агентам для админ-панели."""
        try:
            with _db() as db:
                agents = [r[0] for r in db.execute(
                    "SELECT DISTINCT agent FROM feedback"
                ).fetchall()]
                return [{"agent": a, **FeedbackStore.get_agent_stats(a)} for a in agents]
        except Exception:
            return []


# ══════════════════════════════════════════════════════════════════════════════
#  5. LINTING — ruff проверяет код агента перед отправкой
# ══════════════════════════════════════════════════════════════════════════════

class CodeLinter:
    """
    Запускает ruff на сгенерированном коде.
    Если есть ошибки — просит LLM исправить их.

    Пример:
        clean_code, issues = CodeLinter.lint_and_fix(llm_fn, code, task)
    """

    @staticmethod
    def _ensure_ruff() -> bool:
        """Убедиться что ruff установлен."""
        if subprocess.run(
            ["ruff", "--version"], capture_output=True
        ).returncode == 0:
            return True
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "ruff", "-q",
             "--break-system-packages"],
            capture_output=True, timeout=60
        )
        return result.returncode == 0

    @staticmethod
    def lint(code: str) -> Tuple[bool, List[str]]:
        """
        Прогнать ruff на коде.
        Returns: (ok, issues_list)
        """
        if not CodeLinter._ensure_ruff():
            # Fallback: ast.parse
            try:
                ast.parse(code)
                return True, []
            except SyntaxError as e:
                return False, [f"SyntaxError: {e}"]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                ["ruff", "check", tmp_path,
                 "--select", "E,F,W",   # errors, pyflakes, warnings
                 "--ignore", "E501",     # ignore line-too-long
                 "--output-format", "json"],
                capture_output=True, text=True, timeout=30
            )
            issues = []
            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    for item in data:
                        msg = item.get("message", "")
                        code_rule = item.get("code", "")
                        row = item.get("location", {}).get("row", "?")
                        issues.append(f"L{row} [{code_rule}]: {msg}")
                except json.JSONDecodeError:
                    pass
            return len(issues) == 0, issues
        except Exception as e:
            return True, []  # При ошибке ruff — не блокируем
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    @staticmethod
    def fix_with_ruff(code: str) -> str:
        """Попробовать авто-исправить через ruff --fix."""
        if not CodeLinter._ensure_ruff():
            return code

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            subprocess.run(
                ["ruff", "check", "--fix", "--unsafe-fixes", tmp_path],
                capture_output=True, timeout=30
            )
            with open(tmp_path, encoding="utf-8") as f:
                return f.read()
        except Exception:
            return code
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    @classmethod
    def lint_and_fix(
        cls,
        llm_fn: Callable,
        code: str,
        task: str = "",
        max_attempts: int = 2,
        on_status: Optional[Callable] = None,
    ) -> Tuple[str, List[str]]:
        """
        Линтинг + авто-фикс + LLM-фикс если нужно.
        Returns: (clean_code, remaining_issues)
        """
        for attempt in range(max_attempts):
            ok, issues = cls.lint(code)
            if ok:
                if on_status and attempt > 0:
                    on_status("✅ Ruff: код чистый")
                return code, []

            if on_status:
                on_status(f"🔧 Ruff: {len(issues)} проблем, исправляю (попытка {attempt+1})...")

            # Попытка 1: ruff --fix автоматически
            if attempt == 0:
                code = cls.fix_with_ruff(code)
                continue

            # Попытка 2: просим LLM исправить
            issues_str = "\n".join(issues[:10])
            fix_prompt = (
                f"Исправь Python-код. Ошибки ruff:\n{issues_str}\n\n"
                f"КОД:\n```python\n{code[:3000]}\n```\n\n"
                f"Верни ТОЛЬКО исправленный код в блоке ```python ... ```"
            )
            raw = llm_fn(fix_prompt, max_tokens=3000)
            m = re.search(r"```python\s*(.*?)\s*```", raw, re.DOTALL)
            if m:
                fixed = m.group(1).strip()
                if fixed and len(fixed) > 20:
                    code = fixed

        ok, issues = cls.lint(code)
        return code, issues


# ══════════════════════════════════════════════════════════════════════════════
#  BRAIN MIXIN — подключается к AgentBase
# ══════════════════════════════════════════════════════════════════════════════

class BrainMixin:
    """
    Добавляет интеллект к AgentBase.

    Использование:
        class AgentNeo(BrainMixin, AgentBase):
            BRAIN_REFLEXION = True    # включить само-критику
            BRAIN_LINTING   = True    # ruff для кода
            BRAIN_DELEGATE  = False   # делегировать подзадачи
            BRAIN_GRAPH     = False   # граф выполнения
    """

    # Флаги включения функций (переопределяй в агенте)
    BRAIN_REFLEXION: bool = False
    BRAIN_LINTING:   bool = False
    BRAIN_DELEGATE:  bool = False
    BRAIN_GRAPH:     bool = False
    BRAIN_MIN_SCORE: int  = 7       # минимальный score для reflexion
    BRAIN_MAX_ROUNDS: int = 2       # максимум раундов reflexion

    def brain_execute(
        self,
        task: str,
        chat_id: int,
        files: list = None,
        mode: str = "auto",
        on_status: Optional[Callable] = None,
    ):
        """Обёртка над execute() с подключёнными механизмами мозга."""
        self._status_fn = on_status

        # Анти-паттерны из фидбека
        addon = FeedbackStore.build_system_prompt_addon(self.NAME.lower())
        if addon and hasattr(self, "SYSTEM_PROMPT"):
            original_prompt = self.SYSTEM_PROMPT
            self.SYSTEM_PROMPT = self.SYSTEM_PROMPT + addon

        # Делегирование
        if self.BRAIN_DELEGATE and hasattr(self, "llm"):
            delegated = Delegation.auto_delegate(
                from_agent=self.NAME.lower(),
                task=task,
                chat_id=chat_id,
                llm_fn=self.llm,
                on_status=on_status,
            )
            if delegated and delegated.get("ok"):
                if addon:
                    self.SYSTEM_PROMPT = original_prompt
                from core.agent_base import AgentResult
                return AgentResult(
                    ok=True,
                    answer=delegated["answer"],
                    files=delegated.get("files", []),
                    zip_path=delegated.get("zip_path", ""),
                    agent=f"{self.NAME}→{delegated['agent'].upper()}",
                    mode=mode,
                )

        # Основное выполнение
        result = super().execute(task, chat_id, files, mode, on_status)

        # Восстановить system prompt
        if addon:
            self.SYSTEM_PROMPT = original_prompt

        # Reflexion на ответ
        if self.BRAIN_REFLEXION and result.answer and hasattr(self, "llm"):
            improved_answer, critique_history = Reflexion.run(
                llm_fn=self.llm,
                task=task,
                initial_answer=result.answer,
                agent_name=self.NAME.lower(),
                system=getattr(self, "SYSTEM_PROMPT", ""),
                max_rounds=self.BRAIN_MAX_ROUNDS,
                min_score=self.BRAIN_MIN_SCORE,
                on_status=on_status,
            )
            result.answer = improved_answer
            result.metadata = getattr(result, "metadata", {})
            result.metadata["reflexion"] = critique_history

        return result

    def brain_lint_code(self, code: str, task: str = "") -> Tuple[str, List[str]]:
        """Прогнать ruff на коде (вызывать из execute агента-кодера)."""
        if not self.BRAIN_LINTING:
            return code, []
        llm_fn = getattr(self, "llm", lambda p, s="", **kw: p)
        return CodeLinter.lint_and_fix(
            llm_fn=llm_fn,
            code=code,
            task=task,
            on_status=self._status_fn,
        )

    def brain_record_feedback(self, chat_id: str, task: str,
                               answer: str, score: int, comment: str = ""):
        """Сохранить оценку ответа."""
        FeedbackStore.save(chat_id, self.NAME.lower(), task, answer, score, comment)


# ══════════════════════════════════════════════════════════════════════════════
#  BRAIN — фасад для прямого вызова без наследования
# ══════════════════════════════════════════════════════════════════════════════

class Brain:
    """
    Фасад для применения интеллекта к любому агенту без изменения его класса.

    Пример — сделать NEO умнее без изменения agents/neo.py:
        from core.agent_brain import Brain
        result = Brain.run(
            agent=agent_instance,
            task=task,
            chat_id=chat_id,
            reflexion=True,
            linting=True,
            on_status=on_status,
        )
    """

    @staticmethod
    def run(
        agent,
        task: str,
        chat_id: int,
        files: list = None,
        mode: str = "auto",
        reflexion: bool = False,
        linting: bool = False,
        delegate: bool = False,
        on_status: Optional[Callable] = None,
    ):
        """Выполнить задачу через агента с подключёнными механизмами."""

        # Анти-паттерны
        agent_name = getattr(agent, "NAME", "agent").lower()
        addon = FeedbackStore.build_system_prompt_addon(agent_name)
        original_prompt = None
        if addon and hasattr(agent, "SYSTEM_PROMPT"):
            original_prompt = agent.SYSTEM_PROMPT
            agent.SYSTEM_PROMPT = agent.SYSTEM_PROMPT + addon

        # Делегирование
        if delegate and hasattr(agent, "llm"):
            delegated = Delegation.auto_delegate(
                from_agent=agent_name,
                task=task,
                chat_id=chat_id,
                llm_fn=agent.llm,
                on_status=on_status,
            )
            if delegated and delegated.get("ok"):
                if original_prompt:
                    agent.SYSTEM_PROMPT = original_prompt
                from core.agent_base import AgentResult
                return AgentResult(
                    ok=True, answer=delegated["answer"],
                    files=delegated.get("files", []),
                    agent=f"{agent_name}→{delegated['agent']}", mode=mode,
                )

        # Выполнение
        result = agent.execute(task, chat_id, files=files, mode=mode,
                               on_status=on_status)

        # Восстановить prompt
        if original_prompt:
            agent.SYSTEM_PROMPT = original_prompt

        # Reflexion
        if reflexion and result.answer and hasattr(agent, "llm"):
            improved, history = Reflexion.run(
                llm_fn=agent.llm,
                task=task,
                initial_answer=result.answer,
                agent_name=agent_name,
                max_rounds=2,
                on_status=on_status,
            )
            result.answer = improved

        return result

    @staticmethod
    def feedback(chat_id: str, agent: str, task: str,
                 answer: str, score: int, comment: str = "") -> bool:
        """Записать оценку пользователя."""
        return FeedbackStore.save(chat_id, agent, task, answer, score, comment)

    @staticmethod
    def stats() -> dict:
        """Статистика всех агентов для дашборда."""
        return {
            "agents": FeedbackStore.all_stats(),
            "reflexion_runs": Brain._count_table("reflexion_log"),
            "graph_runs":     Brain._count_table("agent_graph_runs"),
            "feedback_total": Brain._count_table("feedback"),
        }

    @staticmethod
    def _count_table(table: str) -> int:
        try:
            with _db() as db:
                return db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except Exception:
            return 0
