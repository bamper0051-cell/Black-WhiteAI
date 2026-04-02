"""
BlackBugsAI — Code Agent
Pipeline: Analyze → Plan → Generate → Verify → Report → Rollback
Режимы: patch | scaffold | plan_first
"""
import os, json, re, time, subprocess, tempfile, shutil, difflib
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Callable

@dataclass
class CodeChange:
    file_path: str
    original:  str = ""
    modified:  str = ""
    is_new:    bool = False

    def diff(self) -> str:
        a = self.original.splitlines(keepends=True)
        b = self.modified.splitlines(keepends=True)
        return ''.join(difflib.unified_diff(a, b,
                       fromfile=f"a/{self.file_path}",
                       tofile=f"b/{self.file_path}"))

@dataclass
class CodeReport:
    task:        str
    mode:        str
    changes:     List[CodeChange] = field(default_factory=list)
    tests_pass:  bool = False
    lint_pass:   bool = False
    sandbox_out: str = ""
    errors:      List[str] = field(default_factory=list)
    rollback_cmds: List[str] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    duration_s:  float = 0.0

    def to_text(self) -> str:
        icon = "✅" if not self.errors else "⚠️"
        lines = [f"{icon} **Code Agent Report** [{self.mode}]",
                 f"Задача: {self.task}", ""]
        if self.files_created:
            lines += [f"📁 Создано: {', '.join(self.files_created)}", ""]
        for ch in self.changes:
            status = "🆕 NEW" if ch.is_new else "📝 MODIFIED"
            lines.append(f"{status} {ch.file_path}")
        lines.append("")
        checks = []
        if self.lint_pass is not None:
            checks.append(f"{'✅' if self.lint_pass else '❌'} Lint")
        if self.tests_pass is not None:
            checks.append(f"{'✅' if self.tests_pass else '❌'} Tests")
        if checks: lines.append(" | ".join(checks))
        if self.sandbox_out:
            lines += ["", f"🏖 Sandbox:\n```\n{self.sandbox_out[:500]}\n```"]
        if self.errors:
            lines += ["", "❌ Ошибки: " + "; ".join(self.errors[:3])]
        if self.rollback_cmds:
            lines += ["", "↩️ Откат: `" + self.rollback_cmds[0] + "`"]
        return "\n".join(lines)


MODES = {
    'patch':      "Измени только существующие файлы. Минимальные изменения.",
    'scaffold':   "Создай новый модуль/файл по структуре проекта.",
    'plan_first': "Сначала составь детальный план изменений, потом сгенерируй код.",
}

SYSTEM_CODE = """Ты — опытный Python разработчик. Пишешь чистый, рабочий код.

Режим: {mode}
{mode_instruction}

Правила:
1. Код должен быть рабочим и запускаться без ошибок
2. Добавляй docstrings
3. Используй type hints
4. Обрабатывай исключения
5. Не хардкодь токены и пароли

Формат ответа — строго JSON:
{{
  "reasoning": "анализ задачи",
  "files": [
    {{
      "path": "относительный/путь/к/файлу.py",
      "content": "полный код файла",
      "is_new": true
    }}
  ],
  "install": ["пакет1", "пакет2"],
  "test_code": "код для проверки",
  "risks": ["риск1"],
  "rollback": "git checkout -- . или команда отката"
}}"""


class CodeAgent:
    def __init__(self, base_dir: str, llm_caller: Callable = None,
                 on_status: Callable = None):
        self.base_dir   = Path(base_dir)
        self._llm       = llm_caller
        self.on_status  = on_status or (lambda m: None)

    def _status(self, msg): self.on_status(msg)

    def run(self, task: str, mode: str = 'scaffold',
            context_files: List[str] = None) -> CodeReport:
        t0 = time.time()
        report = CodeReport(task=task, mode=mode)
        self._status(f"🧠 Анализирую задачу [{mode}]...")

        # Собираем контекст из файлов проекта
        file_context = self._read_context(context_files or [])

        # Если plan_first — сначала показываем план
        if mode == 'plan_first':
            plan_text = self._generate_plan(task, file_context)
            self._status(f"📋 План:\n{plan_text}")
            report.sandbox_out = plan_text

        # Генерируем код
        self._status("✍️ Генерирую код...")
        raw = self._generate_code(task, mode, file_context)

        try:
            data = json.loads(re.search(r'\{.*\}', raw, re.DOTALL).group())
        except Exception:
            report.errors.append("Не удалось распарсить ответ LLM")
            return report

        # Устанавливаем зависимости
        if data.get('install'):
            self._status(f"📦 Устанавливаю: {data['install']}")
            self._install_packages(data['install'])

        # Записываем файлы
        for f in data.get('files', []):
            path   = self.base_dir / f['path']
            is_new = f.get('is_new', not path.exists())
            original = path.read_text(encoding='utf-8') if path.exists() else ""
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f['content'], encoding='utf-8')
            ch = CodeChange(f['path'], original, f['content'], is_new)
            report.changes.append(ch)
            if is_new: report.files_created.append(f['path'])
            self._status(f"{'🆕' if is_new else '📝'} {f['path']}")

        # Линтинг
        self._status("🔍 Проверяю код...")
        report.lint_pass = self._lint(report.changes)

        # Sandbox тест
        if data.get('test_code'):
            self._status("🏖 Запускаю тесты в sandbox...")
            ok, out = self._sandbox(data['test_code'])
            report.tests_pass = ok
            report.sandbox_out = out

        # Rollback команды
        report.rollback_cmds = [data.get('rollback', 'git checkout -- .')]
        report.duration_s = time.time() - t0
        return report

    def _generate_plan(self, task: str, context: str) -> str:
        if not self._llm: return "Plan: выполнить задачу"
        prompt = f"Задача: {task}\n\nКонтекст:\n{context[:1000]}\n\nСоставь план изменений."
        return self._llm(prompt, "Составь детальный план разработки. Без кода.")

    def _generate_code(self, task: str, mode: str, context: str) -> str:
        system = SYSTEM_CODE.format(
            mode=mode,
            mode_instruction=MODES.get(mode, '')
        )
        prompt = f"Задача: {task}"
        if context:
            prompt += f"\n\nКонтекст проекта:\n{context[:2000]}"
        if self._llm:
            return self._llm(prompt, system)
        # Fallback — шаблон
        return json.dumps({
            "reasoning": f"Создаём модуль для: {task}",
            "files": [{"path": "new_module.py",
                       "content": f'"""Generated by BlackBugsAI\nTask: {task}"""\n\n# TODO: implement\n',
                       "is_new": True}],
            "install": [], "test_code": "", "risks": [], "rollback": "rm new_module.py"
        })

    def _read_context(self, file_paths: List[str]) -> str:
        parts = []
        for fp in file_paths[:5]:
            try:
                content = Path(fp).read_text(encoding='utf-8', errors='ignore')
                parts.append(f"=== {fp} ===\n{content[:1000]}")
            except Exception:
                pass
        return "\n\n".join(parts)

    def _lint(self, changes: List[CodeChange]) -> bool:
        for ch in changes:
            if not ch.file_path.endswith('.py'): continue
            try:
                import ast as _ast
                _ast.parse(ch.modified)
            except SyntaxError as e:
                self._status(f"  ❌ Синтаксис {ch.file_path}: {e}")
                return False
        return True

    def _sandbox(self, code: str, timeout: int = 30) -> tuple[bool, str]:
        with tempfile.NamedTemporaryFile(suffix='.py', mode='w',
                                         delete=False, encoding='utf-8') as f:
            f.write(code)
            tmp = f.name
        try:
            r = subprocess.run(['python3', tmp], capture_output=True,
                              text=True, timeout=timeout)
            out = (r.stdout + r.stderr).strip()
            return r.returncode == 0, out[:1000] or '(нет вывода)'
        except subprocess.TimeoutExpired:
            return False, f"⏰ Таймаут {timeout}с"
        except Exception as e:
            return False, str(e)
        finally:
            try: os.unlink(tmp)
            except: pass

    def _install_packages(self, packages: List[str]):
        safe = [p for p in packages if re.match(r'^[\w\-\[\]>=<.]+$', p)]
        if not safe: return
        try:
            subprocess.run(['pip', 'install', '--quiet'] + safe,
                          capture_output=True, timeout=60)
        except Exception: pass
