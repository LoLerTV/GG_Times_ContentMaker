import asyncio
from telethon import TelegramClient
from config import config
import json
import os

async def main():
    client = TelegramClient(
        "anon_session_check",
        config.TG_API_ID,
        config.TG_API_HASH
    )
    
    # We will use the string session if available
    from telethon.sessions import StringSession
    if config.TG_SESSION_STRING:
        client = TelegramClient(
            StringSession(config.TG_SESSION_STRING),
            config.TG_API_ID,
            config.TG_API_HASH
        )
        
    await client.start()
    
    channels = config.get_source_channels
    if not channels:
        print("No source channels configured.")
        return
        
    for channel in channels:
        print(f"\n--- Channel: {channel} ---")
        try:
            messages = await client.get_messages(channel, limit=15)
            for m in messages:
                if not m.text:
                    continue
                has_media = m.media is not None
                media_type = type(m.media).__name__ if has_media else "None"
                is_spoiler = getattr(m.media, 'spoiler', False) if has_media else False
                
                print(f"ID: {m.id} | Media: {media_type} (Spoiler: {is_spoiler})")
                print(f"Text:\n{m.text[:200]}...\n")
        except Exception as e:
            print(f"Failed to fetch {channel}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
