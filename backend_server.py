"""
AttackGraph backend server entry point for PyInstaller bundle and dev use.
"""
import sys
import os
import argparse
import pathlib

# Set up data directory BEFORE importing any backend modules,
# so config.py picks up the env vars at module-load time.
def _setup_data_dir() -> str:
    xdg = os.environ.get("XDG_DATA_HOME", os.path.join(os.path.expanduser("~"), ".local", "share"))
    data_dir = pathlib.Path(os.environ.get("ATTACKGRAPH_DATA_DIR") or os.path.join(xdg, "attackgraph"))
    data_dir.mkdir(parents=True, exist_ok=True)

    # Set env vars that config.py reads via os.environ.get()
    os.environ.setdefault("ATTACKGRAPH_DATA_DIR", str(data_dir))
    db_path = data_dir / "attackgraph.db"
    os.environ.setdefault("ATTACKGRAPH_DB", f"sqlite+aiosqlite:///{db_path}")
    return str(data_dir)

_setup_data_dir()

# When running as a PyInstaller bundle, sys._MEIPASS is the extraction dir.
if getattr(sys, "frozen", False):
    sys.path.insert(0, sys._MEIPASS)  # type: ignore[attr-defined]

import uvicorn  # noqa: E402 — must come after path setup


def main() -> None:
    parser = argparse.ArgumentParser(description="AttackGraph Backend Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--log-level", default="warning")
    args = parser.parse_args()

    uvicorn.run(
        "backend.api.main:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
