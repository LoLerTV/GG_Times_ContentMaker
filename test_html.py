import asyncio
import os
from telethon import TelegramClient
from config import config

async def test():
    from telethon.sessions import StringSession
    client = TelegramClient(StringSession(config.TG_SESSION_STRING), config.TG_API_ID, config.TG_API_HASH)
    await client.start()
    
    channels = config.get_source_channels
    if not channels:
        print("No channels")
        return
        
    messages = await client.get_messages(channels[0], limit=1)
    if not messages:
        print("No messages")
        return
        
    m = messages[0]
    print("message length:", len(m.text or ""))
    print("message:", m.text[:100] if m.text else "None")
    
    try:
        import telethon.utils
        html_text = telethon.utils.get_message_text(m, 'html')
        print("html:", html_text[:100])
    except Exception as e:
        print("Error telethon.utils:", e)

if __name__ == "__main__":
    asyncio.run(test())
