from __future__ import annotations

from pydantic import BaseModel


class CrawlerConfig(BaseModel):
    max_depth: int = 3
    max_concurrent: int = 5
    request_timeout: float = 30.0
    rate_limit_per_second: float = 10.0
    max_response_size_bytes: int = 10 * 1024 * 1024
    max_pages: int = 1000
    user_agent: str = "AttackGraph/0.1"
    follow_redirects: bool = True
    max_redirects: int = 5


class AIConfig(BaseModel):
    enabled: bool = False
    api_base: str = "http://localhost:11434/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    redaction_enabled: bool = True
    max_tokens: int = 4096
    temperature: float = 0.2


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


class Settings(BaseModel):
    database_url: str = "sqlite+aiosqlite:///./attackgraph.db"
    crawler: CrawlerConfig = CrawlerConfig()
    ai: AIConfig = AIConfig()
    server: ServerConfig = ServerConfig()
    debug: bool = False


settings = Settings()
