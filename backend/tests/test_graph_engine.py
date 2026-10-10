import pytest
from backend.graph_engine.engine import ApplicationGraph, NodeType, EdgeType, GraphNodeData, GraphEdgeData


class TestApplicationGraph:
    def test_add_and_get_node(self):
        g = ApplicationGraph("test")
        node = GraphNodeData(id="n1", node_type=NodeType.ENDPOINT, label="GET /api/users")
        g.add_node(node)
        assert g.get_node("n1") is not None
        assert g.get_node("n1").label == "GET /api/users"

    def test_add_and_get_edge(self):
        g = ApplicationGraph("test")
        g.add_node(GraphNodeData(id="n1", node_type=NodeType.ENDPOINT, label="A"))
        g.add_node(GraphNodeData(id="n2", node_type=NodeType.ENDPOINT, label="B"))
        g.add_edge(GraphEdgeData(id="e1", source_id="n1", target_id="n2", edge_type=EdgeType.NAVIGATION))
        assert g.get_edge("e1") is not None

    def test_find_node_by_url(self):
        g = ApplicationGraph("test")
        g.add_node(GraphNodeData(id="n1", node_type=NodeType.ENDPOINT, label="GET /users", url="https://example.com/users", method="GET"))
        found = g.find_node_by_url("https://example.com/users", "GET")
        assert found is not None
        assert found.id == "n1"

    def test_get_nodes_by_type(self):
        g = ApplicationGraph("test")
        g.add_node(GraphNodeData(id="n1", node_type=NodeType.ENDPOINT, label="A"))
        g.add_node(GraphNodeData(id="n2", node_type=NodeType.HOST, label="B"))
        g.add_node(GraphNodeData(id="n3", node_type=NodeType.ENDPOINT, label="C"))
        endpoints = g.get_nodes_by_type(NodeType.ENDPOINT)
        assert len(endpoints) == 2

    def test_get_neighbors(self):
        g = ApplicationGraph("test")
        g.add_node(GraphNodeData(id="n1", node_type=NodeType.ENDPOINT, label="A"))
        g.add_node(GraphNodeData(id="n2", node_type=NodeType.ENDPOINT, label="B"))
        g.add_edge(GraphEdgeData(id="e1", source_id="n1", target_id="n2", edge_type=EdgeType.NAVIGATION))
        neighbors = g.get_neighbors("n1")
        assert len(neighbors) == 1
        assert neighbors[0].id == "n2"

    def test_find_paths(self):
        g = ApplicationGraph("test")
        g.add_node(GraphNodeData(id="n1", node_type=NodeType.ENDPOINT, label="A"))
        g.add_node(GraphNodeData(id="n2", node_type=NodeType.ENDPOINT, label="B"))
        g.add_node(GraphNodeData(id="n3", node_type=NodeType.ENDPOINT, label="C"))
        g.add_edge(GraphEdgeData(id="e1", source_id="n1", target_id="n2", edge_type=EdgeType.NAVIGATION))
        g.add_edge(GraphEdgeData(id="e2", source_id="n2", target_id="n3", edge_type=EdgeType.NAVIGATION))
        paths = g.find_paths("n1", "n3")
        assert len(paths) == 1
        assert paths[0] == ["n1", "n2", "n3"]

    def test_statistics(self):
        g = ApplicationGraph("test")
        g.add_node(GraphNodeData(id="n1", node_type=NodeType.ENDPOINT, label="A"))
        g.add_node(GraphNodeData(id="n2", node_type=NodeType.HOST, label="B"))
        g.add_edge(GraphEdgeData(id="e1", source_id="n1", target_id="n2", edge_type=EdgeType.NAVIGATION))
        stats = g.get_statistics()
        assert stats["total_nodes"] == 2
        assert stats["total_edges"] == 1

    def test_merge_from_crawl(self):
        g = ApplicationGraph("test")
        results = [
            {"url": "https://example.com/", "method": "GET", "status_code": 200, "content_type": "text/html", "parent_url": None, "forms": []},
            {"url": "https://example.com/about", "method": "GET", "status_code": 200, "content_type": "text/html", "parent_url": "https://example.com/", "forms": []},
        ]
        stats = g.merge_from_crawl(results)
        assert stats["nodes_added"] >= 3  # host + 2 endpoints
        assert stats["edges_added"] >= 1  # navigation

    def test_to_dict_and_from_dict(self):
        g = ApplicationGraph("test")
        g.add_node(GraphNodeData(id="n1", node_type=NodeType.ENDPOINT, label="A", url="https://x.com/a", method="GET"))
        g.add_edge(GraphEdgeData(id="e1", source_id="n1", target_id="n1", edge_type=EdgeType.NAVIGATION))
        data = g.to_dict()
        g2 = ApplicationGraph.from_dict(data)
        assert g2.get_node("n1") is not None
        assert g2.get_statistics()["total_nodes"] == 1

    def test_merge_from_burp(self):
        g = ApplicationGraph("test")
        items = [
            {"url": "https://example.com/api/users", "method": "GET", "status_code": 200, "content_type": "application/json", "headers": {"Authorization": "Bearer x"}, "timestamp": "2026-01-01"},
        ]
        stats = g.merge_from_burp(items)
        assert stats["nodes_added"] >= 1

    def test_merge_from_openapi(self):
        g = ApplicationGraph("test")
        spec = {
            "base_url": "https://example.com",
            "endpoints": [
                {"path": "/api/users", "method": "GET", "operation_id": "listUsers", "parameters": [], "tags": []},
            ],
            "security_schemes": {"bearer": {"type": "http", "scheme": "bearer"}},
        }
        stats = g.merge_from_openapi(spec)
        assert stats["nodes_added"] >= 2  # auth + endpoint
