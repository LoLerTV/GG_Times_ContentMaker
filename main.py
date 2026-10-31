import asyncio
import os
from datetime import timedelta
from aiogram.exceptions import TelegramRetryAfter
from sqlalchemy import exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from ingestion.telegram import TelegramIngestor
from processing.embeddings import EmbeddingClient
from processing.deduplicator import Deduplicator
from processing.llm_router import LLMRouter
from distribution.publisher import TelegramPublisher
from db.session import AsyncSessionLocal
from db.models import RawContent, ProcessedContent
from config import config


def cleanup_media(media_files: list):
    """Deletes downloaded media once a post no longer needs it."""
    for item in media_files or []:
        path = item.get("path")
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError as e:
                print(f"Failed to delete media {path}: {e}")


class ContentFactory:
    def __init__(self):
        self.raw_queue = asyncio.Queue()
        self.embedder = EmbeddingClient()
        self.deduper = Deduplicator()
        self.llm = LLMRouter()
        self.publisher = TelegramPublisher()

    async def _already_ingested(self, external_id: str) -> bool:
        async with AsyncSessionLocal() as session:
            return await session.scalar(select(exists().where(RawContent.external_id == external_id)))

    async def _save(self, item: dict, embedding: list, final_text: str, status: str):
        async with AsyncSessionLocal() as session:
            raw = RawContent(
                external_id=item["external_id"],
                source_id=1, # Should be looked up from sources table
                raw_text=item["text"],
                media_urls=item.get("media", []),
                embedding=embedding
            )
            session.add(raw)
            await session.flush()

            session.add(ProcessedContent(
                parent_id=raw.id,
                final_text=final_text,
                status=status
            ))
            await session.commit()

    async def process_worker(self):
        print("Processing worker started.")
        while True:
            item = await self.raw_queue.get()
            media_files = item.get("media", [])
            keep_media = False
            try:
                text = item["text"]
                if await self._already_ingested(item["external_id"]):
                    print(f"Skipping already ingested: {item['external_id']}")
                    continue

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
                rewritten = (rewrite_result.get("text") or "").strip()

                if not is_relevant or not rewritten:
                    # Saved as rejected so reposts of the same ad/noise are caught by the deduplicator
                    await self._save(item, embedding, rewritten, "rejected")
                    self.deduper.remember(text)
                    print(f"Skipping irrelevant/empty post: {item['external_id']}")
                    continue

                # Publishing happens in publish_worker, so the post survives restarts and failed sends
                await self._save(item, embedding, rewritten, "ready")
                self.deduper.remember(text)
                keep_media = True
                print(f"Content processed and queued for publishing: {item['external_id']}")

            except IntegrityError:
                print(f"Skipping already ingested (race): {item['external_id']}")
            except Exception as e:
                print(f"Error in process_worker: {e}")
            finally:
                if not keep_media:
                    cleanup_media(media_files)
                self.raw_queue.task_done()

    async def _publish_next(self) -> bool:
        """Publishes one post that is due. Returns False when there is nothing to publish."""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(ProcessedContent, RawContent)
                .join(RawContent, ProcessedContent.parent_id == RawContent.id)
                .where(
                    ProcessedContent.status == "ready",
                    or_(ProcessedContent.next_attempt_at.is_(None), ProcessedContent.next_attempt_at <= func.now()),
                )
                .order_by(ProcessedContent.created_at)
                .limit(1)
                .with_for_update(of=ProcessedContent, skip_locked=True)
            )
            row = (await session.execute(stmt)).first()
            if not row:
                return False
            post, raw = row

            try:
                await self.publisher.publish(post.final_text, raw.media_urls)
                post.status = "published"
                post.published_at = func.now()
                post.last_error = None
                print(f"Successfully published {raw.external_id} to channel.")
            except TelegramRetryAfter as e:
                # Flood control is not the post's fault: wait as told without spending an attempt
                post.next_attempt_at = func.now() + timedelta(seconds=e.retry_after)
                print(f"Flood control, retrying {raw.external_id} in {e.retry_after}s")
            except Exception as e:
                post.attempts += 1
                post.last_error = str(e)[:2000]
                if post.attempts >= config.PUBLISH_MAX_ATTEMPTS:
                    post.status = "failed"
                    print(f"Giving up on {raw.external_id} after {post.attempts} attempts: {e}")
                else:
                    delay = min(config.PUBLISH_RETRY_BASE * 2 ** (post.attempts - 1), 3600)
                    post.next_attempt_at = func.now() + timedelta(seconds=delay)
                    print(f"Failed to publish {raw.external_id} (attempt {post.attempts}), retrying in {delay}s: {e}")

            await session.commit()
            if post.status in ("published", "failed"):
                cleanup_media(raw.media_urls)
            return True

    async def publish_worker(self):
        print("Publishing worker started.")
        while True:
            try:
                if await self._publish_next():
                    continue
            except Exception as e:
                print(f"Error in publish_worker: {e}")
            await asyncio.sleep(config.PUBLISH_POLL_INTERVAL)

    async def run(self):
        tg_ingestor = TelegramIngestor(self.raw_queue)

        # Run workers
        try:
            await asyncio.gather(
                tg_ingestor.start(),
                self.process_worker(),
                self.publish_worker()
            )
        finally:
            await self.publisher.close()

if __name__ == "__main__":
    factory = ContentFactory()
    try:
        asyncio.run(factory.run())
    except KeyboardInterrupt:
        pass
