import asyncio
import signal
from ingestion.telegram import TelegramIngestor
from processing.embeddings import EmbeddingClient
from processing.deduplicator import Deduplicator
from processing.llm_router import LLMRouter
from db.session import AsyncSessionLocal
from db.models import RawContent, ProcessedContent
from config import config

class ContentFactory:
    def __init__(self):
        self.raw_queue = asyncio.Queue()
        self.embedder = EmbeddingClient()
        self.deduper = Deduplicator()
        self.llm = LLMRouter()

    async def process_worker(self):
        print("Processing worker started.")
        while True:
            item = await self.raw_queue.get()
            try:
                text = item["text"]
                embedding = await self.embedder.get_embedding(text)
                
                if await self.deduper.is_duplicate(text, embedding):
                    print(f"Skipping duplicate: {item['external_id']}")
                    continue

                # AI Rewrite
                rewritten = await self.llm.rewrite(text)
                if not rewritten:
                    continue

                # Store in DB
                async with AsyncSessionLocal() as session:
                    raw = RawContent(
                        external_id=item["external_id"],
                        source_id=1, # Should be looked up from sources table
                        raw_text=text,
                        embedding=embedding
                    )
                    session.add(raw)
                    await session.flush()
                    
                    processed = ProcessedContent(
                        parent_id=raw.id,
                        final_text=rewritten,
                        status="pending"
                    )
                    session.add(processed)
                    await session.commit()
                
                print(f"Content processed and saved: {item['external_id']}")
                # Here you would trigger publication/distribution

            except Exception as e:
                print(f"Error in process_worker: {e}")
            finally:
                self.raw_queue.task_done()

    async def run(self):
        tg_ingestor = TelegramIngestor(self.raw_queue)
        
        # Run workers
        await asyncio.gather(
            tg_ingestor.start(),
            self.process_worker()
        )

if __name__ == "__main__":
    factory = ContentFactory()
    try:
        asyncio.run(factory.run())
    except KeyboardInterrupt:
        pass
