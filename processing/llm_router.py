import asyncio
import json
from typing import Optional
from openai import AsyncOpenAI
from google import genai
from google.genai import types
from config import config

class LLMRouter:
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        self.gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
        
        self.prompt = (
            "Ты — дерзкий редактор русскоязычного Telegram-канала об игровой индустрии. Оцени, является ли текст крутой новостью про игры (НЕ реклама, НЕ сухой патчноут, НЕ унылое размышление).\n"
            "Если новость РЕЛЕВАНТНАЯ — сделай рерайт по следующим СТРОГИМ правилам:\n"
            "1. ЭМОДЗИ И ЗАГОЛОВОК: Заголовок начать строго БЕЗ ЭМОДЗИ. Внутри текста добавляй эмодзи для разнообразия и живости, но в меру! Не повторяй одинаковые паттерны (не ставь эмодзи в конце каждого абзаца монотонно), делай текст разнообразным, но не слишком пестрым. Важные названия выделяй HTML-тегом <b>: <b>Название</b>.\n"
            "2. СТРУКТУРА И АБЗАЦЫ: Дели текст на 2-4 коротких блока через пустую строку (двойной перенос `\\n\\n`).\n"
            "3. СПИСКИ И ЦИТАТЫ: Если в новости идет перечисление более чем 4-х позиций (например, список игр), ОБЯЗАТЕЛЬНО оборачивай весь этот список в тег перекидной цитаты <blockquote expandable>пункты списка...</blockquote>.\n"
            "4. ТОНАЛЬНОСТЬ: Забудь про канцелярщину. Пиши как геймер для геймеров: кратко, по факту, используя сленг ('завезли', 'апскейлер', 'тайтл', 'слив', 'кряк', 'патч'). Текст должен читаться легко.\n"
            "5. ЦИФРЫ И ФАКТЫ: Всегда оставляй конкретику (даты, деньги, количество скачиваний, терафлопсы).\n"
            "6. HTML И СПОЙЛЕРЫ: Сохраняй теги <tg-spoiler>текст</tg-spoiler>. ВЕСЬ текст должен быть совместим с HTML-разметкой Telegram.\n"
            "7. МУСОР: Никаких ссылок, хештегов или призывов подписаться.\n"
            "8. ДЛИНА: Не больше 900 символов вместе с пробелами — текст должен влезть в подпись к фото.\n"
            "Примеры идеального форматирования:\n"
            "— «<b>Crimson Desert</b> официально завезёт три режима графики на <b>PS5</b>... 🎮\n\n"
            "Настраивать картинку можно будет под себя: упор на качество или на стабильную частоту кадров.\n\n"
            "Релиз обещает раскрыть весь потенциал консолей от Sony.»\n"
            "Верни ответ СТРОГО в валидном JSON: {\"is_relevant\": true/false, \"text\": \"переписанный текст с переносями строк \\n\\n\"}."
        )

    def _parse_json_response(self, text: str) -> Optional[dict]:
        try:
            # Simple cleanup just in case there are markdown code blocks
            clean_text = text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            return json.loads(clean_text)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e} - Raw text: {text}")
            return None

    async def rewrite(self, text: str) -> Optional[dict]:
        # Try OpenAI (gpt-4o-mini by default)
        try:
            response = await asyncio.wait_for(
                self.openai_client.chat.completions.create(
                    model=config.OPENAI_MODEL,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": self.prompt},
                        {"role": "user", "content": text}
                    ]
                ),
                timeout=config.LLM_TIMEOUT
            )
            content = response.choices[0].message.content
            parsed = self._parse_json_response(content)
            if parsed is not None:
                return parsed
            print("Failed to parse OpenAI JSON response. Falling back to Gemini...")
        except Exception as e:
            print(f"OpenAI error or timeout: {e}. Falling back to Gemini...")
            
        # Fallback to Gemini
        try:
            response = await asyncio.wait_for(
                self.gemini_client.aio.models.generate_content(
                    model=config.GEMINI_MODEL,
                    contents=f"Новость:\n{text}",
                    config=types.GenerateContentConfig(
                        system_instruction=self.prompt,
                        response_mime_type="application/json",
                    ),
                ),
                timeout=config.LLM_TIMEOUT
            )
            return self._parse_json_response(response.text or "")
        except Exception as e:
            print(f"Gemini error: {e}")
            return None
