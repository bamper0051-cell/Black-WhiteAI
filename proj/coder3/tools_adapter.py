# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional


class Coder3ToolAdapter:
    """Контролируемый мост между AGENT_CODER3 и файловой системой/проверками."""

    def __init__(self, workspace: str = 'workspace/coder3', project_root: str = '.'):
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.project_root = Path(project_root)
        self.changes: List[str] = []
        self.artifacts: List[str] = []
        self.observations: List[Dict] = []
        self.logs: List[str] = []

    def log(self, message: str) -> None:
        self.logs.append(message)

    def observe(self, stage: str, payload: Dict) -> None:
        self.observations.append({'stage': stage, 'payload': payload})

    def _track(self, path: Path) -> str:
        path_str = str(path)
        if path_str not in self.changes:
            self.changes.append(path_str)
        if path_str not in self.artifacts:
            self.artifacts.append(path_str)
        return path_str

    def create_file(self, rel_path: str, content: str) -> str:
        path = self.workspace / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        self.observe('file_create', {'path': str(path), 'bytes': len(content.encode('utf-8'))})
        return self._track(path)

    def write_workspace_text(self, rel_path: str, content: str) -> str:
        return self.create_file(rel_path, content)

    def write_project_text(self, rel_path: str, content: str) -> str:
        path = self.project_root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        self.observe('project_write', {'path': str(path), 'bytes': len(content.encode('utf-8'))})
        return self._track(path)

    def read_project_text(self, rel_path: str) -> str:
        path = self.project_root / rel_path
        if not path.exists():
            return ''
        text = path.read_text(encoding='utf-8', errors='ignore')
        self.observe('project_read', {'path': str(path), 'chars': len(text)})
        return text

    def list_project_files(self, suffixes: Optional[tuple[str, ...]] = None, limit: int = 80) -> List[str]:
        results: List[str] = []
        suffixes = suffixes or ('.py', '.md', '.txt', '.json', '.yml', '.yaml')
        for p in self.project_root.rglob('*'):
            if len(results) >= limit:
                break
            if p.is_file() and '/.git/' not in str(p).replace('\\', '/') and p.suffix.lower() in suffixes:
                results.append(str(p.relative_to(self.project_root)))
        self.observe('project_list', {'count': len(results), 'suffixes': suffixes})
        return results

    def patch_text(self, original: str, replacement: str, pattern: str) -> Dict:
        new_text, count = re.subn(pattern, replacement, original, flags=re.MULTILINE)
        self.observe('patch_text', {'count': count, 'pattern': pattern})
        return {'text': new_text, 'count': count}

    def extract_python_blocks(self, text: str) -> List[str]:
        blocks = re.findall(r"```(?:python)?\n(.*?)```", text, flags=re.S)
        cleaned = [b.strip() for b in blocks if b.strip()]
        if cleaned:
            self.observe('extract_python_blocks', {'count': len(cleaned)})
            return cleaned
        if any(tok in text for tok in ('def ', 'class ', 'import ', 'print(', 'if __name__')):
            self.observe('extract_python_blocks', {'count': 1, 'fallback': True})
            return [text.strip()]
        return []

    def extract_traceback(self, text: str) -> str:
        match = re.search(r'(Traceback[\s\S]+)', text)
        tb = match.group(1).strip() if match else ''
        if tb:
            self.observe('traceback_detected', {'chars': len(tb)})
        return tb

    def check_python(self, code: str) -> Dict:
        try:
            ast.parse(code)
            return {'ok': True, 'error': ''}
        except SyntaxError as exc:
            return {
                'ok': False,
                'error': f'{exc.msg} (line {exc.lineno})',
                'line': exc.lineno,
                'offset': exc.offset,
                'text': exc.text.strip() if exc.text else '',
            }
        except Exception as exc:
            return {'ok': False, 'error': str(exc)}

    def validate_json(self, text: str) -> Dict:
        try:
            json.loads(text)
            return {'ok': True, 'error': ''}
        except Exception as exc:
            return {'ok': False, 'error': str(exc)}

    def run_sandbox(self, code: str, timeout: int = 20) -> Dict:
        with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False, encoding='utf-8') as tf:
            tf.write(code)
            tmp_path = tf.name
        cmd = ['python3', tmp_path] if os.name != 'nt' else ['python', tmp_path]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            result = {
                'ok': proc.returncode == 0,
                'returncode': proc.returncode,
                'stdout': proc.stdout,
                'stderr': proc.stderr,
                'cmd': cmd,
            }
            self.observe('sandbox_run', result)
            return result
        except subprocess.TimeoutExpired:
            result = {'ok': False, 'returncode': -1, 'stdout': '', 'stderr': 'Timeout expired', 'cmd': cmd}
            self.observe('sandbox_run', result)
            return result
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def scan_entry_points(self) -> List[str]:
        candidates = []
        for name in ('bot.py', 'main.py', 'app.py', 'run.py'):
            if (self.project_root / name).exists():
                candidates.append(name)
        if not candidates:
            for file in self.list_project_files(limit=20):
                if file.endswith('.py'):
                    text = self.read_project_text(file)
                    if 'if __name__ == "__main__":' in text or "if __name__ == '__main__':" in text:
                        candidates.append(file)
        self.observe('entry_points', {'candidates': candidates})
        return candidates[:10]

    def package_workspace(self, zip_name: str = 'agent_coder3_result.zip') -> str:
        zip_path = self.workspace / zip_name
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file in self.workspace.rglob('*'):
                if file.is_file() and file != zip_path:
                    zf.write(file, arcname=str(file.relative_to(self.workspace)))
        self.observe('package_workspace', {'zip': str(zip_path)})
        return self._track(zip_path)
