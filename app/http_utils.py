"""Low-level HTTP utilities shared across LLM and embedding providers."""

import json
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request


def normalize_base_url(base_url: str) -> str:
    """Strip whitespace and trailing slashes from a base URL."""
    return base_url.strip().rstrip("/")


def json_post(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    """Send a JSON POST request and return the parsed response."""
    request = urllib_request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urllib_request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")
        raise RuntimeError(detail or str(error)) from error
