from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from manager import ProjectManager
from dotenv import load_dotenv
import uvicorn
import os
import shutil
import asyncio

config_paths = [
    os.path.expanduser('~/.storage1024/config.env'),
    '.env'
]
for path in config_paths:
    if os.path.exists(path):
        load_dotenv(path)
        break

app = FastAPI(title="Storage1024 API Bridge", docs_url=None, redoc_url=None)
security = HTTPBearer()

TOKEN_PRIVATE = "private"
TOKEN_PUBLIC = "public"

async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    if token.endswith(";qi="):
        t_type = TOKEN_PRIVATE
    elif token.endswith(";gg="):
        t_type = TOKEN_PUBLIC
    else:
        if token.startswith("s1024-"): t_type = TOKEN_PRIVATE
        elif token.endswith(".gg="): t_type = TOKEN_PUBLIC
        else: raise HTTPException(status_code=401, detail="Invalid token format")

    project_id, validated_type = await manager.validate_token(token)
    if not project_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return project_id, validated_type

def check_access(token_type: str, required_scope: str):
    if token_type == TOKEN_PRIVATE:
        return True
    
    allowed_public_ops = ["upload", "get_gv"]
    if required_scope not in allowed_public_ops:
        raise HTTPException(status_code=403, detail="Scope restricted for Public tokens")
    return True

class QueueManager:
    def __init__(self):
        self.lock = asyncio.Lock()

    def get_delay_for_size(self, size_mb: float) -> int:
        if size_mb > 1800: return -1
        if size_mb < 5: return 1
        if size_mb < 25: return 3
        if size_mb < 50: return 5
        if size_mb < 100: return 10
        if size_mb < 350: return 15
        if size_mb < 750: return 20
        if size_mb < 950: return 25
        if size_mb < 1000: return 28
        if size_mb < 1024: return 30
        return 35

    async def enqueue(self, delay: int):
        async with self.lock:
            await asyncio.sleep(delay)

queue_manager = QueueManager()

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = ProjectManager()

@app.get("/api/index")
async def get_index(auth: tuple = Depends(validate_token)):
    project_id, token_type = auth
    check_access(token_type, "admin")
    
    projects = manager.index.get("projects", {})
    p = projects.get(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
        
    return {
        "status": "success",
        "projects": { project_id: p } 
    }

@app.post("/api/projects/create")
async def create_project(data: Request):
    req = await data.json()
    name = req.get("name", "New Project")
    project_id, priv, pub = await manager.create_project(name)
    return {
        "status": "success", 
        "project_id": project_id,
        "tokens": {
            "private": priv,
            "public": pub
        }
    }

@app.post("/api/projects/{project_id}/tokens")
async def generate_project_token(
    project_id: str, 
    data: Request, 
    auth: tuple = Depends(validate_token)
):
    auth_project_id, token_type = auth
    if auth_project_id != project_id:
        raise HTTPException(status_code=403, detail="Token does not match project_id")
    
    check_access(token_type, "admin")
    
    req = await data.json()
    new_type = req.get("type", "public")
    t_const = TOKEN_PRIVATE if new_type == "private" else TOKEN_PUBLIC
    
    new_token = await manager.add_token_to_project(project_id, t_const)
    if not new_token:
        raise HTTPException(status_code=404, detail="Project not found")
        
    return {"status": "success", "token": new_token}

@app.post("/api/projects/{project_id}/upload")
async def upload_project_file(
    project_id: str, 
    file: UploadFile = File(...), 
    alias: str = Form(...),
    auth: tuple = Depends(validate_token)
):
    auth_project_id, token_type = auth
    if auth_project_id != project_id:
        raise HTTPException(status_code=403, detail="Token does not match project_id")
    check_access(token_type, "upload")
    
    file.file.seek(0, 2)
    size_bytes = file.file.tell()
    file.file.seek(0)
    size_mb = size_bytes / (1024 * 1024)
    delay = queue_manager.get_delay_for_size(size_mb)
    if delay == -1:
        raise HTTPException(status_code=413, detail="File exceeds 1800MB limit")

    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        async with queue_manager.lock:
            await manager.add_file_to_project(project_id, alias, temp_path)
            await asyncio.sleep(delay)
        return {"status": "success", "alias": alias}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/api/projects/{project_id}/gv")
async def add_gv(project_id: str, data: Request, auth: tuple = Depends(validate_token)):
    auth_project_id, token_type = auth
    if auth_project_id != project_id:
        raise HTTPException(status_code=403, detail="Token does not match project_id")
    check_access(token_type, "upload")
    
    req = await data.json()
    alias = req.get("alias")
    value = req.get("value")
    if not alias or not value:
        raise HTTPException(status_code=400, detail="Alias and value required")
        
    async with queue_manager.lock:
        await manager.add_gv_to_project(project_id, alias, value)
        await asyncio.sleep(1) 
    return {"status": "success"}

@app.get("/api/projects/{project_id}/gv")
async def list_gvs(project_id: str, auth: tuple = Depends(validate_token)):
    auth_project_id, token_type = auth
    if auth_project_id != project_id:
        raise HTTPException(status_code=403, detail="Token does not match project_id")
    check_access(token_type, "get_gv")
    
    await manager.storage.connect()
    try:
        index = await manager.storage.get_index()
        project = index['projects'].get(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        gv_map = {}
        vars = project.get('global_vars', {})
        for alias, msg_id in vars.items():
            try:
                msg = await manager.storage.client.get_messages(manager.storage.channel_id, ids=msg_id)
                value = msg.text.split(": ", 1)[-1] if msg and msg.text else None
                gv_map[alias] = value
            except:
                gv_map[alias] = None
        return gv_map
    finally:
        await manager.storage.disconnect()

@app.delete("/api/projects/{project_id}/files/{alias}")
async def delete_file(project_id: str, alias: str, auth: tuple = Depends(validate_token)):
    auth_project_id, token_type = auth
    if auth_project_id != project_id:
        raise HTTPException(status_code=403, detail="Token does not match project_id")
    check_access(token_type, "admin")
    await manager.delete_file_from_project(project_id, alias)
    return {"status": "success"}

@app.delete("/api/projects/{project_id}/gv/{alias}")
async def delete_gv(project_id: str, alias: str, auth: tuple = Depends(validate_token)):
    auth_project_id, token_type = auth
    if auth_project_id != project_id:
        raise HTTPException(status_code=403, detail="Token does not match project_id")
    check_access(token_type, "admin")
    await manager.delete_gv_from_project(project_id, alias)
    return {"status": "success"}

@app.post("/api/projects/{project_id}/tokens/revoke")
async def revoke_token(project_id: str, data: Request, auth: tuple = Depends(validate_token)):
    auth_project_id, token_type = auth
    if auth_project_id != project_id:
        raise HTTPException(status_code=403, detail="Token does not match project_id")
    check_access(token_type, "admin")
    
    req = await data.json()
    token_to_revoke = req.get("token")
    if not token_to_revoke:
        raise HTTPException(status_code=400, detail="Token to revoke required")
        
    await manager.revoke_token_from_project(project_id, token_to_revoke)
    return {"status": "success"}

app.mount("/assets", StaticFiles(directory="assets"), name="assets")
app.mount("/docs/static", StaticFiles(directory="docs"), name="docs_static") 

from fastapi.responses import FileResponse

@app.get("/")
async def read_index():
    return FileResponse("index.html")

@app.get("/app.js")
async def read_js():
    return FileResponse("app.js")

@app.get("/style.css")
async def read_css():
    return FileResponse("style.css")

@app.get("/s1024.js")
async def read_sdk():
    return FileResponse("libraries/cdn.js")

@app.get("/files")
async def files_redirect():
    return FileResponse("index.html")

@app.get("/docs")
async def read_docs():
    return FileResponse("docs/index.html")

@app.get("/docs/{path:path}")
async def read_docs_assets(path: str):
    
    if path == "style.css": return FileResponse("style.css")
    if os.path.exists(f"docs/{path}"):
        return FileResponse(f"docs/{path}")
    return FileResponse("docs/index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
