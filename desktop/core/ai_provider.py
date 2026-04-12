"""
AI provider abstraction layer supporting multiple LLM backends.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, AsyncIterator
from dataclasses import dataclass
from enum import Enum
import aiohttp
import json


class ProviderType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    LOCAL_LLAMA_CPP = "local_llama_cpp"


@dataclass
class Message:
    role: str  # "user" or "assistant"
    content: str


@dataclass
class AIResponse:
    content: str
    model: str
    provider: ProviderType
    tokens_used: Optional[int] = None


class AIProvider(ABC):
    """Base class for AI providers."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
    
    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> AIResponse:
        """Generate a response from the AI model."""
        pass
    
    @abstractmethod
    async def stream_generate(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream generate a response from the AI model."""
        pass
    
    @abstractmethod
    async def list_models(self) -> List[str]:
        """List available models."""
        pass


class OpenAIProvider(AIProvider):
    """OpenAI API provider."""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def generate(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> AIResponse:
        """Generate response using OpenAI API."""
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return AIResponse(
                        content=data["choices"][0]["message"]["content"],
                        model=model,
                        provider=ProviderType.OPENAI,
                        tokens_used=data["usage"]["total_tokens"]
                    )
                else:
                    error_text = await resp.text()
                    raise Exception(f"OpenAI API error: {error_text}")
    
    async def stream_generate(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream generate response using OpenAI API."""
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload
            ) as resp:
                if resp.status == 200:
                    async for line in resp.content:
                        line = line.decode().strip()
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str != "[DONE]":
                                data = json.loads(data_str)
                                if "choices" in data:
                                    delta = data["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        yield delta["content"]
                else:
                    error_text = await resp.text()
                    raise Exception(f"OpenAI API error: {error_text}")
    
    async def list_models(self) -> List[str]:
        """List available OpenAI models."""
        return [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ]


class AnthropicProvider(AIProvider):
    """Anthropic Claude API provider."""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://api.anthropic.com/v1"
        self.headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
    
    async def generate(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> AIResponse:
        """Generate response using Anthropic API."""
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/messages",
                headers=self.headers,
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return AIResponse(
                        content=data["content"][0]["text"],
                        model=model,
                        provider=ProviderType.ANTHROPIC,
                        tokens_used=data["usage"]["output_tokens"]
                    )
                else:
                    error_text = await resp.text()
                    raise Exception(f"Anthropic API error: {error_text}")
    
    async def stream_generate(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream generate response using Anthropic API."""
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/messages",
                headers=self.headers,
                json=payload
            ) as resp:
                if resp.status == 200:
                    async for line in resp.content:
                        line = line.decode().strip()
                        if line.startswith("data: "):
                            data_str = line[6:]
                            data = json.loads(data_str)
                            if data.get("type") == "content_block_delta":
                                if data.get("delta", {}).get("type") == "text_delta":
                                    yield data["delta"]["text"]
                else:
                    error_text = await resp.text()
                    raise Exception(f"Anthropic API error: {error_text}")
    
    async def list_models(self) -> List[str]:
        """List available Anthropic models."""
        return [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ]


class OllamaProvider(AIProvider):
    """Ollama local API provider."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        super().__init__()
        self.base_url = base_url
    
    async def generate(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> AIResponse:
        """Generate response using Ollama."""
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "options": {"num_predict": max_tokens},
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return AIResponse(
                        content=data["message"]["content"],
                        model=model,
                        provider=ProviderType.OLLAMA,
                    )
                else:
                    error_text = await resp.text()
                    raise Exception(f"Ollama error: {error_text}")
    
    async def stream_generate(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream generate response using Ollama."""
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "options": {"num_predict": max_tokens},
            "stream": True,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload
            ) as resp:
                if resp.status == 200:
                    async for line in resp.content:
                        line = line.decode().strip()
                        if line:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                yield data["message"]["content"]
                else:
                    error_text = await resp.text()
                    raise Exception(f"Ollama error: {error_text}")
    
    async def list_models(self) -> List[str]:
        """List available Ollama models."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return [m["name"] for m in data.get("models", [])]
        except Exception:
            pass
        return []


class LocalLlamaCppProvider(AIProvider):
    """Local llama.cpp provider."""
    
    def __init__(self, model_path: str):
        super().__init__()
        self.model_path = model_path
        self.model = None
    
    async def _load_model(self):
        """Load the model."""
        if self.model is None:
            try:
                from llama_cpp import Llama
                self.model = Llama(
                    model_path=self.model_path,
                    n_gpu_layers=-1,  # Use GPU if available
                    n_threads=4,
                )
            except Exception as e:
                raise RuntimeError(f"Failed to load model: {e}")
    
    async def generate(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> AIResponse:
        """Generate response using local llama.cpp."""
        await self._load_model()
        
        # Build prompt from messages
        prompt = "\n".join([f"{m.role}: {m.content}" for m in messages])
        
        result = self.model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        return AIResponse(
            content=result["choices"][0]["text"],
            model=model,
            provider=ProviderType.LOCAL_LLAMA_CPP,
            tokens_used=result["usage"]["completion_tokens"]
        )
    
    async def stream_generate(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream generate response using local llama.cpp."""
        await self._load_model()
        
        prompt = "\n".join([f"{m.role}: {m.content}" for m in messages])
        
        for chunk in self.model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        ):
            if "choices" in chunk:
                yield chunk["choices"][0]["text"]
    
    async def list_models(self) -> List[str]:
        """List available local models."""
        return ["local-model"]


class ProviderFactory:
    """Factory for creating AI providers."""
    
    @staticmethod
    def create(
        provider_type: ProviderType,
        config: Optional[dict] = None
    ) -> AIProvider:
        """Create an AI provider."""
        config = config or {}
        
        if provider_type == ProviderType.OPENAI:
            api_key = config.get("api_key") or config.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key required")
            return OpenAIProvider(api_key)
        
        elif provider_type == ProviderType.ANTHROPIC:
            api_key = config.get("api_key") or config.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("Anthropic API key required")
            return AnthropicProvider(api_key)
        
        elif provider_type == ProviderType.OLLAMA:
            base_url = config.get("base_url", "http://localhost:11434")
            return OllamaProvider(base_url)
        
        elif provider_type == ProviderType.LOCAL_LLAMA_CPP:
            model_path = config.get("model_path")
            if not model_path:
                raise ValueError("Model path required for local llama.cpp")
            return LocalLlamaCppProvider(model_path)
        
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
