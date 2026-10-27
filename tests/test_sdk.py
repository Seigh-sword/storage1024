"""Client-library smoke tests that do not need a live network."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "libraries" / "python"))  # test the repo source, not an installed wheel


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
        self.ok = 200 <= status < 300
        self.text = json.dumps(payload)
        self.content = json.dumps(payload).encode()

    def json(self):
        return self._payload


def test_python_sdk_endpoints_and_json_escaping():
    from storage1024 import Storage1024

    sdk = Storage1024("http://localhost:8000/api")
    sdk.set_userid("1234")
    sdk.set_token("tok;qi=")

    calls = []

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if url.endswith("/gv/score"):
            return FakeResponse({"alias": "score", "value": "9001"})
        if url.endswith("/files"):
            return FakeResponse({"files": {}})
        return FakeResponse({"status": "success"})

    sdk.session.request = fake_request
    assert sdk.get_gv("score") == "9001"
    sdk.add_gv("weird name", 'a "quote" \\ newline\n')
    sdk.delete_gv("score")
    sdk.list_files()

    assert calls[0][0] == "GET"
    assert calls[0][1].endswith("/gv/score")
    assert calls[1][2]["json"] == {
        "alias": "weird name", "value": 'a "quote" \\ newline\n'
    }
    assert "weird%20name" not in calls[1][1]
    assert calls[2][0] == "DELETE"
    assert calls[0][2]["headers"]["Authorization"] == "Bearer tok;qi="


def test_python_sdk_raises_with_server_detail():
    import requests
    from storage1024 import Storage1024

    sdk = Storage1024()
    sdk.set_userid("1")
    sdk.set_token("t")
    sdk.session.request = lambda *a, **k: FakeResponse({"detail": "nope"}, status=403)
    with pytest.raises(requests.HTTPError, match="403: nope"):
        sdk.gv_json()


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_javascript_files_parse():
    files = [
        "app.js",
        "docs/script.js",
        "libraries/cdn.js",
        "libraries/s1024/s1024.js",
        "web/cdn.js",
        "web/s1024-client.js",
    ]
    for name in files:
        result = subprocess.run(
            ["node", "--check", str(ROOT / name)], capture_output=True, text=True
        )
        assert result.returncode == 0, f"{name}: {result.stderr}"


def test_cdn_and_npm_sdk_are_identical():
    assert (ROOT / "libraries/cdn.js").read_text() == (ROOT / "libraries/s1024/s1024.js").read_text()


def test_sh_syntax():
    result = subprocess.run(
        ["bash", "-n", str(ROOT / "libraries/bash/storage1024.sh")],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
