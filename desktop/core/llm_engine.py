"""
Local LLM Engine — wraps llama-cpp-python for GGUF model inference.
Supports streaming via callbacks, CPU and GPU (CUDA/Metal/Vulkan).
"""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Callable, Iterator, Optional

from core.config import config, MODELS_DIR

_llama_available = False
try:
    from llama_cpp import Llama, LlamaGrammar
    _llama_available = True
except ImportError:
    pass


class ModelInfo:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.name = path.stem
        self.size_gb = round(path.stat().st_size / 1e9, 2)
        self.filename = path.name

    def __repr__(self) -> str:
        return f"<ModelInfo {self.name} {self.size_gb}GB>"


class LLMEngine:
    """
    Manages loading/unloading GGUF models and running inference.

    Usage:
        engine = LLMEngine()
        engine.load_model("path/to/model.gguf")
        for token in engine.stream("Hello!"):
            print(token, end="", flush=True)
    """

    def __init__(self) -> None:
        self._model: Optional[object] = None
        self._model_path: Optional[str] = None
        self._lock = threading.Lock()
        self._loaded = False
        self._load_error: Optional[str] = None

    @property
    def is_loaded(self) -> bool:
        return self._loaded and self._model is not None

    @property
    def model_name(self) -> str:
        if self._model_path:
            return Path(self._model_path).stem
        return "No model loaded"

    @property
    def load_error(self) -> Optional[str]:
        return self._load_error

    def load_model(
        self,
        model_path: str,
        on_progress: Callable[[str], None] | None = None,
    ) -> bool:
        """Load a GGUF model. Returns True on success."""
        if not _llama_available:
            self._load_error = "llama-cpp-python not installed.\nRun: pip install llama-cpp-python"
            return False

        if not Path(model_path).exists():
            self._load_error = f"Model file not found: {model_path}"
            return False

        if on_progress:
            on_progress(f"Loading {Path(model_path).name}...")

        try:
            with self._lock:
                # Unload previous model
                self._model = None
                self._loaded = False

                n_gpu = config.get("n_gpu_layers", -1)
                n_ctx = config.get("context_length", 4096)
                n_threads = config.get("n_threads", 0) or os.cpu_count()

                self._model = Llama(
                    model_path=model_path,
                    n_ctx=n_ctx,
                    n_gpu_layers=n_gpu,
                    n_threads=n_threads,
                    verbose=False,
                )
                self._model_path = model_path
                self._loaded = True
                self._load_error = None

            if on_progress:
                on_progress(f"✅ Loaded: {Path(model_path).name}")
            return True

        except Exception as exc:
            self._load_error = str(exc)
            self._loaded = False
            if on_progress:
                on_progress(f"❌ Error: {exc}")
            return False

    def unload(self) -> None:
        with self._lock:
            self._model = None
            self._loaded = False
            self._model_path = None

    def stream(
        self,
        prompt: str,
        system_prompt: str = "",
        history: list[dict] | None = None,
        stop_event: threading.Event | None = None,
    ) -> Iterator[str]:
        """
        Stream token-by-token response.
        Yields text chunks as they are generated.
        """
        if not self.is_loaded:
            yield "[Error: No model loaded]"
            return

        # Build chat messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        temperature = config.get("temperature", 0.7)
        top_p = config.get("top_p", 0.95)
        top_k = config.get("top_k", 40)
        max_tokens = config.get("max_tokens", 2048)
        repeat_penalty = config.get("repeat_penalty", 1.1)

        try:
            with self._lock:
                stream = self._model.create_chat_completion(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    repeat_penalty=repeat_penalty,
                    stream=True,
                )

                for chunk in stream:
                    if stop_event and stop_event.is_set():
                        break
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content

        except Exception as exc:
            yield f"\n[Error during generation: {exc}]"

    # ── Model management ──────────────────────────────────────────────────────

    @staticmethod
    def list_models() -> list[ModelInfo]:
        """List all GGUF models in the models directory."""
        return sorted(
            [ModelInfo(p) for p in MODELS_DIR.glob("*.gguf")],
            key=lambda m: m.name.lower(),
        )

    @staticmethod
    def models_dir() -> Path:
        return MODELS_DIR

    def context_info(self) -> dict:
        """Return info about the currently loaded model."""
        if not self.is_loaded or not _llama_available:
            return {}
        try:
            return {
                "n_ctx": self._model.n_ctx(),
                "n_embd": self._model.n_embd(),
                "model": self.model_name,
            }
        except Exception:
            return {"model": self.model_name}


# Global singleton
llm_engine = LLMEngine()
