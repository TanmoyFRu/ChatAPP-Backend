# app/services/tasks.py
import logging
import uuid
import asyncio
from typing import Optional, Any

from celery import Celery
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.core.config import settings
from app.models import Message, Room
from app.services.gemini_client import gemini_client

# cache helpers
from app.services.cache import (
    invalidate_room_messages_cache,
    invalidate_rooms_cache,
    get_cached_room_messages,
    set_cached_room_messages,
)

# Logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Create Celery instance
celery_app = Celery(
    "chat_api",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Optional Celery config (helpful defaults)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
)

# Database setup for Celery tasks
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _run_async(coro):
    """
    Run an async coroutine from sync context safely.
    Creates a new event loop to avoid interfering with any existing loop.
    """
    loop = None
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        if loop:
            try:
                loop.close()
            except Exception:
                pass


@celery_app.task(bind=True)
def process_message_with_ai(self, room_id: str, user_message_content: str, user_id: Optional[str] = None) -> bool:
    """
    Celery task:
      - loads recent messages for context,
      - calls Gemini to generate an AI reply,
      - saves the AI reply to the DB,
      - invalidates caches (best-effort) and updates cached messages if present.
    """
    db = SessionLocal()
    try:
        logger.info("process_message_with_ai: room_id=%s user_id=%s", room_id, user_id)

        # Validate room exists
        room = db.query(Room).filter(Room.id == room_id).first()
        if not room:
            logger.warning("Room not found: %s", room_id)
            return False

        # Load last N messages for context
        recent_messages = (
            db.query(Message)
            .filter(Message.room_id == room_id)
            .order_by(Message.created_at.desc())
            .limit(10)
            .all()
        )

        # Convert to conversation history expected by gemini_client
        conversation_history = []
        for msg in reversed(recent_messages):
            conversation_history.append({
                "content": msg.content,
                "username": msg.user.username if msg.user else "AI Assistant",
                "message_type": msg.message_type
            })

        # Call Gemini (async) in sync context
        try:
            ai_response_raw: Any = _run_async(
                gemini_client.generate_response(user_message_content, conversation_history)
            )
            # gemini_client may return a string or an object with .text
            if isinstance(ai_response_raw, str):
                ai_response_text = ai_response_raw
            elif hasattr(ai_response_raw, "text"):
                ai_response_text = getattr(ai_response_raw, "text") or str(ai_response_raw)
            else:
                ai_response_text = str(ai_response_raw)
        except Exception as e:
            logger.exception("Gemini call failed: %s", e)
            ai_response_text = "I'm experiencing technical difficulties. Please try again later."

        # Save AI response to DB
        ai_message = Message(
            m_id=str(uuid.uuid4()),
            content=ai_response_text,
            user_id=None,  # AI messages don't have a user_id
            room_id=room_id,
            message_type="ai"
        )

        db.add(ai_message)
        db.commit()
        db.refresh(ai_message)

        logger.info("Saved AI message %s for room %s", ai_message.id, room_id)

        # Invalidate caches so GET endpoints reflect new messages (best-effort)
        try:
            invalidate_room_messages_cache(room_id)
        except Exception as e:
            logger.warning("invalidate_room_messages_cache failed: %s", e)

        try:
            invalidate_rooms_cache()
        except Exception as e:
            logger.warning("invalidate_rooms_cache failed: %s", e)

        # Optionally update cached messages list (if exists) to reduce staleness
        try:
            cached = get_cached_room_messages(room_id)
            if isinstance(cached, list):
                new_item = {
                    "id": ai_message.id,
                    "m_id": ai_message.m_id,
                    "content": ai_message.content,
                    "user_id": ai_message.user_id,
                    "room_id": ai_message.room_id,
                    "message_type": ai_message.message_type,
                    "username": "AI Assistant",
                    "created_at": str(ai_message.created_at)
                }
                # prepend (most-recent-first) and trim
                updated = [new_item] + cached
                updated = updated[:50]
                set_cached_room_messages(room_id, updated)
        except Exception:
            logger.debug("Failed to update cached room messages directly", exc_info=True)

        return True

    except Exception as exc:
        logger.exception("Error in process_message_with_ai: %s", exc)
        db.rollback()
        return False
    finally:
        db.close()
