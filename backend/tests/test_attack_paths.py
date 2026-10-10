import pytest
from backend.graph_engine.engine import ApplicationGraph, NodeType, EdgeType, GraphNodeData, GraphEdgeData
from backend.attack_paths.analyzer import AttackPathAnalyzer
from backend.validation.planner import TestPlanner


def _build_attack_graph() -> ApplicationGraph:
    g = ApplicationGraph("test")
    g.add_node(GraphNodeData(id="n1", node_type=NodeType.ENDPOINT, label="GET /", url="https://example.com/", method="GET", observed=True))
    g.add_node(GraphNodeData(id="n2", node_type=NodeType.ENDPOINT, label="GET /api/users", url="https://example.com/api/users", method="GET", observed=True))
    g.add_node(GraphNodeData(id="n3", node_type=NodeType.ENDPOINT, label="POST /api/admin/role", url="https://example.com/api/admin/role", method="POST", observed=True))
    g.add_node(GraphNodeData(id="n4", node_type=NodeType.ENDPOINT, label="DELETE /api/admin/users/1", url="https://example.com/api/admin/users/1", method="DELETE", observed=True))
    g.add_edge(GraphEdgeData(id="e1", source_id="n1", target_id="n2", edge_type=EdgeType.NAVIGATION, observed=True))
    g.add_edge(GraphEdgeData(id="e2", source_id="n2", target_id="n3", edge_type=EdgeType.NAVIGATION, observed=True))
    g.add_edge(GraphEdgeData(id="e3", source_id="n3", target_id="n4", edge_type=EdgeType.NAVIGATION, observed=True))
    return g


class TestAttackPathAnalyzer:
    def test_finds_paths(self):
        g = _build_attack_graph()
        analyzer = AttackPathAnalyzer(g)
        paths = analyzer.analyze()
        assert len(paths) > 0

    def test_paths_have_required_fields(self):
        g = _build_attack_graph()
        analyzer = AttackPathAnalyzer(g)
        paths = analyzer.analyze()
        for p in paths:
            assert p.entry_point_label
            assert p.target_label
            assert p.potential_impact
            assert 0 <= p.confidence <= 1
            assert p.recommended_steps

    def test_paths_are_prioritized(self):
        g = _build_attack_graph()
        analyzer = AttackPathAnalyzer(g)
        paths = analyzer.analyze()
        if len(paths) >= 2:
            assert paths[0].priority_score >= paths[-1].priority_score

    def test_empty_graph_no_paths(self):
        g = ApplicationGraph("empty")
        analyzer = AttackPathAnalyzer(g)
        paths = analyzer.analyze()
        assert len(paths) == 0


class TestTestPlanner:
    def test_generates_plans(self):
        g = _build_attack_graph()
        analyzer = AttackPathAnalyzer(g)
        paths = analyzer.analyze()
        planner = TestPlanner()
        plans = planner.generate_plans(paths, g)
        assert len(plans) == len(paths)

    def test_plans_have_required_fields(self):
        g = _build_attack_graph()
        analyzer = AttackPathAnalyzer(g)
        paths = analyzer.analyze()
        planner = TestPlanner()
        plans = planner.generate_plans(paths, g)
        for p in plans:
            assert p.hypothesis
            assert p.test_procedure
            assert p.expected_secure_behavior
            assert p.potential_insecure_outcomes

    def test_plans_have_actionable_procedures(self):
        g = _build_attack_graph()
        analyzer = AttackPathAnalyzer(g)
        paths = analyzer.analyze()
        planner = TestPlanner()
        plans = planner.generate_plans(paths, g)
        for p in plans:
            assert len(p.test_procedure) > 50
            assert "1." in p.test_procedure
