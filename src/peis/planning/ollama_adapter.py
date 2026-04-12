import json
from typing import Any, Dict, Optional
from urllib import request, error


def invoke_ollama_generate(
    *,
    prompt: str,
    model: str,
    base_url: str = "http://127.0.0.1:11434",
    options: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Invoke Ollama's /api/generate endpoint and return the final response text.

    This adapter is deterministic at the transport layer. Model-level determinism
    still depends on the options and model behavior you choose to supply.
    """

    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    if options is not None:
        payload["options"] = options

    body = json.dumps(payload).encode("utf-8")

    req = request.Request(
        url=f"{base_url.rstrip('/')}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req) as resp:
            response_body = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ollama HTTP error {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"ollama connection error: {exc}") from exc

    try:
        parsed = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON from ollama: {exc}") from exc

    response_text = parsed.get("response")
    if not isinstance(response_text, str):
        raise RuntimeError("ollama response missing string field: response")

    return response_text
