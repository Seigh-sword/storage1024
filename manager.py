import os
import random
import string
import asyncio
import json
from dotenv import load_dotenv
from client import TelegramStorage

# Load config from multiple potential locations
config_paths = [
    os.path.expanduser('~/.storage1024/config.env'), # Local dev (outside repo)
    '.env' # Cloud hosting (injected by host)
]
for path in config_paths:
    if os.path.exists(path):
        load_dotenv(path)
        break

def generate_private_token():
    # s1024-[5 random string]-[3 random number]=
    rand_str = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
    rand_num = ''.join(random.choices(string.digits, k=3))
    return f"s1024-{rand_str}-{rand_num}="

def generate_public_token():
    # 32 chars long, ends with .gg=
    # 32 - 4 (.gg=) = 28 chars
    rand_body = ''.join(random.choices(string.ascii_letters + string.digits, k=28))
    return f"{rand_body}.gg="

class ProjectManager:
    def __init__(self):
        self.storage = TelegramStorage()

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
            
        message_id = await self.storage.upload_file(file_path, caption=f"Project: {project_id} | File: {alias}")
        index['projects'][project_id]['files'][alias] = message_id
        
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
