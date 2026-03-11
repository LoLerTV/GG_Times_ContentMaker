import asyncio
from openai import AsyncOpenAI
from google import generativeai as genai
from config import config

class LLMRouter:
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        
        self.prompt = (
            "Ты — опытный игровой журналист. Твоя задача — сделать качественный рерайт новости. "
            "Стиль: профессиональный, увлекательный, без лишней воды. "
            "Язык: Русский. Сохрани все важные детали и цифры."
        )

    async def rewrite(self, text: str) -> Optional[str]:
        # Try GPT-4o-mini
        try:
            response = await asyncio.wait_for(
                self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": self.prompt},
                        {"role": "user", "content": text}
                    ]
                ),
                timeout=config.LLM_TIMEOUT
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI error or timeout: {e}. Falling back to Gemini...")
            
        # Fallback to Gemini 1.5 Flash
        try:
            response = await self.gemini_model.generate_content_async(
                f"{self.prompt}\n\nНовость для рерайта:\n{text}"
            )
            return response.text
        except Exception as e:
            print(f"Gemini error: {e}")
            return None
