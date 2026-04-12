"""
Cloud/remote LLM providers — OpenAI, Anthropic, Gemini, Mistral, Groq, Ollama.
All providers expose the same async streaming interface.
"""
from __future__ import annotations

import json
from typing import AsyncIterator, Iterator

import httpx

from core.config import config


PROVIDERS = {
    "openai": "OpenAI (GPT-4o, GPT-4o-mini...)",
    "anthropic": "Anthropic (Claude)",
    "gemini": "Google Gemini",
    "mistral": "Mistral AI",
    "groq": "Groq (fast inference)",
    "ollama": "Ollama (local server)",
    "local": "Local GGUF (llama.cpp)",
}

OPENAI_MODELS = [
    "gpt-4o", "gpt-4o-mini", "gpt-4-turbo",
    "gpt-3.5-turbo", "o1-mini", "o1-preview",
]

ANTHROPIC_MODELS = [
    "claude-opus-4-6", "claude-sonnet-4-6",
    "claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022",
]

GEMINI_MODELS = [
    "gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash",
]

MISTRAL_MODELS = [
    "mistral-large-latest", "mistral-medium-latest",
    "mistral-small-latest", "open-mistral-7b",
]

GROQ_MODELS = [
    "llama-3.3-70b-versatile", "llama-3.1-8b-instant",
    "mixtral-8x7b-32768", "gemma2-9b-it",
]


def models_for_provider(provider: str) -> list[str]:
    return {
        "openai": OPENAI_MODELS,
        "anthropic": ANTHROPIC_MODELS,
        "gemini": GEMINI_MODELS,
        "mistral": MISTRAL_MODELS,
        "groq": GROQ_MODELS,
        "ollama": [],  # dynamic
        "local": [],
    }.get(provider, [])


# ── Streaming client ──────────────────────────────────────────────────────────

class ProviderClient:
    """
    Unified provider client — delegates to the correct API based on config.
    Supports streaming via httpx for all providers.
    """

    def __init__(self) -> None:
        self._provider = config.get("provider", "local")

    def _headers(self) -> dict[str, str]:
        provider = config.get("provider")
        if provider == "openai":
            return {"Authorization": f"Bearer {config.get('openai_api_key')}"}
        elif provider == "anthropic":
            return {
                "x-api-key": config.get("anthropic_api_key"),
                "anthropic-version": "2023-06-01",
            }
        elif provider == "gemini":
            return {"Content-Type": "application/json"}
        elif provider in ("mistral", "groq"):
            keys = {"mistral": "mistral_api_key", "groq": "groq_api_key"}
            return {"Authorization": f"Bearer {config.get(keys[provider])}"}
        return {}

    def stream(
        self,
        messages: list[dict],
        model: str | None = None,
        stop_event=None,
    ) -> Iterator[str]:
        """Synchronous streaming (runs in thread)."""
        provider = config.get("provider", "local")

        if provider == "openai":
            yield from self._openai_stream(messages, model, stop_event)
        elif provider == "anthropic":
            yield from self._anthropic_stream(messages, model, stop_event)
        elif provider in ("mistral", "groq"):
            yield from self._openai_compat_stream(messages, model, provider, stop_event)
        elif provider == "ollama":
            yield from self._ollama_stream(messages, model, stop_event)
        elif provider == "gemini":
            yield from self._gemini_stream(messages, model, stop_event)
        else:
            yield "[Select a provider in Settings]"

    def _openai_stream(self, messages, model, stop_event) -> Iterator[str]:
        model = model or config.get("selected_api_model", "gpt-4o-mini")
        base_url = config.get("openai_base_url", "https://api.openai.com/v1")
        headers = {
            "Authorization": f"Bearer {config.get('openai_api_key')}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "max_tokens": config.get("max_tokens", 2048),
            "temperature": config.get("temperature", 0.7),
        }
        yield from self._sse_stream(
            f"{base_url}/chat/completions", headers, payload, stop_event,
            delta_extractor=lambda d: d.get("choices", [{}])[0].get("delta", {}).get("content", ""),
        )

    def _anthropic_stream(self, messages, model, stop_event) -> Iterator[str]:
        model = model or config.get("selected_api_model", "claude-3-5-haiku-20241022")
        sys_msgs = [m for m in messages if m["role"] == "system"]
        chat_msgs = [m for m in messages if m["role"] != "system"]
        system = sys_msgs[0]["content"] if sys_msgs else ""

        headers = {
            "x-api-key": config.get("anthropic_api_key"),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload: dict = {
            "model": model,
            "messages": chat_msgs,
            "max_tokens": config.get("max_tokens", 2048),
            "stream": True,
        }
        if system:
            payload["system"] = system

        with httpx.Client(timeout=120) as client:
            try:
                with client.stream("POST", "https://api.anthropic.com/v1/messages",
                                   headers=headers, json=payload) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if stop_event and stop_event.is_set():
                            break
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                obj = json.loads(data)
                                if obj.get("type") == "content_block_delta":
                                    text = obj.get("delta", {}).get("text", "")
                                    if text:
                                        yield text
                            except json.JSONDecodeError:
                                pass
            except Exception as e:
                yield f"\n[Anthropic error: {e}]"

    def _openai_compat_stream(self, messages, model, provider, stop_event) -> Iterator[str]:
        urls = {
            "mistral": "https://api.mistral.ai/v1/chat/completions",
            "groq": "https://api.groq.com/openai/v1/chat/completions",
        }
        keys = {"mistral": "mistral_api_key", "groq": "groq_api_key"}
        headers = {
            "Authorization": f"Bearer {config.get(keys[provider])}",
            "Content-Type": "application/json",
        }
        model = model or config.get("selected_api_model", "")
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "max_tokens": config.get("max_tokens", 2048),
            "temperature": config.get("temperature", 0.7),
        }
        yield from self._sse_stream(
            urls[provider], headers, payload, stop_event,
            delta_extractor=lambda d: d.get("choices", [{}])[0].get("delta", {}).get("content", ""),
        )

    def _ollama_stream(self, messages, model, stop_event) -> Iterator[str]:
        base = config.get("ollama_base_url", "http://localhost:11434")
        model = model or "llama3.2"
        with httpx.Client(timeout=120) as client:
            try:
                with client.stream("POST", f"{base}/api/chat", json={
                    "model": model,
                    "messages": messages,
                    "stream": True,
                }) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if stop_event and stop_event.is_set():
                            break
                        if line:
                            try:
                                obj = json.loads(line)
                                text = obj.get("message", {}).get("content", "")
                                if text:
                                    yield text
                            except json.JSONDecodeError:
                                pass
            except Exception as e:
                yield f"\n[Ollama error: {e}]"

    def _gemini_stream(self, messages, model, stop_event) -> Iterator[str]:
        model = model or "gemini-2.0-flash"
        api_key = config.get("gemini_api_key", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?key={api_key}&alt=sse"

        # Convert messages to Gemini format
        contents = []
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            if m["role"] == "system":
                continue
            contents.append({"role": role, "parts": [{"text": m["content"]}]})

        payload = {"contents": contents}
        headers = {"Content-Type": "application/json"}
        yield from self._sse_stream(
            url, headers, payload, stop_event,
            delta_extractor=lambda d: (
                d.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            ),
        )

    def _sse_stream(self, url, headers, payload, stop_event, delta_extractor) -> Iterator[str]:
        with httpx.Client(timeout=120) as client:
            try:
                with client.stream("POST", url, headers=headers, json=payload) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if stop_event and stop_event.is_set():
                            break
                        if line.startswith("data: "):
                            data = line[6:]
                            if data.strip() == "[DONE]":
                                break
                            try:
                                obj = json.loads(data)
                                text = delta_extractor(obj)
                                if text:
                                    yield text
                            except json.JSONDecodeError:
                                pass
            except httpx.HTTPStatusError as e:
                yield f"\n[HTTP {e.response.status_code}: {e.response.text[:200]}]"
            except Exception as e:
                yield f"\n[Provider error: {e}]"

    @staticmethod
    def get_ollama_models() -> list[str]:
        """Fetch available Ollama models from local server."""
        base = config.get("ollama_base_url", "http://localhost:11434")
        try:
            resp = httpx.get(f"{base}/api/tags", timeout=5)
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []


# Global singleton
provider_client = ProviderClient()
