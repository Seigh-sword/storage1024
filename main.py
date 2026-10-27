"""Storage1024 command line client (works with either storage backend)."""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

from client import StorageError, get_storage
from config import load_config

load_config()


async def run_upload(args) -> None:
    if not os.path.isfile(args.file):
        raise SystemExit(f"File not found: {args.file}")
    storage = get_storage()
    async with storage.session():
        message_id = await storage.upload_file(args.file, args.caption)
        print(f"Uploaded! Message/File ID: {message_id}")


async def run_list(args) -> None:
    storage = get_storage()
    async with storage.session():
        files = await storage.list_files(args.limit)
    print("\n" + "-" * 60)
    print(f"{'ID':<36} | {'Name':<30} | {'Size (KB)':<10}")
    print("-" * 60)
    for item in files:
        print(f"{str(item['id']):<36} | {str(item['name'])[:30]:<30} | {round(item['size'] / 1024, 2):<10}")
    print("-" * 60)


async def run_download(args) -> None:
    storage = get_storage()
    async with storage.session():
        path = await storage.download_file(args.id, args.output)
        print(f"Downloaded to {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Storage1024: Telegram-based File Storage")
    subparsers = parser.add_subparsers(dest="command")

    upload_parser = subparsers.add_parser("upload", help="Upload a file")
    upload_parser.add_argument("file", help="Path to the file to upload")
    upload_parser.add_argument("--caption", "-c", help="Optional caption for the file")

    list_parser = subparsers.add_parser("list", help="List files in the channel")
    list_parser.add_argument("--limit", "-l", type=int, default=20, help="Number of files to list")

    download_parser = subparsers.add_parser("download", help="Download a file")
    download_parser.add_argument("id", help="Message/File ID of the file")
    download_parser.add_argument("--output", "-o", help="Optional output path")

    args = parser.parse_args()
    runners = {"upload": run_upload, "list": run_list, "download": run_download}
    if args.command not in runners:
        parser.print_help()
        return
    try:
        asyncio.run(runners[args.command](args))
    except (StorageError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
