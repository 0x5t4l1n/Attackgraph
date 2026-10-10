"""Deliberately vulnerable test application for AttackGraph testing.

This is NOT a production application. It intentionally contains security
weaknesses to validate AttackGraph's detection capabilities.

DO NOT deploy this application on any network accessible to untrusted users.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException, Header, Cookie, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="VulnApp - AttackGraph Test Target", version="0.1.0")

USERS = {
    "1": {"id": "1", "name": "Alice Admin", "email": "alice@test.local", "role": "admin", "password_hash": "fakehash_admin"},
    "2": {"id": "2", "name": "Bob User", "email": "bob@test.local", "role": "user", "password_hash": "fakehash_user"},
}
PROJECTS = {
    "p1": {"id": "p1", "name": "Secret Project", "owner_id": "1", "budget": 50000},
    "p2": {"id": "p2", "name": "Public Project", "owner_id": "2", "budget": 1000},
}
SESSIONS: dict[str, str] = {}


class LoginRequest(BaseModel):
    username: str
    password: str


class ProjectUpdate(BaseModel):
    name: str | None = None
    budget: int | None = None
    owner_id: str | None = None
    role: str | None = None


@app.get("/", response_class=HTMLResponse)
async def index():
    return """<html><body>
    <h1>VulnApp</h1>
    <p>Test application for <a href="/docs">API docs</a></p>
    <ul>
      <li><a href="/api/users">Users</a></li>
      <li><a href="/api/projects">Projects</a></li>
      <li><a href="/admin/settings">Admin Settings</a></li>
      <li><a href="/debug/info">Debug Info</a></li>
    </ul>
    <form action="/api/login" method="post">
      <input name="username" placeholder="username">
      <input name="password" type="password" placeholder="password">
      <button type="submit">Login</button>
    </form>
    </body></html>"""


@app.get("/robots.txt")
async def robots():
    return "User-agent: *\nDisallow: /admin/\nDisallow: /debug/\nSitemap: /sitemap.xml"


@app.get("/sitemap.xml")
async def sitemap():
    return """<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>/</loc></url>
  <url><loc>/api/users</loc></url>
  <url><loc>/api/projects</loc></url>
</urlset>"""


@app.post("/api/login")
async def login(data: LoginRequest):
    for user in USERS.values():
        if user["name"].split()[0].lower() == data.username.lower():
            token = str(uuid.uuid4())
            SESSIONS[token] = user["id"]
            return {"token": token, "user_id": user["id"]}
    raise HTTPException(status_code=401, detail="Invalid credentials")


# --- IDOR: No ownership check on user retrieval ---
@app.get("/api/users")
async def list_users():
    return [{"id": u["id"], "name": u["name"], "email": u["email"], "role": u["role"]} for u in USERS.values()]


@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    user = USERS.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user  # Exposes password_hash


# --- No auth on sensitive project endpoints ---
@app.get("/api/projects")
async def list_projects():
    return list(PROJECTS.values())


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    project = PROJECTS.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# --- Mass assignment: allows setting owner_id and role ---
@app.put("/api/projects/{project_id}")
async def update_project(project_id: str, data: ProjectUpdate):
    project = PROJECTS.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if data.name is not None:
        project["name"] = data.name
    if data.budget is not None:
        project["budget"] = data.budget
    if data.owner_id is not None:
        project["owner_id"] = data.owner_id
    return project


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    if project_id in PROJECTS:
        del PROJECTS[project_id]
    return {"detail": "Deleted"}


# --- Admin endpoints without auth ---
@app.get("/admin/settings")
async def admin_settings():
    return {
        "debug_mode": True,
        "database_url": "postgresql://admin:secretpass@db.internal:5432/app",
        "api_key": "sk-fake-key-12345",
    }


@app.post("/admin/users/{user_id}/role")
async def change_role(user_id: str, role: str = "admin"):
    user = USERS.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user["role"] = role
    return user


# --- Debug endpoint ---
@app.get("/debug/info")
async def debug_info(request: Request):
    return {
        "server_time": datetime.utcnow().isoformat(),
        "environment": "development",
        "python_version": "3.14",
        "database": "sqlite:///./test.db",
        "request_headers": dict(request.headers),
    }


@app.get("/api/internal/metrics")
async def internal_metrics():
    return {"requests_total": 42, "errors_total": 3, "uptime_seconds": 86400}
