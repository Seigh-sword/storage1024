import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaDocument
from dotenv import load_dotenv

# Load config from multiple potential locations
config_paths = [
    os.path.expanduser('~/.storage1024/config.env'), # Local dev (outside repo)
    '.env' # Cloud hosting (injected by host)
]
for path in config_paths:
    if os.path.exists(path):
        load_dotenv(path)
        break

class TelegramStorage:
    def __init__(self):
        self.api_id = os.getenv('API_ID')
        self.api_hash = os.getenv('API_HASH')
        
        # Look for session string in env or file
        self.session_str = os.getenv('TELEGRAM_SESSION')
        if not self.session_str:
            session_path = os.path.expanduser('~/.storage1024/storage.session_string')
            if os.path.exists(session_path):
                with open(session_path, 'r') as f:
                    self.session_str = f.read().strip()

        channel_id_env = os.getenv('CHANNEL_ID')
        self.channel_id = int(channel_id_env) if channel_id_env else None
        
        if not self.session_str or self.channel_id is None:
            raise ValueError("TELEGRAM_SESSION or CHANNEL_ID not found. Please check your config.env.")
            
        self.client = TelegramClient(StringSession(self.session_str), self.api_id, self.api_hash)

    async def connect(self):
        if not self.client.is_connected():
            await self.client.connect()

    async def disconnect(self):
        await self.client.disconnect()

    async def upload_file(self, file_path, caption=None):
        if not os.path.exists(file_path):
            print(f"File {file_path} not found.")
            return None
        
        print(f"Uploading {file_path} to channel...")
        message = await self.client.send_file(self.channel_id, file_path, caption=caption)
        print(f"Uploaded! Message ID: {message.id}")
        return message.id

    async def list_files(self, limit=20):
        print(f"Listing last {limit} files in channel...")
        files = []
        async for message in self.client.iter_messages(self.channel_id, limit=limit):
            if message.media and isinstance(message.media, MessageMediaDocument):
                file_name = "Unknown"
                for attr in message.media.document.attributes:
                    if hasattr(attr, 'file_name'):
                        file_name = attr.file_name
                        break
                files.append({
                    'id': message.id,
                    'name': file_name,
                    'date': message.date,
                    'size': message.media.document.size
                })
        return files

    async def download_file(self, message_id, output_path=None):
        message = await self.client.get_messages(self.channel_id, ids=message_id)
        if not message or not message.media:
            print("Message not found or no media attached.")
            return None
        
        print(f"Downloading file from message {message_id}...")
        path = await self.client.download_media(message, file=output_path)
        print(f"Downloaded to {path}")
        return path

    async def get_index(self, message_id=4):
        """Reads JSON data from a specific message."""
        try:
            message = await self.client.get_messages(self.channel_id, ids=message_id)
            if message and message.text:
                import json
                # Handle the user's requested header
                content = message.text.split('——\nIndex\n——\n')[-1]
                return json.loads(content)
        except Exception as e:
            print(f"Error reading index: {e}")
        return {"projects": {}}

    async def update_index(self, data, message_id=4):
        """Writes JSON data to a specific message."""
        import json
        header = "——\nIndex\n——\n"
        content = header + json.dumps(data, indent=2)
        await self.client.edit_message(self.channel_id, message_id, content)
        print("Index updated successfully.")

    async def store_gv(self, key, value):
        """Stores a Global Variable as a text message and returns ID."""
        text = f"GV[{key}]: {value}"
        message = await self.client.send_message(self.channel_id, text)
        return message.id
