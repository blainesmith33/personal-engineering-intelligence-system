from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from peis.runtime.gateway.config import load_gateway_config
from peis.runtime.gateway.schemas import (
    ChatCompletionRequest,
    ChatMessage,
    SchemaError,
    build_response,
)
from peis.runtime.gateway.orchestrator import (
    GatewayOrchestrator,
    GatewayOrchestratorError,
)

app = FastAPI(title="PEIS Gateway", version="1.0.0")

try:
    _config = load_gateway_config()
    _orchestrator = GatewayOrchestrator(_config)
except Exception as exc:
    raise RuntimeError(f"failed to initialize gateway: {exc}") from exc


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/models")
def list_models() -> JSONResponse:
    return JSONResponse(
        content={
            "object": "list",
            "data": [
                {
                    "id": "peis-gateway",
                    "object": "model",
                    "created": 0,
                    "owned_by": "peis",
                }
            ],
        }
    )


@app.post("/v1/chat/completions")
def chat_completions(payload: dict):
    try:
        request = _parse_request(payload)
        user_message = request.get_last_user_message()

        result = _orchestrator.run(user_message)

        response = build_response(
            model="peis-gateway",
            content=result.final_output,
        )

        return JSONResponse(content=response.to_dict())

    except SchemaError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except GatewayOrchestratorError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"unexpected error: {exc}",
        ) from exc


def _parse_request(payload: dict) -> ChatCompletionRequest:
    if not isinstance(payload, dict):
        raise SchemaError("request payload must be an object")

    model = payload.get("model")
    messages_raw = payload.get("messages")

    if not isinstance(messages_raw, list):
        raise SchemaError("messages must be a list")

    messages = []
    for i, item in enumerate(messages_raw):
        if not isinstance(item, dict):
            raise SchemaError(f"messages[{i}] must be an object")

        role = item.get("role")
        content = item.get("content")

        messages.append(ChatMessage(role=role, content=content))

    temperature = payload.get("temperature", 0.0)

    return ChatCompletionRequest(
        model=model,
        messages=messages,
        temperature=temperature,
    )