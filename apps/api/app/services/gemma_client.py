import base64
import json
import mimetypes
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from app.core.config import get_settings


def image_base64(image_file: Path) -> str:
    return base64.b64encode(image_file.read_bytes()).decode("ascii")


def image_data_url(image_file: Path) -> str:
    content_type = mimetypes.guess_type(image_file.name)[0] or "image/jpeg"
    return f"data:{content_type};base64,{image_base64(image_file)}"


def _chat_completions_url(api_base: str) -> str:
    base = api_base.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


def _ollama_chat_url(api_base: str) -> str:
    parts = urlsplit(api_base.rstrip("/"))
    path = parts.path.rstrip("/")

    for suffix in ("/v1/chat/completions", "/chat/completions", "/v1"):
        if path.endswith(suffix):
            path = path[: -len(suffix)]
            break

    path = f"{path}/api/chat" if path else "/api/chat"
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def _headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _post_json(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=_headers(get_settings().gemma_api_key),
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _openai_chat_content(response_payload: dict[str, Any]) -> str:
    message = (
        response_payload.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    if isinstance(message, list):
        return " ".join(
            str(item.get("text", ""))
            for item in message
            if isinstance(item, dict)
        )
    return str(message)


def _ollama_chat_content(response_payload: dict[str, Any]) -> str:
    message = response_payload.get("message", {})
    if isinstance(message, dict):
        return str(message.get("content", ""))
    return str(response_payload.get("response", ""))


def _prefer_ollama_native(api_base: str, model: str) -> bool:
    path = urlsplit(api_base.rstrip("/")).path.rstrip("/")
    return path in {"", "/v1"} and ":" in model


def send_gemma_vision_chat(
    *,
    system_prompt: str,
    user_prompt: str,
    image_file: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    settings = get_settings()
    encoded_image = image_base64(image_file)

    openai_payload = {
        "model": settings.gemma_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_data_url(image_file)},
                    },
                ],
            },
        ],
        "temperature": 0.1,
    }
    ollama_payload = {
        "model": settings.gemma_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": user_prompt,
                "images": [encoded_image],
            },
        ],
        "stream": False,
        "options": {"temperature": 0.1},
    }

    attempts = (
        (
            "ollama_chat",
            _ollama_chat_url(settings.gemma_api_base),
            ollama_payload,
            _ollama_chat_content,
        ),
        (
            "openai_chat_completions",
            _chat_completions_url(settings.gemma_api_base),
            openai_payload,
            _openai_chat_content,
        ),
    )
    if not _prefer_ollama_native(settings.gemma_api_base, settings.gemma_model):
        attempts = (attempts[1], attempts[0])

    failures: list[str] = []
    for provider, url, payload, content_getter in attempts:
        try:
            response_payload = _post_json(url, payload, timeout_seconds)
        except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
            failures.append(f"{provider}: {exc}")
            continue

        return {
            "status": "completed",
            "provider_api": provider,
            "content": content_getter(response_payload),
        }

    return {
        "status": "failed",
        "reason": "; ".join(failures) or "Gemma request failed.",
    }
