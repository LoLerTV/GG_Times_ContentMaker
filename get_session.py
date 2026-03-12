import asyncio
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import os
from dotenv import load_dotenv

load_dotenv()

api_id = os.getenv("TG_API_ID")
api_hash = os.getenv("TG_API_HASH")

if not api_id or not api_hash or api_id == "12345" or api_hash == "dummy_hash":
    print("Ошибка: Пожалуйста, сначала укажите правильные TG_API_ID и TG_API_HASH в файле .env")
    input("Нажмите Enter, чтобы выйти...")
    exit()

print("Создание сессии для аккаунта Telegram...")
with TelegramClient(StringSession(), int(api_id), api_hash) as client:
    print("\nУПЕШНАЯ АВТОРИЗАЦИЯ!")
    print("\nВаша строка сессии (TG_SESSION_STRING):")
    print("-" * 50)
    print(client.session.save())
    print("-" * 50)
    print("\nСкопируйте эту и строку и вставьте её как значение TG_SESSION_STRING в файл .env")
    input("\nНажмите Enter, чтобы выйти...")
