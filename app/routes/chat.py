import os
import uuid
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Room, Message
from app.schemas import MessageCreate, MessageResponse, StandardResponse
from app.auth import get_current_user
from app.services.gemini_client import gemini_client
import json
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rooms/{room_id}/messages", tags=["Messages"])

AI_USER_ID = os.getenv("AI_USER_ID")  # optional DB user id to attribute AI messages to


@router.post("", response_model=StandardResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    room_id: str,
    message_data: MessageCreate,
    # current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Save user message, get AI response from Gemini, save AI message, return both.
    """
    # logger.info(f"User {current_user.id} sending message to room {room_id}")

    # Validate room existence
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        logger.warning(f"Room {room_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    # Save user's message
    user_message = Message(
        m_id=str(uuid.uuid4()),
        content=message_data.content,
        user_id="testuser_1827",
        room_id=room_id,
        message_type="user"
    )
    try:
        db.add(user_message)
        db.commit()
        db.refresh(user_message)
        logger.debug(f"User message saved: {user_message.m_id}")
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to save user message: {e}")
        raise HTTPException(status_code=500, detail="Could not save message")

    # Retrieve last 10 messages for AI context
    conversation_history = (
        db.query(Message)
        .filter(Message.room_id == room_id)
        .order_by(Message.created_at.asc())
        .limit(10)
        .all()
    )
    history_data = [
        {"username": m.user.username if m.user else "AI Assistant", "content": m.content}
        for m in conversation_history
    ]

    # Get AI response
    ai_response_content = None
    try:
        ai_response_content = await gemini_client.generate_response(
            message=message_data.content,
            conversation_history=history_data
        )
        print(f"AI Response: {ai_response_content}")

        # If ai_response_content is a dict (like your Gemini raw response)
        if isinstance(ai_response_content, dict):
            # Extract the plain text safely
            parts = ai_response_content.get("parts")
            if parts and isinstance(parts, list) and parts[0].get("text", "").strip():
                ai_response_content = parts[0]["text"].strip()
            else:
                ai_response_content = "I'm sorry, I couldn't process that."
        else:
            if not ai_response_content or not ai_response_content.strip():
                ai_response_content = "I'm sorry, I couldn't process that."

        logger.debug(f"AI Response (text only): {ai_response_content}")

    except Exception as e:
        logger.exception(f"AI response generation failed: {e}")
        ai_response_content = "There was an error generating a response."

    # Save AI's message with plain text content, no JSON string
    ai_message = Message(
        m_id=str(uuid.uuid4()),
        content=ai_response_content,  # store plain text only
        user_id=AI_USER_ID or None,
        room_id=room_id,
        message_type="ai"
    )

    try:
        db.add(ai_message)
        db.commit()
        db.refresh(ai_message)
        logger.debug(f"AI message saved: {ai_message.m_id}")
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to save AI message: {e}")

    return StandardResponse(
        message="Messages sent successfully",
        data={
            "messages": {
                "user_message": {
                    "id": user_message.id,
                    "m_id": user_message.m_id,
                    "content": user_message.content,
                    "user_id": user_message.user_id,
                    "room_id": user_message.room_id,
                    "message_type": user_message.message_type,
                    # "username": current_user.username,
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
        }
    )


@router.get("", response_model=List[MessageResponse])
def get_room_messages(
    room_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get last 50 messages from a room.
    """
    logger.info(f"Fetching messages for room {room_id}")

    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        logger.warning(f"Room {room_id} not found.")
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
        )
        for m in messages
    ]
