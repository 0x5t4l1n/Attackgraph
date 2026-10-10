from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Text, Float, Boolean, Integer, JSON, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    target_url: Mapped[str] = mapped_column(String(2048))
    allowed_hosts: Mapped[dict | list] = mapped_column(JSON, default=list)
    allowed_schemes: Mapped[dict | list] = mapped_column(JSON, default=lambda: ["https", "http"])
    exclude_paths: Mapped[dict | list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow)
    status: Mapped[str] = mapped_column(String(32), default="active")

    endpoints: Mapped[list[Endpoint]] = relationship(back_populates="project", cascade="all, delete-orphan")
    observations: Mapped[list[Observation]] = relationship(back_populates="project", cascade="all, delete-orphan")
    graph_nodes: Mapped[list[GraphNode]] = relationship(back_populates="project", cascade="all, delete-orphan")
    graph_edges: Mapped[list[GraphEdge]] = relationship(back_populates="project", cascade="all, delete-orphan")
    findings: Mapped[list[Finding]] = relationship(back_populates="project", cascade="all, delete-orphan")
    attack_paths: Mapped[list[AttackPath]] = relationship(back_populates="project", cascade="all, delete-orphan")
    test_plans: Mapped[list[TestPlan]] = relationship(back_populates="project", cascade="all, delete-orphan")
    crawl_sessions: Mapped[list[CrawlSession]] = relationship(back_populates="project", cascade="all, delete-orphan")
    import_sessions: Mapped[list[ImportSession]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Endpoint(Base):
    __tablename__ = "endpoints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(2048))
    normalized_url: Mapped[str] = mapped_column(String(2048), default="")
    method: Mapped[str] = mapped_column(String(16), default="GET")
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    discovery_source: Mapped[str] = mapped_column(String(32))  # crawl, burp, openapi, manual
    parent_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    crawl_depth: Mapped[int | None] = mapped_column(Integer, nullable=True)
    auth_context: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_seen: Mapped[datetime] = mapped_column(default=_utcnow)
    last_seen: Mapped[datetime] = mapped_column(default=_utcnow)
    extra_metadata: Mapped[dict | list | None] = mapped_column(JSON, nullable=True, default=None)

    project: Mapped[Project] = relationship(back_populates="endpoints")
    observations: Mapped[list[Observation]] = relationship(back_populates="endpoint", cascade="all, delete-orphan")


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    endpoint_id: Mapped[str | None] = mapped_column(ForeignKey("endpoints.id", ondelete="SET NULL"), nullable=True)
    source_type: Mapped[str] = mapped_column(String(32))  # crawl, burp, openapi
    source_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    request_method: Mapped[str] = mapped_column(String(16))
    request_url: Mapped[str] = mapped_column(String(2048))
    request_headers: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    request_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_headers: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cookies: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(default=_utcnow)
    redacted: Mapped[bool] = mapped_column(Boolean, default=False)

    project: Mapped[Project] = relationship(back_populates="observations")
    endpoint: Mapped[Endpoint | None] = relationship(back_populates="observations")


class GraphNode(Base):
    __tablename__ = "graph_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    node_type: Mapped[str] = mapped_column(String(32))  # host, page, endpoint, operation, parameter, auth_mechanism, role, workflow, sensitive_op, data_resource
    label: Mapped[str] = mapped_column(String(512))
    properties: Mapped[dict | list | None] = mapped_column(JSON, nullable=True, default=None)
    evidence_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    observed: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    project: Mapped[Project] = relationship(back_populates="graph_nodes")
    outgoing_edges: Mapped[list[GraphEdge]] = relationship(
        foreign_keys="GraphEdge.source_node_id",
        back_populates="source_node",
        cascade="all, delete-orphan",
    )
    incoming_edges: Mapped[list[GraphEdge]] = relationship(
        foreign_keys="GraphEdge.target_node_id",
        back_populates="target_node",
        cascade="all, delete-orphan",
    )


class GraphEdge(Base):
    __tablename__ = "graph_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    source_node_id: Mapped[str] = mapped_column(ForeignKey("graph_nodes.id", ondelete="CASCADE"))
    target_node_id: Mapped[str] = mapped_column(ForeignKey("graph_nodes.id", ondelete="CASCADE"))
    edge_type: Mapped[str] = mapped_column(String(32))  # navigation, request_sequence, workflow_transition, resource_relationship, auth_dependency, authz_boundary, attack_path
    label: Mapped[str] = mapped_column(String(512), default="")
    properties: Mapped[dict | list | None] = mapped_column(JSON, nullable=True, default=None)
    evidence_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    observed: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    project: Mapped[Project] = relationship(back_populates="graph_edges")
    source_node: Mapped[GraphNode] = relationship(foreign_keys=[source_node_id], back_populates="outgoing_edges")
    target_node: Mapped[GraphNode] = relationship(foreign_keys=[target_node_id], back_populates="incoming_edges")


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(512))
    description: Mapped[str] = mapped_column(Text, default="")
    affected_endpoints: Mapped[dict | list] = mapped_column(JSON, default=list)
    evidence_refs: Mapped[dict | list] = mapped_column(JSON, default=list)
    detection_rule: Mapped[str] = mapped_column(String(255), default="")
    reasoning: Mapped[str] = mapped_column(Text, default="")
    assumptions: Mapped[dict | list] = mapped_column(JSON, default=list)
    severity: Mapped[str] = mapped_column(String(16), default="info")  # info, low, medium, high, critical
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    validation_status: Mapped[str] = mapped_column(String(32), default="hypothesis")  # hypothesis, unvalidated, confirmed, false_positive, inconclusive
    reproduction_steps: Mapped[str] = mapped_column(Text, default="")
    remediation: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow)

    project: Mapped[Project] = relationship(back_populates="findings")


class AttackPath(Base):
    __tablename__ = "attack_paths"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    entry_point: Mapped[str] = mapped_column(String(2048))
    target_operation: Mapped[str] = mapped_column(String(2048))
    intermediate_steps: Mapped[dict | list] = mapped_column(JSON, default=list)
    preconditions: Mapped[dict | list] = mapped_column(JSON, default=list)
    observations: Mapped[dict | list] = mapped_column(JSON, default=list)
    unverified_assumptions: Mapped[dict | list] = mapped_column(JSON, default=list)
    potential_impact: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    priority_score: Mapped[float] = mapped_column(Float, default=0.0)
    recommended_steps: Mapped[dict | list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    project: Mapped[Project] = relationship(back_populates="attack_paths")
    test_plans: Mapped[list[TestPlan]] = relationship(back_populates="attack_path", cascade="all, delete-orphan")


class TestPlan(Base):
    __tablename__ = "test_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    attack_path_id: Mapped[str | None] = mapped_column(ForeignKey("attack_paths.id", ondelete="SET NULL"), nullable=True)
    hypothesis: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[dict | list] = mapped_column(JSON, default=list)
    required_accounts: Mapped[dict | list] = mapped_column(JSON, default=list)
    preconditions: Mapped[dict | list] = mapped_column(JSON, default=list)
    test_procedure: Mapped[str] = mapped_column(Text, default="")
    expected_secure_behavior: Mapped[str] = mapped_column(Text, default="")
    potential_insecure_outcomes: Mapped[dict | list] = mapped_column(JSON, default=list)
    cleanup_steps: Mapped[dict | list] = mapped_column(JSON, default=list)
    evidence_to_capture: Mapped[dict | list] = mapped_column(JSON, default=list)
    limitations: Mapped[dict | list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, approved, running, completed, cancelled
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    project: Mapped[Project] = relationship(back_populates="test_plans")
    attack_path: Mapped[AttackPath | None] = relationship(back_populates="test_plans")


class CrawlSession(Base):
    __tablename__ = "crawl_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, running, paused, completed, failed, cancelled
    config: Mapped[dict | list | None] = mapped_column(JSON, nullable=True, default=None)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    pages_discovered: Mapped[int] = mapped_column(Integer, default=0)
    pages_crawled: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[dict | list] = mapped_column(JSON, default=list)

    project: Mapped[Project] = relationship(back_populates="crawl_sessions")


class ImportSession(Base):
    __tablename__ = "import_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    source_type: Mapped[str] = mapped_column(String(32))  # burp, openapi
    filename: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, running, completed, failed
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    items_imported: Mapped[int] = mapped_column(Integer, default=0)
    items_skipped: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[dict | list] = mapped_column(JSON, default=list)

    project: Mapped[Project] = relationship(back_populates="import_sessions")
