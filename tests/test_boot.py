"""Importing the server must never depend on Telegram secrets."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_import_bridge_without_any_credentials():
    env = {k: v for k, v in os.environ.items() if k not in {
        "API_ID", "API_HASH", "TELEGRAM_SESSION", "CHANNEL_ID", "STORAGE_BACKEND"
    }}
    env.pop("TELEGRAM_SESSION", None)
    result = subprocess.run(
        [sys.executable, "-c", "import bridge; print(bridge.manager.storage.name)"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "local" in result.stdout
    assert "ValueError" not in result.stderr


def test_get_storage_modes(monkeypatch):
    from client import LocalStorage, TelegramStorage, get_storage, storage_status

    monkeypatch.delenv("API_ID", raising=False)
    monkeypatch.delenv("API_HASH", raising=False)
    monkeypatch.delenv("TELEGRAM_SESSION", raising=False)
    monkeypatch.delenv("CHANNEL_ID", raising=False)

    monkeypatch.setenv("STORAGE_BACKEND", "auto")
    assert isinstance(get_storage(), LocalStorage)
    assert storage_status()["selected_backend"] == "local"

    monkeypatch.setenv("API_ID", "12345")
    monkeypatch.setenv("API_HASH", "abc")
    monkeypatch.setenv("TELEGRAM_SESSION", "session")
    monkeypatch.setenv("CHANNEL_ID", "-100123")
    assert isinstance(get_storage(), TelegramStorage)
    assert storage_status()["telegram_configured"] is True

    monkeypatch.setenv("STORAGE_BACKEND", "local")
    assert isinstance(get_storage(), LocalStorage)


def test_local_index_rejects_corrupt_file(tmp_path):
    import asyncio

    from client import LocalStorage, StorageUnavailable

    storage = LocalStorage(root=tmp_path)
    asyncio.run(storage.connect())
    storage.index_path.write_text("{not json", encoding="utf-8")

    async def read():
        async with storage.session():
            return await storage.get_index()

    try:
        asyncio.run(read())
        assert False, "corrupt index must not be treated as empty"
    except StorageUnavailable:
        pass
