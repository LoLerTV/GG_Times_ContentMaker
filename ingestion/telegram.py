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

    async def _handle_messages(self, chat_id, messages):
        """Processes a list of messages (either a single message or an album) and puts them into the queue."""
        media_files = []
        combined_text = ""
        
        from telethon.extensions import html
        
        # In Telegram albums, usually only the first message has a caption
        # In single messages, it's just that message.
        for m in messages:
            if m.text:
                if m.entities:
                    combined_text += html.unparse(m.text, m.entities)
                else:
                    combined_text += m.text
            
            if m.media:
                has_spoiler = getattr(m.media, "spoiler", False)
                print(f"Downloading media for {m.id} (Spoiler: {has_spoiler})...")
                file_path = await m.download_media(file="media/")
                if file_path:
                    media_files.append({
                        "path": file_path,
                        "type": "photo" if m.photo else "video" if m.video else "document",
                        "has_spoiler": has_spoiler
                    })

        if not combined_text and not media_files:
            return

        # Use the ID of the first message as a reference
        primary_id = messages[0].id
        data = {
            "platform": "tg",
            "external_id": f"tg_{chat_id}_{primary_id}",
            "text": combined_text,
            "media": media_files
        }
        await self.queue.put(data)
        print(f"Ingested TG message(s) from {chat_id} (Media: {len(media_files)})")

    async def start(self):
        await self.client.start()
        channels = config.get_source_channels
        
        for ch in channels:
            try:
                await self.client.get_entity(ch)
                print(f"Resolved entity for channel: {ch}")
            except Exception as e:
                print(f"Failed to resolve {ch}: {e}")

        @self.client.on(events.Album(chats=channels))
        async def album_handler(event):
            await self._handle_messages(event.chat_id, event.messages)

        @self.client.on(events.NewMessage(chats=channels))
        async def message_handler(event):
            # Ignore messages that are part of an album (they are handled by events.Album)
            if event.grouped_id:
                return
            await self._handle_messages(event.chat_id, [event.message])

        print("Telethon listener started (Albums and NewMessages).")
        await self.client.run_until_disconnected()
