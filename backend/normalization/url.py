from __future__ import annotations

import re
from urllib.parse import parse_qs, unquote, urlencode, urlparse, urlunparse


def normalize_url(url: str) -> str:
    """Normalize URL: lowercase scheme+host, remove default ports, sort query params, remove fragments, normalize path."""
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower() if parsed.hostname else ""
    port = parsed.port

    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None

    netloc = host
    if port:
        netloc = f"{host}:{port}"

    path = _normalize_path(parsed.path or "/")

    query_params = parse_qs(parsed.query, keep_blank_values=True)
    sorted_query = (
        urlencode(
            sorted(((k, v[0] if len(v) == 1 else v) for k, v in query_params.items())),
            doseq=True,
        )
        if query_params
        else ""
    )
    return urlunparse((scheme, netloc, path, "", sorted_query, ""))


def _normalize_path(path: str) -> str:
    """Resolve path segments, remove double slashes."""
    parts = path.split("/")
    resolved: list[str] = []
    for part in parts:
        if part == "..":
            if resolved and resolved[-1] != "":
                resolved.pop()
        elif part == ".":
            continue
        elif part == "" and resolved:
            continue
        else:
            resolved.append(part)
    result = "/".join(resolved)
    if not result.startswith("/"):
        result = "/" + result
    if result != "/" and result.endswith("/"):
        result = result.rstrip("/")
    return result


def is_same_endpoint(
    url1: str, url2: str, method1: str = "GET", method2: str = "GET"
) -> bool:
    """Check if two URL+method combinations refer to the same endpoint."""
    return normalize_url(url1) == normalize_url(url2) and method1.upper() == method2.upper()


_ID_PATTERNS = [
    re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
    ),
    re.compile(r"^\d+$"),
    re.compile(r"^[0-9a-f]{24}$", re.I),
]


def extract_path_pattern(url: str) -> str:
    """Replace UUID/numeric/ObjectId path segments with {id} placeholders."""
    parsed = urlparse(url)
    parts = parsed.path.split("/")
    patterned = []
    for part in parts:
        if any(p.match(part) for p in _ID_PATTERNS):
            patterned.append("{id}")
        else:
            patterned.append(part)
    return "/".join(patterned)


def canonicalize_url(url: str) -> str:
    """Full normalization pipeline."""
    url = unquote(url)
    return normalize_url(url)
