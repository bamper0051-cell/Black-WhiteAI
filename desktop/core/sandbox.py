"""
Code sandbox — safe execution of Python, JavaScript, Shell code.
Uses subprocess with timeout and output capture.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List

from config import settings


@dataclass
class RunResult:
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool = False
    language: str = ""

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    @property
    def output(self) -> str:
        parts = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(f"[stderr]\n{self.stderr}")
        if self.timed_out:
            parts.append(f"[Timed out after {settings.SANDBOX_TIMEOUT}s]")
        return "\n".join(parts) or "(no output)"


_DANGEROUS_PATTERNS = [
    r"os\.system\s*\(", r"subprocess\.(?:call|run|Popen)",
    r"shutil\.rmtree", r"open\s*\(.+[\"']w[\"']",
    r"__import__\s*\(\s*[\"']os[\"']",
    r"eval\s*\(", r"exec\s*\(",
    r"import\s+socket", r"import\s+requests",
    r"rm\s+-rf", r"del\s+/",
    r"format\s+[A-Z]:", r"mkfs",
]


def _is_dangerous(code: str) -> bool:
    return any(re.search(p, code, re.IGNORECASE) for p in _DANGEROUS_PATTERNS)


def extract_code_blocks(text: str) -> list[tuple[str, str]]:
    """
    Extract all code blocks from a markdown text.
    Returns list of (language, code) tuples.
    """
    pattern = r"```(\w+)?\n?(.*?)```"
    blocks = re.findall(pattern, text, re.DOTALL)
    return [(lang.lower() or "python", code.strip()) for lang, code in blocks]


def run_code(code: str, language: str = "python") -> RunResult:
    """Execute code in a sandboxed subprocess."""
    if not settings.ENABLE_SANDBOX:
        return RunResult("", "Sandbox is disabled in settings.", 1, language=language)

    if _is_dangerous(code) and language == "python":
        return RunResult(
            "", "Execution blocked: potentially unsafe code detected.", 1, language=language
        )

    timeout = settings.SANDBOX_TIMEOUT
    suffix = {"python": ".py", "javascript": ".js", "bash": ".sh", "shell": ".sh"}.get(language, ".txt")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False, prefix="bbai_sandbox_", encoding="utf-8"
    ) as f:
        f.write(code)
        tmp = Path(f.name)

    try:
        cmd = _build_cmd(language, str(tmp))
        if not cmd:
            return RunResult("", f"No runner for language: {language}", 1, language=language)

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return RunResult(
            stdout=proc.stdout[:20_000],
            stderr=proc.stderr[:5_000],
            exit_code=proc.returncode,
            language=language,
        )
    except subprocess.TimeoutExpired:
        return RunResult("", "", 1, timed_out=True, language=language)
    except FileNotFoundError as e:
        return RunResult("", f"Runner not found: {e}", 1, language=language)
    except Exception as e:
        return RunResult("", str(e), 1, language=language)
    finally:
        tmp.unlink(missing_ok=True)


def _build_cmd(language: str, filepath: str) -> list[str] | None:
    lang = language.lower()
    if lang == "python":
        return [sys.executable, "-I", filepath]  # -I = isolated mode
    elif lang in ("javascript", "js"):
        node = shutil.which("node") or shutil.which("nodejs")
        return [node, filepath] if node else None
    elif lang in ("bash", "shell", "sh"):
        bash = shutil.which("bash") or shutil.which("sh")
        return [bash, filepath] if bash else None
    elif lang == "typescript":
        tsx = shutil.which("ts-node") or shutil.which("tsx")
        return [tsx, filepath] if tsx else None
    return None


class ToolRegistry:
    """Registry of tools available to AI agents."""
    
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register default tools."""
        self.register_tool(
            "file_read",
            "Read file contents",
            {"file_path": "str"},
            self._tool_file_read
        )
        self.register_tool(
            "file_write",
            "Write content to file",
            {"file_path": "str", "content": "str"},
            self._tool_file_write
        )
        self.register_tool(
            "execute_python",
            "Execute Python code",
            {"code": "str"},
            self._tool_execute_python
        )
        self.register_tool(
            "execute_bash",
            "Execute bash command",
            {"command": "str"},
            self._tool_execute_bash
        )
        self.register_tool(
            "list_files",
            "List files in directory",
            {"directory": "str"},
            self._tool_list_files
        )
    
    def register_tool(
        self,
        name: str,
        description: str,
        params: Dict[str, str],
        func
    ):
        """Register a new tool."""
        self.tools[name] = {
            "description": description,
            "params": params,
            "func": func
        }
    
    async def execute_tool(self, name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool."""
        if name not in self.tools:
            return {"success": False, "error": f"Tool '{name}' not found"}
        
        tool = self.tools[name]
        func = tool["func"]
        
        try:
            result = await func(**kwargs) if asyncio.iscoroutinefunction(func) else func(**kwargs)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _tool_file_read(self, file_path: str) -> str:
        """Read file contents."""
        return Path(file_path).read_text()
    
    async def _tool_file_write(self, file_path: str, content: str):
        """Write content to file."""
        Path(file_path).write_text(content)
        return "File written successfully"
    
    async def _tool_execute_python(self, code: str) -> Dict[str, Any]:
        """Execute Python code."""
        result = run_code(code, "python")
        return {
            "output": result.output,
            "success": result.success,
            "time": 0
        }
    
    async def _tool_execute_bash(self, command: str) -> Dict[str, Any]:
        """Execute bash command."""
        result = run_code(command, "bash")
        return {
            "output": result.output,
            "success": result.success,
            "time": 0
        }
    
    async def _tool_list_files(self, directory: str) -> List[str]:
        """List files in directory."""
        return [f.name for f in Path(directory).iterdir()]
    
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Get OpenAI function calling schema."""
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool["description"],
                    "parameters": {
                        "type": "object",
                        "properties": {
                            param: {"type": param_type}
                            for param, param_type in tool["params"].items()
                        },
                        "required": list(tool["params"].keys())
                    }
                }
            }
            for name, tool in self.tools.items()
        ]
