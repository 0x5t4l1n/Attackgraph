import pytest
from backend.openapi_import.parser import OpenAPIParser


class TestOpenAPIParser:
    def test_parse_v3(self, openapi_yaml):
        parser = OpenAPIParser()
        spec = parser.parse_content(openapi_yaml)
        assert spec.title == "Test API"
        assert spec.version == "1.0.0"
        assert len(spec.endpoints) >= 6
        assert spec.base_url == "https://example.com"

    def test_endpoints_extracted(self, openapi_yaml):
        parser = OpenAPIParser()
        spec = parser.parse_content(openapi_yaml)
        methods = {(e.path, e.method.upper()) for e in spec.endpoints}
        assert ("/api/users", "GET") in methods
        assert ("/api/users", "POST") in methods
        assert ("/api/users/{id}", "GET") in methods
        assert ("/api/users/{id}", "PUT") in methods
        assert ("/api/users/{id}", "DELETE") in methods

    def test_security_schemes(self, openapi_yaml):
        parser = OpenAPIParser()
        spec = parser.parse_content(openapi_yaml)
        assert "bearerAuth" in spec.security_schemes
        assert spec.security_schemes["bearerAuth"].type == "http"
        assert spec.security_schemes["bearerAuth"].scheme == "bearer"

    def test_parameters_extracted(self, openapi_yaml):
        parser = OpenAPIParser()
        spec = parser.parse_content(openapi_yaml)
        get_user = next((e for e in spec.endpoints if e.path == "/api/users/{id}" and e.method.upper() == "GET"), None)
        assert get_user is not None
        assert len(get_user.parameters) >= 1
        assert get_user.parameters[0].name == "id"
        assert get_user.parameters[0].location == "path"

    def test_parse_json_content(self):
        content = '{"openapi": "3.0.0", "info": {"title": "Test", "version": "1.0"}, "paths": {}}'
        parser = OpenAPIParser()
        spec = parser.parse_content(content)
        assert spec.title == "Test"

    def test_parse_swagger_v2(self):
        content = """
swagger: "2.0"
info:
  title: Legacy API
  version: "1.0"
host: api.example.com
basePath: /v1
schemes:
  - https
paths:
  /users:
    get:
      operationId: listUsers
      produces:
        - application/json
      responses:
        "200":
          description: OK
"""
        parser = OpenAPIParser()
        spec = parser.parse_content(content)
        assert spec.title == "Legacy API"
        assert len(spec.endpoints) >= 1
        assert any("users" in e.path for e in spec.endpoints)
