import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
phone = os.getenv('PHONE_NUMBER')

async def main():
    print("Initializing Telegram Client...")
    
    async with TelegramClient(StringSession(), api_id, api_hash) as client:
     
        if not await client.is_user_authorized():
            await client.send_code_request(phone)
            code = input('Enter the code you received on Telegram: ')
            try:
                await client.sign_in(phone, code)
            except Exception as e:
           
                password = input('Two-step verification is enabled. Please enter your password: ')
                await client.sign_in(password=password)
        
        session_str = client.session.save()
        print("\n" + "="*50)
        print("SUCCESSFULLY AUTHENTICATED!")
        print("Your Session String is below. Please copy it and save it safely.")
        print("Copy EVERYTHING between the lines:")
        print("-" * 20)
        print(session_str)
        print("-" * 20)
        print("="*50)
        
        # Also save to a file for local use
        with open('storage.session_string', 'w') as f:
            f.write(session_str)
        print("\nSession string also saved to 'storage.session_string'")

if __name__ == '__main__':
    if not api_id or not api_hash or not phone:
        print("Error: Please set API_ID, API_HASH, and PHONE_NUMBER in .env file.")
    else:
        asyncio.run(main())
