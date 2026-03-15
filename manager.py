import os
import random
import string
import asyncio
import json
import uuid
from dotenv import load_dotenv
from client import TelegramStorage

TOKEN_PRIVATE = "private"
TOKEN_PUBLIC = "public"

config_paths = [
    os.path.expanduser('~/.storage1024/config.env'),
    '.env'
]
for path in config_paths:
    if os.path.exists(path):
        load_dotenv(path)
        break

def generate_private_token():
    unique_id = str(uuid.uuid4())[:18]
    return f"s1024-{unique_id};qi="

def generate_public_token():
    rand_body = "".join(random.choices(string.ascii_letters + string.digits, k=28))
    return f"s1024-{rand_body};gg="

class ProjectManager:
    def __init__(self):
        self.storage = TelegramStorage()
        self.index = {"projects": {}}

    async def _load_index(self):
        await self.storage.connect()
        self.index = await self.storage.get_index()
        await self.storage.disconnect()

    async def validate_token(self, token):
        if not token: return None, None
        
        await self._load_index()
        
        for project_id, p in self.index.get("projects", {}).items():
            if token in p.get("tokens", {}).get("private", []):
                return project_id, TOKEN_PRIVATE
            if token in p.get("tokens", {}).get("public", []):
                return project_id, TOKEN_PUBLIC
        return None, None

    async def create_project(self, name):
        await self.storage.connect()
        index = await self.storage.get_index()
        
        project_id = str(random.randint(1000, 9999))
        while project_id in index['projects']:
            project_id = str(random.randint(1000, 9999))
            
        private_token = generate_private_token()
        public_token = generate_public_token()
        
        index['projects'][project_id] = {
            "name": name,
            "tokens": {
                "private": [private_token],
                "public": [public_token]
            },
            "files": {},
            "global_vars": {}
        }
        
        await self.storage.update_index(index)
        await self.storage.disconnect()
        
        print(f"Project '{name}' created!")
        print(f"ID: {project_id}")
        print(f"Private Token: {private_token}")
        print(f"Public Token: {public_token}")
        return project_id, private_token, public_token

    async def add_file_to_project(self, project_id, alias, file_path):
        await self.storage.connect()
        index = await self.storage.get_index()
        
        if project_id not in index['projects']:
            print("Project not found.")
            return
            
        message_id = await self.storage.upload_file(file_path, caption=f"Project: {project_id} | File: {alias} | Size: {os.path.getsize(file_path)/(1024*1024):.2f}MB")
        index['projects'][project_id]['files'][alias] = {
            "id": message_id,
            "size": os.path.getsize(file_path) / (1024 * 1024) # Store in MB
        }
        
        await self.storage.update_index(index)
        await self.storage.disconnect()

    async def add_gv_to_project(self, project_id, alias, value):
        await self.storage.connect()
        index = await self.storage.get_index()
        
        if project_id not in index['projects']:
            print("Project not found.")
            return
            
        message_id = await self.storage.store_gv(alias, value)
        index['projects'][project_id]['global_vars'][alias] = message_id
        
        await self.storage.update_index(index)
        await self.storage.disconnect()

    async def add_token_to_project(self, project_id, token_type):
        await self.storage.connect()
        index = await self.storage.get_index()
        
        if project_id not in index['projects']:
            await self.storage.disconnect()
            return None
            
        new_token = generate_private_token() if token_type == TOKEN_PRIVATE else generate_public_token()
        
        t_key = "private" if token_type == TOKEN_PRIVATE else "public"
        if t_key not in index['projects'][project_id]['tokens']:
            index['projects'][project_id]['tokens'][t_key] = []
            
        index['projects'][project_id]['tokens'][t_key].append(new_token)
        
        await self.storage.update_index(index)
        await self.storage.disconnect()
        return new_token

    async def delete_file_from_project(self, project_id, alias):
        await self.storage.connect()
        index = await self.storage.get_index()
        if project_id in index['projects'] and alias in index['projects'][project_id]['files']:
            del index['projects'][project_id]['files'][alias]
            await self.storage.update_index(index)
        await self.storage.disconnect()

    async def delete_gv_from_project(self, project_id, alias):
        await self.storage.connect()
        index = await self.storage.get_index()
        if project_id in index['projects'] and alias in index['projects'][project_id]['global_vars']:
            del index['projects'][project_id]['global_vars'][alias]
            await self.storage.update_index(index)
        await self.storage.disconnect()

    async def revoke_token_from_project(self, project_id, token):
        await self.storage.connect()
        index = await self.storage.get_index()
        if project_id in index['projects']:
            tokens = index['projects'][project_id]['tokens']
            if token in tokens.get("private", []):
                tokens["private"].remove(token)
            elif token in tokens.get("public", []):
                tokens["public"].remove(token)
            await self.storage.update_index(index)
        await self.storage.disconnect()

async def main():
    import sys
    manager = ProjectManager()
    if len(sys.argv) < 2:
        print("Usage: python manager.py <command>")
        return
        
    cmd = sys.argv[1]
    if cmd == "create":
        name = sys.argv[2] if len(sys.argv) > 2 else "New Project"
        await manager.create_project(name)
    elif cmd == "add-file":
        await manager.add_file_to_project(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "add-gv":
        await manager.add_gv_to_project(sys.argv[2], sys.argv[3], sys.argv[4])

if __name__ == "__main__":
    asyncio.run(main())
