# app/routes/chat.py
import os
import uuid
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import httpx

from app.database import get_db
from app.models import User, Room, Message
from app.schemas import MessageCreate, MessageResponse, StandardResponse
from app.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rooms/{room_id}/messages", tags=["Messages"])

# Read configuration from environment
GEMINI_API_URL = os.getenv(
    "GEMINI_API_URL",
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # must be set in env for API-key flow
AI_USER_ID = os.getenv("AI_USER_ID")  # optional DB user id to attribute AI messages to


async def call_gemini_api(user_message: str, room_id: str, user_id: str) -> str:
    """
    Call Gemini using API key (AI Studio / Generative Language REST).
    Expects GEMINI_API_KEY environment variable to be set.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set")

    # Build request URL with key param
    url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"

    # Payload shape using 'contents' -> 'parts' -> 'text' (per REST examples)
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": user_message}
                ]
            }
        ],
        # optional tuning parameters
        "temperature": 0.2,
        "maxOutputTokens": 512
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.exception("Gemini API returned HTTP error")
        # include some detail but don't leak secrets
        raise RuntimeError(f"Gemini API HTTP error: {e.response.status_code}") from e
    except Exception as e:
        logger.exception("Error calling Gemini API")
        raise

    # Defensive parsing for common shapes returned by the API
    # Example shapes: {"candidates":[{"content":"..."}]}, {"outputs":[{"content":"..."}]}, nested content, etc.
    if isinstance(data, dict):
        # Try candidates/outputs first
        for list_key in ("candidates", "outputs", "output"):
            lst = data.get(list_key)
            if isinstance(lst, list) and lst:
                first = lst[0]
                if isinstance(first, dict):
                    return first.get("content") or first.get("text") or first.get("output") or str(first)
                return str(first)

        # Some responses include 'content' directly or other fallback keys
        for key in ("content", "generated_text", "response", "text"):
            if key in data:
                return data[key]

        # Sometimes the response contains nested structure like: {'candidates': [{'message': {'content': ...}}]}
        # Try to find any string in nested dict
        def find_first_string(v):
            if isinstance(v, str):
                return v
            if isinstance(v, dict):
                for vv in v.values():
                    res = find_first_string(vv)
                    if res:
                        return res
            if isinstance(v, list):
                for item in v:
                    res = find_first_string(item)
                    if res:
                        return res
            return None

        nested = find_first_string(data)
        if nested:
            return nested

    # final fallback
    return "Sorry, I could not generate a reply."


@router.post("", response_model=StandardResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    room_id: str,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validate room existence
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    # Save user message
    user_message = Message(
        m_id=str(uuid.uuid4()),
        content=message_data.content,
        user_id=current_user.id,
        room_id=room_id,
        message_type="user"
    )
    try:
        db.add(user_message)
        db.commit()
        db.refresh(user_message)
    except Exception:
        db.rollback()
        logger.exception("Failed to save user message")
        raise HTTPException(status_code=500, detail="Could not save message")

    # Call Gemini API to get AI response
    try:
        ai_response_content = await call_gemini_api(message_data.content, room_id, current_user.id)
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        ai_response_content = "Sorry, I couldn't generate a response at the moment."

    # Save AI message (optionally attribute to a configured AI user)
    ai_user_id_to_use: Optional[str] = AI_USER_ID or None
    ai_message = Message(
        m_id=str(uuid.uuid4()),
        content=ai_response_content,
        user_id=ai_user_id_to_use,
        room_id=room_id,
        message_type="ai"
    )
    try:
        db.add(ai_message)
        db.commit()
        db.refresh(ai_message)
    except Exception:
        db.rollback()
        logger.exception("Failed to save AI message")

    # Prepare response dict with both messages
    message_response = {
        "user_message": {
            "id": user_message.id,
            "m_id": user_message.m_id,
            "content": user_message.content,
            "user_id": user_message.user_id,
            "room_id": user_message.room_id,
            "message_type": user_message.message_type,
            "username": current_user.username,
            "created_at": user_message.created_at
        },
        "ai_message": {
            "id": ai_message.id,
            "m_id": ai_message.m_id,
            "content": ai_message.content,
            "user_id": ai_message.user_id,
            "room_id": ai_message.room_id,
            "message_type": ai_message.message_type,
            "username": "AI Assistant",
            "created_at": ai_message.created_at
        }
    }

    return StandardResponse(message="Messages sent successfully", data={"messages": message_response})


@router.get("", response_model=List[MessageResponse])
def get_room_messages(
    room_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get last messages for a room, most recent first
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    messages = (
        db.query(Message)
        .filter(Message.room_id == room_id)
        .order_by(Message.created_at.desc())
        .limit(50)
        .all()
    )

    return [
        MessageResponse(
            id=m.id,
            m_id=m.m_id,
            content=m.content,
            user_id=m.user_id,
            room_id=m.room_id,
            message_type=m.message_type,
            username=m.user.username if m.user else "AI Assistant",
            created_at=m.created_at
        ) for m in messages
    ]
