from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, List, Literal, Optional


class SchemaError(ValueError):
    """Raised when schema validation fails."""


# -------------------------
# REQUEST SCHEMA
# -------------------------

@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: Literal["system", "user", "assistant"]
    content: str

    def __post_init__(self) -> None:
        if self.role not in {"system", "user", "assistant"}:
            raise SchemaError(f"invalid role: {self.role}")

        if not isinstance(self.content, str) or not self.content.strip():
            raise SchemaError("content must be a non-empty string")


@dataclass(frozen=True, slots=True)
class ChatCompletionRequest:
    model: str
    messages: List[ChatMessage]
    temperature: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model.strip():
            raise SchemaError("model must be a non-empty string")

        if not isinstance(self.messages, list) or not self.messages:
            raise SchemaError("messages must be a non-empty list")

        for i, msg in enumerate(self.messages):
            if not isinstance(msg, ChatMessage):
                raise SchemaError(f"messages[{i}] must be ChatMessage")

        if not isinstance(self.temperature, (int, float)):
            raise SchemaError("temperature must be numeric")

        if self.temperature < 0:
            raise SchemaError("temperature must be >= 0")

    def get_last_user_message(self) -> str:
        for msg in reversed(self.messages):
            if msg.role == "user":
                return msg.content.strip()
        raise SchemaError("no user message found")


# -------------------------
# RESPONSE SCHEMA
# -------------------------

@dataclass(frozen=True, slots=True)
class ChatCompletionChoice:
    index: int
    message: ChatMessage
    finish_reason: Literal["stop"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "message": {
                "role": self.message.role,
                "content": self.message.content,
            },
            "finish_reason": self.finish_reason,
        }


@dataclass(frozen=True, slots=True)
class Usage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    def to_dict(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass(frozen=True, slots=True)
class ChatCompletionResponse:
    id: str
    object: Literal["chat.completion"]
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Usage

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "object": self.object,
            "created": self.created,
            "model": self.model,
            "choices": [c.to_dict() for c in self.choices],
            "usage": self.usage.to_dict(),
        }


# -------------------------
# FACTORY HELPERS
# -------------------------

def build_response(
    *,
    model: str,
    content: str,
) -> ChatCompletionResponse:
    if not isinstance(content, str) or not content.strip():
        raise SchemaError("content must be non-empty")

    message = ChatMessage(role="assistant", content=content.strip())

    choice = ChatCompletionChoice(
        index=0,
        message=message,
        finish_reason="stop",
    )

    # Token usage placeholder (deterministic, not estimated)
    usage = Usage(
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
    )

    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex}",
        object="chat.completion",
        created=int(time.time()),
        model=model,
        choices=[choice],
        usage=usage,
    )