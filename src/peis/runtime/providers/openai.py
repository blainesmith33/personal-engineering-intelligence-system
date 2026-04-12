from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openai import OpenAI
from openai import OpenAIError

from peis.runtime.gateway.config import GatewayConfig


class OpenAIProviderError(ValueError):
    """Raised when the OpenAI provider fails or returns invalid data."""


@dataclass(frozen=True, slots=True)
class OpenAIChatRequest:
    """
    Canonical request shape for one OpenAI reasoning/refinement call.
    """

    system_prompt: str
    user_prompt: str
    temperature: float = 0.0

    def __post_init__(self) -> None:
        if (
            not isinstance(self.system_prompt, str)
            or not self.system_prompt.strip()
        ):
            raise OpenAIProviderError(
                "system_prompt must be a non-empty string"
            )

        if not isinstance(self.user_prompt, str) or not self.user_prompt.strip():
            raise OpenAIProviderError("user_prompt must be a non-empty string")

        if not isinstance(self.temperature, (int, float)):
            raise OpenAIProviderError("temperature must be numeric")

        if self.temperature < 0:
            raise OpenAIProviderError("temperature must be >= 0")


@dataclass(frozen=True, slots=True)
class OpenAIChatResult:
    """
    Canonical normalized result from one OpenAI response call.
    """

    model: str
    response_text: str
    raw_response: Any

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model.strip():
            raise OpenAIProviderError("model must be a non-empty string")

        if (
            not isinstance(self.response_text, str)
            or not self.response_text.strip()
        ):
            raise OpenAIProviderError(
                "response_text must be a non-empty string"
            )


class OpenAIProvider:
    """
    Thin provider client for OpenAI-backed refinement/finalization.

    Responsibilities:
    - enforce request invariants
    - call the configured OpenAI model
    - normalize response payloads
    - raise deterministic, explicit errors on failure
    """

    def __init__(self, config: GatewayConfig) -> None:
        if not isinstance(config, GatewayConfig):
            raise OpenAIProviderError("config must be a GatewayConfig")

        self._config = config
        self._client = OpenAI(
            api_key=config.openai_api_key,
            timeout=config.openai_timeout_seconds,
        )

    @property
    def model_name(self) -> str:
        return self._config.openai_model_name

    def generate(
        self,
        request: OpenAIChatRequest,
    ) -> OpenAIChatResult:
        if not isinstance(request, OpenAIChatRequest):
            raise OpenAIProviderError(
                "request must be an OpenAIChatRequest"
            )

        try:
            response = self._client.responses.create(
                model=self.model_name,
                temperature=float(request.temperature),
                input=[
                    {
                        "role": "system",
                        "content": request.system_prompt.strip(),
                    },
                    {
                        "role": "user",
                        "content": request.user_prompt.strip(),
                    },
                ],
            )
        except OpenAIError as exc:
            raise OpenAIProviderError(
                f"openai request failed: {exc}"
            ) from exc
        except Exception as exc:
            raise OpenAIProviderError(
                f"unexpected openai failure: {exc}"
            ) from exc

        response_text = getattr(response, "output_text", None)
        if not isinstance(response_text, str) or not response_text.strip():
            raise OpenAIProviderError(
                "openai response missing non-empty output_text"
            )

        model = getattr(response, "model", None)
        if not isinstance(model, str) or not model.strip():
            model = self.model_name

        return OpenAIChatResult(
            model=model.strip(),
            response_text=response_text.strip(),
            raw_response=response,
        )