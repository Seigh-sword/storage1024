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

# Load config from multiple potential locations
config_paths = [
    os.path.expanduser('~/.storage1024/config.env'), # Local dev (outside repo)
    '.env' # Cloud hosting (injected by host)
]
for path in config_paths:
    if os.path.exists(path):
        load_dotenv(path)
        break

app = FastAPI(title="Storage1024 API Bridge")
security = HTTPBearer()

TOKEN_PRIVATE = "PRIVATE"
TOKEN_PUBLIC = "PUBLIC"

async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    if token.startswith("s1024-"):
        return TOKEN_PRIVATE
    elif token.endswith(".gg="):
        return TOKEN_PUBLIC
    else:
        raise HTTPException(status_code=403, detail="Invalid token format")

def check_access(token_type: str, required_scope: str):
    if token_type == TOKEN_PRIVATE:
        return True # Private has full access
    
    # Public scope restrictions
    allowed_public_ops = ["upload", "get_gv"]
    if required_scope not in allowed_public_ops:
        raise HTTPException(status_code=403, detail="Scope restricted for Public tokens")
    return True

# Rate Limiting & Queuing
class QueueManager:
    def __init__(self):
        self.lock = asyncio.Lock()

    def get_delay_for_size(self, size_mb: float) -> int:
        if size_mb > 1800: return -1 # Reject
        if size_mb < 5: return 1
        if size_mb < 25: return 3
        if size_mb < 50: return 5
        if size_mb < 100: return 10
        if size_mb < 350: return 15
        if size_mb < 750: return 20
        if size_mb < 950: return 25
        if size_mb < 1000: return 28
        if size_mb < 1024: return 30
        return 35 # 1024 to 1800

    async def enqueue(self, delay: int):
        async with self.lock:
            await asyncio.sleep(delay)

queue_manager = QueueManager()

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = ProjectManager()

@app.get("/api/index")
async def get_index(token_type: str = Depends(validate_token)):
    check_access(token_type, "admin") # Only private
    await manager.storage.connect()
    try:
        index = await manager.storage.get_index()
        return index
    finally:
        await manager.storage.disconnect()

@app.post("/api/projects/create")
async def create_project(data: Request, token_type: str = Depends(validate_token)):
    check_access(token_type, "admin") # Only private
    req = await data.json()
    name = req.get("name", "New Project")
    project_id = await manager.create_project(name)
    return {"status": "success", "project_id": project_id}

@app.post("/api/projects/{project_id}/upload")
async def upload_project_file(
    project_id: str, 
    file: UploadFile = File(...), 
    alias: str = Form(...),
    token_type: str = Depends(validate_token)
):
    check_access(token_type, "upload")
    
    # 1. Check size limit
    size_mb = 0
    file.file.seek(0, 2) # Seek to end
    size_bytes = file.file.tell()
    file.file.seek(0) # Reset
    size_mb = size_bytes / (1024 * 1024)

    delay = queue_manager.get_delay_for_size(size_mb)
    if delay == -1:
        raise HTTPException(status_code=413, detail="File exceeds 1800MB limit")

    # 2. Wait in queue
    await queue_manager.enqueue(delay)

    # Save file temporarily
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        await manager.add_file_to_project(project_id, alias, temp_path)
        return {"status": "success", "alias": alias}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/api/projects/{project_id}/gv")
async def add_gv(project_id: str, data: Request, token_type: str = Depends(validate_token)):
    check_access(token_type, "upload") # Uploading/setting is allowed if they have the token
    
    # 1s queue for GV
    await queue_manager.enqueue(1)

    req = await data.json()
    alias = req.get("alias")
    value = req.get("value")
    if not alias or not value:
        raise HTTPException(status_code=400, detail="Alias and value required")
    await manager.add_gv_to_project(project_id, alias, value)
    return {"status": "success"}

@app.get("/api/projects/{project_id}/gv/{alias}")
async def get_gv(project_id: str, alias: str, token_type: str = Depends(validate_token)):
    check_access(token_type, "get_gv")
    await manager.storage.connect()
    try:
        index = await manager.storage.get_index()
        project = index['projects'].get(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        msg_id = project['global_vars'].get(alias)
        if not msg_id:
            raise HTTPException(status_code=404, detail="GV not found")
            
        # Get the actual message content
        msg = await manager.storage.client.get_messages(manager.storage.channel_id, ids=msg_id)
        # Extract value from GV[key]: value
        value = msg.text.split(": ", 1)[-1] if msg and msg.text else None
        return {"alias": alias, "value": value}
    finally:
        await manager.storage.disconnect()

# Serve the web frontend
app.mount("/", StaticFiles(directory="web", html=True), name="web")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
