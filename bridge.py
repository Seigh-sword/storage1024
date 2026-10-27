"""Storage1024 HTTP API and dashboard server.

Run with ``python bridge.py`` (or ``uvicorn bridge:app``). The process starts
even when Telegram credentials are missing: it falls back to the local backend
and reports the situation on ``/api/health``.
"""
from __future__ import annotations

import asyncio
import mimetypes
import os
import shutil
import tempfile
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask

from client import StorageNotFound, StorageUnavailable, _safe_name, storage_status
from config import BASE_DIR, data_dir, load_config
from manager import (
    TOKEN_PRIVATE,
    TOKEN_PUBLIC,
    ProjectManager,
    validate_alias,
)

load_config()

app = FastAPI(title="Storage1024 API Bridge", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = ProjectManager()
security = HTTPBearer(auto_error=False)  # auto_error=True returns 403, not 401

MAX_UPLOAD_MB = float(os.getenv("MAX_UPLOAD_MB", "1800"))
CREATE_PROJECT_KEY = os.getenv("CREATE_PROJECT_KEY", "").strip()
PUBLIC_SCOPES = {"upload", "get_gv", "download"}
_create_attempts: Dict[str, deque] = defaultdict(deque)


# --------------------------------------------------------------------------- #
# Dependencies & shared helpers
# --------------------------------------------------------------------------- #
async def storage_session():
    """Keep one backend connection open for the whole request (re-entrant)."""
    async with manager.storage.session():
        yield


api = APIRouter(prefix="/api", dependencies=[Depends(storage_session)])


def check_access(token_type: str, required_scope: str) -> None:
    if token_type == TOKEN_PRIVATE:
        return
    if required_scope not in PUBLIC_SCOPES:
        raise HTTPException(status_code=403, detail="Scope restricted for Public tokens")


async def validate_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Tuple[str, str]:
    token = credentials.credentials.strip() if credentials and credentials.credentials else None
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    project_id, token_type = await manager.validate_token(token)
    if not project_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return project_id, token_type


def require_project(auth: Tuple[str, str], project_id: str, scope: str) -> str:
    owner, token_type = auth
    if owner != project_id:
        raise HTTPException(status_code=403, detail="Token does not match project_id")
    check_access(token_type, scope)
    return owner


async def json_body(request: Request) -> Dict[str, Any]:
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON body: {exc}") from exc
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON body must be an object")
    return body


@app.exception_handler(StorageUnavailable)
async def storage_unavailable_handler(_: Request, exc: StorageUnavailable):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(StorageNotFound)
async def storage_not_found_handler(_: Request, exc: StorageNotFound):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


class Throttle:
    """Space out heavy writes without holding a lock during the whole upload."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self.lock = asyncio.Lock()
        self.next_allowed = 0.0

    @staticmethod
    def delay_for_size(size_mb: float) -> Optional[float]:
        if size_mb > MAX_UPLOAD_MB:
            return None
        for limit, delay in (
            (5, 1), (25, 3), (50, 5), (100, 10), (350, 15),
            (750, 20), (950, 25), (1000, 28), (1024, 30),
        ):
            if size_mb < limit:
                return float(delay)
        return 35.0

    async def wait(self, delay: float) -> None:
        if not self.enabled or delay <= 0:
            return
        async with self.lock:
            now = time.monotonic()
            if now < self.next_allowed:
                await asyncio.sleep(self.next_allowed - now)
            self.next_allowed = time.monotonic() + delay


# Only Telegram needs flood protection; local/tests stay instant.
throttle = Throttle(enabled=manager.storage.name == "telegram" and
                    os.getenv("THROTTLE_ENABLED", "true").lower() not in ("0", "false", "no"))


def share_url(request: Request, project_id: str, alias: str, key: str) -> str:
    """Build an absolute link that survives reverse proxies (Render, previews)."""
    from urllib.parse import quote

    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
    scheme = forwarded_proto or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    base = f"{scheme}://{host}".rstrip("/")
    return (
        f"{base}/f/{quote(project_id, safe='')}/{quote(alias, safe='')}"
        f"?key={quote(key, safe='')}"
    )


# --------------------------------------------------------------------------- #
# Health (no auth, never crashes on backend problems)
# --------------------------------------------------------------------------- #
@app.get("/health")
@app.get("/api/health")
async def health(request: Request, strict: bool = False):
    """Liveness probe. Always 200 by default (Render keeps routing to the
    landing page even when Telegram is down); ``?strict=true`` returns 503 so
    external monitors can alert on a broken backend."""
    status: Dict[str, Any] = {"status": "ok", **storage_status()}
    try:
        status.update(await manager.health())
        status.pop("selected_backend", None)
    except Exception as exc:
        status.update({"status": "degraded", "error": str(exc)})
        if strict:
            return JSONResponse(status_code=503, content=status)
    return status


# --------------------------------------------------------------------------- #
# Projects, tokens
# --------------------------------------------------------------------------- #
@api.get("/index")
async def get_index(auth: Tuple[str, str] = Depends(validate_token)):
    project_id, token_type = auth
    require_project(auth, project_id, "admin")
    project = await manager.read_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "success", "projects": {project_id: project}}


@api.post("/projects/create")
async def create_project(request: Request):
    body = await json_body(request)

    # Optional deploy-time guard against drive-by project creation.
    if CREATE_PROJECT_KEY and request.headers.get("x-create-key") != CREATE_PROJECT_KEY:
        raise HTTPException(status_code=403, detail="Invalid create key")

    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    attempts = _create_attempts[ip]
    while attempts and now - attempts[0] > 60:
        attempts.popleft()
    if len(attempts) >= 10:
        raise HTTPException(status_code=429, detail="Too many projects created. Try again shortly.")
    attempts.append(now)

    project_id, private, public = await manager.create_project(body.get("name", "New Project"))
    return {
        "status": "success",
        "project_id": project_id,
        "tokens": {"private": private, "public": public},
    }


@api.post("/projects/{project_id}/tokens")
async def generate_project_token(
    project_id: str, request: Request, auth: Tuple[str, str] = Depends(validate_token)
):
    require_project(auth, project_id, "admin")
    body = await json_body(request)
    new_type = body.get("type", TOKEN_PUBLIC)
    if new_type not in (TOKEN_PRIVATE, TOKEN_PUBLIC):
        raise HTTPException(status_code=400, detail="type must be 'private' or 'public'")
    try:
        new_token = await manager.add_token(project_id, new_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not new_token:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "success", "type": new_type, "token": new_token}


@api.post("/projects/{project_id}/tokens/revoke")
async def revoke_token(
    project_id: str, request: Request, auth: Tuple[str, str] = Depends(validate_token)
):
    require_project(auth, project_id, "admin")
    body = await json_body(request)
    token = body.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Token to revoke required")
    try:
        removed = await manager.revoke_token(project_id, token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "success", "revoked": removed}


# --------------------------------------------------------------------------- #
# Files
# --------------------------------------------------------------------------- #
def _file_view(request: Request, project_id: str, alias: str, record: Dict[str, Any]) -> Dict[str, Any]:
    view = dict(record)
    if record.get("key"):
        view["url"] = share_url(request, project_id, alias, str(record["key"]))
    view.pop("key", None)  # the share secret is only exposed inside the URL
    return view


@api.get("/projects/{project_id}/files")
async def list_files(project_id: str, request: Request, auth: Tuple[str, str] = Depends(validate_token)):
    require_project(auth, project_id, "download")
    project = await manager.read_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    files = project.get("files") or {}
    return {
        "status": "success",
        "files": {
            alias: _file_view(request, project_id, alias, record if isinstance(record, dict) else {"id": record})
            for alias, record in files.items()
        },
    }


@api.post("/projects/{project_id}/upload")
async def upload_project_file(
    project_id: str,
    request: Request,
    file: UploadFile = File(...),
    alias: str = Form(...),
    auth: Tuple[str, str] = Depends(validate_token),
):
    require_project(auth, project_id, "upload")
    try:
        alias = validate_alias(alias)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Starlette exposes the size; fall back to the spooled file's position.
    size_bytes = getattr(file, "size", None)
    if size_bytes is None:
        file.file.seek(0, 2)
        size_bytes = file.file.tell()
        file.file.seek(0)
    size_mb = size_bytes / (1024 * 1024)
    delay = throttle.delay_for_size(size_mb)
    if delay is None:
        raise HTTPException(
            status_code=413, detail=f"File exceeds {MAX_UPLOAD_MB:g}MB limit"
        )

    tmp_root = data_dir() / "tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix="upload-", dir=tmp_root))
    temp_path = tmp_dir / _safe_name(file.filename)
    try:
        # Copy off the event loop: large uploads must not freeze the server.
        def _copy() -> None:
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer, length=1024 * 1024)

        await asyncio.to_thread(_copy)
        real_size = temp_path.stat().st_size
        if real_size / (1024 * 1024) > MAX_UPLOAD_MB:
            raise HTTPException(status_code=413, detail=f"File exceeds {MAX_UPLOAD_MB:g}MB limit")

        await throttle.wait(delay)
        try:
            record = await manager.add_file(
                project_id, alias, str(temp_path), file.filename or alias, real_size
            )
        except (ValueError, StorageNotFound) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "status": "success",
            "alias": alias,
            "url": share_url(request, project_id, alias, record["key"]),
            "file": _file_view(request, project_id, alias, record),
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        await file.close()


async def _send_file(path: str, filename: str, media_type: str, temporary: bool):
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Stored file is missing")
    # Telegram downloads land in a per-request temp directory; remove the
    # whole directory afterwards (local backend files are permanent).
    cleanup = (
        BackgroundTask(shutil.rmtree, os.path.dirname(path), True) if temporary else None
    )
    return FileResponse(path, filename=filename, media_type=media_type, background=cleanup)


async def _download(project_id: str, alias: str):
    record = await manager.get_file(project_id, alias)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    filename = _safe_name(record.get("name") or alias)
    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    temporary = manager.storage.name == "telegram"
    try:
        path = await manager.download_file(record.get("id"))
    except StorageNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return await _send_file(str(path), filename, media_type, temporary)


@api.get("/projects/{project_id}/files/{alias}")
async def download_project_file(
    project_id: str,
    alias: str,
    auth: Tuple[str, str] = Depends(validate_token),
):
    """Authenticated download (Bearer token)."""
    require_project(auth, project_id, "download")
    return await _download(project_id, alias)


@api.delete("/projects/{project_id}/files/{alias}")
async def delete_file(project_id: str, alias: str, auth: Tuple[str, str] = Depends(validate_token)):
    require_project(auth, project_id, "admin")
    removed = await manager.delete_file(project_id, alias)
    if not removed:
        raise HTTPException(status_code=404, detail="File not found")
    return {"status": "success"}


@app.get("/f/{project_id}/{alias}", dependencies=[Depends(storage_session)])
@app.get("/files/{project_id}/{alias}", dependencies=[Depends(storage_session)])
async def public_file(
    project_id: str,
    alias: str,
    key: Optional[str] = None,
):
    """Stable, shareable URL. The random per-file key acts as an unguessable
    read capability; no account token is embedded in the link."""
    if not await manager.verify_share_key(project_id, alias, key):
        raise HTTPException(status_code=403, detail="Invalid or missing file key")
    return await _download(project_id, alias)


# --------------------------------------------------------------------------- #
# Global variables
# --------------------------------------------------------------------------- #
@api.get("/projects/{project_id}/gv")
async def list_gvs(project_id: str, auth: Tuple[str, str] = Depends(validate_token)):
    require_project(auth, project_id, "get_gv")
    try:
        return await manager.list_gvs(project_id)
    except StorageNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@api.get("/projects/{project_id}/gv/{alias}")
async def get_gv(project_id: str, alias: str, auth: Tuple[str, str] = Depends(validate_token)):
    """Single variable. Every SDK calls this endpoint (it was missing)."""
    require_project(auth, project_id, "get_gv")
    value = await manager.get_gv(project_id, alias)
    if value is None:
        raise HTTPException(status_code=404, detail="Variable not found")
    return {"alias": alias, "value": value}


@api.post("/projects/{project_id}/gv")
async def add_gv(project_id: str, request: Request, auth: Tuple[str, str] = Depends(validate_token)):
    require_project(auth, project_id, "upload")
    body = await json_body(request)
    alias = body.get("alias")
    value = body.get("value")
    if alias is None or value is None:
        raise HTTPException(status_code=400, detail="Alias and value required")
    try:
        message_id = await manager.set_gv(project_id, alias, value)
    except (ValueError, StorageNotFound) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await throttle.wait(1 if throttle.enabled else 0)
    return {"status": "success", "alias": alias, "id": message_id}


@api.delete("/projects/{project_id}/gv/{alias}")
async def delete_gv(project_id: str, alias: str, auth: Tuple[str, str] = Depends(validate_token)):
    require_project(auth, project_id, "admin")
    removed = await manager.delete_gv(project_id, alias)
    if not removed:
        raise HTTPException(status_code=404, detail="Variable not found")
    return {"status": "success"}


app.include_router(api)


# --------------------------------------------------------------------------- #
# Static site (paths are relative to this file, not the process CWD)
# --------------------------------------------------------------------------- #
app.mount("/assets", StaticFiles(directory=BASE_DIR / "assets"), name="assets")
app.mount("/docs/static", StaticFiles(directory=BASE_DIR / "docs"), name="docs_static")
app.mount("/docs/assets", StaticFiles(directory=BASE_DIR / "docs"), name="docs_assets")


def static_file(path: str) -> FileResponse:
    return FileResponse(BASE_DIR / path)


@app.get("/")
async def read_index():
    return static_file("index.html")


@app.get("/app.js")
async def read_js():
    return static_file("app.js")


@app.get("/style.css")
async def read_css():
    return static_file("style.css")


@app.get("/s1024.js")
async def read_sdk():
    return static_file("libraries/cdn.js")


@app.get("/files")
async def files_redirect():
    """Legacy dashboard URL."""
    return static_file("index.html")


@app.get("/docs")
@app.get("/docs/")
async def read_docs():
    return static_file("docs/index.html")


@app.get("/docs/{path:path}")
async def read_docs_assets(path: str):
    docs_root = (BASE_DIR / "docs").resolve()
    candidate = (docs_root / path).resolve()
    if candidate.is_relative_to(docs_root) and candidate.is_file():
        return FileResponse(candidate)
    # Only extensionless navigation paths fall back to the docs shell.
    if Path(path).suffix:
        raise HTTPException(status_code=404, detail="Documentation file not found")
    return static_file("docs/index.html")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    print(f"Storage1024 starting on 0.0.0.0:{port} ({storage_status()['selected_backend']} backend)")
    uvicorn.run(app, host="0.0.0.0", port=port)
