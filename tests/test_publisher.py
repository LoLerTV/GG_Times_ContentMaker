import asyncio
import os
from unittest.mock import AsyncMock, MagicMock

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("GEMINI_API_KEY", "test")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:" + "A" * 35)

from aiogram.exceptions import TelegramBadRequest
from distribution.publisher import TelegramPublisher


def make_publisher():
    publisher = TelegramPublisher()
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.send_photo = AsyncMock()
    bot.send_media_group = AsyncMock()
    publisher.bot = bot
    return publisher, bot


def photo(tmp_path, name="a.jpg"):
    path = tmp_path / name
    path.write_bytes(b"x")
    return {"path": str(path), "type": "photo", "has_spoiler": False}


def test_short_text_goes_into_caption(tmp_path):
    publisher, bot = make_publisher()
    asyncio.run(publisher.publish("<b>Новость", [photo(tmp_path)]))
    assert bot.send_photo.await_args.kwargs["caption"] == "<b>Новость</b>"
    bot.send_message.assert_not_awaited()


def test_long_text_sent_after_media(tmp_path):
    publisher, bot = make_publisher()
    asyncio.run(publisher.publish("слово " * 400, [photo(tmp_path, "a.jpg"), photo(tmp_path, "b.jpg")]))
    group = bot.send_media_group.await_args.kwargs["media"]
    assert group[0].caption is None
    bot.send_message.assert_awaited_once()


def test_missing_media_falls_back_to_text():
    publisher, bot = make_publisher()
    asyncio.run(publisher.publish("текст", [{"path": "/nonexistent.jpg", "type": "photo"}]))
    bot.send_photo.assert_not_awaited()
    bot.send_message.assert_awaited_once()


def test_parse_error_retries_as_plain_text():
    publisher, bot = make_publisher()
    bot.send_message.side_effect = [TelegramBadRequest(MagicMock(), "Bad Request: can't parse entities"), None]
    asyncio.run(publisher.publish("<b>текст</b>"))
    retry = bot.send_message.await_args_list[1].kwargs
    assert retry["text"] == "текст" and retry["parse_mode"] is None


def test_other_errors_propagate_for_retry():
    publisher, bot = make_publisher()
    bot.send_message.side_effect = TelegramBadRequest(MagicMock(), "Bad Request: chat not found")
    try:
        asyncio.run(publisher.publish("текст"))
        assert False, "expected exception"
    except TelegramBadRequest:
        pass
