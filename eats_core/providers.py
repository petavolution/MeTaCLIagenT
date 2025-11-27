# providers.py - LLM Provider Abstraction Layer
"""
Unified interface for multiple LLM providers.

Supports:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Local models (Ollama, vLLM)
- Mock provider for testing

Based on LiteLLM patterns but zero-dependency by default.
"""

from __future__ import annotations
import os
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Iterator, AsyncIterator
from enum import Enum

# Optional imports
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    httpx = None
    HTTPX_AVAILABLE = False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Role(str, Enum):
    """Message roles."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    """A chat message."""
    role: Role
    content: str

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role.value, "content": self.content}

    @classmethod
    def system(cls, content: str) -> Message:
        return cls(Role.SYSTEM, content)

    @classmethod
    def user(cls, content: str) -> Message:
        return cls(Role.USER, content)

    @classmethod
    def assistant(cls, content: str) -> Message:
        return cls(Role.ASSISTANT, content)


@dataclass
class CompletionResponse:
    """Response from LLM completion."""
    content: str
    model: str
    provider: str
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: str = "stop"
    latency_ms: float = 0.0
    raw: Optional[Dict] = None

    @property
    def input_tokens(self) -> int:
        return self.usage.get("prompt_tokens", 0)

    @property
    def output_tokens(self) -> int:
        return self.usage.get("completion_tokens", 0)

    @property
    def total_tokens(self) -> int:
        return self.usage.get("total_tokens", self.input_tokens + self.output_tokens)


@dataclass
class StreamChunk:
    """A chunk from streaming response."""
    content: str
    finish_reason: Optional[str] = None
    is_final: bool = False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Provider Base Class
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class LLMProvider(ABC):
    """Abstract base for LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @abstractmethod
    def complete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> CompletionResponse:
        """Synchronous completion."""
        pass

    @abstractmethod
    async def acomplete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> CompletionResponse:
        """Async completion."""
        pass

    def chat(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Simple chat interface."""
        messages = []
        if system:
            messages.append(Message.system(system))
        messages.append(Message.user(prompt))

        response = self.complete(messages, **kwargs)
        return response.content

    async def achat(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Async simple chat interface."""
        messages = []
        if system:
            messages.append(Message.system(system))
        messages.append(Message.user(prompt))

        response = await self.acomplete(messages, **kwargs)
        return response.content


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# OpenAI Provider
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class OpenAIProvider(LLMProvider):
    """
    OpenAI API provider.

    Usage:
        provider = OpenAIProvider(api_key="sk-...")
        response = provider.chat("Hello!")

        # Or use environment variable OPENAI_API_KEY
        provider = OpenAIProvider()
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        default_model: str = "gpt-4o-mini",
        timeout: float = 60.0,
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout = timeout

        if not self.api_key:
            raise ValueError("OpenAI API key required (set OPENAI_API_KEY or pass api_key)")

    @property
    def name(self) -> str:
        return "openai"

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def complete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> CompletionResponse:
        if not HTTPX_AVAILABLE:
            raise RuntimeError("httpx required: pip install httpx")

        start = time.time()
        model = model or self.default_model

        payload = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        latency = (time.time() - start) * 1000

        return CompletionResponse(
            content=data["choices"][0]["message"]["content"],
            model=model,
            provider=self.name,
            usage=data.get("usage", {}),
            finish_reason=data["choices"][0].get("finish_reason", "stop"),
            latency_ms=latency,
            raw=data,
        )

    async def acomplete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> CompletionResponse:
        if not HTTPX_AVAILABLE:
            raise RuntimeError("httpx required: pip install httpx")

        start = time.time()
        model = model or self.default_model

        payload = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        latency = (time.time() - start) * 1000

        return CompletionResponse(
            content=data["choices"][0]["message"]["content"],
            model=model,
            provider=self.name,
            usage=data.get("usage", {}),
            finish_reason=data["choices"][0].get("finish_reason", "stop"),
            latency_ms=latency,
            raw=data,
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Anthropic Provider
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AnthropicProvider(LLMProvider):
    """
    Anthropic Claude API provider.

    Usage:
        provider = AnthropicProvider(api_key="sk-ant-...")
        response = provider.chat("Hello!")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.anthropic.com/v1",
        default_model: str = "claude-3-haiku-20240307",
        timeout: float = 60.0,
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout = timeout

        if not self.api_key:
            raise ValueError("Anthropic API key required (set ANTHROPIC_API_KEY)")

    @property
    def name(self) -> str:
        return "anthropic"

    def _headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    def complete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> CompletionResponse:
        if not HTTPX_AVAILABLE:
            raise RuntimeError("httpx required: pip install httpx")

        start = time.time()
        model = model or self.default_model

        # Extract system message
        system_msg = None
        chat_messages = []
        for m in messages:
            if m.role == Role.SYSTEM:
                system_msg = m.content
            else:
                chat_messages.append(m.to_dict())

        payload = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }
        if system_msg:
            payload["system"] = system_msg

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}/messages",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        latency = (time.time() - start) * 1000

        # Extract content
        content = ""
        if data.get("content"):
            content = data["content"][0].get("text", "")

        return CompletionResponse(
            content=content,
            model=model,
            provider=self.name,
            usage={
                "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
                "completion_tokens": data.get("usage", {}).get("output_tokens", 0),
            },
            finish_reason=data.get("stop_reason", "end_turn"),
            latency_ms=latency,
            raw=data,
        )

    async def acomplete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> CompletionResponse:
        if not HTTPX_AVAILABLE:
            raise RuntimeError("httpx required: pip install httpx")

        start = time.time()
        model = model or self.default_model

        # Extract system message
        system_msg = None
        chat_messages = []
        for m in messages:
            if m.role == Role.SYSTEM:
                system_msg = m.content
            else:
                chat_messages.append(m.to_dict())

        payload = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }
        if system_msg:
            payload["system"] = system_msg

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/messages",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        latency = (time.time() - start) * 1000

        content = ""
        if data.get("content"):
            content = data["content"][0].get("text", "")

        return CompletionResponse(
            content=content,
            model=model,
            provider=self.name,
            usage={
                "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
                "completion_tokens": data.get("usage", {}).get("output_tokens", 0),
            },
            finish_reason=data.get("stop_reason", "end_turn"),
            latency_ms=latency,
            raw=data,
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Ollama Provider (Local Models)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class OllamaProvider(LLMProvider):
    """
    Ollama local model provider.

    Uses OpenAI-compatible API endpoint.

    Usage:
        provider = OllamaProvider(model="llama3")
        response = provider.chat("Hello!")
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        default_model: str = "llama3",
        timeout: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "ollama"

    def complete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> CompletionResponse:
        if not HTTPX_AVAILABLE:
            raise RuntimeError("httpx required: pip install httpx")

        start = time.time()
        model = model or self.default_model

        payload = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        latency = (time.time() - start) * 1000

        return CompletionResponse(
            content=data["choices"][0]["message"]["content"],
            model=model,
            provider=self.name,
            usage=data.get("usage", {}),
            finish_reason=data["choices"][0].get("finish_reason", "stop"),
            latency_ms=latency,
            raw=data,
        )

    async def acomplete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> CompletionResponse:
        if not HTTPX_AVAILABLE:
            raise RuntimeError("httpx required: pip install httpx")

        start = time.time()
        model = model or self.default_model

        payload = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        latency = (time.time() - start) * 1000

        return CompletionResponse(
            content=data["choices"][0]["message"]["content"],
            model=model,
            provider=self.name,
            usage=data.get("usage", {}),
            finish_reason=data["choices"][0].get("finish_reason", "stop"),
            latency_ms=latency,
            raw=data,
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Mock Provider (Testing)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class MockProvider(LLMProvider):
    """
    Mock provider for testing.

    Returns configurable responses without making API calls.

    Usage:
        provider = MockProvider(responses=["Hello!", "How can I help?"])
        provider.chat("Hi")  # Returns "Hello!"
        provider.chat("Help")  # Returns "How can I help?"
    """

    def __init__(
        self,
        responses: Optional[List[str]] = None,
        response_fn: Optional[callable] = None,
        latency_ms: float = 100.0,
    ):
        self.responses = responses or ["Mock response"]
        self.response_fn = response_fn
        self.latency_ms = latency_ms
        self._call_count = 0
        self._history: List[Dict] = []

    @property
    def name(self) -> str:
        return "mock"

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def history(self) -> List[Dict]:
        return self._history

    def complete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> CompletionResponse:
        # Record call
        self._call_count += 1
        self._history.append({
            "messages": [m.to_dict() for m in messages],
            "model": model,
            "temperature": temperature,
        })

        # Generate response
        if self.response_fn:
            content = self.response_fn(messages)
        else:
            idx = (self._call_count - 1) % len(self.responses)
            content = self.responses[idx]

        # Simulate latency
        time.sleep(self.latency_ms / 1000)

        return CompletionResponse(
            content=content,
            model=model or "mock-model",
            provider=self.name,
            usage={
                "prompt_tokens": sum(len(m.content.split()) for m in messages),
                "completion_tokens": len(content.split()),
            },
            latency_ms=self.latency_ms,
        )

    async def acomplete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> CompletionResponse:
        import asyncio
        await asyncio.sleep(self.latency_ms / 1000)
        return self.complete(messages, model, temperature, max_tokens, **kwargs)

    def reset(self) -> None:
        """Reset call count and history."""
        self._call_count = 0
        self._history.clear()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Provider Registry
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_providers: Dict[str, type] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
    "mock": MockProvider,
}


def get_provider(
    name: str,
    **kwargs,
) -> LLMProvider:
    """
    Get provider by name.

    Args:
        name: Provider name (openai, anthropic, ollama, mock)
        **kwargs: Provider-specific configuration

    Returns:
        Configured provider instance
    """
    if name not in _providers:
        raise ValueError(f"Unknown provider: {name}. Available: {list(_providers.keys())}")

    return _providers[name](**kwargs)


def register_provider(name: str, provider_class: type) -> None:
    """Register a custom provider."""
    _providers[name] = provider_class


def list_providers() -> List[str]:
    """List available provider names."""
    return list(_providers.keys())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Convenience Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def chat(
    prompt: str,
    provider: str = "openai",
    model: Optional[str] = None,
    system: Optional[str] = None,
    **kwargs,
) -> str:
    """
    Quick chat function.

    Usage:
        response = chat("What is 2+2?")
        response = chat("Hello", provider="anthropic", model="claude-3-haiku-20240307")
    """
    p = get_provider(provider)
    return p.chat(prompt, system=system, model=model, **kwargs)


async def achat(
    prompt: str,
    provider: str = "openai",
    model: Optional[str] = None,
    system: Optional[str] = None,
    **kwargs,
) -> str:
    """Async quick chat."""
    p = get_provider(provider)
    return await p.achat(prompt, system=system, model=model, **kwargs)
