from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from manager import ProjectManager
from dotenv import load_dotenv
import uvicorn
import os
import shutil

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
    uvicorn.run(app, host="127.0.0.1", port=8000)
