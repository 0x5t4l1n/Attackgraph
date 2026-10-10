from __future__ import annotations
import json
import re

SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie", "x-api-key", "x-auth-token", "proxy-authorization"}


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """Replace sensitive header values with [REDACTED]."""
    result = {}
    for key, value in headers.items():
        if key.lower() in SENSITIVE_HEADERS:
            result[key] = "[REDACTED]"
        else:
            result[key] = value
    return result


SENSITIVE_BODY_KEYS = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|access[_-]?token|refresh[_-]?token|auth|credential|private[_-]?key)",
    re.I,
)


def redact_body(body: str | None, content_type: str | None) -> str | None:
    """Redact sensitive fields in JSON and form-encoded bodies."""
    if not body:
        return body
    if content_type and "json" in content_type.lower():
        try:
            data = json.loads(body)
            return json.dumps(_redact_dict(data))
        except (json.JSONDecodeError, TypeError):
            return body
    if content_type and "form" in content_type.lower():
        parts = []
        for pair in body.split("&"):
            if "=" in pair:
                key, value = pair.split("=", 1)
                if SENSITIVE_BODY_KEYS.search(key):
                    parts.append(f"{key}=[REDACTED]")
                else:
                    parts.append(pair)
            else:
                parts.append(pair)
        return "&".join(parts)
    return body


def _redact_dict(data):
    if isinstance(data, dict):
        return {
            k: "[REDACTED]" if SENSITIVE_BODY_KEYS.search(k) else _redact_dict(v)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [_redact_dict(item) for item in data]
    return data
