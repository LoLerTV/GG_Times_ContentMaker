from openai import AsyncOpenAI
from config import config

class EmbeddingClient:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

    async def get_embedding(self, text: str) -> list:
        """Get 768-dim embedding using text-embedding-3-small."""
        response = await self.client.embeddings.create(
            input=[text.replace("\n", " ")],
            model="text-embedding-3-small",
            dimensions=768
        )
        return response.data[0].embedding
