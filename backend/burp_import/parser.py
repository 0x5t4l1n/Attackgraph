from __future__ import annotations

import base64
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from lxml import etree


@dataclass
class BurpItem:
    timestamp: str | None
    url: str
    host: str
    port: int
    protocol: str
    method: str
    path: str
    request_raw: bytes | None
    response_raw: bytes | None
    status_code: int | None
    mime_type: str | None
    comment: str | None


@dataclass
class ParsedRequest:
    method: str
    url: str
    path: str
    headers: dict[str, str]
    body: str | None
    content_type: str | None
    cookies: dict[str, str]
    query_params: dict[str, str]


@dataclass
class ParsedResponse:
    status_code: int
    headers: dict[str, str]
    body: str | None
    content_type: str | None
    set_cookies: dict[str, str]


@dataclass
class BurpImportResult:
    items: list[BurpItem] = field(default_factory=list)
    parsed_requests: list[ParsedRequest] = field(default_factory=list)
    parsed_responses: list[ParsedResponse] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    skipped: int = 0
    total: int = 0


class BurpParser:
    """Parser for Burp Suite XML export files."""

    def parse_file(self, file_path: str) -> BurpImportResult:
        path = Path(file_path)
        if not path.exists():
            return BurpImportResult(errors=[f"File not found: {file_path}"])
        return self.parse_xml(path.read_bytes())

    def parse_xml(self, xml_content: str | bytes) -> BurpImportResult:
        if isinstance(xml_content, str):
            xml_content = xml_content.encode("utf-8")

        result = BurpImportResult()
        try:
            root = etree.fromstring(xml_content)
        except etree.XMLSyntaxError as exc:
            result.errors.append(f"XML parse error: {exc}")
            return result

        items_elems = root.findall("item") if root.tag == "items" else root.findall(".//item")
        result.total = len(items_elems)
        seen: set[tuple[str, str]] = set()

        for idx, item_elem in enumerate(items_elems):
            try:
                burp_item = self._parse_item(item_elem)
                if burp_item is None:
                    result.errors.append(f"Item {idx}: could not parse (missing required fields)")
                    result.skipped += 1
                    continue

                key = (burp_item.method.upper(), self._normalize_url(burp_item.url))
                if key in seen:
                    result.skipped += 1
                else:
                    seen.add(key)

                result.items.append(burp_item)

                req = self._parse_raw_request(burp_item.request_raw, burp_item.url)
                if req:
                    result.parsed_requests.append(req)

                resp = self._parse_raw_response(burp_item.response_raw)
                if resp:
                    result.parsed_responses.append(resp)

            except Exception as exc:  # noqa: BLE001
                result.errors.append(f"Item {idx}: {exc}")
                result.skipped += 1

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_item(self, elem) -> BurpItem | None:
        url = self._text(elem, "url")
        method = self._text(elem, "method")
        if not url or not method:
            return None

        host = self._text(elem, "host") or urlparse(url).hostname or ""
        port_str = self._text(elem, "port")
        protocol = self._text(elem, "protocol") or urlparse(url).scheme or "https"

        try:
            port = int(port_str) if port_str else (443 if protocol == "https" else 80)
        except ValueError:
            port = 443 if protocol == "https" else 80

        status_str = self._text(elem, "status")
        try:
            status_code = int(status_str) if status_str else None
        except ValueError:
            status_code = None

        return BurpItem(
            timestamp=self._text(elem, "time"),
            url=url,
            host=host,
            port=port,
            protocol=protocol,
            method=method,
            path=self._text(elem, "path") or urlparse(url).path or "/",
            request_raw=self._decode_base64_field(elem, "request"),
            response_raw=self._decode_base64_field(elem, "response"),
            status_code=status_code,
            mime_type=self._text(elem, "mimetype"),
            comment=self._text(elem, "comment"),
        )

    def _parse_raw_request(self, raw: bytes | None, fallback_url: str = "") -> ParsedRequest | None:
        if not raw:
            return None
        try:
            text = raw.decode("utf-8", errors="replace")
        except Exception:
            return None

        header_part, _, body = text.partition("\r\n\r\n")
        if not header_part:
            header_part, _, body = text.partition("\n\n")

        lines = header_part.split("\r\n") if "\r\n" in header_part else header_part.split("\n")
        if not lines:
            return None

        request_line = lines[0]
        parts = request_line.split(" ", 2)
        method = parts[0] if parts else "GET"
        raw_path = parts[1] if len(parts) > 1 else "/"

        headers: dict[str, str] = {}
        for line in lines[1:]:
            if ":" in line:
                key, _, value = line.partition(":")
                headers[key.strip()] = value.strip()

        content_type = headers.get("Content-Type") or headers.get("content-type")

        cookies: dict[str, str] = {}
        cookie_header = headers.get("Cookie") or headers.get("cookie") or ""
        for pair in cookie_header.split(";"):
            pair = pair.strip()
            if "=" in pair:
                k, _, v = pair.partition("=")
                cookies[k.strip()] = v.strip()

        parsed_url = urlparse(fallback_url)
        query_params: dict[str, str] = {}
        qs = urlparse(raw_path).query or parsed_url.query
        for k, vals in parse_qs(qs, keep_blank_values=True).items():
            query_params[k] = vals[0] if vals else ""

        return ParsedRequest(
            method=method,
            url=fallback_url,
            path=raw_path.split("?")[0],
            headers=headers,
            body=body if body else None,
            content_type=content_type,
            cookies=cookies,
            query_params=query_params,
        )

    def _parse_raw_response(self, raw: bytes | None) -> ParsedResponse | None:
        if not raw:
            return None
        try:
            text = raw.decode("utf-8", errors="replace")
        except Exception:
            return None

        header_part, _, body = text.partition("\r\n\r\n")
        if not header_part:
            header_part, _, body = text.partition("\n\n")

        lines = header_part.split("\r\n") if "\r\n" in header_part else header_part.split("\n")
        if not lines:
            return None

        status_line = lines[0]
        status_parts = status_line.split(" ", 2)
        try:
            status_code = int(status_parts[1]) if len(status_parts) > 1 else 0
        except ValueError:
            status_code = 0

        headers: dict[str, str] = {}
        for line in lines[1:]:
            if ":" in line:
                key, _, value = line.partition(":")
                headers[key.strip()] = value.strip()

        content_type = headers.get("Content-Type") or headers.get("content-type")

        set_cookies: dict[str, str] = {}
        for key, value in headers.items():
            if key.lower() == "set-cookie":
                cookie_part = value.split(";")[0].strip()
                if "=" in cookie_part:
                    k, _, v = cookie_part.partition("=")
                    set_cookies[k.strip()] = v.strip()

        return ParsedResponse(
            status_code=status_code,
            headers=headers,
            body=body if body else None,
            content_type=content_type,
            set_cookies=set_cookies,
        )

    def _decode_base64_field(self, parent_elem, tag: str) -> bytes | None:
        elem = parent_elem.find(tag)
        if elem is None or not elem.text:
            return None
        is_b64 = (elem.get("base64") or "").lower() == "true"
        if is_b64:
            try:
                return base64.b64decode(elem.text)
            except Exception:
                return None
        try:
            return elem.text.encode("utf-8")
        except Exception:
            return None

    @staticmethod
    def _text(elem, tag: str) -> str | None:
        child = elem.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        return None

    @staticmethod
    def _normalize_url(url: str) -> str:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        scheme = (parsed.scheme or "https").lower()
        path = parsed.path or "/"
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        params = sorted(parse_qs(parsed.query, keep_blank_values=True).items())
        qs = "&".join(f"{k}={v[0]}" for k, v in params) if params else ""
        port = parsed.port
        if port and ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
            port = None
        netloc = f"{host}:{port}" if port else host
        return f"{scheme}://{netloc}{path}" + (f"?{qs}" if qs else "")
