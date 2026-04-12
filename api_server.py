"""
Local OpenAI-compatible API server.
When enabled, exposes POST /v1/chat/completions on localhost.
Other apps (bots, scripts) can use this as a drop-in replacement for OpenAI API.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from core.config import config

_server_thread: threading.Thread | None = None
_running = False

_fastapi_available = False
try:
    import uvicorn
    from fastapi import FastAPI
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel
    _fastapi_available = True
except ImportError:
    pass


def _create_app():
    app = FastAPI(title="BlackBugsAI Local API", version="1.0.0")

    class ChatMessage(BaseModel):
        role: str
        content: str

    class ChatRequest(BaseModel):
        model: str = "local"
        messages: list[ChatMessage]
        stream: bool = False
        max_tokens: int = 2048
        temperature: float = 0.7

    @app.get("/v1/models")
    def list_models():
        from core.llm_engine import llm_engine
        models = [{"id": m.name, "object": "model"} for m in llm_engine.list_models()]
        return {"object": "list", "data": models}

    @app.post("/v1/chat/completions")
    def chat(req: ChatRequest):
        from core.llm_engine import llm_engine
        from core.providers import provider_client

        messages = [{"role": m.role, "content": m.content} for m in req.messages]
        provider = config.get("provider", "local")

        def _generate():
            if provider == "local":
                gen = llm_engine.stream(
                    messages[-1]["content"],
                    system_prompt=config.get("system_prompt", ""),
                    history=messages[:-1],
                )
            else:
                gen = provider_client.stream(messages)

            completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
            chunk_tmpl = (
                'data: {{"id":"{cid}","object":"chat.completion.chunk","created":{ts},'
                '"model":"{model}","choices":[{{"delta":{{"content":{content}}},'
                '"finish_reason":null,"index":0}}]}}\n\n'
            )

            for token in gen:
                import json
                yield chunk_tmpl.format(
                    cid=completion_id,
                    ts=int(time.time()),
                    model=req.model,
                    content=json.dumps(token),
                )
            yield "data: [DONE]\n\n"

        if req.stream:
            return StreamingResponse(_generate(), media_type="text/event-stream")

        # Non-streaming: collect all tokens
        full = "".join(
            llm_engine.stream(
                messages[-1]["content"],
                system_prompt=config.get("system_prompt", ""),
                history=messages[:-1],
            ) if config.get("provider") == "local"
            else provider_client.stream(messages)
        )
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": req.model,
            "choices": [{"message": {"role": "assistant", "content": full}, "finish_reason": "stop", "index": 0}],
        }

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


def start_server() -> bool:
    global _server_thread, _running

    if not _fastapi_available:
        return False

    if _running:
        return True

    port = config.get("api_server_port", 8765)
    app = _create_app()

    def _run():
        global _running
        _running = True
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
        _running = False

    _server_thread = threading.Thread(target=_run, daemon=True)
    _server_thread.start()
    return True


def stop_server() -> None:
    global _running
    _running = False
    # uvicorn doesn't expose a clean stop API; daemon thread exits with app


def is_running() -> bool:
    return _running
