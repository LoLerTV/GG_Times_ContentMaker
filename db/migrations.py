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
