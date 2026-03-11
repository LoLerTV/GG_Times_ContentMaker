import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from config import config

class TelegramIngestor:
    def __init__(self, queue: asyncio.Queue):
        self.queue = queue
        self.client = TelegramClient(
            StringSession(config.TG_SESSION_STRING),
            config.TG_API_ID,
            config.TG_API_HASH
        )

    async def start(self):
        @self.client.on(events.NewMessage(chats=config.TG_SOURCE_CHANNELS))
        async def handler(event):
            if event.text:
                data = {
                    "platform": "tg",
                    "external_id": f"tg_{event.chat_id}_{event.id}",
                    "text": event.text,
                    "media": [] # Logic for downloading media can be added here
                }
                await self.queue.put(data)
                print(f"Ingested TG message from {event.chat_id}")

        await self.client.start()
        print("Telethon listener started.")
        await self.client.run_until_disconnected()
