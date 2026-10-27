"""Offline tests for the GitHub storage backend using a fake Contents API."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote

import httpx
import pytest

from client import GitHubStorage, StorageNotFound, StorageUnavailable, get_storage, storage_status
from manager import ProjectManager

PREFIX = "/repos/o/r/contents/"


def _sha(content: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()


@pytest.fixture
def fake_api(tmp_path):
    """In-memory GitHub Contents API + a storage client wired to it."""
    files: dict[str, bytes] = {}
    large: set[str] = set()

    def entry(key: str, as_dir_entry: bool = False):
        content = files[key]
        name = key.rsplit("/", 1)[-1]
        if as_dir_entry:
            return {"name": name, "path": key, "size": len(content),
                    "sha": _sha(content), "type": "file"}
        return {
            "name": name,
            "path": key,
            "size": len(content),
            "sha": _sha(content),
            "type": "file",
            "encoding": "none" if key in large else "base64",
            "content": "" if key in large else base64.b64encode(content).decode(),
        }

    def handler(request: httpx.Request) -> httpx.Response:
        path = unquote(request.url.path)
        if path.startswith(PREFIX):
            key = path[len(PREFIX):]
            if request.method == "GET":
                if key in files:
                    return httpx.Response(200, json=entry(key))
                children = [
                    entry(k, as_dir_entry=True)
                    for k in files
                    if k.startswith(key.rstrip("/") + "/")
                    and "/" not in k[len(key.rstrip("/")) + 1:]
                ]
                if children:
                    return httpx.Response(200, json=children)
                return httpx.Response(404, json={"message": "Not Found"})
            if request.method == "PUT":
                body = json.loads(request.content)
                current = _sha(files[key]) if key in files else None
                if body.get("sha") != current:
                    return httpx.Response(409, json={"message": "conflict"})
                files[key] = base64.b64decode(body["content"])
                return httpx.Response(200, json={"content": {"name": key}})
            if request.method == "DELETE":
                body = json.loads(request.content)
                if key not in files or body.get("sha") != _sha(files[key]):
                    return httpx.Response(409, json={"message": "conflict"})
                del files[key]
                return httpx.Response(200, json={})

        if path.startswith("/repos/o/r/git/blobs/"):
            blob_sha = path.rsplit("/", 1)[-1]
            for content in files.values():
                if _sha(content) == blob_sha:
                    return httpx.Response(200, json={
                        "sha": blob_sha,
                        "encoding": "base64",
                        "content": base64.b64encode(content).decode(),
                    })
            return httpx.Response(404, json={"message": "Not Found"})

        return httpx.Response(404, json={"message": "Not Found"})

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://api.github.com"
    )
    storage = GitHubStorage(
        token="ghp_test", repo="o/r", branch="main",
        path="storage1024-data", max_file_mb=1, client=client,
    )
    return storage, files, large, tmp_path, client


def run(coro):
    return asyncio.run(coro)


def test_index_round_trip_and_no_size_ceiling(fake_api):
    storage, files, _, _, _ = fake_api

    async def scenario():
        async with storage.session():
            assert await storage.get_index() == {"projects": {}}
            # Far bigger than Telegram's 4096-character text-message limit.
            data = {"projects": {"1234": {"name": "Big " * 5000}}}
            await storage.update_index(data)
            assert await storage.get_index() == data
            data["projects"]["5678"] = {"name": "second write"}
            await storage.update_index(data)
            assert (await storage.get_index())["projects"]["5678"]["name"] == "second write"

    run(scenario())
    assert "storage1024-data/index.json" in files


def test_corrupt_index_raises_instead_of_wiping(fake_api):
    storage, files, _, _, _ = fake_api
    files["storage1024-data/index.json"] = b"{not json"

    async def scenario():
        async with storage.session():
            return await storage.get_index()

    with pytest.raises(StorageUnavailable, match="unreadable"):
        run(scenario())


def test_file_upload_download_delete(fake_api):
    storage, files, _, tmp_path, _ = fake_api
    source = tmp_path / "hello.txt"
    source.write_bytes(b"hello github")

    async def scenario():
        async with storage.session():
            file_id = await storage.upload_file(str(source))
            out = await storage.download_file(file_id)
            assert Path(out).read_bytes() == b"hello github"
            assert Path(out).name == "hello.txt"
            listed = await storage.list_files()
            assert listed and listed[0]["name"] == "hello.txt"
            assert await storage.delete_file(file_id) is True
            with pytest.raises(StorageNotFound):
                await storage.download_file(file_id)

    run(scenario())
    assert not [k for k in files if k.startswith("storage1024-data/files/")]


def test_large_file_is_read_through_blob_api(fake_api):
    storage, files, large, tmp_path, _ = fake_api
    source = tmp_path / "large.bin"
    source.write_bytes(b"x" * 4096)

    async def scenario():
        async with storage.session():
            file_id = await storage.upload_file(str(source))
            key = next(k for k in files if k.startswith("storage1024-data/files/"))
            large.add(key)  # GitHub returns encoding "none" above 1 MB
            out = await storage.download_file(file_id)
            assert Path(out).read_bytes() == b"x" * 4096

    run(scenario())


def test_file_size_cap(fake_api, tmp_path):
    storage, _, _, tmp_path, _ = fake_api
    source = tmp_path / "too-big.bin"
    source.write_bytes(b"x" * (2 * 1024 * 1024))  # limit is 1 MB

    async def scenario():
        async with storage.session():
            return await storage.upload_file(str(source))

    with pytest.raises(StorageUnavailable, match="exceeds the GitHub backend limit"):
        run(scenario())


def test_gv_crud_and_manager_integration(fake_api, tmp_path):
    storage, files, _, tmp_path, _ = fake_api
    source = tmp_path / "note.txt"
    source.write_bytes(b"note")

    async def scenario():
        manager = ProjectManager(storage=storage)
        project_id, private, _ = await manager.create_project("GH project")
        assert (await manager.validate_token(private))[0] == project_id
        await manager.set_gv(project_id, "score", "9001")
        assert await manager.get_gv(project_id, "score") == "9001"
        assert await manager.list_gvs(project_id) == {"score": "9001"}
        record = await manager.add_file(project_id, "note", str(source), "note.txt", 4)
        assert Path(await manager.download_file(record["id"])).read_bytes() == b"note"
        assert await manager.delete_gv(project_id, "score") is True
        assert await manager.delete_file(project_id, "note") is True

    run(scenario())
    assert "storage1024-data/global_vars.json" in files


def test_api_returns_413_for_backend_cap(fake_api, app_module, client, monkeypatch):
    storage, _, _, _, _ = fake_api
    storage.max_file_bytes = 10
    monkeypatch.setattr(app_module, "manager", ProjectManager(storage=storage))
    created = client.post("/api/projects/create", json={"name": "gh"}).json()
    token = created["tokens"]["private"]
    res = client.post(
        f"/api/projects/{created['project_id']}/upload",
        files={"file": ("big.txt", b"x" * 100)},
        data={"alias": "big"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 413


def test_missing_credentials_raise_on_connect():
    storage = GitHubStorage(token="", repo="")
    with pytest.raises(StorageUnavailable, match="Missing GitHub settings"):
        async def scenario():
            async with storage.session():
                pass
        run(scenario())


def test_factory_prefers_github_when_configured(monkeypatch):
    monkeypatch.delenv("API_ID", raising=False)
    monkeypatch.delenv("API_HASH", raising=False)
    monkeypatch.delenv("TELEGRAM_SESSION", raising=False)
    monkeypatch.delenv("CHANNEL_ID", raising=False)
    monkeypatch.setenv("STORAGE_BACKEND", "auto")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    monkeypatch.setenv("GITHUB_REPO", "o/r")
    assert isinstance(get_storage(), GitHubStorage)
    assert storage_status()["selected_backend"] == "github"
    assert storage_status()["github_configured"] is True
