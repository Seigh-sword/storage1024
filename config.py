"""Shared configuration loading for Storage1024.

Everything that needs credentials goes through :func:`load_config` so that the
same lookup rules apply to the web server, the CLI tools and the libraries.
Importing this module never raises: a missing config is a runtime problem, not
an import-time crash.
"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# The first existing file wins. A real deployment uses environment variables
# (Render injects them directly), while local development uses .env.
CONFIG_PATHS = (
    Path.home() / ".storage1024" / "config.env",
    BASE_DIR / ".env",
    Path.cwd() / ".env",
)

SESSION_FILES = (
    Path.home() / ".storage1024" / "storage.session_string",
    BASE_DIR / "storage.session_string",
)

_config_loaded = False


def load_config(force: bool = False) -> None:
    """Load a .env file once. Real environment variables always win."""
    global _config_loaded
    if _config_loaded and not force:
        return
    _config_loaded = True
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - dotenv is in requirements.txt
        return
    for path in CONFIG_PATHS:
        if path.is_file():
            load_dotenv(path, override=False)
            break


def data_dir() -> Path:
    load_config()
    raw = os.getenv("DATA_DIR", str(BASE_DIR / "data"))
    path = Path(raw)
    if not path.is_absolute():
        path = BASE_DIR / path
    return path.resolve()


def telegram_credentials() -> dict:
    """Return the Telegram credentials found in env / .env / session files."""
    load_config()
    session = os.getenv("TELEGRAM_SESSION", "").strip()
    if not session:
        for path in SESSION_FILES:
            if path.is_file():
                session = path.read_text(encoding="utf-8").strip()
                if session:
                    break

    channel_raw = os.getenv("CHANNEL_ID", "").strip()
    try:
        channel_id = int(channel_raw) if channel_raw else None
    except ValueError:
        channel_id = None

    api_id_raw = os.getenv("API_ID", "").strip()
    try:
        api_id = int(api_id_raw) if api_id_raw else None
    except ValueError:
        api_id = None

    return {
        "api_id": api_id,
        "api_hash": os.getenv("API_HASH", "").strip() or None,
        "session": session or None,
        "channel_id": channel_id,
        "index_message_id": int(os.getenv("INDEX_MESSAGE_ID", "4") or 4),
    }


load_config()
