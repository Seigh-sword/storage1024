"""Project/token/state management for Storage1024.

All state lives in the index returned by the configured storage backend. Every
operation that changes the index is a locked read-modify-write transaction, so
two simultaneous uploads can no longer overwrite each other's data.
"""
from __future__ import annotations

import asyncio
import os
import re
import secrets
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, Tuple

from client import (
    StorageNotFound,
    StorageUnavailable,
    _safe_name,
    get_storage,
)
from config import load_config

load_config()

TOKEN_PRIVATE = "private"
TOKEN_PUBLIC = "public"

MAX_ALIAS_LENGTH = 120


def generate_private_token() -> str:
    # secrets, not random/uuid4[:18]: these strings are the only credential.
    return f"s1024-{secrets.token_urlsafe(24)};qi="


def generate_public_token() -> str:
    return f"s1024-{secrets.token_urlsafe(24)};gg="


def validate_alias(alias: str) -> str:
    alias = str(alias or "").strip()
    if not alias:
        raise ValueError("Alias is required")
    if len(alias) > MAX_ALIAS_LENGTH:
        raise ValueError(f"Alias must be at most {MAX_ALIAS_LENGTH} characters")
    if alias in (".", "..") or re.search(r"[\x00-\x1f/\\]", alias):
        raise ValueError("Alias contains invalid characters")
    return alias


class ProjectManager:
    def __init__(self, storage=None) -> None:
        self.storage = storage or get_storage()
        self.index: Dict[str, Any] = {"projects": {}}
        self._op_lock: Optional[asyncio.Lock] = None
        self._op_loop = None

    def _lock(self) -> asyncio.Lock:
        loop = asyncio.get_running_loop()
        if self._op_lock is None or self._op_loop is not loop:
            self._op_lock = asyncio.Lock()
            self._op_loop = loop
        return self._op_lock

    @asynccontextmanager
    async def _guard(self):
        async with self._lock():
            async with self.storage.session():
                yield

    async def _read(self) -> Dict[str, Any]:
        index = await self.storage.get_index()
        self.index = index
        return index

    async def _write(self, index: Dict[str, Any]) -> None:
        await self.storage.update_index(index)
        self.index = index

    # ------------------------------------------------------------------ auth
    async def validate_token(self, token: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Return (project_id, token_type) or (None, None). Invalid backend = 503."""
        if not token:
            return None, None
        async with self._guard():
            index = await self._read()
        for project_id, project in index.get("projects", {}).items():
            tokens = project.get("tokens") or {}
            if token in (tokens.get("private") or []):
                return project_id, TOKEN_PRIVATE
            if token in (tokens.get("public") or []):
                return project_id, TOKEN_PUBLIC
        return None, None

    # --------------------------------------------------------------- projects
    async def read_index(self) -> Dict[str, Any]:
        async with self._guard():
            return await self._read()

    async def read_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        async with self._guard():
            index = await self._read()
        return index.get("projects", {}).get(project_id)

    async def create_project(self, name: str) -> Tuple[str, str, str]:
        name = str(name or "New Project").strip()[:120] or "New Project"
        async with self._guard():
            index = await self._read()
            projects = index.setdefault("projects", {})
            for _ in range(100):
                project_id = str(secrets.randbelow(9000) + 1000)
                if project_id not in projects:
                    break
            else:  # pragma: no cover - 9000 projects in one channel
                raise StorageUnavailable("No free project id left")
            private_token = generate_private_token()
            public_token = generate_public_token()
            projects[project_id] = {
                "name": name,
                "tokens": {"private": [private_token], "public": [public_token]},
                "files": {},
                "global_vars": {},
            }
            await self._write(index)
        return project_id, private_token, public_token

    async def add_token(self, project_id: str, token_type: str) -> Optional[str]:
        if token_type not in (TOKEN_PRIVATE, TOKEN_PUBLIC):
            raise ValueError("Token type must be 'private' or 'public'")
        async with self._guard():
            index = await self._read()
            project = index.get("projects", {}).get(project_id)
            if not project:
                return None
            new_token = (
                generate_private_token()
                if token_type == TOKEN_PRIVATE
                else generate_public_token()
            )
            project.setdefault("tokens", {}).setdefault(token_type, []).append(new_token)
            await self._write(index)
            return new_token

    async def revoke_token(self, project_id: str, token: str) -> bool:
        async with self._guard():
            index = await self._read()
            tokens = index.get("projects", {}).get(project_id, {}).get("tokens", {})
            for kind in (TOKEN_PRIVATE, TOKEN_PUBLIC):
                bucket = tokens.get(kind) or []
                if token in bucket:
                    if kind == TOKEN_PRIVATE and len(bucket) <= 1:
                        raise ValueError("Cannot revoke the last private token")
                    bucket.remove(token)
                    await self._write(index)
                    return True
        return False

    # ------------------------------------------------------------------ files
    async def add_file(
        self,
        project_id: str,
        alias: str,
        file_path: str,
        filename: str,
        size_bytes: int,
    ) -> Dict[str, Any]:
        alias = validate_alias(alias)
        async with self._guard():
            index = await self._read()
            project = index.get("projects", {}).get(project_id)
            if not project:
                raise StorageNotFound("Project not found")
            caption = (
                f"Project: {project_id} | File: {alias} | "
                f"Size: {size_bytes / (1024 * 1024):.2f}MB"
            )
            file_id = await self.storage.upload_file(file_path, caption=caption)
            record = {
                "id": file_id,
                "name": _safe_name(filename),
                "size": round(size_bytes / (1024 * 1024), 4),
                "bytes": size_bytes,
                "key": secrets.token_urlsafe(18),
            }
            project.setdefault("files", {})[alias] = record
            await self._write(index)
            return record

    @staticmethod
    def _file_record(raw: Any) -> Dict[str, Any]:
        # Old indexes stored a bare Telegram message id. Accept both shapes.
        if isinstance(raw, dict):
            return dict(raw)
        return {"id": raw, "name": "file", "size": 0, "bytes": 0}

    async def get_file(self, project_id: str, alias: str) -> Optional[Dict[str, Any]]:
        async with self._guard():
            index = await self._read()
        project = index.get("projects", {}).get(project_id)
        raw = (project or {}).get("files", {}).get(alias)
        return self._file_record(raw) if raw is not None else None

    async def delete_file(self, project_id: str, alias: str) -> bool:
        async with self._guard():
            index = await self._read()
            files = index.get("projects", {}).get(project_id, {}).get("files", {})
            if alias not in files:
                return False
            record = self._file_record(files.pop(alias))
            await self._write(index)
            try:
                await self.storage.delete_file(record.get("id"))
            except Exception:
                pass  # index is the source of truth; storage cleanup is best effort
            return True

    async def download_file(self, file_id: Any) -> str:
        async with self._guard():
            return await self.storage.download_file(file_id)

    async def verify_share_key(self, project_id: str, alias: str, key: Optional[str]) -> bool:
        if not key:
            return False
        record = await self.get_file(project_id, alias)
        return bool(record and secrets.compare_digest(str(record.get("key", "")), key))

    # ------------------------------------------------------- global variables
    async def set_gv(self, project_id: str, alias: str, value: Any) -> Any:
        alias = validate_alias(alias)
        if value is None:
            raise ValueError("Value is required")
        text = value if isinstance(value, str) else str(value)
        async with self._guard():
            index = await self._read()
            project = index.get("projects", {}).get(project_id)
            if not project:
                raise StorageNotFound("Project not found")
            gvs = project.setdefault("global_vars", {})
            # Edit the existing message instead of leaking a new one per write.
            message_id = await self.storage.store_gv(alias, text, gvs.get(alias))
            gvs[alias] = message_id
            await self._write(index)
            return message_id

    async def get_gv(self, project_id: str, alias: str) -> Optional[str]:
        async with self._guard():
            index = await self._read()
            gvs = index.get("projects", {}).get(project_id, {}).get("global_vars", {})
            if alias not in gvs:
                return None
            return await self.storage.get_gv(gvs[alias])

    async def list_gvs(self, project_id: str) -> Dict[str, Optional[str]]:
        async with self._guard():
            index = await self._read()
            project = index.get("projects", {}).get(project_id)
            if not project:
                raise StorageNotFound("Project not found")
            result = {}
            for alias, message_id in (project.get("global_vars") or {}).items():
                try:
                    result[alias] = await self.storage.get_gv(message_id)
                except Exception:
                    result[alias] = None
            return result

    async def delete_gv(self, project_id: str, alias: str) -> bool:
        async with self._guard():
            index = await self._read()
            gvs = index.get("projects", {}).get(project_id, {}).get("global_vars", {})
            if alias not in gvs:
                return False
            message_id = gvs.pop(alias)
            await self._write(index)
            try:
                await self.storage.delete_gv(message_id)
            except Exception:
                pass
            return True

    async def health(self) -> Dict[str, Any]:
        async with self._guard():
            index = await self._read()
        return {"backend": self.storage.name, "projects": len(index.get("projects", {}))}

    # ------------------------------------------------------------------- CLI
    async def add_file_cli(self, project_id: str, alias: str, file_path: str) -> None:
        if not os.path.isfile(file_path):
            raise FileNotFoundError(file_path)
        record = await self.add_file(
            project_id, alias, file_path, os.path.basename(file_path), os.path.getsize(file_path)
        )
        print(f"Added '{alias}' (id: {record['id']})")


async def _cli() -> None:
    manager = ProjectManager()
    if len(sys.argv) < 2:
        print("Usage: python manager.py <create|add-file|add-gv|list> [args]")
        return
    cmd = sys.argv[1]
    try:
        if cmd == "create":
            name = sys.argv[2] if len(sys.argv) > 2 else "New Project"
            project_id, priv, pub = await manager.create_project(name)
            print(f"Project '{name}' created!\nID: {project_id}")
            print(f"Private Token: {priv}\nPublic Token: {pub}")
        elif cmd == "add-file":
            await manager.add_file_cli(sys.argv[2], sys.argv[3], sys.argv[4])
        elif cmd == "add-gv":
            await manager.set_gv(sys.argv[2], sys.argv[3], sys.argv[4])
            print("Global variable saved.")
        elif cmd == "list":
            print(await manager.read_index())
        else:
            print(f"Unknown command: {cmd}")
    except (StorageUnavailable, StorageNotFound, ValueError, IndexError) as exc:
        print(f"Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(_cli())
