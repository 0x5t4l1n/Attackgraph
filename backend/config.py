from __future__ import annotations

import json
import os
import pathlib
from pydantic import BaseModel

# User data directory — uses XDG_DATA_HOME or ~/.local/share/attackgraph
_DATA_DIR = pathlib.Path(
    os.environ.get("ATTACKGRAPH_DATA_DIR")
    or os.path.join(os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")), "attackgraph")
)
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_CONFIG_FILE = _DATA_DIR / "ai_config.json"

# Legacy config file in cwd (for development)
_LEGACY_CONFIG = pathlib.Path("./attackgraph_ai_config.json")


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
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "tauri://localhost",
        "https://tauri.localhost",
    ]


class Settings(BaseModel):
    database_url: str = os.environ.get(
        "ATTACKGRAPH_DB",
        f"sqlite+aiosqlite:///{str(_DATA_DIR / 'attackgraph.db')}"
    )
    crawler: CrawlerConfig = CrawlerConfig()
    ai: AIConfig = AIConfig()
    server: ServerConfig = ServerConfig()
    debug: bool = False


settings = Settings()


def load_persisted_ai_config() -> None:
    # Try XDG data dir first, fall back to legacy cwd file
    for cfg_path in [_CONFIG_FILE, _LEGACY_CONFIG]:
        if cfg_path.exists():
            try:
                data = json.loads(cfg_path.read_text())
                for k, v in data.items():
                    if hasattr(settings.ai, k):
                        setattr(settings.ai, k, v)
                return
            except Exception:
                pass


def save_ai_config() -> None:
    _CONFIG_FILE.write_text(json.dumps(settings.ai.model_dump(), indent=2))


load_persisted_ai_config()
