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
            return True
        
        # L2: Vector search in PostgreSQL
        async with AsyncSessionLocal() as session:
            # Using cosine distance (<=> operator in SQL)
            stmt = select(RawContent.id).filter(
                RawContent.embedding.cosine_distance(embedding) < config.DEDUPLICATION_THRESHOLD
            ).limit(1)
            
            result = await session.execute(stmt)
            exists = result.scalar_one_or_none() is not None
            
            if not exists:
                self.l1_cache.add(h)
                # Keep cache size manageable
                if len(self.l1_cache) > 10000:
                    self.l1_cache.pop()
                    
            return exists
