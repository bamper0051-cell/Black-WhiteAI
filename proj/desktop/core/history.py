"""
Chat history — SQLite storage via SQLAlchemy sync.
Stores conversations per session with full message history.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Column, DateTime, Integer, String, Text, create_engine, desc, select
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from core.config import DB_PATH


class Base(DeclarativeBase):
    pass


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(256), nullable=False, default="New Chat")
    provider = Column(String(32), default="local")
    model = Column(String(128), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(36), nullable=False, index=True)
    role = Column(String(16), nullable=False)  # user | assistant | system
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
    echo=False,
)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class HistoryManager:
    """Thread-safe chat history manager."""

    def new_conversation(self, title: str = "New Chat", provider: str = "local", model: str = "") -> str:
        with Session(engine) as s:
            conv = Conversation(
                id=str(uuid.uuid4()),
                title=title,
                provider=provider,
                model=model,
            )
            s.add(conv)
            s.commit()
            return conv.id

    def save_message(self, conversation_id: str, role: str, content: str) -> None:
        with Session(engine) as s:
            msg = Message(conversation_id=conversation_id, role=role, content=content)
            s.add(msg)
            # Update conversation timestamp
            conv = s.get(Conversation, conversation_id)
            if conv:
                conv.updated_at = datetime.utcnow()
                # Auto-title from first user message
                if role == "user" and conv.title == "New Chat":
                    conv.title = content[:60].replace("\n", " ") + ("..." if len(content) > 60 else "")
            s.commit()

    def get_messages(self, conversation_id: str) -> list[dict]:
        with Session(engine) as s:
            msgs = s.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at)
            ).scalars().all()
            return [{"role": m.role, "content": m.content} for m in msgs]

    def list_conversations(self, limit: int = 50) -> list[dict]:
        with Session(engine) as s:
            convs = s.execute(
                select(Conversation)
                .order_by(desc(Conversation.updated_at))
                .limit(limit)
            ).scalars().all()
            return [
                {
                    "id": c.id,
                    "title": c.title,
                    "provider": c.provider,
                    "model": c.model,
                    "updated_at": c.updated_at,
                }
                for c in convs
            ]

    def delete_conversation(self, conversation_id: str) -> None:
        with Session(engine) as s:
            s.execute(
                Message.__table__.delete().where(Message.conversation_id == conversation_id)
            )
            conv = s.get(Conversation, conversation_id)
            if conv:
                s.delete(conv)
            s.commit()

    def clear_messages(self, conversation_id: str) -> None:
        with Session(engine) as s:
            s.execute(
                Message.__table__.delete().where(Message.conversation_id == conversation_id)
            )
            s.commit()

    def rename_conversation(self, conversation_id: str, title: str) -> None:
        with Session(engine) as s:
            conv = s.get(Conversation, conversation_id)
            if conv:
                conv.title = title[:256]
                s.commit()


history_manager = HistoryManager()
