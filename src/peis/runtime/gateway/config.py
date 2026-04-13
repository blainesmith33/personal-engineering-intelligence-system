from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final


class GatewayConfigError(ValueError):
    """Raised when gateway configuration is invalid."""


DEFAULT_OLLAMA_BASE_URL: Final[str] = "http://192.168.1.253:11434"
DEFAULT_OLLAMA_GENERATE_PATH: Final[str] = "/api/generate"
DEFAULT_OPENAI_MODEL: Final[str] = "gpt-5.4"
DEFAULT_LOCAL_MODEL: Final[str] = "qwen2.5:3b"
DEFAULT_HOST: Final[str] = "0.0.0.0"
DEFAULT_PORT: Final[int] = 8010

DEFAULT_LOCAL_TIMEOUT_SECONDS: Final[float] = 120.0
DEFAULT_OPENAI_TIMEOUT_SECONDS: Final[float] = 120.0
DEFAULT_REQUEST_TIMEOUT_SECONDS: Final[float] = 180.0
DEFAULT_CANCEL_POLL_INTERVAL_SECONDS: Final[float] = 0.25

DEFAULT_MAX_LOCAL_TURNS: Final[int] = 2
DEFAULT_MAX_OPENAI_TURNS: Final[int] = 2
DEFAULT_MAX_TOTAL_TURNS: Final[int] = 4

DEFAULT_REQUIRE_APPROVAL: Final[bool] = False
DEFAULT_ALLOW_CANCELLATION: Final[bool] = True
DEFAULT_STRICT_JSON_ONLY: Final[bool] = True
DEFAULT_ENABLE_PIPELINE_EXECUTION: Final[bool] = False
DEFAULT_PERSIST_GATEWAY_RUNS: Final[bool] = False
DEFAULT_LOG_PROMPTS: Final[bool] = False


def _parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    raise GatewayConfigError(
        f"invalid boolean value {value!r}; expected one of "
        "{'1','true','yes','on','0','false','no','off'}"
    )


def _parse_int(
    value: str | None,
    *,
    default: int,
    field_name: str,
    minimum: int | None = None,
) -> int:
    if value is None:
        result = default
    else:
        try:
            result = int(value.strip())
        except (TypeError, ValueError) as exc:
            raise GatewayConfigError(
                f"{field_name} must be an integer"
            ) from exc

    if minimum is not None and result < minimum:
        raise GatewayConfigError(
            f"{field_name} must be >= {minimum}, got {result}"
        )
    return result


def _parse_float(
    value: str | None,
    *,
    default: float,
    field_name: str,
    minimum: float | None = None,
) -> float:
    if value is None:
        result = default
    else:
        try:
            result = float(value.strip())
        except (TypeError, ValueError) as exc:
            raise GatewayConfigError(
                f"{field_name} must be a float"
            ) from exc

    if minimum is not None and result < minimum:
        raise GatewayConfigError(
            f"{field_name} must be >= {minimum}, got {result}"
        )
    return result


def _require_non_empty(value: str | None, *, field_name: str) -> str:
    if value is None:
        raise GatewayConfigError(f"{field_name} is required")

    normalized = value.strip()
    if not normalized:
        raise GatewayConfigError(f"{field_name} must not be empty")
    return normalized


def get_gateway_startup_requirements() -> dict[str, object]:
    """
    Return the canonical startup requirements for the PEIS gateway.

    This is intended for launch-time validation and user-facing startup errors.
    """
    return {
        "required_environment_variables": ["OPENAI_API_KEY"],
        "default_host": DEFAULT_HOST,
        "default_port": DEFAULT_PORT,
        "default_ollama_base_url": DEFAULT_OLLAMA_BASE_URL,
        "default_local_model_name": DEFAULT_LOCAL_MODEL,
        "default_openai_model_name": DEFAULT_OPENAI_MODEL,
    }


def build_gateway_startup_error_message(error: GatewayConfigError) -> str:
    """
    Convert a GatewayConfigError into a launch-time error message that makes the
    missing or invalid requirement explicit.
    """
    requirements = get_gateway_startup_requirements()

    lines = [
        "PEIS gateway startup failed.",
        "",
        f"Configuration error: {error}",
        "",
        "Gateway startup requirements:",
        f"- Required environment variables: {', '.join(requirements['required_environment_variables'])}",
        f"- Default host: {requirements['default_host']}",
        f"- Default port: {requirements['default_port']}",
        f"- Default Ollama base URL: {requirements['default_ollama_base_url']}",
        f"- Default local model: {requirements['default_local_model_name']}",
        f"- Default OpenAI model: {requirements['default_openai_model_name']}",
    ]

    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if openai_api_key is None or not openai_api_key.strip():
        lines.extend(
            [
                "",
                "OPENAI_API_KEY is missing or empty.",
                "Set it before starting the gateway.",
            ]
        )

    return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class GatewayConfig:
    """
    Authoritative runtime configuration for the PEIS gateway layer.

    This config governs:
    - network binding for the gateway API
    - upstream model providers
    - turn-budget enforcement
    - cancellation / approval behavior
    - strict output mode
    - optional PEIS pipeline execution
    """

    host: str
    port: int

    ollama_base_url: str
    ollama_generate_url: str
    local_model_name: str

    openai_api_key: str
    openai_model_name: str

    local_timeout_seconds: float
    openai_timeout_seconds: float
    request_timeout_seconds: float
    cancel_poll_interval_seconds: float

    max_local_turns: int
    max_openai_turns: int
    max_total_turns: int

    require_approval: bool
    allow_cancellation: bool
    strict_json_only: bool
    enable_pipeline_execution: bool
    persist_gateway_runs: bool
    log_prompts: bool

    gateway_emitted_by: str
    local_agent_name: str
    openai_agent_name: str

    def __post_init__(self) -> None:
        if not self.host.strip():
            raise GatewayConfigError("host must not be empty")
        if self.port < 1 or self.port > 65535:
            raise GatewayConfigError("port must be between 1 and 65535")

        if not self.ollama_base_url.strip():
            raise GatewayConfigError("ollama_base_url must not be empty")
        if not self.ollama_generate_url.strip():
            raise GatewayConfigError("ollama_generate_url must not be empty")
        if not self.local_model_name.strip():
            raise GatewayConfigError("local_model_name must not be empty")

        if not self.openai_api_key.strip():
            raise GatewayConfigError("openai_api_key must not be empty")
        if not self.openai_model_name.strip():
            raise GatewayConfigError("openai_model_name must not be empty")

        if self.local_timeout_seconds <= 0:
            raise GatewayConfigError("local_timeout_seconds must be > 0")
        if self.openai_timeout_seconds <= 0:
            raise GatewayConfigError("openai_timeout_seconds must be > 0")
        if self.request_timeout_seconds <= 0:
            raise GatewayConfigError("request_timeout_seconds must be > 0")
        if self.cancel_poll_interval_seconds <= 0:
            raise GatewayConfigError(
                "cancel_poll_interval_seconds must be > 0"
            )

        if self.max_local_turns < 1:
            raise GatewayConfigError("max_local_turns must be >= 1")
        if self.max_openai_turns < 1:
            raise GatewayConfigError("max_openai_turns must be >= 1")
        if self.max_total_turns < 2:
            raise GatewayConfigError("max_total_turns must be >= 2")

        required_total = self.max_local_turns + self.max_openai_turns
        if self.max_total_turns > required_total:
            raise GatewayConfigError(
                "max_total_turns cannot exceed "
                "max_local_turns + max_openai_turns"
            )

        if self.max_total_turns < 2:
            raise GatewayConfigError(
                "max_total_turns must allow at least one local turn and "
                "one OpenAI turn"
            )

        if not self.gateway_emitted_by.strip():
            raise GatewayConfigError("gateway_emitted_by must not be empty")
        if not self.local_agent_name.strip():
            raise GatewayConfigError("local_agent_name must not be empty")
        if not self.openai_agent_name.strip():
            raise GatewayConfigError("openai_agent_name must not be empty")


def load_gateway_config() -> GatewayConfig:
    """
    Load gateway configuration from environment variables.

    Required:
    - OPENAI_API_KEY

    Optional:
    - PEIS_GATEWAY_HOST
    - PEIS_GATEWAY_PORT
    - PEIS_OLLAMA_BASE_URL
    - PEIS_OLLAMA_GENERATE_PATH
    - PEIS_LOCAL_MODEL_NAME
    - PEIS_OPENAI_MODEL_NAME
    - PEIS_LOCAL_TIMEOUT_SECONDS
    - PEIS_OPENAI_TIMEOUT_SECONDS
    - PEIS_REQUEST_TIMEOUT_SECONDS
    - PEIS_CANCEL_POLL_INTERVAL_SECONDS
    - PEIS_MAX_LOCAL_TURNS
    - PEIS_MAX_OPENAI_TURNS
    - PEIS_MAX_TOTAL_TURNS
    - PEIS_REQUIRE_APPROVAL
    - PEIS_ALLOW_CANCELLATION
    - PEIS_STRICT_JSON_ONLY
    - PEIS_ENABLE_PIPELINE_EXECUTION
    - PEIS_PERSIST_GATEWAY_RUNS
    - PEIS_LOG_PROMPTS
    - PEIS_GATEWAY_EMITTED_BY
    - PEIS_LOCAL_AGENT_NAME
    - PEIS_OPENAI_AGENT_NAME
    """
    host = os.environ.get("PEIS_GATEWAY_HOST", DEFAULT_HOST).strip()
    port = _parse_int(
        os.environ.get("PEIS_GATEWAY_PORT"),
        default=DEFAULT_PORT,
        field_name="PEIS_GATEWAY_PORT",
        minimum=1,
    )

    ollama_base_url = os.environ.get(
        "PEIS_OLLAMA_BASE_URL",
        DEFAULT_OLLAMA_BASE_URL,
    ).rstrip("/")
    ollama_generate_path = os.environ.get(
        "PEIS_OLLAMA_GENERATE_PATH",
        DEFAULT_OLLAMA_GENERATE_PATH,
    ).strip()
    if not ollama_generate_path.startswith("/"):
        raise GatewayConfigError(
            "PEIS_OLLAMA_GENERATE_PATH must start with '/'"
        )

    ollama_generate_url = f"{ollama_base_url}{ollama_generate_path}"

    local_model_name = os.environ.get(
        "PEIS_LOCAL_MODEL_NAME",
        DEFAULT_LOCAL_MODEL,
    ).strip()

    openai_api_key = _require_non_empty(
        os.environ.get("OPENAI_API_KEY"),
        field_name="OPENAI_API_KEY",
    )
    openai_model_name = os.environ.get(
        "PEIS_OPENAI_MODEL_NAME",
        DEFAULT_OPENAI_MODEL,
    ).strip()

    local_timeout_seconds = _parse_float(
        os.environ.get("PEIS_LOCAL_TIMEOUT_SECONDS"),
        default=DEFAULT_LOCAL_TIMEOUT_SECONDS,
        field_name="PEIS_LOCAL_TIMEOUT_SECONDS",
        minimum=0.001,
    )
    openai_timeout_seconds = _parse_float(
        os.environ.get("PEIS_OPENAI_TIMEOUT_SECONDS"),
        default=DEFAULT_OPENAI_TIMEOUT_SECONDS,
        field_name="PEIS_OPENAI_TIMEOUT_SECONDS",
        minimum=0.001,
    )
    request_timeout_seconds = _parse_float(
        os.environ.get("PEIS_REQUEST_TIMEOUT_SECONDS"),
        default=DEFAULT_REQUEST_TIMEOUT_SECONDS,
        field_name="PEIS_REQUEST_TIMEOUT_SECONDS",
        minimum=0.001,
    )
    cancel_poll_interval_seconds = _parse_float(
        os.environ.get("PEIS_CANCEL_POLL_INTERVAL_SECONDS"),
        default=DEFAULT_CANCEL_POLL_INTERVAL_SECONDS,
        field_name="PEIS_CANCEL_POLL_INTERVAL_SECONDS",
        minimum=0.001,
    )

    max_local_turns = _parse_int(
        os.environ.get("PEIS_MAX_LOCAL_TURNS"),
        default=DEFAULT_MAX_LOCAL_TURNS,
        field_name="PEIS_MAX_LOCAL_TURNS",
        minimum=1,
    )
    max_openai_turns = _parse_int(
        os.environ.get("PEIS_MAX_OPENAI_TURNS"),
        default=DEFAULT_MAX_OPENAI_TURNS,
        field_name="PEIS_MAX_OPENAI_TURNS",
        minimum=1,
    )
    max_total_turns = _parse_int(
        os.environ.get("PEIS_MAX_TOTAL_TURNS"),
        default=DEFAULT_MAX_TOTAL_TURNS,
        field_name="PEIS_MAX_TOTAL_TURNS",
        minimum=2,
    )

    require_approval = _parse_bool(
        os.environ.get("PEIS_REQUIRE_APPROVAL"),
        default=DEFAULT_REQUIRE_APPROVAL,
    )
    allow_cancellation = _parse_bool(
        os.environ.get("PEIS_ALLOW_CANCELLATION"),
        default=DEFAULT_ALLOW_CANCELLATION,
    )
    strict_json_only = _parse_bool(
        os.environ.get("PEIS_STRICT_JSON_ONLY"),
        default=DEFAULT_STRICT_JSON_ONLY,
    )
    enable_pipeline_execution = _parse_bool(
        os.environ.get("PEIS_ENABLE_PIPELINE_EXECUTION"),
        default=DEFAULT_ENABLE_PIPELINE_EXECUTION,
    )
    persist_gateway_runs = _parse_bool(
        os.environ.get("PEIS_PERSIST_GATEWAY_RUNS"),
        default=DEFAULT_PERSIST_GATEWAY_RUNS,
    )
    log_prompts = _parse_bool(
        os.environ.get("PEIS_LOG_PROMPTS"),
        default=DEFAULT_LOG_PROMPTS,
    )

    gateway_emitted_by = os.environ.get(
        "PEIS_GATEWAY_EMITTED_BY",
        "peis.runtime.gateway",
    ).strip()
    local_agent_name = os.environ.get(
        "PEIS_LOCAL_AGENT_NAME",
        "local_ai",
    ).strip()
    openai_agent_name = os.environ.get(
        "PEIS_OPENAI_AGENT_NAME",
        "chatgpt",
    ).strip()

    return GatewayConfig(
        host=host,
        port=port,
        ollama_base_url=ollama_base_url,
        ollama_generate_url=ollama_generate_url,
        local_model_name=local_model_name,
        openai_api_key=openai_api_key,
        openai_model_name=openai_model_name,
        local_timeout_seconds=local_timeout_seconds,
        openai_timeout_seconds=openai_timeout_seconds,
        request_timeout_seconds=request_timeout_seconds,
        cancel_poll_interval_seconds=cancel_poll_interval_seconds,
        max_local_turns=max_local_turns,
        max_openai_turns=max_openai_turns,
        max_total_turns=max_total_turns,
        require_approval=require_approval,
        allow_cancellation=allow_cancellation,
        strict_json_only=strict_json_only,
        enable_pipeline_execution=enable_pipeline_execution,
        persist_gateway_runs=persist_gateway_runs,
        log_prompts=log_prompts,
        gateway_emitted_by=gateway_emitted_by,
        local_agent_name=local_agent_name,
        openai_agent_name=openai_agent_name,
    )