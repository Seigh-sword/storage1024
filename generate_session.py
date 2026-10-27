"""One-time helper: create a Telethon StringSession for the Telegram backend.

Run locally (needs an interactive terminal):

    python generate_session.py

Then put the printed string in the TELEGRAM_SESSION environment variable on
Render, or in .env / ~/.storage1024/config.env for local development.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

from config import load_config, telegram_credentials

load_config()


async def main() -> None:
    creds = telegram_credentials()
    phone = os.getenv("PHONE_NUMBER")
    if not creds["api_id"] or not creds["api_hash"] or not phone:
        raise SystemExit(
            "Error: set API_ID, API_HASH and PHONE_NUMBER in .env "
            "(or ~/.storage1024/config.env) first."
        )

    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError
    from telethon.sessions import StringSession

    print("Initializing Telegram Client...")
    async with TelegramClient(StringSession(), creds["api_id"], creds["api_hash"]) as client:
        if not await client.is_user_authorized():
            await client.send_code_request(phone)
            code = input("Enter the code you received on Telegram: ").strip()
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                password = input("Two-step verification is enabled. Enter your password: ")
                await client.sign_in(password=password)

        session_str = client.session.save()
        print("\n" + "=" * 60)
        print("SUCCESSFULLY AUTHENTICATED!")
        print("Set this as TELEGRAM_SESSION in your environment:")
        print("-" * 60)
        print(session_str)
        print("-" * 60)
        print("=" * 60)

        out = Path("storage.session_string")
        out.write_text(session_str, encoding="utf-8")
        print(f"\nSession string also saved to '{out}' (gitignored).")


if __name__ == "__main__":
    asyncio.run(main())
