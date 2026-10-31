import asyncio
import hashlib
from typing import Optional
from sqlalchemy import select
from pgvector.sqlalchemy import Vector
from db.models import RawContent
from db.session import AsyncSessionLocal
from config import config

class Deduplicator:
    def __init__(self):
        self.l1_cache = set()  # In-memory MD5 cache

    def _get_hash(self, text: str) -> str:
        """Normalized text MD5 hash."""
        normalized = "".join(text.lower().split())
        return hashlib.md5(normalized.encode()).hexdigest()

    async def is_duplicate(self, text: str, embedding: list) -> bool:
        # L1: In-memory hash check
        h = self._get_hash(text)
        if h in self.l1_cache:
            print(f"Deduplicator: L1 Cache hit (exact text match) for {h}")
            return True
        
        # L2: Vector search in PostgreSQL
        async with AsyncSessionLocal() as session:
            # Vector search
            stmt = select(
                RawContent.id,
                RawContent.embedding.cosine_distance(embedding).label("dist")
            ).order_by("dist").limit(1)
            
            result = await session.execute(stmt)
            match = result.first()
            
            if match:
                distance = float(match.dist)
                is_dupe = distance < config.DEDUPLICATION_THRESHOLD
                print(f"Deduplicator: Closest match found. Distance: {distance:.4f} (Threshold: {config.DEDUPLICATION_THRESHOLD})")
                if is_dupe:
                    print(f"Deduplicator: MATCH! Distance {distance:.4f} < {config.DEDUPLICATION_THRESHOLD}. Blocking as duplicate.")
                    return True
            else:
                print("Deduplicator: Database is empty or no similar messages found.")

        # If we reached here, it's not a duplicate (or didn't meet threshold)
        return False

    def remember(self, text: str):
        """Adds text to the in-memory cache. Called only once the post is saved, so failed posts can be retried."""
        self.l1_cache.add(self._get_hash(text))
        if len(self.l1_cache) > 10000:
            self.l1_cache.pop()
