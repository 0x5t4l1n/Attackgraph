from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class APIParameter:
    name: str
    location: str  # query, header, path, cookie
    required: bool = False
    schema_type: str | None = None
    description: str | None = None


@dataclass
class APIRequestBody:
    content_types: list[str] = field(default_factory=list)
    required: bool = False
    schema_summary: str | None = None


@dataclass
class APIResponse:
    status_code: str
    description: str | None = None
    content_types: list[str] = field(default_factory=list)


@dataclass
class SecurityScheme:
    name: str
    type: str  # apiKey, http, oauth2, openIdConnect
    location: str | None = None
    scheme: str | None = None


@dataclass
class APIEndpoint:
    path: str
    method: str
    operation_id: str | None = None
    summary: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)
    parameters: list[APIParameter] = field(default_factory=list)
    request_body: APIRequestBody | None = None
    responses: dict[str, APIResponse] = field(default_factory=dict)
    security: list[dict] | None = None
    deprecated: bool = False


@dataclass
class OpenAPISpec:
    title: str = ""
    version: str = ""
    base_url: str | None = None
    endpoints: list[APIEndpoint] = field(default_factory=list)
    security_schemes: dict[str, SecurityScheme] = field(default_factory=dict)
    global_security: list[dict] | None = None
    tags: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


class OpenAPIParser:
    """Parser for OpenAPI 2.0 (Swagger), 3.0, and 3.1 specifications."""

    def parse_file(self, file_path: str) -> OpenAPISpec:
        path = Path(file_path)
        if not path.exists():
            return OpenAPISpec(errors=[f"File not found: {file_path}"])
        content = path.read_text(encoding="utf-8")
        return self.parse_content(content)

    def parse_content(self, content: str) -> OpenAPISpec:
        doc: dict | None = None
        try:
            doc = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            pass
        if doc is None:
            try:
                doc = yaml.safe_load(content)
            except yaml.YAMLError as exc:
                return OpenAPISpec(errors=[f"Failed to parse as JSON or YAML: {exc}"])

        if not isinstance(doc, dict):
            return OpenAPISpec(errors=["Document root must be a JSON/YAML object"])

        version = self._detect_version(doc)
        if version == "2.0":
            return self._parse_v2(doc)
        if version.startswith("3."):
            return self._parse_v3(doc)
        return OpenAPISpec(errors=[f"Unsupported spec version: {version}"])

    # ------------------------------------------------------------------

    def _detect_version(self, doc: dict) -> str:
        if "swagger" in doc:
            return str(doc["swagger"])
        if "openapi" in doc:
            return str(doc["openapi"])
        return "unknown"

    # ------------------------------------------------------------------
    # Swagger / OpenAPI 2.0
    # ------------------------------------------------------------------

    def _parse_v2(self, doc: dict) -> OpenAPISpec:
        errors: list[str] = []
        info = doc.get("info", {})
        host = doc.get("host", "")
        base_path = doc.get("basePath", "")
        schemes = doc.get("schemes", ["https"])
        scheme = schemes[0] if schemes else "https"
        base_url = f"{scheme}://{host}{base_path}" if host else None

        endpoints = self._extract_paths_v2(doc, errors)
        security_schemes = self._parse_security_definitions_v2(doc)
        global_security = doc.get("security")
        tags = [t.get("name", "") for t in doc.get("tags", []) if isinstance(t, dict)]

        return OpenAPISpec(
            title=info.get("title", ""),
            version=info.get("version", ""),
            base_url=base_url,
            endpoints=endpoints,
            security_schemes=security_schemes,
            global_security=global_security,
            tags=tags,
            errors=errors,
        )

    def _extract_paths_v2(self, doc: dict, errors: list[str]) -> list[APIEndpoint]:
        endpoints: list[APIEndpoint] = []
        paths = doc.get("paths", {})
        if not isinstance(paths, dict):
            errors.append("'paths' is not an object")
            return endpoints

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            path_params = self._parse_parameters(doc, path_item.get("parameters", []))
            for method in HTTP_METHODS:
                operation = path_item.get(method)
                if not isinstance(operation, dict):
                    continue
                op_params = self._parse_parameters(doc, operation.get("parameters", []))
                all_params = self._merge_params(path_params, op_params)

                body_params = [p for p in operation.get("parameters", []) if isinstance(p, dict) and p.get("in") == "body"]
                request_body = None
                if body_params:
                    consumes = operation.get("consumes") or doc.get("consumes") or []
                    request_body = APIRequestBody(
                        content_types=consumes,
                        required=body_params[0].get("required", False),
                        schema_summary=self._schema_summary(body_params[0].get("schema", {})),
                    )

                responses: dict[str, APIResponse] = {}
                for status_code, resp_obj in (operation.get("responses") or {}).items():
                    if isinstance(resp_obj, dict):
                        produces = operation.get("produces") or doc.get("produces") or []
                        responses[str(status_code)] = APIResponse(
                            status_code=str(status_code),
                            description=resp_obj.get("description"),
                            content_types=produces,
                        )

                endpoints.append(APIEndpoint(
                    path=path,
                    method=method.upper(),
                    operation_id=operation.get("operationId"),
                    summary=operation.get("summary"),
                    description=operation.get("description"),
                    tags=operation.get("tags", []),
                    parameters=all_params,
                    request_body=request_body,
                    responses=responses,
                    security=operation.get("security"),
                    deprecated=operation.get("deprecated", False),
                ))
        return endpoints

    def _parse_security_definitions_v2(self, doc: dict) -> dict[str, SecurityScheme]:
        schemes: dict[str, SecurityScheme] = {}
        for name, defn in (doc.get("securityDefinitions") or {}).items():
            if not isinstance(defn, dict):
                continue
            schemes[name] = SecurityScheme(
                name=name,
                type=defn.get("type", ""),
                location=defn.get("in"),
                scheme=None,
            )
        return schemes

    # ------------------------------------------------------------------
    # OpenAPI 3.0 / 3.1
    # ------------------------------------------------------------------

    def _parse_v3(self, doc: dict) -> OpenAPISpec:
        errors: list[str] = []
        info = doc.get("info", {})
        servers = doc.get("servers", [])
        base_url = servers[0].get("url") if servers and isinstance(servers[0], dict) else None

        endpoints = self._extract_paths_v3(doc, errors)
        security_schemes = self._parse_security_schemes(doc)
        global_security = doc.get("security")
        tags = [t.get("name", "") for t in doc.get("tags", []) if isinstance(t, dict)]

        return OpenAPISpec(
            title=info.get("title", ""),
            version=info.get("version", ""),
            base_url=base_url,
            endpoints=endpoints,
            security_schemes=security_schemes,
            global_security=global_security,
            tags=tags,
            errors=errors,
        )

    def _extract_paths_v3(self, doc: dict, errors: list[str]) -> list[APIEndpoint]:
        endpoints: list[APIEndpoint] = []
        paths = doc.get("paths", {})
        if not isinstance(paths, dict):
            errors.append("'paths' is not an object")
            return endpoints

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            path_item = self._maybe_resolve(doc, path_item, errors)
            path_params = self._parse_parameters(doc, path_item.get("parameters", []))
            for method in HTTP_METHODS:
                operation = path_item.get(method)
                if not isinstance(operation, dict):
                    continue
                op_params = self._parse_parameters(doc, operation.get("parameters", []))
                all_params = self._merge_params(path_params, op_params)

                request_body = None
                rb = operation.get("requestBody")
                if isinstance(rb, dict):
                    rb = self._maybe_resolve(doc, rb, errors)
                    content_types = list((rb.get("content") or {}).keys())
                    first_schema = {}
                    if content_types:
                        first_schema = (rb.get("content") or {}).get(content_types[0], {}).get("schema", {})
                    request_body = APIRequestBody(
                        content_types=content_types,
                        required=rb.get("required", False),
                        schema_summary=self._schema_summary(first_schema),
                    )

                responses: dict[str, APIResponse] = {}
                for status_code, resp_obj in (operation.get("responses") or {}).items():
                    if isinstance(resp_obj, dict):
                        resp_obj = self._maybe_resolve(doc, resp_obj, errors)
                        ct = list((resp_obj.get("content") or {}).keys())
                        responses[str(status_code)] = APIResponse(
                            status_code=str(status_code),
                            description=resp_obj.get("description"),
                            content_types=ct,
                        )

                endpoints.append(APIEndpoint(
                    path=path,
                    method=method.upper(),
                    operation_id=operation.get("operationId"),
                    summary=operation.get("summary"),
                    description=operation.get("description"),
                    tags=operation.get("tags", []),
                    parameters=all_params,
                    request_body=request_body,
                    responses=responses,
                    security=operation.get("security"),
                    deprecated=operation.get("deprecated", False),
                ))
        return endpoints

    def _parse_security_schemes(self, doc: dict) -> dict[str, SecurityScheme]:
        schemes: dict[str, SecurityScheme] = {}
        components = doc.get("components", {})
        if not isinstance(components, dict):
            return schemes
        for name, defn in (components.get("securitySchemes") or {}).items():
            if not isinstance(defn, dict):
                continue
            schemes[name] = SecurityScheme(
                name=name,
                type=defn.get("type", ""),
                location=defn.get("in"),
                scheme=defn.get("scheme"),
            )
        return schemes

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _parse_parameters(self, doc: dict, params: list) -> list[APIParameter]:
        result: list[APIParameter] = []
        if not isinstance(params, list):
            return result
        for p in params:
            if not isinstance(p, dict):
                continue
            p = self._maybe_resolve(doc, p, [])
            if p.get("in") == "body":
                continue
            schema = p.get("schema", {})
            result.append(APIParameter(
                name=p.get("name", ""),
                location=p.get("in", "query"),
                required=p.get("required", False),
                schema_type=schema.get("type") if isinstance(schema, dict) else p.get("type"),
                description=p.get("description"),
            ))
        return result

    def _resolve_ref(self, doc: dict, ref: str) -> dict | None:
        if not ref.startswith("#/"):
            return None
        parts = ref[2:].split("/")
        current: dict = doc
        for part in parts:
            part = part.replace("~1", "/").replace("~0", "~")
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current if isinstance(current, dict) else None

    def _maybe_resolve(self, doc: dict, obj: dict, errors: list[str]) -> dict:
        ref = obj.get("$ref")
        if not ref:
            return obj
        resolved = self._resolve_ref(doc, ref)
        if resolved is None:
            errors.append(f"Unresolved $ref: {ref}")
            return obj
        return resolved

    @staticmethod
    def _merge_params(
        path_params: list[APIParameter], op_params: list[APIParameter]
    ) -> list[APIParameter]:
        by_key: dict[tuple[str, str], APIParameter] = {}
        for p in path_params:
            by_key[(p.name, p.location)] = p
        for p in op_params:
            by_key[(p.name, p.location)] = p
        return list(by_key.values())

    @staticmethod
    def _schema_summary(schema: dict) -> str | None:
        if not isinstance(schema, dict):
            return None
        stype = schema.get("type", "")
        if stype == "object":
            props = list((schema.get("properties") or {}).keys())
            return f"object({', '.join(props[:8])})" if props else "object"
        if stype == "array":
            items = schema.get("items", {})
            inner = items.get("type", "?") if isinstance(items, dict) else "?"
            return f"array[{inner}]"
        return stype or None
