import asyncio
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from config import config

class TelegramPublisher:
    def __init__(self):
        # aiogram 3.x requires a token, parse_mode can be set on bot or message
        from aiogram.client.session.aiohttp import AiohttpSession
        session = AiohttpSession()
        self.bot = Bot(
            token=config.TELEGRAM_BOT_TOKEN, 
            default=DefaultBotProperties(parse_mode="HTML"),
            session=session
        )
        # Increase default timeout for session
        self.bot.session.timeout = 60 
        self.channel_id = config.TELEGRAM_CHANNEL_ID

    async def publish(self, text: str, media: list = None) -> bool:
        """Publishes the given text and media to the configured Telegram channel."""
        try:
            if not media:
                await self.bot.send_message(chat_id=self.channel_id, text=text)
            elif len(media) == 1:
                item = media[0]
                has_spoiler = item.get("has_spoiler", False)
                # Note: aiogram uses parse_mode from the bot instance, but setting it explicitly is safe
                if item["type"] == "photo":
                    from aiogram.types import FSInputFile
                    await self.bot.send_photo(
                        chat_id=self.channel_id, 
                        photo=FSInputFile(item["path"]), 
                        caption=text,
                        has_spoiler=has_spoiler
                    )
                elif item["type"] == "video":
                    from aiogram.types import FSInputFile
                    await self.bot.send_video(
                        chat_id=self.channel_id, 
                        video=FSInputFile(item["path"]), 
                        caption=text,
                        has_spoiler=has_spoiler
                    )
                else:
                    from aiogram.types import FSInputFile
                    await self.bot.send_document(
                        chat_id=self.channel_id, 
                        document=FSInputFile(item["path"]), 
                        caption=text
                    )
            else:
                # Group of media
                from aiogram.types import InputMediaPhoto, InputMediaVideo, InputMediaDocument, FSInputFile
                media_group = []
                for idx, item in enumerate(media):
                    has_spoiler = item.get("has_spoiler", False)
                    # Only the first item should have the caption
                    caption = text if idx == 0 else None
                    if item["type"] == "photo":
                        media_group.append(InputMediaPhoto(media=FSInputFile(item["path"]), caption=caption, has_spoiler=has_spoiler))
                    elif item["type"] == "video":
                        media_group.append(InputMediaVideo(media=FSInputFile(item["path"]), caption=caption, has_spoiler=has_spoiler))
                    else:
                        media_group.append(InputMediaDocument(media=FSInputFile(item["path"]), caption=caption))
                
                if media_group:
                    await self.bot.send_media_group(chat_id=self.channel_id, media=media_group)

            print(f"Successfully published to {self.channel_id}")
            return True
        except Exception as e:
            print(f"Failed to publish to Telegram: {e}")
            return False
            
    async def close(self):
        """Closes the bot session."""
        await self.bot.session.close()
