from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from urllib.parse import urlparse

import networkx as nx


class NodeType(str, Enum):
    HOST = "host"
    PAGE = "page"
    ENDPOINT = "endpoint"
    OPERATION = "operation"
    PARAMETER = "parameter"
    AUTH_MECHANISM = "auth_mechanism"
    ROLE = "role"
    WORKFLOW = "workflow"
    SENSITIVE_OP = "sensitive_op"
    DATA_RESOURCE = "data_resource"


class EdgeType(str, Enum):
    NAVIGATION = "navigation"
    REQUEST_SEQUENCE = "request_sequence"
    WORKFLOW_TRANSITION = "workflow_transition"
    RESOURCE_RELATIONSHIP = "resource_relationship"
    AUTH_DEPENDENCY = "auth_dependency"
    AUTHZ_BOUNDARY = "authz_boundary"
    ATTACK_PATH = "attack_path"


@dataclass
class GraphNodeData:
    id: str
    node_type: NodeType
    label: str
    url: str | None = None
    method: str | None = None
    properties: dict = field(default_factory=dict)
    evidence_source: str = "unknown"
    confidence: float = 1.0
    observed: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class GraphEdgeData:
    id: str
    source_id: str
    target_id: str
    edge_type: EdgeType
    label: str = ""
    properties: dict = field(default_factory=dict)
    evidence_source: str = "unknown"
    confidence: float = 1.0
    observed: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _make_id() -> str:
    return str(uuid.uuid4())


class ApplicationGraph:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.graph = nx.MultiDiGraph()
        self._node_index: dict[str, GraphNodeData] = {}
        self._url_index: dict[str, str] = {}

    def add_node(self, data: GraphNodeData) -> str:
        self._node_index[data.id] = data
        self.graph.add_node(data.id, data=data)
        if data.url:
            key = f"{(data.method or 'GET').upper()} {data.url}"
            self._url_index[key] = data.id
        return data.id

    def add_edge(self, data: GraphEdgeData) -> str:
        self.graph.add_edge(data.source_id, data.target_id, key=data.id, data=data)
        return data.id

    def get_node(self, node_id: str) -> GraphNodeData | None:
        return self._node_index.get(node_id)

    def get_edge(self, edge_id: str) -> GraphEdgeData | None:
        for _u, _v, key, edata in self.graph.edges(keys=True, data=True):
            if key == edge_id:
                return edata.get("data")
        return None

    def find_node_by_url(self, url: str, method: str = "GET") -> GraphNodeData | None:
        key = f"{method.upper()} {url}"
        node_id = self._url_index.get(key)
        return self._node_index.get(node_id) if node_id else None

    def get_nodes_by_type(self, node_type: NodeType) -> list[GraphNodeData]:
        return [n for n in self._node_index.values() if n.node_type == node_type]

    def get_edges_by_type(self, edge_type: EdgeType) -> list[GraphEdgeData]:
        result = []
        for _u, _v, edata in self.graph.edges(data=True):
            d = edata.get("data")
            if d and d.edge_type == edge_type:
                result.append(d)
        return result

    def get_neighbors(self, node_id: str) -> list[GraphNodeData]:
        if node_id not in self.graph:
            return []
        return [self._node_index[n] for n in self.graph.neighbors(node_id) if n in self._node_index]

    def get_incoming(self, node_id: str) -> list[GraphEdgeData]:
        if node_id not in self.graph:
            return []
        result = []
        for _u, _v, edata in self.graph.in_edges(node_id, data=True):
            d = edata.get("data")
            if d:
                result.append(d)
        return result

    def get_outgoing(self, node_id: str) -> list[GraphEdgeData]:
        if node_id not in self.graph:
            return []
        result = []
        for _u, _v, edata in self.graph.out_edges(node_id, data=True):
            d = edata.get("data")
            if d:
                result.append(d)
        return result

    def find_paths(self, source_id: str, target_id: str, max_length: int = 10) -> list[list[str]]:
        try:
            return list(nx.all_simple_paths(self.graph, source_id, target_id, cutoff=max_length))
        except (nx.NodeNotFound, nx.NetworkXError):
            return []

    def get_subgraph(self, node_ids: list[str]) -> dict:
        sub = self.graph.subgraph(node_ids)
        nodes = [self._node_index[n] for n in sub.nodes() if n in self._node_index]
        edges = []
        for _u, _v, edata in sub.edges(data=True):
            d = edata.get("data")
            if d:
                edges.append(d)
        return {"nodes": nodes, "edges": edges}

    def get_statistics(self) -> dict:
        type_counts: dict[str, int] = {}
        for n in self._node_index.values():
            t = n.node_type.value if isinstance(n.node_type, Enum) else str(n.node_type)
            type_counts[t] = type_counts.get(t, 0) + 1
        edge_type_counts: dict[str, int] = {}
        for _u, _v, edata in self.graph.edges(data=True):
            d = edata.get("data")
            if d:
                t = d.edge_type.value if isinstance(d.edge_type, Enum) else str(d.edge_type)
                edge_type_counts[t] = edge_type_counts.get(t, 0) + 1
        observed = sum(1 for n in self._node_index.values() if n.observed)
        inferred = len(self._node_index) - observed
        return {
            "total_nodes": len(self._node_index),
            "total_edges": self.graph.number_of_edges(),
            "node_types": type_counts,
            "edge_types": edge_type_counts,
            "observed_nodes": observed,
            "inferred_nodes": inferred,
            "density": nx.density(self.graph) if len(self.graph) > 1 else 0.0,
            "components": nx.number_weakly_connected_components(self.graph),
        }

    def merge_from_crawl(self, crawl_results: list[dict]) -> dict:
        stats = {"nodes_added": 0, "edges_added": 0, "nodes_merged": 0}
        hosts_seen: set[str] = set()

        for result in crawl_results:
            url = result.get("url", "")
            method = result.get("method", "GET")
            parsed = urlparse(url)
            host = parsed.hostname or ""

            if host and host not in hosts_seen:
                hosts_seen.add(host)
                self.add_node(GraphNodeData(
                    id=_make_id(), node_type=NodeType.HOST, label=host,
                    url=f"{parsed.scheme}://{host}", evidence_source="crawl", observed=True,
                ))
                stats["nodes_added"] += 1

            existing = self.find_node_by_url(url, method)
            if existing:
                stats["nodes_merged"] += 1
                endpoint_id = existing.id
            else:
                node = GraphNodeData(
                    id=_make_id(), node_type=NodeType.ENDPOINT,
                    label=f"{method} {parsed.path or '/'}", url=url, method=method,
                    properties={"status_code": result.get("status_code"), "content_type": result.get("content_type")},
                    evidence_source="crawl", observed=True,
                )
                self.add_node(node)
                endpoint_id = node.id
                stats["nodes_added"] += 1

            parent_url = result.get("parent_url")
            if parent_url:
                parent = self.find_node_by_url(parent_url, "GET")
                if parent:
                    self.add_edge(GraphEdgeData(
                        id=_make_id(), source_id=parent.id, target_id=endpoint_id,
                        edge_type=EdgeType.NAVIGATION, label="navigates to",
                        evidence_source="crawl", observed=True,
                    ))
                    stats["edges_added"] += 1

            for form in result.get("forms", []):
                for fld in form.get("fields", []):
                    p_node = GraphNodeData(
                        id=_make_id(), node_type=NodeType.PARAMETER,
                        label=fld.get("name", "unknown"),
                        properties={"field_type": fld.get("type"), "form_action": form.get("action"), "form_method": form.get("method")},
                        evidence_source="crawl", observed=True,
                    )
                    self.add_node(p_node)
                    self.add_edge(GraphEdgeData(
                        id=_make_id(), source_id=endpoint_id, target_id=p_node.id,
                        edge_type=EdgeType.RESOURCE_RELATIONSHIP, label="has parameter",
                        evidence_source="crawl", observed=True,
                    ))
                    stats["nodes_added"] += 1
                    stats["edges_added"] += 1

        return stats

    def merge_from_burp(self, burp_items: list[dict]) -> dict:
        stats = {"nodes_added": 0, "edges_added": 0, "nodes_merged": 0}
        prev_endpoint_id: str | None = None

        for item in sorted(burp_items, key=lambda x: x.get("timestamp", "")):
            url = item.get("url", "")
            method = item.get("method", "GET")
            parsed = urlparse(url)

            existing = self.find_node_by_url(url, method)
            if existing:
                stats["nodes_merged"] += 1
                endpoint_id = existing.id
            else:
                node = GraphNodeData(
                    id=_make_id(), node_type=NodeType.ENDPOINT,
                    label=f"{method} {parsed.path or '/'}", url=url, method=method,
                    properties={"status_code": item.get("status_code"), "content_type": item.get("content_type")},
                    evidence_source="burp", observed=True,
                )
                self.add_node(node)
                endpoint_id = node.id
                stats["nodes_added"] += 1

            if prev_endpoint_id and prev_endpoint_id != endpoint_id:
                self.add_edge(GraphEdgeData(
                    id=_make_id(), source_id=prev_endpoint_id, target_id=endpoint_id,
                    edge_type=EdgeType.REQUEST_SEQUENCE, label="followed by",
                    evidence_source="burp", observed=True, confidence=0.7,
                ))
                stats["edges_added"] += 1

            headers = item.get("headers", {})
            if headers:
                auth_keys = {"authorization", "cookie", "x-api-key", "x-auth-token"}
                if any(k.lower() in auth_keys for k in headers):
                    auth_label = "session_auth"
                    existing_auth = [n for n in self.get_nodes_by_type(NodeType.AUTH_MECHANISM) if n.label == auth_label]
                    if existing_auth:
                        auth_id = existing_auth[0].id
                    else:
                        auth_node = GraphNodeData(
                            id=_make_id(), node_type=NodeType.AUTH_MECHANISM,
                            label=auth_label, evidence_source="burp", observed=True,
                        )
                        self.add_node(auth_node)
                        auth_id = auth_node.id
                        stats["nodes_added"] += 1
                    self.add_edge(GraphEdgeData(
                        id=_make_id(), source_id=endpoint_id, target_id=auth_id,
                        edge_type=EdgeType.AUTH_DEPENDENCY, label="requires auth",
                        evidence_source="burp", observed=True,
                    ))
                    stats["edges_added"] += 1

            prev_endpoint_id = endpoint_id

        return stats

    def merge_from_openapi(self, spec_data: dict) -> dict:
        stats = {"nodes_added": 0, "edges_added": 0, "nodes_merged": 0}
        base_url = spec_data.get("base_url", "")

        for name, scheme in spec_data.get("security_schemes", {}).items():
            self.add_node(GraphNodeData(
                id=_make_id(), node_type=NodeType.AUTH_MECHANISM, label=name,
                properties={"type": scheme.get("type"), "scheme": scheme.get("scheme")},
                evidence_source="openapi", observed=False,
            ))
            stats["nodes_added"] += 1

        for ep in spec_data.get("endpoints", []):
            path = ep.get("path", "")
            method = ep.get("method", "GET").upper()
            full_url = f"{base_url.rstrip('/')}{path}" if base_url else path

            existing = self.find_node_by_url(full_url, method)
            if existing:
                existing.properties["from_spec"] = True
                existing.properties["operation_id"] = ep.get("operation_id")
                stats["nodes_merged"] += 1
            else:
                node = GraphNodeData(
                    id=_make_id(), node_type=NodeType.ENDPOINT,
                    label=f"{method} {path}", url=full_url, method=method,
                    properties={"operation_id": ep.get("operation_id"), "from_spec": True, "tags": ep.get("tags", [])},
                    evidence_source="openapi", observed=False,
                )
                self.add_node(node)
                stats["nodes_added"] += 1

                for param in ep.get("parameters", []):
                    p_node = GraphNodeData(
                        id=_make_id(), node_type=NodeType.PARAMETER,
                        label=param.get("name", ""),
                        properties={"location": param.get("location"), "type": param.get("schema_type"), "required": param.get("required")},
                        evidence_source="openapi", observed=False,
                    )
                    self.add_node(p_node)
                    self.add_edge(GraphEdgeData(
                        id=_make_id(), source_id=node.id, target_id=p_node.id,
                        edge_type=EdgeType.RESOURCE_RELATIONSHIP, label="has parameter",
                        evidence_source="openapi", observed=False,
                    ))
                    stats["nodes_added"] += 1
                    stats["edges_added"] += 1

        return stats

    def to_dict(self) -> dict:
        nodes = []
        for data in self._node_index.values():
            nodes.append({
                "id": data.id,
                "type": data.node_type.value if isinstance(data.node_type, Enum) else str(data.node_type),
                "label": data.label,
                "url": data.url,
                "method": data.method,
                "properties": data.properties,
                "evidence_source": data.evidence_source,
                "confidence": data.confidence,
                "observed": data.observed,
            })
        edges = []
        for _u, _v, edata in self.graph.edges(data=True):
            d = edata.get("data")
            if d:
                edges.append({
                    "id": d.id,
                    "source": d.source_id,
                    "target": d.target_id,
                    "type": d.edge_type.value if isinstance(d.edge_type, Enum) else str(d.edge_type),
                    "label": d.label,
                    "properties": d.properties,
                    "evidence_source": d.evidence_source,
                    "confidence": d.confidence,
                    "observed": d.observed,
                })
        return {
            "project_id": self.project_id,
            "nodes": nodes,
            "edges": edges,
            "statistics": self.get_statistics(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> ApplicationGraph:
        graph = cls(data.get("project_id", ""))
        for n in data.get("nodes", []):
            node = GraphNodeData(
                id=n["id"], node_type=NodeType(n["type"]), label=n["label"],
                url=n.get("url"), method=n.get("method"),
                properties=n.get("properties", {}),
                evidence_source=n.get("evidence_source", "unknown"),
                confidence=n.get("confidence", 1.0),
                observed=n.get("observed", True),
            )
            graph.add_node(node)
        for e in data.get("edges", []):
            edge = GraphEdgeData(
                id=e["id"], source_id=e["source"], target_id=e["target"],
                edge_type=EdgeType(e["type"]), label=e.get("label", ""),
                properties=e.get("properties", {}),
                evidence_source=e.get("evidence_source", "unknown"),
                confidence=e.get("confidence", 1.0),
                observed=e.get("observed", True),
            )
            graph.add_edge(edge)
        return graph
