import asyncio
import signal
from ingestion.telegram import TelegramIngestor
from processing.embeddings import EmbeddingClient
from processing.deduplicator import Deduplicator
from processing.llm_router import LLMRouter
from distribution.publisher import TelegramPublisher
from db.session import AsyncSessionLocal
from db.models import RawContent, ProcessedContent
from config import config

class ContentFactory:
    def __init__(self):
        self.raw_queue = asyncio.Queue()
        self.embedder = EmbeddingClient()
        self.deduper = Deduplicator()
        self.llm = LLMRouter()
        self.publisher = TelegramPublisher()

    async def process_worker(self):
        print("Processing worker started.")
        while True:
            item = await self.raw_queue.get()
            try:
                text = item["text"]
                media_files = item.get("media", [])
                embedding = await self.embedder.get_embedding(text)
                
                if await self.deduper.is_duplicate(text, embedding):
                    print(f"Skipping duplicate: {item['external_id']}")
                    continue

                # AI Rewrite
                rewrite_result = await self.llm.rewrite(text)
                if not rewrite_result:
                    print(f"Failed to rewrite or parse AI output for: {item['external_id']}")
                    continue

                is_relevant = rewrite_result.get("is_relevant")
                rewritten = rewrite_result.get("text", "").strip()

                if not is_relevant or not rewritten:
                    print(f"Skipping irrelevant/empty post: {item['external_id']}")
                    continue

                # Store in DB
                async with AsyncSessionLocal() as session:
                    raw = RawContent(
                        external_id=item["external_id"],
                        source_id=1, # Should be looked up from sources table
                        raw_text=text,
                        media_urls=media_files,
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
                
                print(f"Content processed and saved (relevant): {item['external_id']}")
                
                # Publish the rewritten content
                published = await self.publisher.publish(rewritten, media_files)
                if published:
                    # Additional DB updates or logs can go here
                    print(f"Successfully published {item['external_id']} to channel.")

            except Exception as e:
                print(f"Error in process_worker: {e}")
            finally:
                self.raw_queue.task_done()

    async def run(self):
        tg_ingestor = TelegramIngestor(self.raw_queue)
        
        # Run workers
        try:
            await asyncio.gather(
                tg_ingestor.start(),
                self.process_worker()
            )
        finally:
            await self.publisher.close()

if __name__ == "__main__":
    factory = ContentFactory()
    try:
        asyncio.run(factory.run())
    except KeyboardInterrupt:
        pass
