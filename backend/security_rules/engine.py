from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field

from backend.graph_engine.engine import ApplicationGraph, NodeType, EdgeType


@dataclass
class SecurityFinding:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    affected_endpoints: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    detection_rule: str = ""
    reasoning: str = ""
    assumptions: list[str] = field(default_factory=list)
    severity: str = "info"
    confidence: float = 0.5
    validation_status: str = "hypothesis"
    reproduction_steps: str = ""
    remediation: str = ""


class SecurityRule:
    rule_id: str = ""
    name: str = ""
    description: str = ""

    def evaluate(self, graph: ApplicationGraph) -> list[SecurityFinding]:
        return []


SENSITIVE_RE = re.compile(
    r"(admin|user|account|settings|payment|password|profile|billing|config|manage|private|internal)",
    re.I,
)
DEBUG_RE = re.compile(
    r"(debug|actuator|\.env|phpinfo|console|__debug__|server-status|trace|elmah|profiler)",
    re.I,
)
ID_SEGMENT_RE = re.compile(r"/(\d+|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[0-9a-f]{24})(/|$)", re.I)


class UnauthenticatedSensitiveEndpoints(SecurityRule):
    rule_id = "unauth-sensitive"
    name = "Unauthenticated Sensitive Endpoints"
    description = "Endpoints handling sensitive operations with no observed authentication evidence"

    def evaluate(self, graph: ApplicationGraph) -> list[SecurityFinding]:
        findings = []
        endpoints = graph.get_nodes_by_type(NodeType.ENDPOINT)
        for ep in endpoints:
            if not SENSITIVE_RE.search(ep.label) and not SENSITIVE_RE.search(ep.url or ""):
                continue
            auth_edges = [e for e in graph.get_outgoing(ep.id) if e.edge_type == EdgeType.AUTH_DEPENDENCY]
            if auth_edges:
                continue
            findings.append(SecurityFinding(
                title=f"Potentially unauthenticated sensitive endpoint: {ep.label}",
                description=f"Endpoint {ep.label} ({ep.url}) appears to handle sensitive functionality but no authentication evidence was observed.",
                affected_endpoints=[ep.url or ep.label],
                detection_rule=self.rule_id,
                reasoning="The endpoint label or URL matches sensitive patterns and no authentication dependency edges exist in the graph.",
                assumptions=["Authentication may be enforced at a layer not captured by crawling or traffic import", "Session cookies may have been present but not detected as auth mechanisms"],
                severity="medium",
                confidence=0.4,
                validation_status="hypothesis",
                reproduction_steps=f"1. Access {ep.url} without authentication credentials\n2. Check if the response contains sensitive data or allows state changes",
                remediation="Verify authentication is enforced on this endpoint. Implement authentication middleware if missing.",
            ))
        return findings


class PotentialIDOR(SecurityRule):
    rule_id = "potential-idor"
    name = "Potential IDOR"
    description = "Endpoints with resource IDs that may be vulnerable to insecure direct object reference"

    def evaluate(self, graph: ApplicationGraph) -> list[SecurityFinding]:
        findings = []
        endpoints = graph.get_nodes_by_type(NodeType.ENDPOINT)
        for ep in endpoints:
            url = ep.url or ""
            if not ID_SEGMENT_RE.search(url):
                continue
            findings.append(SecurityFinding(
                title=f"Candidate for IDOR testing: {ep.label}",
                description=f"Endpoint {ep.label} contains resource identifiers in the URL path that may reference user-specific or access-controlled resources.",
                affected_endpoints=[url],
                detection_rule=self.rule_id,
                reasoning="The URL contains numeric or UUID path segments that likely reference specific resources. Without server-side authorization checks, another user's resources might be accessible.",
                assumptions=["Path segments are resource identifiers", "The application uses these IDs to look up user-specific data", "Authorization is not enforced server-side"],
                severity="medium",
                confidence=0.3,
                validation_status="hypothesis",
                reproduction_steps=f"1. Authenticate as User A, access {url}\n2. Note the resource ID\n3. Authenticate as User B\n4. Replace the resource ID with User A's ID\n5. Check if User A's data is returned",
                remediation="Implement object-level authorization checks. Verify the authenticated user owns the requested resource.",
            ))
        return findings


class PropertyLevelAuthIssues(SecurityRule):
    rule_id = "property-level-auth"
    name = "Property-Level Authorization Issues"
    description = "Endpoints accepting PUT/PATCH that may allow mass assignment"

    def evaluate(self, graph: ApplicationGraph) -> list[SecurityFinding]:
        findings = []
        endpoints = graph.get_nodes_by_type(NodeType.ENDPOINT)
        for ep in endpoints:
            method = (ep.method or "").upper()
            if method not in ("PUT", "PATCH"):
                continue
            params = [n for n in graph.get_neighbors(ep.id) if n.node_type == NodeType.PARAMETER]
            if len(params) < 2:
                continue
            findings.append(SecurityFinding(
                title=f"Potential mass assignment: {ep.label}",
                description=f"Endpoint {ep.label} accepts {method} requests with multiple parameters, which may allow setting properties beyond the intended scope.",
                affected_endpoints=[ep.url or ep.label],
                detection_rule=self.rule_id,
                reasoning=f"{method} endpoint with {len(params)} parameters may accept properties not intended to be user-modifiable (e.g., role, is_admin, price).",
                assumptions=["Server does not restrict which properties can be set", "Some properties are privileged"],
                severity="low",
                confidence=0.3,
                validation_status="hypothesis",
                reproduction_steps=f"1. Send a {method} request to {ep.url} with additional properties like 'role', 'is_admin', etc.\n2. Check if the server accepts and applies the extra properties",
                remediation="Implement allowlists for writable properties. Reject unknown or privileged fields.",
            ))
        return findings


class UnexpectedHTTPMethods(SecurityRule):
    rule_id = "unexpected-methods"
    name = "Unexpected HTTP Methods"
    description = "Endpoints responding to uncommon or undocumented HTTP methods"

    def evaluate(self, graph: ApplicationGraph) -> list[SecurityFinding]:
        findings = []
        endpoints = graph.get_nodes_by_type(NodeType.ENDPOINT)
        path_methods: dict[str, list[str]] = {}
        for ep in endpoints:
            url = ep.url or ""
            method = (ep.method or "GET").upper()
            path_methods.setdefault(url, []).append(method)

        for url, methods in path_methods.items():
            dangerous = {"DELETE", "PUT", "PATCH"} & set(methods)
            if not dangerous:
                continue
            if "GET" in methods and dangerous:
                findings.append(SecurityFinding(
                    title=f"State-changing methods on readable endpoint: {url}",
                    description=f"Endpoint {url} accepts both read (GET) and state-changing ({', '.join(sorted(dangerous))}) methods.",
                    affected_endpoints=[url],
                    detection_rule=self.rule_id,
                    reasoning="Endpoints responding to both safe and state-changing methods may indicate insufficient method restriction or missing authorization for destructive operations.",
                    assumptions=["The state-changing methods are not intentionally exposed", "Authorization for destructive methods may differ from read access"],
                    severity="low",
                    confidence=0.4,
                    validation_status="hypothesis",
                    reproduction_steps=f"1. Send {', '.join(sorted(dangerous))} requests to {url}\n2. Verify authorization is enforced for each method",
                    remediation="Restrict allowed HTTP methods per endpoint. Enforce per-method authorization.",
                ))
        return findings


class SensitiveDataExposure(SecurityRule):
    rule_id = "sensitive-data-exposure"
    name = "Sensitive Data Exposure"
    description = "Endpoints that may expose sensitive information in responses"

    EXPOSURE_RE = re.compile(r"(password|ssn|credit.?card|secret|token|internal.?ip|stack.?trace|debug|private.?key)", re.I)

    def evaluate(self, graph: ApplicationGraph) -> list[SecurityFinding]:
        findings = []
        endpoints = graph.get_nodes_by_type(NodeType.ENDPOINT)
        for ep in endpoints:
            props = ep.properties or {}
            label = ep.label + " " + str(props)
            if not self.EXPOSURE_RE.search(label):
                continue
            findings.append(SecurityFinding(
                title=f"Potential sensitive data exposure: {ep.label}",
                description=f"Endpoint {ep.label} may expose sensitive information based on its properties or naming patterns.",
                affected_endpoints=[ep.url or ep.label],
                detection_rule=self.rule_id,
                reasoning="Endpoint metadata contains patterns associated with sensitive data (passwords, tokens, internal information).",
                assumptions=["Response content was not fully inspected", "Matching patterns indicate actual sensitive data exposure"],
                severity="high",
                confidence=0.3,
                validation_status="hypothesis",
                reproduction_steps=f"1. Request {ep.url}\n2. Inspect response body for sensitive fields\n3. Check if PII, tokens, or internal details are exposed",
                remediation="Review response schemas. Remove unnecessary sensitive fields. Implement field-level filtering.",
            ))
        return findings


class InconsistentBehavior(SecurityRule):
    rule_id = "inconsistent-behavior"
    name = "Inconsistent Authorization Behavior"
    description = "Similar endpoints with inconsistent authentication patterns"

    def evaluate(self, graph: ApplicationGraph) -> list[SecurityFinding]:
        findings = []
        endpoints = graph.get_nodes_by_type(NodeType.ENDPOINT)
        url_groups: dict[str, list[tuple[str, str, bool]]] = {}
        for ep in endpoints:
            url = ep.url or ""
            base_path = re.sub(r"/\d+|/[0-9a-f-]{36}", "/{id}", url)
            has_auth = any(e.edge_type == EdgeType.AUTH_DEPENDENCY for e in graph.get_outgoing(ep.id))
            url_groups.setdefault(base_path, []).append((ep.method or "GET", ep.url or "", has_auth))

        for base_path, group in url_groups.items():
            if len(group) < 2:
                continue
            auth_states = {has_auth for _, _, has_auth in group}
            if len(auth_states) > 1:
                authed = [(m, u) for m, u, a in group if a]
                unauthed = [(m, u) for m, u, a in group if not a]
                findings.append(SecurityFinding(
                    title=f"Inconsistent auth on {base_path}",
                    description=f"Endpoints on the same resource path show inconsistent authentication: {len(authed)} with auth, {len(unauthed)} without.",
                    affected_endpoints=[u for _, u in unauthed],
                    detection_rule=self.rule_id,
                    reasoning="Different HTTP methods on the same resource have different auth requirements, which may indicate a misconfiguration.",
                    assumptions=["All methods on the same resource should have consistent auth requirements"],
                    severity="medium",
                    confidence=0.5,
                    validation_status="hypothesis",
                    reproduction_steps="1. Compare authentication requirements between methods on this path\n2. Attempt unauthenticated access to the unprotected methods",
                    remediation="Apply consistent authentication across all methods on shared resource paths.",
                ))
        return findings


class SuspiciousWorkflowTransitions(SecurityRule):
    rule_id = "suspicious-workflow"
    name = "Suspicious Workflow Transitions"
    description = "Workflow transitions to sensitive operations without auth boundaries"

    def evaluate(self, graph: ApplicationGraph) -> list[SecurityFinding]:
        findings = []
        wf_edges = graph.get_edges_by_type(EdgeType.WORKFLOW_TRANSITION)
        for edge in wf_edges:
            target = graph.get_node(edge.target_id)
            if not target:
                continue
            is_sensitive = target.node_type == NodeType.SENSITIVE_OP or SENSITIVE_RE.search(target.label)
            if not is_sensitive:
                continue
            auth_boundary = any(
                e.edge_type == EdgeType.AUTHZ_BOUNDARY
                for e in graph.get_incoming(target.id)
            )
            if auth_boundary:
                continue
            source = graph.get_node(edge.source_id)
            findings.append(SecurityFinding(
                title=f"Unguarded workflow to sensitive operation: {target.label}",
                description=f"Workflow transition from {source.label if source else 'unknown'} to sensitive operation {target.label} has no observed authorization boundary.",
                affected_endpoints=[target.url or target.label],
                detection_rule=self.rule_id,
                reasoning="Sensitive operations reachable through workflow transitions should have explicit authorization checks at each boundary.",
                assumptions=["Authorization boundaries may exist but were not observed", "Workflow sequence can be manipulated"],
                severity="medium",
                confidence=0.4,
                validation_status="hypothesis",
                reproduction_steps=f"1. Follow the workflow to {target.label}\n2. Attempt to skip intermediate steps\n3. Attempt the sensitive operation without expected preconditions",
                remediation="Add authorization checks at workflow transition points. Validate state before sensitive operations.",
            ))
        return findings


class ExposedDebugEndpoints(SecurityRule):
    rule_id = "exposed-debug"
    name = "Exposed Debug/Admin Endpoints"
    description = "Endpoints matching common debug, admin, or monitoring patterns"

    def evaluate(self, graph: ApplicationGraph) -> list[SecurityFinding]:
        findings = []
        endpoints = graph.get_nodes_by_type(NodeType.ENDPOINT)
        for ep in endpoints:
            url = ep.url or ""
            label = ep.label or ""
            combined = url + " " + label
            if not DEBUG_RE.search(combined):
                if not any(p in url.lower() for p in ["/swagger", "/graphql", "/graphiql", "/.env", "/health"]):
                    continue
            if "/health" in url.lower():
                sev = "info"
            elif any(p in url.lower() for p in ["/.env", "/debug", "/actuator", "/phpinfo", "/trace"]):
                sev = "high"
            else:
                sev = "medium"
            findings.append(SecurityFinding(
                title=f"Exposed diagnostic endpoint: {ep.label}",
                description=f"Endpoint {url} matches patterns associated with debug, monitoring, or administrative interfaces.",
                affected_endpoints=[url],
                detection_rule=self.rule_id,
                reasoning="Debug and administrative endpoints often expose internal state, configuration, or provide elevated access.",
                assumptions=["The endpoint is publicly accessible", "It exposes information useful to an attacker"],
                severity=sev,
                confidence=0.7,
                validation_status="hypothesis",
                reproduction_steps=f"1. Access {url} without authentication\n2. Check for configuration data, stack traces, or admin functionality",
                remediation="Restrict access to debug endpoints in production. Disable unnecessary diagnostic features.",
            ))
        return findings


class SpecDiscrepancies(SecurityRule):
    rule_id = "spec-discrepancy"
    name = "API Specification Discrepancies"
    description = "Endpoints observed but undocumented, or documented but unobserved"

    def evaluate(self, graph: ApplicationGraph) -> list[SecurityFinding]:
        findings = []
        endpoints = graph.get_nodes_by_type(NodeType.ENDPOINT)
        for ep in endpoints:
            props = ep.properties or {}
            if ep.observed and not props.get("from_spec"):
                if ep.evidence_source != "openapi":
                    findings.append(SecurityFinding(
                        title=f"Undocumented endpoint: {ep.label}",
                        description=f"Endpoint {ep.url} was observed but is not present in the API specification.",
                        affected_endpoints=[ep.url or ep.label],
                        detection_rule=self.rule_id,
                        reasoning="Undocumented endpoints may represent hidden or forgotten functionality with less scrutiny.",
                        assumptions=["An API spec was imported for comparison"],
                        severity="low",
                        confidence=0.6,
                        validation_status="hypothesis",
                        reproduction_steps=f"1. Review {ep.url} and its purpose\n2. Check if it should be in the API spec\n3. Assess authorization requirements",
                        remediation="Document all API endpoints. Review whether undocumented endpoints should be exposed.",
                    ))
            elif not ep.observed and props.get("from_spec"):
                findings.append(SecurityFinding(
                    title=f"Unobserved documented endpoint: {ep.label}",
                    description=f"Endpoint {ep.url} is in the API specification but was not observed during testing.",
                    affected_endpoints=[ep.url or ep.label],
                    detection_rule=self.rule_id,
                    reasoning="Endpoints in the spec but not observed may indicate incomplete test coverage.",
                    assumptions=["The spec is accurate and the endpoint exists"],
                    severity="info",
                    confidence=0.6,
                    validation_status="hypothesis",
                    reproduction_steps=f"1. Attempt to access {ep.url}\n2. Include in future crawl/test scope",
                    remediation="Expand testing coverage to include all documented endpoints.",
                ))
        return findings


class InsufficientAuthEvidence(SecurityRule):
    rule_id = "insufficient-auth"
    name = "Insufficient Authentication Evidence on State-Changing Endpoints"
    description = "State-changing endpoints with no observed authentication or CSRF protection"

    def evaluate(self, graph: ApplicationGraph) -> list[SecurityFinding]:
        findings = []
        endpoints = graph.get_nodes_by_type(NodeType.ENDPOINT)
        for ep in endpoints:
            method = (ep.method or "GET").upper()
            if method not in ("POST", "PUT", "DELETE", "PATCH"):
                continue
            has_auth = any(e.edge_type == EdgeType.AUTH_DEPENDENCY for e in graph.get_outgoing(ep.id))
            if has_auth:
                continue
            has_csrf = any(
                n.node_type == NodeType.PARAMETER and "csrf" in (n.label or "").lower()
                for n in graph.get_neighbors(ep.id)
            )
            if has_csrf:
                continue
            findings.append(SecurityFinding(
                title=f"No auth evidence on state-changing endpoint: {ep.label}",
                description=f"Endpoint {ep.label} ({method}) handles state changes but has no observed authentication or CSRF protection.",
                affected_endpoints=[ep.url or ep.label],
                detection_rule=self.rule_id,
                reasoning="State-changing operations should require authentication and CSRF protection to prevent unauthorized modifications.",
                assumptions=["Auth may exist but was not captured in observations", "The endpoint modifies server state"],
                severity="medium",
                confidence=0.4,
                validation_status="hypothesis",
                reproduction_steps=f"1. Send {method} request to {ep.url} without auth credentials\n2. Check if the operation succeeds\n3. Attempt cross-site request to test CSRF protection",
                remediation="Enforce authentication and CSRF protection on all state-changing endpoints.",
            ))
        return findings


class RulesEngine:
    def __init__(self) -> None:
        self.rules: list[SecurityRule] = [
            UnauthenticatedSensitiveEndpoints(),
            PotentialIDOR(),
            PropertyLevelAuthIssues(),
            UnexpectedHTTPMethods(),
            SensitiveDataExposure(),
            InconsistentBehavior(),
            SuspiciousWorkflowTransitions(),
            ExposedDebugEndpoints(),
            SpecDiscrepancies(),
            InsufficientAuthEvidence(),
        ]

    def analyze(self, graph: ApplicationGraph) -> list[SecurityFinding]:
        findings = []
        for rule in self.rules:
            findings.extend(rule.evaluate(graph))
        return findings

    def analyze_with_rule(self, graph: ApplicationGraph, rule_id: str) -> list[SecurityFinding]:
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule.evaluate(graph)
        return []
