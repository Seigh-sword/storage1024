"""Synchronous Python client for the Storage1024 API."""
from __future__ import annotations

import os
from typing import Any, Dict, Optional
from urllib.parse import quote

import requests


class Storage1024:
    DEFAULT_API = "https://storage1024.onrender.com/api"

    def __init__(self, api_base: Optional[str] = None, timeout: float = 30.0):
        self.api_base = (api_base or os.getenv("STORAGE1024_API") or self.DEFAULT_API).rstrip("/")
        self.timeout = timeout
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.session = requests.Session()

    # ------------------------------------------------------------------ setup
    def set_api_base(self, api_base: str) -> "Storage1024":
        self.api_base = api_base.rstrip("/")
        return self

    def set_token(self, token: str) -> "Storage1024":
        self.token = token
        return self

    def set_userid(self, user_id: str) -> "Storage1024":
        self.user_id = str(user_id)
        return self

    def set_userID(self, user_id: str) -> "Storage1024":
        """Alias for users coming from the JS SDK."""
        return self.set_userid(user_id)

    # --------------------------------------------------------------- internals
    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        if not self.token:
            raise ValueError("Token not set. Use set_token()")
        headers = {"Authorization": f"Bearer {self.token}"}
        if extra:
            headers.update(extra)
        return headers

    def _project_url(self, suffix: str = "") -> str:
        if not self.user_id:
            raise ValueError("Project ID not set. Use set_userid()")
        return f"{self.api_base}/projects/{quote(str(self.user_id), safe='')}{suffix}"

    @staticmethod
    def _check(res: requests.Response) -> requests.Response:
        if not res.ok:
            try:
                detail = res.json().get("detail", res.text)
            except ValueError:
                detail = res.text
            raise requests.HTTPError(f"Storage1024 {res.status_code}: {detail}", response=res)
        return res

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", self.timeout)
        return self._check(self.session.request(method, url, **kwargs))

    # --------------------------------------------------------------- variables
    def get_gv(self, name: str) -> Optional[str]:
        url = self._project_url(f"/gv/{quote(name, safe='')}")
        res = self._request("GET", url, headers=self._headers())
        return res.json().get("value")

    def add_gv(self, name: str, value: Any) -> Dict[str, Any]:
        url = self._project_url("/gv")
        res = self._request(
            "POST", url,
            headers=self._headers({"Content-Type": "application/json"}),
            json={"alias": name, "value": value},
        )
        return res.json()

    def gv_json(self) -> Dict[str, Any]:
        res = self._request("GET", self._project_url("/gv"), headers=self._headers())
        return res.json()

    def delete_gv(self, name: str) -> Dict[str, Any]:
        url = self._project_url(f"/gv/{quote(name, safe='')}")
        return self._request("DELETE", url, headers=self._headers()).json()

    # -------------------------------------------------------------------- files
    def upload_file(self, alias: str, file_path: str) -> Dict[str, Any]:
        with open(file_path, "rb") as handle:
            files = {"file": (os.path.basename(file_path), handle)}
            res = self._request(
                "POST", self._project_url("/upload"),
                headers=self._headers(), files=files, data={"alias": alias},
            )
        return res.json()

    def list_files(self) -> Dict[str, Any]:
        res = self._request("GET", self._project_url("/files"), headers=self._headers())
        return res.json().get("files", {})

    def get_file(self, alias: str) -> bytes:
        url = self._project_url(f"/files/{quote(alias, safe='')}")
        return self._request("GET", url, headers=self._headers()).content

    def save_file(self, alias: str, output_path: str) -> str:
        data = self.get_file(alias)
        with open(output_path, "wb") as handle:
            handle.write(data)
        return output_path

    def delete_file(self, alias: str) -> Dict[str, Any]:
        url = self._project_url(f"/files/{quote(alias, safe='')}")
        return self._request("DELETE", url, headers=self._headers()).json()

    # ----------------------------------------------------------------- projects
    def create_project(self, name: str) -> Dict[str, Any]:
        res = self._request(
            "POST", f"{self.api_base}/projects/create", json={"name": name},
            headers={"Content-Type": "application/json"},
        )
        return res.json()

    def create_token(self, name: str, token_type: str = "public") -> str:
        if token_type not in ("private", "public"):
            raise ValueError("token_type must be 'private' or 'public'")
        res = self._request(
            "POST", self._project_url("/tokens"),
            headers=self._headers({"Content-Type": "application/json"}),
            json={"name": name, "type": token_type},
        )
        return res.json().get("token")

    def revoke_token(self, token_to_revoke: str) -> Dict[str, Any]:
        res = self._request(
            "POST", self._project_url("/tokens/revoke"),
            headers=self._headers({"Content-Type": "application/json"}),
            json={"token": token_to_revoke},
        )
        return res.json()

    def health(self) -> Dict[str, Any]:
        return self.session.get(f"{self.api_base}/health", timeout=self.timeout).json()
