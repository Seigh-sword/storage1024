"""End-to-end API tests against the local backend."""
from __future__ import annotations

import json
from pathlib import Path


def test_health_reports_local_backend(client, app_module):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["backend"] == "local"
    assert data["telegram_configured"] is False
    assert data["github_configured"] is False


def test_health_strict_reflects_storage_failure(client, app_module, monkeypatch):
    async def broken():
        raise RuntimeError("backend offline")

    monkeypatch.setattr(app_module.manager, "health", broken)
    assert client.get("/api/health").json()["status"] == "degraded"
    assert client.get("/api/health?strict=true").status_code == 503


def test_static_site_and_sdk_are_served(client):
    for path in ("/", "/app.js", "/style.css", "/assets/icon.svg", "/s1024.js", "/files"):
        assert client.get(path).status_code == 200, path
    assert "s1024" in client.get("/s1024.js").text
    assert "dashboard-grid" in client.get("/style.css").text


def test_docs_pages_and_no_path_traversal(client):
    assert client.get("/docs").status_code == 200
    assert "Developer Docs" in client.get("/docs").text
    assert client.get("/docs/style.css").status_code == 200
    assert "REST API" in client.get("/docs/langs/api.md").text
    assert "Free 24/7 Hosting" in client.get("/docs/langs/hosting.md").text
    assert "Storage1024" in client.get("/docs/story.md").text
    assert client.get("/docs/script.js").status_code == 200
    assert client.get("/docs/marked.umd.js").status_code == 200
    # A missing asset must 404, not return the docs shell.
    assert client.get("/docs/missing.md").status_code == 404
    # Traversal outside docs/ must not expose repository files.
    res = client.get("/docs/../requirements.txt")
    assert res.status_code in (404, 422)
    assert "fastapi" not in res.text


def test_create_project_and_index(client, project, auth):
    project_id, private, public = project
    assert private.endswith(";qi=") and public.endswith(";gg=")
    res = client.get("/api/index", headers=auth)
    assert res.status_code == 200
    data = res.json()
    assert data["projects"][project_id]["name"] == "Test Project"
    assert data["projects"][project_id]["files"] == {}


def test_missing_and_invalid_tokens(client, project):
    assert client.get("/api/index").status_code == 401
    assert client.get("/api/index", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_public_token_scope(client, project):
    project_id, _, public = project
    headers = {"Authorization": f"Bearer {public}"}
    assert client.get("/api/index", headers=headers).status_code == 403
    assert client.post(
        f"/api/projects/{project_id}/tokens", json={"type": "public"}, headers=headers
    ).status_code == 403
    # Public tokens may read/write GVs and upload.
    assert client.get(f"/api/projects/{project_id}/gv", headers=headers).status_code == 200
    assert client.post(
        f"/api/projects/{project_id}/gv", json={"alias": "a", "value": "b"}, headers=headers
    ).status_code == 200


def test_token_cannot_touch_another_project(client, project, auth):
    other = client.post("/api/projects/create", json={"name": "Other"}).json()
    assert client.get(
        f"/api/projects/{other['project_id']}/gv", headers=auth
    ).status_code == 403


def test_gv_crud_and_single_value_endpoint(client, project, auth):
    project_id, _, _ = project
    base = f"/api/projects/{project_id}/gv"
    assert client.get(f"{base}/score", headers=auth).status_code == 404
    assert client.post(base, json={"alias": "score", "value": "9001"}, headers=auth).status_code == 200
    assert client.get(f"{base}/score", headers=auth).json() == {
        "alias": "score", "value": "9001"
    }
    assert client.get(base, headers=auth).json() == {"score": "9001"}
    # Updating edits in place instead of leaking a new message per write.
    assert client.post(base, json={"alias": "score", "value": "over 9000"}, headers=auth).status_code == 200
    index = client.get("/api/index", headers=auth).json()
    gvs = index["projects"][project_id]["global_vars"]
    assert len(gvs) == 1
    assert client.get(f"{base}/score", headers=auth).json()["value"] == "over 9000"
    assert client.delete(f"{base}/score", headers=auth).status_code == 200
    assert client.get(f"{base}/score", headers=auth).status_code == 404
    assert client.delete(f"{base}/score", headers=auth).status_code == 404


def test_gv_accepts_empty_and_numeric_values(client, project, auth):
    base = f"/api/projects/{project[0]}/gv"
    assert client.post(base, json={"alias": "empty", "value": ""}, headers=auth).status_code == 200
    assert client.post(base, json={"alias": "zero", "value": 0}, headers=auth).status_code == 200
    assert client.post(base, json={"alias": "quotes", "value": 'a "quoted" \\ value\n'}, headers=auth).status_code == 200
    values = client.get(base, headers=auth).json()
    assert values["empty"] == ""
    assert values["zero"] == "0"
    assert values["quotes"] == 'a "quoted" \\ value\n'


def test_upload_download_share_and_delete(client, project, auth, tmp_path):
    project_id, _, public = project
    res = client.post(
        f"/api/projects/{project_id}/upload",
        files={"file": ("hello.txt", b"hello storage1024", "text/plain")},
        data={"alias": "greeting"},
        headers=auth,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "success"
    assert data["url"].startswith("http://testserver/f/")
    assert data["file"]["name"] == "hello.txt"
    assert data["file"]["bytes"] == len(b"hello storage1024")

    # Stable share link works without any Authorization header.
    share_path = data["url"].split("testserver", 1)[1]
    shared = client.get(share_path)
    assert shared.status_code == 200
    assert shared.content == b"hello storage1024"
    assert 'filename="hello.txt"' in shared.headers["content-disposition"]
    assert client.get(f"/f/{project_id}/greeting").status_code == 403
    assert client.get(f"/f/{project_id}/greeting?key=wrong").status_code == 403

    # Authenticated download also works, including for public tokens.
    authed = client.get(f"/api/projects/{project_id}/files/greeting", headers=auth)
    assert authed.content == b"hello storage1024"
    assert client.get(
        f"/api/projects/{project_id}/files/greeting",
        headers={"Authorization": f"Bearer {public}"},
    ).status_code == 200

    files = client.get(f"/api/projects/{project_id}/files", headers=auth).json()["files"]
    assert files["greeting"]["url"] == data["url"]

    assert client.delete(f"/api/projects/{project_id}/files/greeting", headers=auth).status_code == 200
    assert client.get(f"/api/projects/{project_id}/files/greeting", headers=auth).status_code == 404
    assert client.get(share_path).status_code == 403


def test_concurrent_uploads_both_land_in_index(client, project, auth):
    project_id, _, _ = project
    import concurrent.futures

    def upload(name):
        return client.post(
            f"/api/projects/{project_id}/upload",
            files={"file": (f"{name}.txt", name.encode())},
            data={"alias": name},
            headers=auth,
        ).status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        statuses = list(pool.map(upload, [f"f{i}" for i in range(5)]))
    assert statuses == [200] * 5
    index = client.get("/api/index", headers=auth).json()
    assert len(index["projects"][project_id]["files"]) == 5


def test_alias_and_filename_validation(client, project, auth):
    project_id, _, _ = project
    bad = client.post(
        f"/api/projects/{project_id}/upload",
        files={"file": ("../../evil.js", b"x")},
        data={"alias": "../escape"},
        headers=auth,
    )
    assert bad.status_code == 400
    gv = client.post(
        f"/api/projects/{project_id}/gv",
        json={"alias": "a/b", "value": "x"},
        headers=auth,
    )
    assert gv.status_code == 400
    # A hostile filename is sanitized, never used as a path.
    ok = client.post(
        f"/api/projects/{project_id}/upload",
        files={"file": ("../../../etc/passwd", b"safe")},
        data={"alias": "safe"},
        headers=auth,
    )
    assert ok.status_code == 200
    assert ok.json()["file"]["name"] == "passwd"


def test_upload_size_limit(client, project, auth, app_module, monkeypatch):
    monkeypatch.setattr(app_module, "MAX_UPLOAD_MB", 0.0001)
    res = client.post(
        f"/api/projects/{project[0]}/upload",
        files={"file": ("big.bin", b"x" * 4096)},
        data={"alias": "big"},
        headers=auth,
    )
    assert res.status_code == 413


def test_tokens_create_revoke_and_last_private_guard(client, project, auth):
    project_id, private, public = project
    created = client.post(
        f"/api/projects/{project_id}/tokens", json={"type": "public"}, headers=auth
    )
    assert created.status_code == 200
    token = created.json()["token"]
    new_headers = {"Authorization": f"Bearer {token}"}
    assert client.get(f"/api/projects/{project_id}/gv", headers=new_headers).status_code == 200

    assert client.post(
        f"/api/projects/{project_id}/tokens", json={"type": "nonsense"}, headers=auth
    ).status_code == 400

    assert client.post(
        f"/api/projects/{project_id}/tokens/revoke", json={"token": private}, headers=auth
    ).status_code == 400  # last private token cannot be revoked
    assert client.post(
        f"/api/projects/{project_id}/tokens/revoke", json={"token": token}, headers=auth
    ).status_code == 200
    assert client.get(f"/api/projects/{project_id}/gv", headers=new_headers).status_code == 401
    assert client.post(
        f"/api/projects/{project_id}/tokens/revoke", json={}, headers=auth
    ).status_code == 400


def test_index_persists_across_manager_instances(client, project, auth, app_module):
    from manager import ProjectManager

    fresh = ProjectManager(storage=app_module.manager.storage)
    import asyncio

    index = asyncio.run(fresh.read_index())
    assert project[0] in index["projects"]


def test_backend_failure_is_503_not_empty_index(client, app_module, monkeypatch, project, auth):
    from client import StorageUnavailable

    async def broken(*_args, **_kwargs):
        raise StorageUnavailable("simulated outage")

    monkeypatch.setattr(app_module.manager.storage, "get_index", broken)
    assert client.get("/api/index", headers=auth).status_code == 503
    # A failed read must never be mistaken for an empty database.
    assert client.get("/api/health").status_code == 200
