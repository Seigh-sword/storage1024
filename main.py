import sys
import asyncio
import argparse
import os
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

async def run_upload(args):
    storage = TelegramStorage()
    await storage.connect()
    try:
        await storage.upload_file(args.file, args.caption)
    finally:
        await storage.disconnect()

async def run_list(args):
    storage = TelegramStorage()
    await storage.connect()
    try:
        files = await storage.list_files(args.limit)
        print("\n" + "-"*50)
        print(f"{'ID':<10} | {'Name':<30} | {'Size (KB)':<10}")
        print("-"*50)
        for f in files:
            size_kb = round(f['size'] / 1024, 2)
            print(f"{f['id']:<10} | {f['name'][:30]:<30} | {size_kb:<10}")
        print("-"*50)
    finally:
        await storage.disconnect()

async def run_download(args):
    storage = TelegramStorage()
    await storage.connect()
    try:
        await storage.download_file(args.id, args.output)
    finally:
        await storage.disconnect()

def main():
    parser = argparse.ArgumentParser(description="Storage1024: Telegram-based File Storage")
    subparsers = parser.add_subparsers(dest="command")

    # Upload command
    upload_parser = subparsers.add_parser("upload", help="Upload a file")
    upload_parser.add_argument("file", help="Path to the file to upload")
    upload_parser.add_argument("--caption", "-c", help="Optional caption for the file")

    # List command
    list_parser = subparsers.add_parser("list", help="List files in the channel")
    list_parser.add_argument("--limit", "-l", type=int, default=20, help="Number of files to list")

    # Download command
    download_parser = subparsers.add_parser("download", help="Download a file")
    download_parser.add_argument("id", type=int, help="Message ID of the file to download")
    download_parser.add_argument("--output", "-o", help="Optional output path")

    args = parser.parse_args()

    if args.command == "upload":
        asyncio.run(run_upload(args))
    elif args.command == "list":
        asyncio.run(run_list(args))
    elif args.command == "download":
        asyncio.run(run_download(args))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
