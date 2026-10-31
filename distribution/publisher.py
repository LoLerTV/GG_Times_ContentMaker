import os
from typing import List, Optional
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile, InputMediaDocument, InputMediaPhoto, InputMediaVideo
from config import config
from processing.formatting import CAPTION_LIMIT, MESSAGE_LIMIT, sanitize_html, split_html, strip_tags, visible_length

# Bot API upload limits
PHOTO_MAX_BYTES = 10 * 1024 * 1024
FILE_MAX_BYTES = 50 * 1024 * 1024


def _is_parse_error(e: TelegramBadRequest) -> bool:
    return "parse entities" in str(e).lower()


class TelegramPublisher:
    def __init__(self):
        self.bot = Bot(
            token=config.TELEGRAM_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode="HTML"),
            session=AiohttpSession(timeout=60),
        )
        self.channel_id = config.TELEGRAM_CHANNEL_ID

    def _usable_media(self, media: Optional[list]) -> list:
        """Drops files that disappeared from disk or exceed Bot API upload limits."""
        usable = []
        for item in media or []:
            path = item.get("path")
            if not path or not os.path.exists(path):
                print(f"Publisher: media file missing, skipping: {path}")
                continue
            size = os.path.getsize(path)
            max_size = PHOTO_MAX_BYTES if item["type"] == "photo" else FILE_MAX_BYTES
            if size > max_size:
                print(f"Publisher: media file too large ({size} bytes), skipping: {path}")
                continue
            usable.append(item)
        return usable[:10]  # media groups hold at most 10 items

    async def _send_text(self, text: str):
        for chunk in split_html(text, MESSAGE_LIMIT):
            try:
                await self.bot.send_message(chat_id=self.channel_id, text=chunk)
            except TelegramBadRequest as e:
                if not _is_parse_error(e):
                    raise
                print(f"Publisher: HTML rejected ({e}), sending as plain text")
                await self.bot.send_message(chat_id=self.channel_id, text=strip_tags(chunk), parse_mode=None)

    async def _send_media(self, media: list, caption: Optional[str], parse_mode: Optional[str]):
        if len(media) == 1:
            item = media[0]
            file = FSInputFile(item["path"])
            has_spoiler = item.get("has_spoiler", False)
            if item["type"] == "photo":
                await self.bot.send_photo(chat_id=self.channel_id, photo=file, caption=caption,
                                          parse_mode=parse_mode, has_spoiler=has_spoiler)
            elif item["type"] == "video":
                await self.bot.send_video(chat_id=self.channel_id, video=file, caption=caption,
                                          parse_mode=parse_mode, has_spoiler=has_spoiler)
            else:
                await self.bot.send_document(chat_id=self.channel_id, document=file, caption=caption,
                                             parse_mode=parse_mode)
            return

        media_group = []
        for idx, item in enumerate(media):
            file = FSInputFile(item["path"])
            has_spoiler = item.get("has_spoiler", False)
            # Only the first item carries the caption
            item_caption = caption if idx == 0 else None
            if item["type"] == "photo":
                media_group.append(InputMediaPhoto(media=file, caption=item_caption, parse_mode=parse_mode, has_spoiler=has_spoiler))
            elif item["type"] == "video":
                media_group.append(InputMediaVideo(media=file, caption=item_caption, parse_mode=parse_mode, has_spoiler=has_spoiler))
            else:
                media_group.append(InputMediaDocument(media=file, caption=item_caption, parse_mode=parse_mode))
        await self.bot.send_media_group(chat_id=self.channel_id, media=media_group)

    async def publish(self, text: str, media: list = None):
        """Publishes text and media to the channel. Raises on failure so the caller can retry."""
        text = sanitize_html(text)
        media = self._usable_media(media)

        if not media:
            await self._send_text(text)
        elif visible_length(text) <= CAPTION_LIMIT:
            try:
                await self._send_media(media, text, "HTML")
            except TelegramBadRequest as e:
                if not _is_parse_error(e):
                    raise
                print(f"Publisher: HTML caption rejected ({e}), sending as plain text")
                await self._send_media(media, strip_tags(text), None)
        else:
            # Too long for a caption: media first, then the text as a separate message
            await self._send_media(media, None, None)
            await self._send_text(text)

        print(f"Successfully published to {self.channel_id}")

    async def close(self):
        """Closes the bot session."""
        await self.bot.session.close()
