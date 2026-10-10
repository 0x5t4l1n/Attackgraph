import pytest
from backend.graph_engine.engine import ApplicationGraph, NodeType, EdgeType, GraphNodeData, GraphEdgeData
from backend.security_rules.engine import RulesEngine


def _build_test_graph() -> ApplicationGraph:
    g = ApplicationGraph("test")
    g.add_node(GraphNodeData(id="n1", node_type=NodeType.ENDPOINT, label="GET /api/users", url="https://example.com/api/users", method="GET"))
    g.add_node(GraphNodeData(id="n2", node_type=NodeType.ENDPOINT, label="GET /api/users/1", url="https://example.com/api/users/1", method="GET"))
    g.add_node(GraphNodeData(id="n3", node_type=NodeType.ENDPOINT, label="DELETE /api/admin/users/1", url="https://example.com/api/admin/users/1", method="DELETE"))
    g.add_node(GraphNodeData(id="n4", node_type=NodeType.ENDPOINT, label="GET /debug/info", url="https://example.com/debug/info", method="GET"))
    g.add_node(GraphNodeData(id="n5", node_type=NodeType.ENDPOINT, label="PUT /api/account/settings", url="https://example.com/api/account/settings", method="PUT"))
    g.add_node(GraphNodeData(id="n6", node_type=NodeType.PARAMETER, label="username", properties={"field_type": "text"}))
    g.add_node(GraphNodeData(id="n7", node_type=NodeType.PARAMETER, label="email"))
    g.add_edge(GraphEdgeData(id="e1", source_id="n1", target_id="n2", edge_type=EdgeType.NAVIGATION))
    g.add_edge(GraphEdgeData(id="e2", source_id="n5", target_id="n6", edge_type=EdgeType.RESOURCE_RELATIONSHIP))
    g.add_edge(GraphEdgeData(id="e3", source_id="n5", target_id="n7", edge_type=EdgeType.RESOURCE_RELATIONSHIP))
    return g


class TestRulesEngine:
    def test_analyze_returns_findings(self):
        g = _build_test_graph()
        engine = RulesEngine()
        findings = engine.analyze(g)
        assert len(findings) > 0

    def test_all_findings_are_hypotheses(self):
        g = _build_test_graph()
        engine = RulesEngine()
        findings = engine.analyze(g)
        for f in findings:
            assert f.validation_status == "hypothesis"

    def test_unauthenticated_sensitive_detected(self):
        g = _build_test_graph()
        engine = RulesEngine()
        findings = engine.analyze(g)
        unauth = [f for f in findings if f.detection_rule == "unauth-sensitive"]
        assert len(unauth) > 0

    def test_potential_idor_detected(self):
        g = _build_test_graph()
        engine = RulesEngine()
        findings = engine.analyze(g)
        idor = [f for f in findings if f.detection_rule == "potential-idor"]
        assert len(idor) > 0

    def test_debug_endpoint_detected(self):
        g = _build_test_graph()
        engine = RulesEngine()
        findings = engine.analyze(g)
        debug = [f for f in findings if f.detection_rule == "exposed-debug"]
        assert len(debug) > 0

    def test_insufficient_auth_detected(self):
        g = _build_test_graph()
        engine = RulesEngine()
        findings = engine.analyze(g)
        insufficient = [f for f in findings if f.detection_rule == "insufficient-auth"]
        assert len(insufficient) > 0

    def test_analyze_with_specific_rule(self):
        g = _build_test_graph()
        engine = RulesEngine()
        findings = engine.analyze_with_rule(g, "exposed-debug")
        assert all(f.detection_rule == "exposed-debug" for f in findings)

    def test_empty_graph_no_findings(self):
        g = ApplicationGraph("empty")
        engine = RulesEngine()
        findings = engine.analyze(g)
        assert len(findings) == 0

    def test_findings_have_required_fields(self):
        g = _build_test_graph()
        engine = RulesEngine()
        findings = engine.analyze(g)
        for f in findings:
            assert f.title
            assert f.description
            assert f.detection_rule
            assert f.severity in ("info", "low", "medium", "high", "critical")
            assert 0 <= f.confidence <= 1
