from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urlparse

import asyncio

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.storage.database import get_db, engine, async_session_factory
from backend.storage.init_db import init_database
from backend.storage.models import (
    Project,
    Endpoint,
    Observation,
    GraphNode,
    GraphEdge,
    Finding,
    AttackPath,
    TestPlan,
    CrawlSession,
    ImportSession,
)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_database()
    yield
    await engine.dispose()


app = FastAPI(
    title="AttackGraph",
    description="Intelligent Web Application Attack-Path Mapping Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.server.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    target_url: str
    allowed_hosts: list[str] = []
    allowed_schemes: list[str] = ["https", "http"]
    exclude_paths: list[str] = []


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    target_url: str
    allowed_hosts: list
    allowed_schemes: list
    exclude_paths: list
    created_at: datetime
    updated_at: datetime
    status: str

    class Config:
        from_attributes = True


class CrawlConfigRequest(BaseModel):
    max_depth: int = 3
    max_concurrent: int = 5
    max_pages: int = 500
    request_timeout: float = 30.0
    rate_limit_rps: float = 10.0
    respect_robots_txt: bool = True
    allow_private_networks: bool = False
    auth_cookies: dict[str, str] | None = None
    auth_headers: dict[str, str] | None = None


class EndpointResponse(BaseModel):
    id: str
    url: str
    normalized_url: str
    method: str
    status_code: int | None
    content_type: str | None
    discovery_source: str
    parent_url: str | None
    first_seen: datetime

    class Config:
        from_attributes = True


class FindingResponse(BaseModel):
    id: str
    title: str
    description: str
    affected_endpoints: list
    evidence_refs: list = []
    severity: str
    confidence: float
    validation_status: str
    detection_rule: str
    reasoning: str
    assumptions: list
    reproduction_steps: str
    remediation: str
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class AttackPathResponse(BaseModel):
    id: str
    entry_point: str
    target_operation: str
    intermediate_steps: list
    preconditions: list
    observations: list
    unverified_assumptions: list
    potential_impact: str
    confidence: float
    priority_score: float
    recommended_steps: list
    created_at: datetime

    class Config:
        from_attributes = True


class TestPlanResponse(BaseModel):
    id: str
    attack_path_id: str | None
    hypothesis: str
    evidence: list
    required_accounts: list
    preconditions: list
    test_procedure: str
    expected_secure_behavior: str
    potential_insecure_outcomes: list
    evidence_to_capture: list
    cleanup_steps: list
    limitations: list
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class GraphResponse(BaseModel):
    project_id: str
    nodes: list[dict]
    edges: list[dict]
    statistics: dict


class FindingUpdate(BaseModel):
    validation_status: str | None = None
    severity: str | None = None


class TestPlanUpdate(BaseModel):
    status: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_project(project_id: str, db: AsyncSession) -> Project:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# ---------------------------------------------------------------------------
# Active crawlers registry (for cancellation)
# ---------------------------------------------------------------------------

_active_crawlers: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Background tasks
# ---------------------------------------------------------------------------

async def _run_crawl(session_id: str, project_id: str, config: dict):
    from backend.crawler.crawler import WebCrawler, CrawlConfig

    async with async_session_factory() as db:
        session = await db.get(CrawlSession, session_id)
        if not session:
            return
        session.status = "running"
        session.started_at = datetime.now(timezone.utc)
        await db.commit()

        project = await db.get(Project, project_id)
        if not project:
            session.status = "failed"
            session.errors = ["Project not found"]
            session.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return

        crawl_config = CrawlConfig(
            target_url=project.target_url,
            allowed_hosts=project.allowed_hosts or [],
            allowed_schemes=project.allowed_schemes or ["https", "http"],
            exclude_paths=project.exclude_paths or [],
            max_depth=config.get("max_depth", 3),
            max_concurrent=config.get("max_concurrent", 5),
            max_pages=config.get("max_pages", 500),
            request_timeout=config.get("request_timeout", 30.0),
            rate_limit_rps=config.get("rate_limit_rps", 10.0),
            respect_robots_txt=config.get("respect_robots_txt", True),
            allow_private_networks=config.get("allow_private_networks", False),
            auth_cookies=config.get("auth_cookies"),
            auth_headers=config.get("auth_headers"),
        )

        crawler = WebCrawler(crawl_config)
        _active_crawlers[session_id] = crawler

        try:
            errors: list[str] = []
            pages_crawled = 0
            pages_discovered = 0

            async for result in crawler.crawl():
                pages_crawled += 1
                pages_discovered += len(result.discovered_urls)

                endpoint = Endpoint(
                    project_id=project_id,
                    url=result.url,
                    normalized_url=result.normalized_url,
                    method=result.method,
                    status_code=result.status_code,
                    content_type=result.content_type,
                    discovery_source="crawl",
                    parent_url=result.parent_url,
                    crawl_depth=result.depth,
                )
                db.add(endpoint)

                obs = Observation(
                    project_id=project_id,
                    endpoint_id=endpoint.id,
                    source_type="crawl",
                    source_id=session_id,
                    request_method=result.method,
                    request_url=result.url,
                    response_status=result.status_code,
                    content_type=result.content_type,
                    request_headers=result.headers if hasattr(result, "headers") else None,
                )
                db.add(obs)

                if result.error:
                    errors.append(result.error)

                await db.commit()

            session.status = "completed"
            session.pages_crawled = pages_crawled
            session.pages_discovered = pages_discovered
            session.errors = errors
        except Exception as e:
            session.status = "failed"
            session.errors = [str(e)]
        finally:
            session.completed_at = datetime.now(timezone.utc)
            await db.commit()
            _active_crawlers.pop(session_id, None)


async def _run_burp_import(import_id: str, project_id: str, content: bytes):
    from backend.burp_import.parser import BurpParser

    async with async_session_factory() as db:
        imp = await db.get(ImportSession, import_id)
        if not imp:
            return
        imp.status = "running"
        imp.started_at = datetime.now(timezone.utc)
        await db.commit()

        parser = BurpParser()
        try:
            result = parser.parse_xml(content)
        except Exception as e:
            imp.status = "failed"
            imp.errors = [str(e)]
            imp.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return

        imported = 0
        skipped = 0
        seen: set[tuple[str, str]] = set()

        for idx, item in enumerate(result.items):
            key = (item.method, item.url)
            req = result.parsed_requests[idx] if idx < len(result.parsed_requests) else None
            resp = result.parsed_responses[idx] if idx < len(result.parsed_responses) else None

            is_dup = key in seen
            seen.add(key)

            endpoint: Endpoint | None = None
            if not is_dup:
                endpoint = Endpoint(
                    project_id=project_id,
                    url=item.url,
                    normalized_url=item.url,
                    method=item.method,
                    status_code=item.status_code,
                    content_type=item.mime_type,
                    discovery_source="burp",
                )
                db.add(endpoint)

            obs = Observation(
                project_id=project_id,
                endpoint_id=endpoint.id if endpoint else None,
                source_type="burp",
                source_id=import_id,
                request_method=item.method,
                request_url=item.url,
                request_headers=req.headers if req else None,
                request_body=req.body if req else None,
                response_status=resp.status_code if resp else item.status_code,
                response_headers=resp.headers if resp else None,
                response_body=resp.body if resp else None,
                content_type=resp.content_type if resp else item.mime_type,
                cookies=req.cookies if req else None,
            )
            db.add(obs)
            imported += 1

        imp.status = "completed"
        imp.items_imported = imported
        imp.items_skipped = skipped
        imp.errors = result.errors
        imp.completed_at = datetime.now(timezone.utc)
        await db.commit()


async def _run_openapi_import(import_id: str, project_id: str, content: str):
    from backend.openapi_import.parser import OpenAPIParser

    async with async_session_factory() as db:
        imp = await db.get(ImportSession, import_id)
        if not imp:
            return
        imp.status = "running"
        imp.started_at = datetime.now(timezone.utc)
        await db.commit()

        parser = OpenAPIParser()
        try:
            spec = parser.parse_content(content)
        except Exception as e:
            imp.status = "failed"
            imp.errors = [str(e)]
            imp.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return

        imported = 0
        base = spec.base_url or ""
        for ep in spec.endpoints:
            full_url = base.rstrip("/") + "/" + ep.path.lstrip("/") if base else ep.path
            endpoint = Endpoint(
                project_id=project_id,
                url=full_url,
                normalized_url=full_url,
                method=ep.method.upper(),
                content_type=None,
                discovery_source="openapi",
                extra_metadata={
                    "operation_id": ep.operation_id,
                    "tags": ep.tags,
                    "parameters": [
                        {"name": p.name, "in": p.location, "required": p.required, "type": p.schema_type}
                        for p in ep.parameters
                    ],
                    "security": ep.security,
                    "deprecated": ep.deprecated,
                },
            )
            db.add(endpoint)
            imported += 1

        imp.status = "completed"
        imp.items_imported = imported
        imp.items_skipped = 0
        imp.errors = spec.errors
        imp.completed_at = datetime.now(timezone.utc)
        await db.commit()


def _build_graph_from_db(project_id: str, endpoints: list[Endpoint], observations: list[Observation]) -> dict:
    """Build a graph dict from DB records (no dependency on graph_engine module)."""
    nodes: list[dict] = []
    edges: list[dict] = []
    node_ids: dict[str, str] = {}

    project_hosts: set[str] = set()
    for ep in endpoints:
        parsed = urlparse(ep.url)
        if parsed.hostname:
            project_hosts.add(parsed.hostname)

    for host in project_hosts:
        nid = str(uuid.uuid4())
        node_ids[f"host:{host}"] = nid
        nodes.append({
            "id": nid,
            "type": "host",
            "label": host,
            "url": None,
            "method": None,
            "properties": {},
            "evidence_source": "discovery",
            "confidence": 1.0,
            "observed": True,
        })

    for ep in endpoints:
        nid = str(uuid.uuid4())
        key = f"ep:{ep.method}:{ep.normalized_url or ep.url}"
        node_ids[key] = nid
        nodes.append({
            "id": nid,
            "type": "endpoint",
            "label": f"{ep.method} {ep.url}",
            "url": ep.url,
            "method": ep.method,
            "properties": {
                "url": ep.url,
                "method": ep.method,
                "status_code": ep.status_code,
                "content_type": ep.content_type,
                "discovery_source": ep.discovery_source,
            },
            "evidence_source": ep.discovery_source,
            "confidence": 1.0,
            "observed": True,
        })

        parsed = urlparse(ep.url)
        host_key = f"host:{parsed.hostname}" if parsed.hostname else None
        if host_key and host_key in node_ids:
            edges.append({
                "id": str(uuid.uuid4()),
                "source": node_ids[host_key],
                "target": nid,
                "type": "navigation",
                "label": "",
                "properties": {},
                "evidence_source": ep.discovery_source,
                "confidence": 1.0,
                "observed": True,
            })

        if ep.parent_url:
            parent_key_get = f"ep:GET:{ep.parent_url}"
            parent_nid = node_ids.get(parent_key_get)
            if parent_nid:
                edges.append({
                    "id": str(uuid.uuid4()),
                    "source": parent_nid,
                    "target": nid,
                    "type": "navigation",
                    "label": "link",
                    "properties": {},
                    "evidence_source": ep.discovery_source,
                    "confidence": 1.0,
                    "observed": True,
                })

    observed_count = sum(1 for n in nodes if n["observed"])
    inferred_count = len(nodes) - observed_count

    statistics = {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "observed_nodes": observed_count,
        "inferred_nodes": inferred_count,
        "node_types": {},
        "edge_types": {},
        "components": 1,
    }
    for n in nodes:
        t = n["type"]
        statistics["node_types"][t] = statistics["node_types"].get(t, 0) + 1
    for e in edges:
        t = e["type"]
        statistics["edge_types"][t] = statistics["edge_types"].get(t, 0) + 1

    return {
        "project_id": project_id,
        "nodes": nodes,
        "edges": edges,
        "statistics": statistics,
    }


# ---------------------------------------------------------------------------
# PROJECTS
# ---------------------------------------------------------------------------

@app.post("/api/projects", response_model=ProjectResponse)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    hosts = data.allowed_hosts
    if not hosts:
        parsed = urlparse(data.target_url)
        if parsed.hostname:
            hosts = [parsed.hostname]
    project = Project(
        name=data.name,
        description=data.description,
        target_url=data.target_url,
        allowed_hosts=hosts,
        allowed_schemes=data.allowed_schemes,
        exclude_paths=data.exclude_paths,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


@app.get("/api/projects", response_model=list[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    return result.scalars().all()


@app.get("/api/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    return await _get_project(project_id, db)


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    project = await _get_project(project_id, db)
    await db.delete(project)
    return {"detail": "Project deleted"}


# ---------------------------------------------------------------------------
# CRAWL
# ---------------------------------------------------------------------------

@app.post("/api/projects/{project_id}/crawl")
async def start_crawl(
    project_id: str,
    config: CrawlConfigRequest,
    db: AsyncSession = Depends(get_db),
):
    await _get_project(project_id, db)
    session = CrawlSession(
        project_id=project_id,
        status="pending",
        config=config.model_dump(),
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    sid = session.id
    asyncio.create_task(_run_crawl(sid, project_id, config.model_dump()))
    return {"session_id": sid, "status": "pending"}


@app.get("/api/projects/{project_id}/crawl/sessions")
async def list_crawl_sessions(project_id: str, db: AsyncSession = Depends(get_db)):
    await _get_project(project_id, db)
    result = await db.execute(
        select(CrawlSession)
        .where(CrawlSession.project_id == project_id)
        .order_by(CrawlSession.started_at.desc())
    )
    sessions = result.scalars().all()
    return [
        {
            "id": s.id,
            "status": s.status,
            "started_at": s.started_at,
            "completed_at": s.completed_at,
            "pages_discovered": s.pages_discovered,
            "pages_crawled": s.pages_crawled,
            "errors": s.errors,
            "config": s.config,
        }
        for s in sessions
    ]


@app.get("/api/projects/{project_id}/crawl/sessions/{session_id}")
async def get_crawl_session(project_id: str, session_id: str, db: AsyncSession = Depends(get_db)):
    await _get_project(project_id, db)
    session = await db.get(CrawlSession, session_id)
    if not session or session.project_id != project_id:
        raise HTTPException(status_code=404, detail="Crawl session not found")
    return {
        "id": session.id,
        "status": session.status,
        "started_at": session.started_at,
        "completed_at": session.completed_at,
        "pages_discovered": session.pages_discovered,
        "pages_crawled": session.pages_crawled,
        "errors": session.errors,
        "config": session.config,
    }


@app.post("/api/projects/{project_id}/crawl/sessions/{session_id}/cancel")
async def cancel_crawl(project_id: str, session_id: str):
    crawler = _active_crawlers.get(session_id)
    if crawler is None:
        raise HTTPException(status_code=404, detail="No active crawl for this session")
    await crawler.cancel()
    return {"detail": "Cancellation requested"}


# ---------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------

@app.post("/api/projects/{project_id}/import/burp")
async def import_burp(
    project_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    await _get_project(project_id, db)
    content = await file.read()
    imp = ImportSession(
        project_id=project_id,
        source_type="burp",
        filename=file.filename or "unknown.xml",
        status="pending",
    )
    db.add(imp)
    await db.flush()
    await db.refresh(imp)
    iid = imp.id
    asyncio.create_task(_run_burp_import(iid, project_id, content))
    return {"import_id": iid, "status": "pending"}


@app.post("/api/projects/{project_id}/import/openapi")
async def import_openapi(
    project_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    await _get_project(project_id, db)
    raw = await file.read()
    content = raw.decode("utf-8", errors="replace")
    imp = ImportSession(
        project_id=project_id,
        source_type="openapi",
        filename=file.filename or "unknown",
        status="pending",
    )
    db.add(imp)
    await db.flush()
    await db.refresh(imp)
    iid = imp.id
    asyncio.create_task(_run_openapi_import(iid, project_id, content))
    return {"import_id": iid, "status": "pending"}


@app.get("/api/projects/{project_id}/imports")
async def list_imports(project_id: str, db: AsyncSession = Depends(get_db)):
    await _get_project(project_id, db)
    result = await db.execute(
        select(ImportSession)
        .where(ImportSession.project_id == project_id)
        .order_by(ImportSession.started_at.desc())
    )
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "source_type": r.source_type,
            "filename": r.filename,
            "status": r.status,
            "started_at": r.started_at,
            "completed_at": r.completed_at,
            "items_imported": r.items_imported,
            "items_skipped": r.items_skipped,
            "errors": r.errors,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# ENDPOINTS
# ---------------------------------------------------------------------------

@app.get("/api/projects/{project_id}/endpoints", response_model=list[EndpointResponse])
async def list_endpoints(
    project_id: str,
    method: str | None = None,
    source: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    await _get_project(project_id, db)
    stmt = select(Endpoint).where(Endpoint.project_id == project_id)
    if method:
        stmt = stmt.where(Endpoint.method == method.upper())
    if source:
        stmt = stmt.where(Endpoint.discovery_source == source)
    stmt = stmt.order_by(Endpoint.first_seen.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@app.get("/api/projects/{project_id}/endpoints/{endpoint_id}")
async def get_endpoint(project_id: str, endpoint_id: str, db: AsyncSession = Depends(get_db)):
    await _get_project(project_id, db)
    ep = await db.get(Endpoint, endpoint_id)
    if not ep or ep.project_id != project_id:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    obs_result = await db.execute(
        select(Observation).where(Observation.endpoint_id == endpoint_id)
    )
    observations = obs_result.scalars().all()

    return {
        "id": ep.id,
        "url": ep.url,
        "normalized_url": ep.normalized_url,
        "method": ep.method,
        "status_code": ep.status_code,
        "content_type": ep.content_type,
        "discovery_source": ep.discovery_source,
        "parent_url": ep.parent_url,
        "first_seen": ep.first_seen,
        "last_seen": ep.last_seen,
        "observations": [
            {
                "id": o.id,
                "source_type": o.source_type,
                "request_method": o.request_method,
                "request_url": o.request_url,
                "response_status": o.response_status,
                "content_type": o.content_type,
                "timestamp": o.timestamp,
                "redacted": o.redacted,
            }
            for o in observations
        ],
    }


# ---------------------------------------------------------------------------
# GRAPH
# ---------------------------------------------------------------------------

@app.get("/api/projects/{project_id}/graph", response_model=GraphResponse)
async def get_graph(project_id: str, db: AsyncSession = Depends(get_db)):
    await _get_project(project_id, db)

    db_nodes = (await db.execute(
        select(GraphNode).where(GraphNode.project_id == project_id)
    )).scalars().all()
    db_edges = (await db.execute(
        select(GraphEdge).where(GraphEdge.project_id == project_id)
    )).scalars().all()

    if db_nodes:
        nodes = [
            {
                "id": n.id,
                "type": n.node_type,
                "label": n.label,
                "url": (n.properties or {}).get("url"),
                "method": (n.properties or {}).get("method"),
                "properties": n.properties,
                "evidence_source": n.evidence_source,
                "confidence": n.confidence,
                "observed": n.observed,
            }
            for n in db_nodes
        ]
        edges_list = [
            {
                "id": e.id,
                "source": e.source_node_id,
                "target": e.target_node_id,
                "type": e.edge_type,
                "label": e.label,
                "properties": e.properties,
                "evidence_source": e.evidence_source,
                "confidence": e.confidence,
                "observed": e.observed,
            }
            for e in db_edges
        ]
        observed = sum(1 for n in db_nodes if n.observed)
        statistics = {
            "total_nodes": len(nodes),
            "total_edges": len(edges_list),
            "observed_nodes": observed,
            "inferred_nodes": len(nodes) - observed,
            "components": 1,
        }
        return GraphResponse(project_id=project_id, nodes=nodes, edges=edges_list, statistics=statistics)

    ep_result = await db.execute(select(Endpoint).where(Endpoint.project_id == project_id))
    endpoints = ep_result.scalars().all()
    obs_result = await db.execute(select(Observation).where(Observation.project_id == project_id))
    observations = obs_result.scalars().all()
    graph_dict = _build_graph_from_db(project_id, endpoints, observations)
    return GraphResponse(**graph_dict)


@app.post("/api/projects/{project_id}/graph/build")
async def build_graph(project_id: str, db: AsyncSession = Depends(get_db)):
    project = await _get_project(project_id, db)

    ep_result = await db.execute(select(Endpoint).where(Endpoint.project_id == project_id))
    endpoints = ep_result.scalars().all()
    obs_result = await db.execute(select(Observation).where(Observation.project_id == project_id))
    observations = obs_result.scalars().all()

    # Clear old graph data
    old_edges = (await db.execute(select(GraphEdge).where(GraphEdge.project_id == project_id))).scalars().all()
    for e in old_edges:
        await db.delete(e)
    old_nodes = (await db.execute(select(GraphNode).where(GraphNode.project_id == project_id))).scalars().all()
    for n in old_nodes:
        await db.delete(n)
    await db.flush()

    graph_dict = _build_graph_from_db(project_id, endpoints, observations)

    node_id_map: dict[str, str] = {}
    for nd in graph_dict["nodes"]:
        gn = GraphNode(
            project_id=project_id,
            node_type=nd["type"],
            label=nd["label"],
            properties=nd.get("properties"),
            evidence_source=nd.get("evidence_source"),
            confidence=nd.get("confidence", 1.0),
            observed=nd.get("observed", True),
        )
        db.add(gn)
        await db.flush()
        node_id_map[nd["id"]] = gn.id

    for ed in graph_dict["edges"]:
        src_id = node_id_map.get(ed["source"])
        tgt_id = node_id_map.get(ed["target"])
        if src_id and tgt_id:
            ge = GraphEdge(
                project_id=project_id,
                source_node_id=src_id,
                target_node_id=tgt_id,
                edge_type=ed["type"],
                label=ed.get("label", ""),
                properties=ed.get("properties"),
                evidence_source=ed.get("evidence_source"),
                confidence=ed.get("confidence", 1.0),
                observed=ed.get("observed", True),
            )
            db.add(ge)

    await db.flush()
    return {
        "detail": "Graph built",
        "nodes": len(graph_dict["nodes"]),
        "edges": len(graph_dict["edges"]),
    }


# ---------------------------------------------------------------------------
# ANALYSIS
# ---------------------------------------------------------------------------

@app.post("/api/projects/{project_id}/analyze")
async def run_analysis(project_id: str, db: AsyncSession = Depends(get_db)):
    project = await _get_project(project_id, db)

    ep_result = await db.execute(select(Endpoint).where(Endpoint.project_id == project_id))
    endpoints = ep_result.scalars().all()
    obs_result = await db.execute(select(Observation).where(Observation.project_id == project_id))
    observations = obs_result.scalars().all()

    try:
        from backend.graph_engine.engine import ApplicationGraph
        from backend.security_rules.engine import RulesEngine
        from backend.attack_paths.analyzer import AttackPathAnalyzer
        from backend.validation.planner import TestPlanner

        graph = ApplicationGraph(project_id)
        crawl_data = [
            {
                "url": ep.url,
                "normalized_url": ep.normalized_url or ep.url,
                "method": ep.method,
                "status_code": ep.status_code,
                "content_type": ep.content_type,
                "parent_url": ep.parent_url,
                "discovery_source": ep.discovery_source,
            }
            for ep in endpoints
        ]
        graph.merge_from_crawl(crawl_data)

        rules_engine = RulesEngine()
        findings = rules_engine.analyze(graph)

        # Clear old findings
        old_findings = (await db.execute(select(Finding).where(Finding.project_id == project_id))).scalars().all()
        for of in old_findings:
            await db.delete(of)
        await db.flush()

        for sf in findings:
            f = Finding(
                project_id=project_id,
                title=sf.title,
                description=sf.description,
                affected_endpoints=sf.affected_endpoints,
                evidence_refs=sf.evidence_refs,
                detection_rule=sf.detection_rule,
                reasoning=sf.reasoning,
                assumptions=sf.assumptions,
                severity=sf.severity,
                confidence=sf.confidence,
                validation_status=sf.validation_status,
                reproduction_steps=sf.reproduction_steps,
                remediation=sf.remediation,
            )
            db.add(f)

        analyzer = AttackPathAnalyzer(graph)
        attack_paths = analyzer.analyze()

        old_ap = (await db.execute(select(AttackPath).where(AttackPath.project_id == project_id))).scalars().all()
        for oap in old_ap:
            await db.delete(oap)
        await db.flush()

        for cap in attack_paths:
            ap = AttackPath(
                project_id=project_id,
                entry_point=cap.entry_point_label,
                target_operation=cap.target_label,
                intermediate_steps=cap.intermediate_steps,
                preconditions=cap.preconditions,
                observations=cap.observations,
                unverified_assumptions=cap.unverified_assumptions,
                potential_impact=cap.potential_impact,
                confidence=cap.confidence,
                priority_score=cap.priority_score,
                recommended_steps=cap.recommended_steps,
            )
            db.add(ap)
            await db.flush()

            planner = TestPlanner()
            plans = planner.generate_plans([cap], graph)
            for tp_item in plans:
                tp = TestPlan(
                    project_id=project_id,
                    attack_path_id=ap.id,
                    hypothesis=tp_item.hypothesis,
                    evidence=tp_item.evidence,
                    required_accounts=tp_item.required_accounts,
                    preconditions=tp_item.preconditions,
                    test_procedure=tp_item.test_procedure,
                    expected_secure_behavior=tp_item.expected_secure_behavior,
                    potential_insecure_outcomes=tp_item.potential_insecure_outcomes,
                    cleanup_steps=tp_item.cleanup_steps,
                    evidence_to_capture=tp_item.evidence_to_capture,
                    limitations=tp_item.limitations,
                )
                db.add(tp)

        await db.flush()
        return {
            "detail": "Analysis complete",
            "findings": len(findings),
            "attack_paths": len(attack_paths),
        }

    except ImportError:
        return {
            "detail": "Analysis modules not yet available",
            "findings": 0,
            "attack_paths": 0,
        }


@app.get("/api/projects/{project_id}/findings", response_model=list[FindingResponse])
async def list_findings(
    project_id: str,
    severity: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    await _get_project(project_id, db)
    stmt = select(Finding).where(Finding.project_id == project_id)
    if severity:
        stmt = stmt.where(Finding.severity == severity)
    if status:
        stmt = stmt.where(Finding.validation_status == status)
    stmt = stmt.order_by(Finding.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@app.get("/api/projects/{project_id}/findings/{finding_id}")
async def get_finding(project_id: str, finding_id: str, db: AsyncSession = Depends(get_db)):
    await _get_project(project_id, db)
    finding = await db.get(Finding, finding_id)
    if not finding or finding.project_id != project_id:
        raise HTTPException(status_code=404, detail="Finding not found")
    return {
        "id": finding.id,
        "title": finding.title,
        "description": finding.description,
        "affected_endpoints": finding.affected_endpoints,
        "evidence_refs": finding.evidence_refs,
        "detection_rule": finding.detection_rule,
        "reasoning": finding.reasoning,
        "assumptions": finding.assumptions,
        "severity": finding.severity,
        "confidence": finding.confidence,
        "validation_status": finding.validation_status,
        "reproduction_steps": finding.reproduction_steps,
        "remediation": finding.remediation,
        "created_at": finding.created_at,
        "updated_at": finding.updated_at,
    }


@app.patch("/api/projects/{project_id}/findings/{finding_id}")
async def update_finding_status(
    project_id: str,
    finding_id: str,
    data: FindingUpdate,
    db: AsyncSession = Depends(get_db),
):
    await _get_project(project_id, db)
    finding = await db.get(Finding, finding_id)
    if not finding or finding.project_id != project_id:
        raise HTTPException(status_code=404, detail="Finding not found")

    valid_statuses = {"hypothesis", "unvalidated", "confirmed", "false_positive", "inconclusive"}
    if data.validation_status is not None:
        if data.validation_status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
        finding.validation_status = data.validation_status

    valid_severities = {"info", "low", "medium", "high", "critical"}
    if data.severity is not None:
        if data.severity not in valid_severities:
            raise HTTPException(status_code=400, detail=f"Invalid severity. Must be one of: {valid_severities}")
        finding.severity = data.severity

    finding.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return {"detail": "Finding updated"}


# ---------------------------------------------------------------------------
# ATTACK PATHS
# ---------------------------------------------------------------------------

@app.get("/api/projects/{project_id}/attack-paths", response_model=list[AttackPathResponse])
async def list_attack_paths(project_id: str, db: AsyncSession = Depends(get_db)):
    await _get_project(project_id, db)
    result = await db.execute(
        select(AttackPath)
        .where(AttackPath.project_id == project_id)
        .order_by(AttackPath.priority_score.desc())
    )
    return result.scalars().all()


@app.get("/api/projects/{project_id}/attack-paths/{path_id}")
async def get_attack_path(project_id: str, path_id: str, db: AsyncSession = Depends(get_db)):
    await _get_project(project_id, db)
    ap = await db.get(AttackPath, path_id)
    if not ap or ap.project_id != project_id:
        raise HTTPException(status_code=404, detail="Attack path not found")
    return {
        "id": ap.id,
        "entry_point": ap.entry_point,
        "target_operation": ap.target_operation,
        "intermediate_steps": ap.intermediate_steps,
        "preconditions": ap.preconditions,
        "observations": ap.observations,
        "unverified_assumptions": ap.unverified_assumptions,
        "potential_impact": ap.potential_impact,
        "confidence": ap.confidence,
        "priority_score": ap.priority_score,
        "recommended_steps": ap.recommended_steps,
        "created_at": ap.created_at,
    }


# ---------------------------------------------------------------------------
# TEST PLANS
# ---------------------------------------------------------------------------

@app.get("/api/projects/{project_id}/test-plans", response_model=list[TestPlanResponse])
async def list_test_plans(project_id: str, db: AsyncSession = Depends(get_db)):
    await _get_project(project_id, db)
    result = await db.execute(
        select(TestPlan)
        .where(TestPlan.project_id == project_id)
        .order_by(TestPlan.created_at.desc())
    )
    return result.scalars().all()


@app.get("/api/projects/{project_id}/test-plans/{plan_id}")
async def get_test_plan(project_id: str, plan_id: str, db: AsyncSession = Depends(get_db)):
    await _get_project(project_id, db)
    tp = await db.get(TestPlan, plan_id)
    if not tp or tp.project_id != project_id:
        raise HTTPException(status_code=404, detail="Test plan not found")
    return {
        "id": tp.id,
        "attack_path_id": tp.attack_path_id,
        "hypothesis": tp.hypothesis,
        "evidence": tp.evidence,
        "required_accounts": tp.required_accounts,
        "preconditions": tp.preconditions,
        "test_procedure": tp.test_procedure,
        "expected_secure_behavior": tp.expected_secure_behavior,
        "potential_insecure_outcomes": tp.potential_insecure_outcomes,
        "cleanup_steps": tp.cleanup_steps,
        "evidence_to_capture": tp.evidence_to_capture,
        "limitations": tp.limitations,
        "status": tp.status,
        "created_at": tp.created_at,
    }


@app.patch("/api/projects/{project_id}/test-plans/{plan_id}")
async def update_test_plan_status(
    project_id: str,
    plan_id: str,
    data: TestPlanUpdate,
    db: AsyncSession = Depends(get_db),
):
    await _get_project(project_id, db)
    tp = await db.get(TestPlan, plan_id)
    if not tp or tp.project_id != project_id:
        raise HTTPException(status_code=404, detail="Test plan not found")

    valid = {"pending", "approved", "running", "completed", "cancelled"}
    if data.status is not None:
        if data.status not in valid:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid}")
        tp.status = data.status
    await db.flush()
    return {"detail": "Test plan updated"}


# ---------------------------------------------------------------------------
# REPORTS
# ---------------------------------------------------------------------------

@app.get("/api/projects/{project_id}/reports/{report_format}")
async def generate_report(project_id: str, report_format: str, db: AsyncSession = Depends(get_db)):
    if report_format not in ("json", "markdown", "html"):
        raise HTTPException(status_code=400, detail="Format must be json, markdown, or html")

    project = await _get_project(project_id, db)

    ep_result = await db.execute(select(Endpoint).where(Endpoint.project_id == project_id))
    endpoints = ep_result.scalars().all()

    cs_result = await db.execute(
        select(CrawlSession).where(CrawlSession.project_id == project_id)
    )
    crawl_sessions = cs_result.scalars().all()
    total_crawled = sum(s.pages_crawled for s in crawl_sessions)
    total_discovered = sum(s.pages_discovered for s in crawl_sessions)
    total_errors = sum(len(s.errors) for s in crawl_sessions if s.errors)

    f_result = await db.execute(select(Finding).where(Finding.project_id == project_id))
    findings = f_result.scalars().all()

    ap_result = await db.execute(select(AttackPath).where(AttackPath.project_id == project_id))
    attack_paths = ap_result.scalars().all()

    tp_result = await db.execute(select(TestPlan).where(TestPlan.project_id == project_id))
    test_plans = tp_result.scalars().all()

    gn_result = await db.execute(select(GraphNode).where(GraphNode.project_id == project_id))
    graph_nodes = gn_result.scalars().all()
    ge_result = await db.execute(select(GraphEdge).where(GraphEdge.project_id == project_id))
    graph_edges = ge_result.scalars().all()

    from backend.reporting.generator import ReportGenerator, ReportData

    observed = sum(1 for n in graph_nodes if n.observed)
    report_data = ReportData(
        project_name=project.name,
        target_url=project.target_url,
        scope={
            "allowed_hosts": project.allowed_hosts or [],
            "allowed_schemes": project.allowed_schemes or [],
            "exclude_paths": project.exclude_paths or [],
        },
        crawl_summary={
            "pages_crawled": total_crawled,
            "pages_discovered": total_discovered,
            "errors": total_errors,
        },
        endpoints=[
            {
                "url": ep.url,
                "method": ep.method,
                "status_code": ep.status_code,
                "discovery_source": ep.discovery_source,
            }
            for ep in endpoints
        ],
        graph_statistics={
            "total_nodes": len(graph_nodes),
            "total_edges": len(graph_edges),
            "observed_nodes": observed,
            "inferred_nodes": len(graph_nodes) - observed,
            "components": 1,
        },
        findings=[
            {
                "title": f.title,
                "description": f.description,
                "affected_endpoints": f.affected_endpoints,
                "severity": f.severity,
                "confidence": f.confidence,
                "validation_status": f.validation_status,
                "detection_rule": f.detection_rule,
                "reasoning": f.reasoning,
                "assumptions": f.assumptions,
                "remediation": f.remediation,
            }
            for f in findings
        ],
        attack_paths=[
            {
                "entry_point": ap.entry_point,
                "target_operation": ap.target_operation,
                "confidence": ap.confidence,
                "priority_score": ap.priority_score,
                "potential_impact": ap.potential_impact,
                "unverified_assumptions": ap.unverified_assumptions,
            }
            for ap in attack_paths
        ],
        test_plans=[
            {
                "hypothesis": tp.hypothesis,
                "test_procedure": tp.test_procedure,
                "expected_secure_behavior": tp.expected_secure_behavior,
            }
            for tp in test_plans
        ],
    )

    gen = ReportGenerator()
    if report_format == "json":
        return json.loads(gen.generate_json(report_data))
    elif report_format == "markdown":
        return PlainTextResponse(content=gen.generate_markdown(report_data), media_type="text/markdown")
    else:
        return HTMLResponse(content=gen.generate_html(report_data))


# ---------------------------------------------------------------------------
# AI
# ---------------------------------------------------------------------------

@app.get("/api/ai/status")
async def ai_status():
    return {
        "enabled": settings.ai.enabled,
        "model": settings.ai.model if settings.ai.enabled else None,
    }


@app.get("/api/ai/config")
async def get_ai_config():
    return {
        "enabled": settings.ai.enabled,
        "api_base": settings.ai.api_base,
        "api_key_set": bool(settings.ai.api_key),
        "model": settings.ai.model,
        "max_tokens": settings.ai.max_tokens,
        "temperature": settings.ai.temperature,
    }


class AIConfigUpdate(BaseModel):
    enabled: bool | None = None
    api_base: str | None = None
    api_key: str | None = None
    model: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None


@app.patch("/api/ai/config")
async def update_ai_config(update: AIConfigUpdate):
    from backend.config import save_ai_config
    if update.enabled is not None:
        settings.ai.enabled = update.enabled
    if update.api_base is not None:
        settings.ai.api_base = update.api_base
    if update.api_key is not None:
        settings.ai.api_key = update.api_key
    if update.model is not None:
        settings.ai.model = update.model
    if update.max_tokens is not None:
        settings.ai.max_tokens = update.max_tokens
    if update.temperature is not None:
        settings.ai.temperature = update.temperature
    save_ai_config()
    return {
        "enabled": settings.ai.enabled,
        "api_base": settings.ai.api_base,
        "api_key_set": bool(settings.ai.api_key),
        "model": settings.ai.model,
    }


@app.post("/api/projects/{project_id}/ai/summarize")
async def ai_summarize(project_id: str, db: AsyncSession = Depends(get_db)):
    await _get_project(project_id, db)

    ep_result = await db.execute(select(Endpoint).where(Endpoint.project_id == project_id))
    endpoints = ep_result.scalars().all()
    obs_result = await db.execute(select(Observation).where(Observation.project_id == project_id))
    observations = obs_result.scalars().all()
    graph_dict = _build_graph_from_db(project_id, endpoints, observations)

    # Enrich with findings for better context
    f_result = await db.execute(select(Finding).where(Finding.project_id == project_id))
    findings = f_result.scalars().all()
    graph_dict["findings"] = [
        {
            "title": f.title,
            "severity": f.severity,
            "validation_status": f.validation_status,
            "affected_endpoints": f.affected_endpoints,
        }
        for f in findings
    ]

    from backend.ai_assistant.assistant import AIAssistant

    assistant = AIAssistant()
    summary = await assistant.summarize_graph(graph_dict)
    return {"summary": summary}


# ---------------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------------

@app.get("/api/settings")
async def get_settings():
    return {
        "crawler": settings.crawler.model_dump(),
        "ai": {"enabled": settings.ai.enabled, "model": settings.ai.model},
        "server": {"cors_origins": settings.server.cors_origins},
    }
