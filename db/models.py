import uuid
from datetime import datetime
from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Column, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(20))  # 'tg' or 'reddit'
    target_id: Mapped[str] = mapped_column(String(255))
    priority: Mapped[int] = mapped_column(default=0)


class RawContent(Base):
    __tablename__ = "raw_content"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    external_id: Mapped[str] = mapped_column(String(255), unique=True)
    raw_text: Mapped[str] = mapped_column(Text)
    media_urls: Mapped[dict] = mapped_column(JSONB, default=list)
    embedding: Mapped[Vector] = mapped_column(Vector(768))  # text-embedding-3-small
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ProcessedContent(Base):
    __tablename__ = "processed_content"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("raw_content.id"))
    final_text: Mapped[str] = mapped_column(Text)
    # ready -> published | failed (after PUBLISH_MAX_ATTEMPTS); rejected = filtered out by the LLM
    status: Mapped[str] = mapped_column(String(20), default="ready", index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    attempts: Mapped[int] = mapped_column(default=0, server_default="0")
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    content: Mapped["RawContent"] = relationship()
