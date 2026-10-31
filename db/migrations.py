import asyncio
from sqlalchemy import text
from db.session import engine, AsyncSessionLocal
from db.models import Base, Source

async def init_db():
    async with engine.begin() as conn:
        # Enable pgvector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        # create_all does not touch existing tables, so add columns introduced later by hand
        for ddl in (
            "ALTER TABLE processed_content ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE processed_content ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMP",
            "ALTER TABLE processed_content ADD COLUMN IF NOT EXISTS last_error TEXT",
            "ALTER TABLE processed_content ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT now()",
            "ALTER TABLE processed_content ADD COLUMN IF NOT EXISTS published_at TIMESTAMP",
            "CREATE INDEX IF NOT EXISTS ix_processed_content_status ON processed_content (status)",
            # Rows from the old version were published inline and never got a status update
            "UPDATE processed_content SET status = 'legacy' WHERE status = 'pending'",
        ):
            await conn.execute(text(ddl))
    
    # Add an empty source with id=1 if it doesn't exist
    async with AsyncSessionLocal() as session:
        try:
            # Check if source with ID=1 exists
            source = await session.get(Source, 1)
            if not source:
                default_source = Source(id=1, platform="tg", target_id="default_source_fallback")
                session.add(default_source)
                await session.commit()
                print("Default Source (id=1) added to the database.")
        except Exception as e:
            await session.rollback()
            print(f"Error seeding source: {e}")

    print("Database initialized successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())
