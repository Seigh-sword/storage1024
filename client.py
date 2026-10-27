"""Storage backends for Storage1024.

Three interchangeable backends implement the same small interface:

``TelegramStorage``
    The original backend. The index lives in a Telegram channel as a JSON
    document (pinned, or found through a searchable locator message). The old
    fixed-message-id / plain-text index is still readable for migration.

``GitHubStorage``
    A free, durable backend that keeps the index, files and variables in a
    GitHub repository. Ideal for free hosts with ephemeral disks.

``LocalStorage``
    A filesystem backend used when no remote credentials are available, and
    for local development/tests. Index, files and variables live in DATA_DIR.

Importing this module must never raise: a dead/missing backend is reported by
``/api/health`` and produces HTTP 503 on the endpoints that need it. Silently
returning an empty index (the old behaviour) is what used to wipe projects.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import shutil
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from config import BASE_DIR, data_dir, load_config, telegram_credentials

LEGACY_INDEX_HEADER = "——\nIndex\n——\n"
INDEX_MARKER = "S1024-INDEX-V2"
INDEX_FILENAME = "storage1024-index.json"
GV_SEPARATOR = "]: "

load_config()


class StorageError(Exception):
    """Base class for backend failures."""


class StorageUnavailable(StorageError):
    """The backend could not be reached or its data could not be trusted."""


class StorageNotFound(StorageError):
    """A requested object does not exist in the backend."""


def _safe_name(name: str) -> str:
    """Strip path separators / control chars from a user supplied filename."""
    name = Path(str(name or "file")).name
    name = re.sub(r"[\x00-\x1f/\\]", "_", name)
    return (name or "file")[:180]


def _as_index(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict) or not isinstance(data.get("projects"), dict):
        raise StorageUnavailable("Index is malformed (missing 'projects' object)")
    return data


class BaseStorage:
    """Connection bookkeeping shared by both backends.

    ``session()`` is re-entrant and reference counted, so a request-level
    dependency can hold a session open while nested manager calls reuse it.
    """

    name = "base"
    configured = True

    def __init__(self) -> None:
        self._users = 0
        self._conn_lock: Optional[asyncio.Lock] = None
        self._conn_loop = None
        self.last_error: Optional[str] = None

    def _lock(self) -> asyncio.Lock:
        # asyncio.Lock binds to a loop on first use. Tests and uvicorn may use
        # different loops in the same process, so recreate it per loop.
        loop = asyncio.get_running_loop()
        if self._conn_lock is None or self._conn_loop is not loop:
            self._conn_lock = asyncio.Lock()
            self._conn_loop = loop
            self._users = 0
        return self._conn_lock

    async def connect(self) -> None:  # pragma: no cover - overridden
        raise NotImplementedError

    async def disconnect(self) -> None:  # pragma: no cover - overridden
        raise NotImplementedError

    @asynccontextmanager
    async def session(self):
        async with self._lock():
            if self._users == 0:
                await self.connect()
            self._users += 1
        try:
            yield self
        finally:
            async with self._lock():
                self._users -= 1
                if self._users == 0:
                    await self.disconnect()

    async def health(self) -> Dict[str, Any]:
        """Cheap, non-destructive probe used by the health endpoint."""
        async with self.session():
            index = await self.get_index()
        return {"backend": self.name, "projects": len(index.get("projects", {}))}


class LocalStorage(BaseStorage):
    """Filesystem backend. Works with zero configuration."""

    name = "local"

    def __init__(self, root: Optional[str | Path] = None) -> None:
        super().__init__()
        self.root = Path(root).resolve() if root else data_dir()
        self.files_dir = self.root / "files"
        self.tmp_dir = self.root / "tmp"
        self.index_path = self.root / "index.json"
        self.gv_path = self.root / "global_vars.json"

    @property
    def configuration_error(self) -> Optional[str]:
        return None

    async def connect(self) -> None:
        self.files_dir.mkdir(parents=True, exist_ok=True)
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    async def disconnect(self) -> None:
        return None

    async def get_index(self) -> Dict[str, Any]:
        try:
            return _as_index(json.loads(self.index_path.read_text(encoding="utf-8")))
        except FileNotFoundError:
            return {"projects": {}}
        except (json.JSONDecodeError, UnicodeDecodeError, StorageUnavailable) as exc:
            raise StorageUnavailable(
                f"Index file {self.index_path} is unreadable: {exc}"
            ) from exc

    async def update_index(self, data: Dict[str, Any]) -> None:
        _as_index(data)
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.index_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, self.index_path)

    def _file_path(self, file_id: Any) -> Path:
        fid = str(file_id)
        if not re.fullmatch(r"[0-9a-f]{32}", fid):
            raise StorageNotFound(f"Unknown file id: {fid!r}")
        matches = sorted(self.files_dir.glob(f"{fid}-*"))
        if not matches:
            raise StorageNotFound(f"File {fid} is missing from disk")
        return matches[0]

    async def upload_file(self, file_path: str, caption: Optional[str] = None) -> str:
        src = Path(file_path)
        if not src.is_file():
            raise StorageNotFound(f"File not found: {file_path}")
        file_id = uuid.uuid4().hex
        dest = self.files_dir / f"{file_id}-{_safe_name(src.name)}"
        await asyncio.to_thread(shutil.copyfile, src, dest)
        return file_id

    async def download_file(self, file_id: Any, output_path: Optional[str] = None) -> str:
        src = self._file_path(file_id)
        if output_path:
            dest = Path(output_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(shutil.copyfile, src, dest)
            return str(dest)
        return str(src)

    async def delete_file(self, file_id: Any) -> bool:
        try:
            path = self._file_path(file_id)
        except StorageNotFound:
            return False
        path.unlink(missing_ok=True)
        return True

    def _read_gvs(self) -> Dict[str, str]:
        try:
            data = json.loads(self.gv_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except FileNotFoundError:
            return {}
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise StorageUnavailable(f"Global variable store is unreadable: {exc}") from exc

    def _write_gvs(self, data: Dict[str, str]) -> None:
        tmp = self.gv_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, self.gv_path)

    async def store_gv(self, key: str, value: Any, message_id: Any = None) -> str:
        gvs = self._read_gvs()
        mid = str(message_id) if message_id else uuid.uuid4().hex
        gvs[mid] = str(value)
        self._write_gvs(gvs)
        return mid

    async def get_gv(self, message_id: Any) -> Optional[str]:
        return self._read_gvs().get(str(message_id))

    async def delete_gv(self, message_id: Any) -> bool:
        gvs = self._read_gvs()
        if str(message_id) not in gvs:
            return False
        del gvs[str(message_id)]
        self._write_gvs(gvs)
        return True

    async def list_files(self, limit: int = 20) -> List[Dict[str, Any]]:
        entries = []
        for path in sorted(self.files_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
            entries.append({
                "id": path.name.split("-", 1)[0],
                "name": path.name.split("-", 1)[-1],
                "size": path.stat().st_size,
                "date": path.stat().st_mtime,
            })
        return entries


class TelegramStorage(BaseStorage):
    """Telegram channel backend (Telethon). No network calls before connect()."""

    name = "telegram"

    def __init__(self, credentials: Optional[dict] = None) -> None:
        super().__init__()
        creds = credentials or telegram_credentials()
        self.api_id = creds.get("api_id")
        self.api_hash = creds.get("api_hash")
        self.session_str = creds.get("session")
        self.channel_id = creds.get("channel_id")
        self.index_message_id = creds.get("index_message_id") or 4
        self.client = None
        self._telethon = None

    @property
    def configuration_error(self) -> Optional[str]:
        missing = []
        if not self.api_id:
            missing.append("API_ID")
        if not self.api_hash:
            missing.append("API_HASH")
        if not self.session_str:
            missing.append("TELEGRAM_SESSION")
        if self.channel_id is None:
            missing.append("CHANNEL_ID")
        return "Missing Telegram settings: " + ", ".join(missing) if missing else None

    @property
    def configured(self) -> bool:
        return self.configuration_error is None

    def _import_telethon(self):
        if self._telethon is None:
            try:
                from telethon import TelegramClient
                from telethon.sessions import StringSession
                from telethon.tl import types
            except ImportError as exc:  # pragma: no cover - dependency is declared
                raise StorageUnavailable(
                    "telethon is not installed (pip install -r requirements.txt)"
                ) from exc
            self._telethon = (TelegramClient, StringSession, types)
        return self._telethon

    async def connect(self) -> None:
        error = self.configuration_error
        if error:
            raise StorageUnavailable(error)
        TelegramClient, StringSession, _ = self._import_telethon()
        if self.client is None:
            self.client = TelegramClient(
                StringSession(self.session_str), self.api_id, self.api_hash
            )
        if not self.client.is_connected():
            await self.client.connect()
        if not await self.client.is_user_authorized():
            await self.client.disconnect()
            raise StorageUnavailable(
                "The Telegram session is not authorized. Run generate_session.py again."
            )

    async def disconnect(self) -> None:
        if self.client is not None and self.client.is_connected():
            await self.client.disconnect()

    async def _client(self):
        if self.client is None or not self.client.is_connected():
            await self.connect()
        return self.client

    async def _parse_index_message(self, msg) -> Optional[Dict[str, Any]]:
        if not msg:
            return None
        text = msg.text or ""
        if INDEX_MARKER in text and getattr(msg, "document", None):
            raw = await self.client.download_media(msg, file=bytes)
            if not raw:
                raise StorageUnavailable("Index message has no readable attachment")
            return _as_index(json.loads(raw.decode("utf-8")))
        if INDEX_MARKER in text:
            body = text.split(INDEX_MARKER, 1)[1].strip()
            if not body or body.startswith("LOCATOR"):
                return None
            return _as_index(json.loads(body))
        if text.startswith(LEGACY_INDEX_HEADER):
            return _as_index(json.loads(text.split(LEGACY_INDEX_HEADER, 1)[1]))
        return None

    async def _find_index_messages(self) -> List[Any]:
        """Return marker messages, newest first (pinned first, then search)."""
        _, _, types = self._import_telethon()
        found, seen, failures = [], set(), []
        try:
            pinned = await self.client.get_messages(
                self.channel_id, filter=types.InputMessagesFilterPinned(), limit=20
            )
            for msg in pinned or []:
                if msg and msg.id not in seen and INDEX_MARKER in (msg.text or ""):
                    seen.add(msg.id)
                    found.append(msg)
        except Exception as exc:  # pinned messages may be unavailable
            failures.append(f"pinned index lookup: {exc}")
        try:
            async for msg in self.client.iter_messages(
                self.channel_id, search=INDEX_MARKER, limit=20
            ):
                if msg and msg.id not in seen and INDEX_MARKER in (msg.text or ""):
                    seen.add(msg.id)
                    found.append(msg)
        except Exception as exc:
            failures.append(f"index search: {exc}")
        self.last_error = "; ".join(failures) or None
        self._lookup_failed = bool(failures)
        return found

    async def get_index(self) -> Dict[str, Any]:
        await self._client()
        self._lookup_failed = False
        try:
            for msg in await self._find_index_messages():
                text = msg.text or ""
                locator = re.search(rf"{INDEX_MARKER}\s+LOCATOR\s+(\d+)", text)
                if locator:
                    target = await self.client.get_messages(
                        self.channel_id, ids=int(locator.group(1))
                    )
                    data = await self._parse_index_message(target)
                else:
                    data = await self._parse_index_message(msg)
                if data is not None:
                    return data

            # Migration path: the original deployment edited message id 4.
            legacy = await self.client.get_messages(
                self.channel_id, ids=self.index_message_id
            )
            data = await self._parse_index_message(legacy)
            if data is not None:
                return data
        except StorageUnavailable:
            raise
        except Exception as exc:
            raise StorageUnavailable(f"Could not read the Telegram index: {exc}") from exc
        if getattr(self, "_lookup_failed", False):
            # An empty index here means "we could not look", not "no data".
            raise StorageUnavailable(
                f"Could not verify the Telegram index: {self.last_error}"
            )
        return {"projects": {}}

    async def update_index(self, data: Dict[str, Any]) -> None:
        """Write the index as a JSON document; never edit a text message again.

        Telegram limits text messages to 4096 characters, which the old
        ``edit_message(..., json.dumps(index, indent=2))`` hit very quickly.
        Documents have no such limit. The message is pinned so it can be found
        after thousands of uploads; when pinning is not allowed, a small
        searchable locator message points at the document instead.
        """
        await self._client()
        _as_index(data)
        _, _, types = self._import_telethon()
        old_messages = await self._find_index_messages()
        payload = json.dumps(data, separators=(",", ":")).encode("utf-8")

        try:
            message = await self.client.send_file(
                self.channel_id,
                payload,
                caption=INDEX_MARKER,
                mime_type="application/json",
                force_document=True,
                attributes=[types.DocumentAttributeFilename(INDEX_FILENAME)],
            )
        except Exception as exc:
            raise StorageUnavailable(f"Could not upload the index: {exc}") from exc

        pinned = False
        try:
            await self.client.pin_message(self.channel_id, message.id)
            pinned = True
        except Exception as exc:
            self.last_error = f"pin_message failed (using locator): {exc}"
        if not pinned:
            try:
                await self.client.send_message(
                    self.channel_id, f"{INDEX_MARKER} LOCATOR {message.id}"
                )
            except Exception as exc:
                # Without a way to find the new index, a successful write would
                # be a lie. Fail loudly instead of losing data.
                raise StorageUnavailable(
                    f"Index was uploaded but is not discoverable: {exc}"
                ) from exc

        # Housekeeping only - never let it fail an otherwise successful write.
        for old in old_messages:
            if old.id == message.id:
                continue
            try:
                await self.client.delete_messages(self.channel_id, old.id)
            except Exception:
                pass

    async def upload_file(self, file_path: str, caption: Optional[str] = None) -> int:
        client = await self._client()
        if not Path(file_path).is_file():
            raise StorageNotFound(f"File not found: {file_path}")
        message = await client.send_file(self.channel_id, file_path, caption=caption)
        return message.id

    async def download_file(self, file_id: Any, output_path: Optional[str] = None) -> str:
        client = await self._client()
        message = await client.get_messages(self.channel_id, ids=int(file_id))
        if not message or not message.media:
            raise StorageNotFound(f"Message {file_id} has no file attached")
        # A private directory per download avoids two concurrent downloads of
        # the same message fighting over one filename.
        target = output_path or str(self._download_dir())
        path = await client.download_media(message, file=target)
        if not path:
            raise StorageUnavailable(f"Telegram returned no data for message {file_id}")
        return str(path)

    def _download_dir(self) -> Path:
        root = data_dir() / "tmp"
        root.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(prefix="download-", dir=root))

    async def delete_file(self, file_id: Any) -> bool:
        client = await self._client()
        try:
            await client.delete_messages(self.channel_id, int(file_id))
            return True
        except Exception:
            return False

    async def store_gv(self, key: str, value: Any, message_id: Any = None) -> int:
        client = await self._client()
        text = f"GV[{key}]: {value}"
        if message_id:
            try:
                await client.edit_message(self.channel_id, int(message_id), text)
                return int(message_id)
            except Exception:
                pass  # message may be gone; create a fresh one
        message = await client.send_message(self.channel_id, text)
        return message.id

    async def get_gv(self, message_id: Any) -> Optional[str]:
        client = await self._client()
        try:
            message = await client.get_messages(self.channel_id, ids=int(message_id))
        except (TypeError, ValueError):
            return None
        if not message or not message.text:
            return None
        text = message.text
        if text.startswith("GV[") and GV_SEPARATOR in text:
            return text.split(GV_SEPARATOR, 1)[1]
        return text

    async def delete_gv(self, message_id: Any) -> bool:
        client = await self._client()
        try:
            await client.delete_messages(self.channel_id, int(message_id))
            return True
        except Exception:
            return False

    async def list_files(self, limit: int = 20) -> List[Dict[str, Any]]:
        client = await self._client()
        _, _, types = self._import_telethon()
        files = []
        async for message in client.iter_messages(self.channel_id, limit=limit):
            media = getattr(message, "media", None)
            if not isinstance(media, types.MessageMediaDocument):
                continue
            name = "Unknown"
            for attr in media.document.attributes:
                if hasattr(attr, "file_name"):
                    name = attr.file_name
                    break
            files.append({
                "id": message.id,
                "name": name,
                "date": message.date,
                "size": media.document.size,
            })
        return files



class GitHubStorage(BaseStorage):
    """Durable storage in a GitHub repository (free, no card, no server disk).

    A private repo + a fine-grained personal access token survive redeploys on
    ephemeral free hosts. The GitHub Contents API caps files at 100 MB; this
    backend enforces a safer configurable cap (``GITHUB_MAX_FILE_MB``, 20 by
    default) and reports HTTP 413 above it.
    """

    name = "github"

    def __init__(self, token=None, repo=None, branch=None, path=None,
                 max_file_mb=None, client=None) -> None:
        super().__init__()
        load_config()
        self.token = (token or os.getenv("GITHUB_TOKEN", "")).strip() or None
        self.repo = (repo or os.getenv("GITHUB_REPO", "")).strip().strip("/") or None
        self.branch = (branch or os.getenv("GITHUB_BRANCH", "main")).strip() or "main"
        self.root = (path or os.getenv("GITHUB_PATH", "storage1024-data")).strip("/")
        raw_limit = max_file_mb if max_file_mb is not None else os.getenv("GITHUB_MAX_FILE_MB", "20")
        self.max_file_bytes = int(float(raw_limit) * 1024 * 1024)
        self._http = client
        self._owns_http = client is None

    @property
    def configuration_error(self) -> Optional[str]:
        missing = []
        if not self.token:
            missing.append("GITHUB_TOKEN")
        if not self.repo or "/" not in self.repo:
            missing.append("GITHUB_REPO (owner/repo)")
        return "Missing GitHub settings: " + ", ".join(missing) if missing else None

    @property
    def configured(self) -> bool:
        return self.configuration_error is None

    async def connect(self) -> None:
        error = self.configuration_error
        if error:
            raise StorageUnavailable(error)
        if self._http is None:
            try:
                import httpx
            except ImportError as exc:  # pragma: no cover - declared dependency
                raise StorageUnavailable(
                    "httpx is not installed (pip install -r requirements.txt)"
                ) from exc
            self._http = httpx.AsyncClient(
                base_url="https://api.github.com",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "User-Agent": "storage1024",
                },
                timeout=httpx.Timeout(60.0, connect=10.0),
            )
            self._owns_http = True

    async def disconnect(self) -> None:
        if self._owns_http and self._http is not None:
            await self._http.aclose()
            self._http = None

    async def _http_client(self):
        if self._http is None:
            await self.connect()
        return self._http

    def _url(self, path: str) -> str:
        full = f"{self.root}/{path}" if self.root else path
        return f"/repos/{self.repo}/contents/{quote(full, safe='/')}"

    @staticmethod
    def _decode(encoded: str) -> bytes:
        try:
            return base64.b64decode("".join(encoded.split()))
        except Exception as exc:
            raise StorageUnavailable(f"GitHub returned unreadable content: {exc}") from exc

    async def _request(self, method: str, url: str, **kwargs):
        client = await self._http_client()
        try:
            response = await client.request(method, url, **kwargs)
        except Exception as exc:
            raise StorageUnavailable(f"GitHub API request failed: {exc}") from exc
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise StorageUnavailable(
                f"GitHub API {method} {url} -> {response.status_code}: "
                f"{response.text[:300]}"
            )
        return response.json() if response.content else {}

    async def _read(self, path: str):
        data = await self._request("GET", self._url(path), params={"ref": self.branch})
        if data is None:
            return None, None
        if isinstance(data, list):
            raise StorageUnavailable(f"Expected a file at {path}, found a directory")
        if data.get("encoding") == "base64" and data.get("content"):
            return self._decode(data["content"]), data.get("sha")
        # Files above 1 MB come back with encoding "none": read the git blob.
        blob = await self._request("GET", f"/repos/{self.repo}/git/blobs/{data.get('sha')}")
        if not blob or not blob.get("content"):
            raise StorageUnavailable(f"GitHub did not return the contents of {path}")
        return self._decode(blob["content"]), data.get("sha")

    async def _write(self, path: str, content: bytes, message: str) -> None:
        client = await self._http_client()
        url = self._url(path)
        payload = {
            "message": message,
            "content": base64.b64encode(content).decode("ascii"),
            "branch": self.branch,
        }
        for attempt in range(3):
            existing = await self._request("GET", url, params={"ref": self.branch})
            if isinstance(existing, dict) and existing.get("sha"):
                payload["sha"] = existing["sha"]
            else:
                payload.pop("sha", None)
            try:
                response = await client.put(url, json=payload)
            except Exception as exc:
                raise StorageUnavailable(f"GitHub API write failed: {exc}") from exc
            if response.status_code in (200, 201):
                return
            if response.status_code == 409 and attempt < 2:
                await asyncio.sleep(0.2 * (attempt + 1))  # stale sha, retry
                continue
            raise StorageUnavailable(
                f"GitHub could not write {path}: {response.status_code} "
                f"{response.text[:300]}"
            )
        raise StorageUnavailable(f"GitHub could not write {path} after 3 attempts")

    async def _remove(self, path: str) -> bool:
        existing = await self._request("GET", self._url(path), params={"ref": self.branch})
        if not isinstance(existing, dict) or not existing.get("sha"):
            return False
        client = await self._http_client()
        try:
            response = await client.request(
                "DELETE", self._url(path),
                json={"message": f"chore: delete {path}", "sha": existing["sha"],
                      "branch": self.branch},
            )
        except Exception:
            return False
        return response.status_code in (200, 204)

    async def _list(self, path: str) -> List[Dict[str, Any]]:
        data = await self._request("GET", self._url(path), params={"ref": self.branch})
        return data if isinstance(data, list) else []

    # ------------------------------------------------------------------ index
    async def get_index(self) -> Dict[str, Any]:
        raw, _ = await self._read("index.json")
        if raw is None:
            return {"projects": {}}
        try:
            return _as_index(json.loads(raw.decode("utf-8")))
        except (ValueError, UnicodeDecodeError, StorageUnavailable) as exc:
            raise StorageUnavailable(f"GitHub index is unreadable: {exc}") from exc

    async def update_index(self, data: Dict[str, Any]) -> None:
        _as_index(data)
        await self._write(
            "index.json",
            json.dumps(data, separators=(",", ":")).encode("utf-8"),
            "chore: update Storage1024 index",
        )

    # ------------------------------------------------------------------ files
    async def upload_file(self, file_path: str, caption: Optional[str] = None) -> str:
        source = Path(file_path)
        if not source.is_file():
            raise StorageNotFound(f"File not found: {file_path}")
        size = source.stat().st_size
        if size > self.max_file_bytes:
            raise StorageUnavailable(
                f"File exceeds the GitHub backend limit of "
                f"{self.max_file_bytes / (1024 * 1024):g}MB"
            )
        content = await asyncio.to_thread(source.read_bytes)
        file_id = uuid.uuid4().hex
        name = _safe_name(source.name)
        await self._write(f"files/{file_id}-{name}", content, f"chore: upload {name}")
        return file_id

    async def _file_path(self, file_id: Any) -> Optional[str]:
        fid = str(file_id)
        if not re.fullmatch(r"[0-9a-f]{32}", fid):
            raise StorageNotFound(f"Unknown file id: {fid!r}")
        for entry in await self._list("files"):
            if entry.get("name", "").startswith(fid + "-"):
                return "files/" + entry["name"]
        return None

    def _temp_dir(self) -> Path:
        root = data_dir() / "tmp"
        root.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(prefix="download-", dir=root))

    async def download_file(self, file_id: Any, output_path: Optional[str] = None) -> str:
        path = await self._file_path(file_id)
        if not path:
            raise StorageNotFound(f"File {file_id} is missing from GitHub")
        content, _ = await self._read(path)
        if content is None:
            raise StorageNotFound(f"File {file_id} is missing from GitHub")
        if output_path:
            dest = Path(output_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(dest.write_bytes, content)
            return str(dest)
        dest = self._temp_dir() / path.rsplit("/", 1)[-1].split("-", 1)[-1]
        await asyncio.to_thread(dest.write_bytes, content)
        return str(dest)

    async def delete_file(self, file_id: Any) -> bool:
        path = await self._file_path(file_id)
        return await self._remove(path) if path else False

    async def list_files(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [
            {
                "id": entry["name"].split("-", 1)[0],
                "name": entry["name"].split("-", 1)[-1],
                "size": entry.get("size", 0),
                "date": None,
            }
            for entry in (await self._list("files"))[:limit]
        ]

    # ------------------------------------------------------- global variables
    async def _gvs(self) -> Dict[str, str]:
        raw, _ = await self._read("global_vars.json")
        if raw is None:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
            return data if isinstance(data, dict) else {}
        except (ValueError, UnicodeDecodeError) as exc:
            raise StorageUnavailable(f"GitHub variable store is unreadable: {exc}") from exc

    async def _save_gvs(self, data: Dict[str, str]) -> None:
        await self._write(
            "global_vars.json", json.dumps(data).encode("utf-8"),
            "chore: update Storage1024 variables",
        )

    async def store_gv(self, key: str, value: Any, message_id: Any = None) -> str:
        gvs = await self._gvs()
        mid = str(message_id) if message_id else uuid.uuid4().hex
        gvs[mid] = str(value)
        await self._save_gvs(gvs)
        return mid

    async def get_gv(self, message_id: Any) -> Optional[str]:
        return (await self._gvs()).get(str(message_id))

    async def delete_gv(self, message_id: Any) -> bool:
        gvs = await self._gvs()
        if str(message_id) not in gvs:
            return False
        del gvs[str(message_id)]
        await self._save_gvs(gvs)
        return True

def get_storage():
    """Pick a backend without ever touching the network or raising."""
    load_config()
    mode = os.getenv("STORAGE_BACKEND", "auto").strip().lower()
    telegram = TelegramStorage()
    github = GitHubStorage()
    if mode == "local":
        return LocalStorage()
    if mode == "github":
        return github
    if mode == "telegram":
        return telegram
    if mode != "auto":
        raise StorageUnavailable(
            f"Unknown STORAGE_BACKEND={mode!r} "
            "(expected auto, telegram, github or local)"
        )
    if telegram.configured:
        return telegram
    if github.configured:
        return github
    return LocalStorage()


def storage_status() -> Dict[str, Any]:
    """Describe configuration without leaking any secret."""
    creds = telegram_credentials()
    mode = os.getenv("STORAGE_BACKEND", "auto").strip().lower()
    telegram_ready = all(
        creds.get(k) not in (None, "") for k in ("api_id", "api_hash", "session", "channel_id")
    )
    github_ready = bool(
        os.getenv("GITHUB_TOKEN", "").strip()
        and "/" in os.getenv("GITHUB_REPO", "")
    )
    if mode in ("local", "github", "telegram"):
        selected = mode
    elif telegram_ready:
        selected = "telegram"
    elif github_ready:
        selected = "github"
    else:
        selected = "local"
    return {
        "configured_mode": mode,
        "selected_backend": selected,
        "telegram_configured": telegram_ready,
        "github_configured": github_ready,
        "data_dir": str(data_dir()),
    }
