import logging
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas import MessageCreate, MessageResponse, StandardResponse
from app.auth import get_current_user
from app.redis_model import Room, Message, User  # Redis OM models
from app.services.gemini_client import gemini_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rooms/{room_id}/messages", tags=["Messages"])

AI_USER_ID = None  # or set your AI user id if needed


@router.post("", response_model=StandardResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    room_id: str,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
):

    # Validate room existence via Redis OM
    room = Room.get(room_id)
    if not room:
        logger.warning(f"Room {room_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    # Save user's message
    user_message = Message(
        content=message_data.content,
        user_id=current_user.pk,
        room_id=room_id,
        message_type="user"
    )
    user_message.save()
    logger.debug(f"User message saved: {user_message.pk}")

    # Retrieve last 10 messages for AI context (ordered ascending)
    try:
        # Avoid Redis OM chain that caused 'int is not callable' by sorting in Python
        history = list(Message.find(Message.room_id == room_id).all())
        history.sort(key=lambda m: m.created_at)
        conversation_history = history[-10:]
    except Exception as e:
        logger.exception(f"Failed to fetch conversation history: {e}")
        conversation_history = []

    history_data = [
        {"username": "User" if msg.user_id else "AI Assistant", "content": msg.content}
        for msg in conversation_history
    ]

    # Get AI response
    try:
        ai_response_content = await gemini_client.generate_response(
            message=message_data.content,
            conversation_history=history_data
        )
        if isinstance(ai_response_content, dict):
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

    # Save AI message
    ai_message = Message(
        content=ai_response_content,
        user_id=AI_USER_ID,
        room_id=room_id,
        message_type="ai"
    )
    ai_message.save()
    logger.debug(f"AI message saved: {ai_message.pk}")

    return StandardResponse(
        message="Messages sent successfully",
        data={
            "messages": {
                "user_message": {
                    "id": user_message.pk,
                    "content": user_message.content,
                    "user_id": user_message.user_id,
                    "room_id": user_message.room_id,
                    "message_type": user_message.message_type,
                    "created_at": user_message.created_at,
                },
                "ai_message": {
                    "id": ai_message.pk,
                    "content": ai_message.content,
                    "user_id": ai_message.user_id,
                    "room_id": ai_message.room_id,
                    "message_type": ai_message.message_type,
                    "username": "AI Assistant",
                    "created_at": ai_message.created_at,
                }
            }
        }
    )


@router.get("", response_model=List[MessageResponse])
def get_room_messages(
    room_id: str,
    current_user: User = Depends(get_current_user)
):

    logger.info(f"Fetching messages for room {room_id}")

    room = Room.get(room_id)
    if not room:
        logger.warning(f"Room {room_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    print(f"ROOM ID :: {room_id}")
    try:
        messages = Message.find(Message.room_id == room_id).sort_by("-created_at").limit(50).all()
        print(f"MESSAGES :: {messages}")
    except:
        messages = []
    # Reverse for chronological order if you want oldest first
    messages = list(reversed(messages))

    return [
        MessageResponse(
            id=msg.pk,
            m_id=msg.m_id if hasattr(msg, "m_id") else "",
            content=msg.content,
            user_id=msg.user_id,
            room_id=msg.room_id,
            message_type=msg.message_type,
            username="AI Assistant" if not msg.user_id else "User",  # or resolve actual username if stored
            created_at=msg.created_at
        )
        for msg in messages
    ]
