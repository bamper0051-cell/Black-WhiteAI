"""
llm_router.py — Per-agent LLM routing for BlackBugsAI

Each agent can have its own LLM provider/model via .env:
  SMITH_PROVIDER / SMITH_MODEL       -- AGENT_SMITH
  CODER_PROVIDER / CODER_MODEL       -- chat_agent code tasks
  CODER3_PROVIDER / CODER3_MODEL     -- AGENT_CODER3
  CHAT_PROVIDER  / CHAT_MODEL        -- chat_agent chat mode
  AGENT_PROVIDER / AGENT_MODEL       -- agent_core / planner
  FIX_PROVIDER   / FIX_MODEL         -- autofix specialist

Falls back to global LLM_PROVIDER / LLM_MODEL if not set.

Usage:
    from llm_router import get_llm_for, call_llm_for

    # Get a caller bound to a specific agent role
    llm = get_llm_for("smith")
    reply = llm("Write a Python script for X", system_prompt)

    # Or call directly
    reply = call_llm_for("coder", prompt, system, max_tokens=8000)
"""
from __future__ import annotations
import os
import config
from typing import Callable, Optional

AGENT_ROLES = [
    "smith",    # AGENT_SMITH pipeline (agent_session.py)
    "coder",    # chat_agent code tasks
    "coder3",   # AGENT_CODER3
    "chat",     # chat mode (chat_agent / agent_core)
    "agent",    # agent_core planner/executor
    "fix",      # autofix specialist
    "review",   # code review
    "sandbox",  # sandbox execution analysis
]

# Env key prefixes for each role
_ROLE_ENV: dict[str, tuple[str, str]] = {
    "smith":   ("SMITH_PROVIDER",   "SMITH_MODEL"),
    "coder":   ("CODER_PROVIDER",   "CODER_MODEL"),
    "coder3":  ("CODER3_PROVIDER",  "CODER3_MODEL"),
    "chat":    ("CHAT_PROVIDER",    "CHAT_MODEL"),
    "agent":   ("AGENT_PROVIDER",   "AGENT_MODEL"),
    "fix":     ("FIX_PROVIDER",     "FIX_MODEL"),
    "review":  ("REVIEW_PROVIDER",  "REVIEW_MODEL"),
    "sandbox": ("SANDBOX_PROVIDER", "SANDBOX_MODEL"),
}


def get_provider_model(role: str) -> tuple[str, str]:
    """Returns (provider, model) for the given agent role."""
    role = role.lower().strip()
    prov_key, model_key = _ROLE_ENV.get(role, ("", ""))
    provider = ""
    model    = ""
    if prov_key:
        provider = os.environ.get(prov_key, "").strip()
    if model_key:
        model = os.environ.get(model_key, "").strip()
    # Fallback to global
    if not provider:
        provider = getattr(config, "LLM_PROVIDER", "openai") or "openai"
    if not model:
        model = getattr(config, "LLM_MODEL", "") or ""
    return provider.lower(), model


def call_llm_for(role: str, prompt: str, system: str = "",
<<<<<<< HEAD
                 max_tokens: int = 4000, temperature: float = 0.2) -> str:   # FIX: temperature
=======
                 max_tokens: int = 4000) -> str:
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    """Call LLM using the provider/model assigned to this agent role."""
    provider, model = get_provider_model(role)
    try:
        from llm_client import _call_provider
<<<<<<< HEAD
        return _call_provider(provider, prompt, system, max_tokens, model=model,
                              temperature=temperature)
    except Exception:
        # Fallback to global call_llm
        from llm_client import call_llm
        return call_llm(prompt, system, max_tokens, temperature=temperature)
=======
        return _call_provider(provider, prompt, system, max_tokens, model=model)
    except Exception:
        # Fallback to global call_llm
        from llm_client import call_llm
        return call_llm(prompt, system, max_tokens)
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999


def get_llm_for(role: str) -> Callable[[str, str], str]:
    """Returns a callable(prompt, system) bound to this agent role."""
    def _call(prompt: str, system: str = "", max_tokens: int = 4000) -> str:
        return call_llm_for(role, prompt, system, max_tokens)
    return _call


def llm_status() -> str:
    """HTML summary of current per-agent LLM assignments (for admin panel)."""
    lines = ["<b>Per-agent LLM assignments</b>\n"]
    global_p = getattr(config, "LLM_PROVIDER", "openai")
    global_m = getattr(config, "LLM_MODEL", "?")
    lines.append(f"Global: <code>{global_p} / {global_m}</code>\n")
    for role in AGENT_ROLES:
        p, m = get_provider_model(role)
        pkey, mkey = _ROLE_ENV.get(role, ("", ""))
        custom_p = bool(os.environ.get(pkey, ""))
        custom_m = bool(os.environ.get(mkey, ""))
        mark = " *" if (custom_p or custom_m) else ""
        lines.append(f"  {role:10s} {p} / {m}{mark}")
    lines.append("\n* = custom override set")
    return "\n".join(lines)


def set_agent_llm(role: str, provider: str, model: str) -> bool:
    """Persist per-agent LLM to .env and live env."""
    role = role.lower().strip()
    if role not in _ROLE_ENV:
        return False
    pkey, mkey = _ROLE_ENV[role]
    os.environ[pkey] = provider.lower().strip()
    os.environ[mkey] = model.strip()
    # Also write to .env file
    try:
        _write_env(pkey, provider.lower().strip())
        _write_env(mkey, model.strip())
    except Exception:
        pass
    return True


def _write_env(key: str, value: str):
    env_path = getattr(config, "ENV_PATH", ".env")
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        found = False
        for i, line in enumerate(lines):
            if line.startswith(key + "="):
                lines[i] = f"{key}={value}\n"
                found = True
                break
        if not found:
            lines.append(f"{key}={value}\n")
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception:
        pass
