"""Test configuration: force the local backend into a throwaway directory."""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import pytest

TEST_DATA = tempfile.mkdtemp(prefix="storage1024-tests-")
os.environ["STORAGE_BACKEND"] = "local"
os.environ["DATA_DIR"] = TEST_DATA
os.environ["THROTTLE_ENABLED"] = "false"
os.environ.pop("API_ID", None)
os.environ.pop("API_HASH", None)
os.environ.pop("TELEGRAM_SESSION", None)
os.environ.pop("CHANNEL_ID", None)
os.environ.pop("CREATE_PROJECT_KEY", None)


@pytest.fixture(scope="session")
def app_module():
    import bridge

    return bridge


@pytest.fixture(scope="session")
def client(app_module):
    from fastapi.testclient import TestClient

    with TestClient(app_module.app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_state(app_module):
    """Each test starts with an empty index and no throttling/rate-limit state."""
    root = Path(app_module.manager.storage.root)
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    app_module._create_attempts.clear()
    yield


@pytest.fixture
def project(client):
    """Create a project and return (id, private_token, public_token)."""
    res = client.post("/api/projects/create", json={"name": "Test Project"})
    assert res.status_code == 200, res.text
    data = res.json()
    return data["project_id"], data["tokens"]["private"], data["tokens"]["public"]


@pytest.fixture
def auth(project):
    return {"Authorization": f"Bearer {project[1]}"}
