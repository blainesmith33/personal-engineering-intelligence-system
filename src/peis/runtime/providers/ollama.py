from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from peis.runtime.gateway.config import GatewayConfig


class OllamaProviderError(ValueError):
    """Raised when the Ollama provider fails or returns invalid data."""


@dataclass(frozen=True, slots=True)
class OllamaGenerationRequest:
    """
    Canonical request shape for one Ollama generation call.
    """

    prompt: str
    system_prompt: str | None = None
    temperature: float = 0.0
    stream: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise OllamaProviderError("prompt must be a non-empty string")

        if self.system_prompt is not None:
            if (
                not isinstance(self.system_prompt, str)
                or not self.system_prompt.strip()
            ):
                raise OllamaProviderError(
                    "system_prompt must be None or a non-empty string"
                )

        if not isinstance(self.temperature, (int, float)):
            raise OllamaProviderError("temperature must be numeric")

        if self.temperature < 0:
            raise OllamaProviderError("temperature must be >= 0")

        if not isinstance(self.stream, bool):
            raise OllamaProviderError("stream must be a bool")


@dataclass(frozen=True, slots=True)
class OllamaGenerationResult:
    """
    Canonical normalized result from one Ollama generation call.
    """

    model: str
    response_text: str
    raw_response: dict[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model.strip():
            raise OllamaProviderError("model must be a non-empty string")

        if (
            not isinstance(self.response_text, str)
            or not self.response_text.strip()
        ):
            raise OllamaProviderError(
                "response_text must be a non-empty string"
            )

        if not isinstance(self.raw_response, dict):
            raise OllamaProviderError("raw_response must be a dict")


class OllamaProvider:
    """
    Thin provider client for the configured Ollama endpoint.

    Responsibilities:
    - enforce request invariants
    - call the configured Ollama generate endpoint
    - normalize response payloads
    - raise deterministic, explicit errors on failure
    """

    def __init__(self, config: GatewayConfig) -> None:
        if not isinstance(config, GatewayConfig):
            raise OllamaProviderError("config must be a GatewayConfig")

        self._config = config

    @property
    def model_name(self) -> str:
        return self._config.local_model_name

    @property
    def generate_url(self) -> str:
        return self._config.ollama_generate_url

    def generate(
        self,
        request: OllamaGenerationRequest,
    ) -> OllamaGenerationResult:
        if not isinstance(request, OllamaGenerationRequest):
            raise OllamaProviderError(
                "request must be an OllamaGenerationRequest"
            )

        payload = self._build_payload(request)

        try:
            response = requests.post(
                self.generate_url,
                json=payload,
                timeout=self._config.local_timeout_seconds,
            )
        except requests.RequestException as exc:
            raise OllamaProviderError(
                f"ollama request failed: {exc}"
            ) from exc

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            body = _safe_text(response)
            raise OllamaProviderError(
                f"ollama returned HTTP {response.status_code}: {body}"
            ) from exc

        try:
            raw = response.json()
        except ValueError as exc:
            raise OllamaProviderError(
                "ollama returned non-JSON response"
            ) from exc

        if not isinstance(raw, dict):
            raise OllamaProviderError(
                "ollama returned non-object JSON payload"
            )

        response_text = raw.get("response")
        if not isinstance(response_text, str) or not response_text.strip():
            raise OllamaProviderError(
                "ollama response missing non-empty 'response' field"
            )

        model = raw.get("model", self.model_name)
        if not isinstance(model, str) or not model.strip():
            model = self.model_name

        return OllamaGenerationResult(
            model=model.strip(),
            response_text=response_text.strip(),
            raw_response=raw,
        )

    def _build_payload(
        self,
        request: OllamaGenerationRequest,
    ) -> dict[str, Any]:
        prompt = request.prompt.strip()

        if request.system_prompt is not None:
            prompt = (
                f"{request.system_prompt.strip()}\n\n"
                f"{prompt}"
            )

        return {
            "model": self.model_name,
            "prompt": prompt,
            "stream": request.stream,
            "options": {
                "temperature": float(request.temperature),
            },
        }


def _safe_text(response: requests.Response) -> str:
    try:
        body = response.text.strip()
    except Exception:
        body = ""

    if not body:
        return "<empty response body>"

    if len(body) > 500:
        return body[:500] + "...<truncated>"

    return body