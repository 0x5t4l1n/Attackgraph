from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field

from backend.graph_engine.engine import ApplicationGraph, NodeType, EdgeType

SENSITIVE_PATTERNS = re.compile(
    r"(admin|delete|role|permission|settings|config|user|account|payment|password|token|key|billing|profile|manage)",
    re.I,
)


@dataclass
class CandidateAttackPath:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entry_point: str = ""
    entry_point_label: str = ""
    target_operation: str = ""
    target_label: str = ""
    intermediate_steps: list[dict] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    unverified_assumptions: list[str] = field(default_factory=list)
    potential_impact: str = ""
    confidence: float = 0.5
    priority_score: float = 0.0
    recommended_steps: list[str] = field(default_factory=list)


class AttackPathAnalyzer:
    def __init__(self, graph: ApplicationGraph):
        self.graph = graph

    def analyze(self) -> list[CandidateAttackPath]:
        paths: list[CandidateAttackPath] = []
        paths.extend(self._find_privilege_escalation_paths())
        paths.extend(self._find_auth_bypass_paths())
        paths.extend(self._find_data_access_paths())
        paths.extend(self._find_workflow_abuse_paths())
        return self._prioritize(paths)

    def _find_entry_points(self) -> list[str]:
        entries = []
        for ep in self.graph.get_nodes_by_type(NodeType.ENDPOINT):
            if not ep.observed:
                continue
            incoming_auth = any(
                e.edge_type == EdgeType.AUTH_DEPENDENCY
                for e in self.graph.get_outgoing(ep.id)
            )
            if not incoming_auth:
                entries.append(ep.id)
            elif ep.method and ep.method.upper() == "GET":
                entries.append(ep.id)
        return entries

    def _find_sensitive_targets(self) -> list[str]:
        targets = []
        for node in self.graph._node_index.values():
            if node.node_type == NodeType.SENSITIVE_OP:
                targets.append(node.id)
            elif node.node_type == NodeType.ENDPOINT and SENSITIVE_PATTERNS.search(node.label):
                targets.append(node.id)
        return targets

    def _find_privilege_escalation_paths(self) -> list[CandidateAttackPath]:
        results = []
        entries = self._find_entry_points()
        targets = self._find_sensitive_targets()

        for entry_id in entries[:20]:
            entry = self.graph.get_node(entry_id)
            if not entry:
                continue
            for target_id in targets[:20]:
                if entry_id == target_id:
                    continue
                target = self.graph.get_node(target_id)
                if not target:
                    continue
                paths = self.graph.find_paths(entry_id, target_id, max_length=6)
                for path_nodes in paths[:3]:
                    steps = []
                    for nid in path_nodes[1:-1]:
                        n = self.graph.get_node(nid)
                        steps.append({
                            "node_id": nid,
                            "label": n.label if n else "unknown",
                            "type": n.node_type.value if n else "unknown",
                        })
                    results.append(CandidateAttackPath(
                        entry_point=entry_id,
                        entry_point_label=entry.label,
                        target_operation=target_id,
                        target_label=target.label,
                        intermediate_steps=steps,
                        preconditions=["Access to the entry point endpoint"],
                        observations=[f"Entry point {entry.label} is accessible", f"Target {target.label} is a sensitive operation"],
                        unverified_assumptions=["Authorization may exist at intermediate steps but was not observed", "The full path is reachable in sequence"],
                        potential_impact=f"Privilege escalation to {target.label}",
                        confidence=0.4,
                        recommended_steps=[
                            f"Verify access to entry point: {entry.url or entry.label}",
                            "Follow the path sequentially and check authorization at each step",
                            f"Attempt to reach {target.url or target.label} directly",
                        ],
                    ))
        return results

    def _find_auth_bypass_paths(self) -> list[CandidateAttackPath]:
        results = []
        endpoints = self.graph.get_nodes_by_type(NodeType.ENDPOINT)
        for ep in endpoints:
            if not ep.observed:
                continue
            has_auth = any(
                e.edge_type == EdgeType.AUTH_DEPENDENCY
                for e in self.graph.get_outgoing(ep.id)
            )
            if has_auth:
                continue
            if not SENSITIVE_PATTERNS.search(ep.label):
                continue
            results.append(CandidateAttackPath(
                entry_point=ep.id,
                entry_point_label=ep.label,
                target_operation=ep.id,
                target_label=ep.label,
                intermediate_steps=[],
                preconditions=["Network access to the endpoint"],
                observations=[f"Endpoint {ep.label} has no observed authentication dependency"],
                unverified_assumptions=["Authentication may be enforced at a layer not visible in traffic"],
                potential_impact=f"Direct unauthenticated access to {ep.label}",
                confidence=0.3,
                recommended_steps=[
                    f"Access {ep.url or ep.label} without credentials",
                    "Compare response with authenticated access",
                ],
            ))
        return results

    def _find_data_access_paths(self) -> list[CandidateAttackPath]:
        results = []
        entries = self._find_entry_points()
        data_nodes = self.graph.get_nodes_by_type(NodeType.DATA_RESOURCE)

        for entry_id in entries[:15]:
            entry = self.graph.get_node(entry_id)
            if not entry:
                continue
            for data_node in data_nodes[:10]:
                paths = self.graph.find_paths(entry_id, data_node.id, max_length=5)
                for path_nodes in paths[:2]:
                    steps = []
                    for nid in path_nodes[1:-1]:
                        n = self.graph.get_node(nid)
                        steps.append({
                            "node_id": nid,
                            "label": n.label if n else "unknown",
                            "type": n.node_type.value if n else "unknown",
                        })
                    results.append(CandidateAttackPath(
                        entry_point=entry_id,
                        entry_point_label=entry.label,
                        target_operation=data_node.id,
                        target_label=data_node.label,
                        intermediate_steps=steps,
                        preconditions=["Access to entry point"],
                        observations=[f"Data resource {data_node.label} is reachable from {entry.label}"],
                        unverified_assumptions=["Data access controls are insufficient"],
                        potential_impact=f"Unauthorized access to {data_node.label}",
                        confidence=0.35,
                        recommended_steps=[
                            f"Trace path from {entry.label} to {data_node.label}",
                            "Check authorization at each step",
                        ],
                    ))
        return results

    def _find_workflow_abuse_paths(self) -> list[CandidateAttackPath]:
        results = []
        wf_edges = self.graph.get_edges_by_type(EdgeType.WORKFLOW_TRANSITION)

        for edge in wf_edges:
            target = self.graph.get_node(edge.target_id)
            source = self.graph.get_node(edge.source_id)
            if not target or not source:
                continue
            if not SENSITIVE_PATTERNS.search(target.label):
                continue
            boundary = any(
                e.edge_type == EdgeType.AUTHZ_BOUNDARY
                for e in self.graph.get_incoming(target.id)
            )
            if boundary:
                continue
            results.append(CandidateAttackPath(
                entry_point=source.id,
                entry_point_label=source.label,
                target_operation=target.id,
                target_label=target.label,
                intermediate_steps=[],
                preconditions=[f"Access to {source.label}"],
                observations=[f"Workflow transition from {source.label} to {target.label} without auth boundary"],
                unverified_assumptions=["Workflow steps cannot be skipped", "Authorization is checked at the target"],
                potential_impact=f"Workflow abuse reaching {target.label}",
                confidence=0.4,
                recommended_steps=[
                    f"Attempt to access {target.label} directly without completing {source.label}",
                    "Attempt to skip intermediate workflow steps",
                ],
            ))
        return results

    def _prioritize(self, paths: list[CandidateAttackPath]) -> list[CandidateAttackPath]:
        for p in paths:
            score = 0.0
            score += 0.3 if p.confidence > 0.4 else 0.1
            if any(kw in p.target_label.lower() for kw in ("admin", "role", "permission", "delete")):
                score += 0.3
            elif SENSITIVE_PATTERNS.search(p.target_label):
                score += 0.2
            else:
                score += 0.1
            score += 0.2 if len(p.unverified_assumptions) < 2 else 0.05
            score += 0.2 if len(p.intermediate_steps) < 4 else 0.05
            p.priority_score = round(score, 2)
        return sorted(paths, key=lambda p: p.priority_score, reverse=True)
