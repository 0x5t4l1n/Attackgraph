import pytest
from backend.burp_import.parser import BurpParser
from backend.burp_import.redaction import redact_headers, redact_body


class TestBurpParser:
    def test_parse_sample(self, burp_xml):
        parser = BurpParser()
        result = parser.parse_xml(burp_xml)
        assert len(result.items) == 3
        assert result.items[0].method == "GET"
        assert result.items[0].url == "https://example.com/api/users"
        assert result.items[0].status_code == 200

    def test_parse_base64_request(self, burp_xml):
        parser = BurpParser()
        result = parser.parse_xml(burp_xml)
        req = result.parsed_requests[0]
        assert req.method == "GET"
        assert "example.com" in req.headers.get("Host", "")

    def test_parse_non_base64(self, burp_xml):
        parser = BurpParser()
        result = parser.parse_xml(burp_xml)
        assert len(result.items) >= 3
        admin_item = result.items[2]
        assert admin_item.path == "/admin/settings"

    def test_parse_empty_xml(self):
        parser = BurpParser()
        result = parser.parse_xml(b'<?xml version="1.0"?><items></items>')
        assert len(result.items) == 0

    def test_parse_malformed_xml(self):
        parser = BurpParser()
        result = parser.parse_xml(b"not xml at all")
        assert len(result.errors) > 0


class TestRedaction:
    def test_redact_auth_header(self):
        headers = {"Authorization": "Bearer secret123", "Content-Type": "application/json"}
        redacted = redact_headers(headers)
        assert redacted["Authorization"] == "[REDACTED]"
        assert redacted["Content-Type"] == "application/json"

    def test_redact_cookie_header(self):
        headers = {"Cookie": "session=abc123"}
        redacted = redact_headers(headers)
        assert redacted["Cookie"] == "[REDACTED]"

    def test_redact_json_body(self):
        body = '{"username": "admin", "password": "secret123"}'
        result = redact_body(body, "application/json")
        assert "secret123" not in result
        assert "[REDACTED]" in result

    def test_redact_form_body(self):
        body = "username=admin&password=secret123&action=login"
        result = redact_body(body, "application/x-www-form-urlencoded")
        assert "secret123" not in result

    def test_no_redaction_on_safe_body(self):
        body = '{"name": "test", "value": 42}'
        result = redact_body(body, "application/json")
        assert result == body
