import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.schemas import (
    RoomCreate, RoomResponse, RoomWithMessages,
    RoomsListResponse, StandardResponse, MessageResponse
)
from redis_om.model.model import NotFoundError

from app.auth import get_current_user
from app.redis_model import Room, Message, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rooms", tags=["Rooms"])

@router.post("/", response_model=StandardResponse, status_code=status.HTTP_201_CREATED)
def create_room(room_data: RoomCreate, current_user: User = Depends(get_current_user)):
    try:
        try:
            existing_room = Room.find(Room.name == room_data.name).first()
        except NotFoundError:
            existing_room = None

        if existing_room:
            raise HTTPException(status_code=400, detail="Room with this name already exists")

        new_room = Room(
            name=room_data.name,
            description=room_data.description or "",
            created_by=current_user.id
        )
        new_room.save()

        room_response = RoomResponse(
            id=new_room.pk,
            name=new_room.name,
            description=new_room.description,
            created_by=new_room.created_by,
            created_at=new_room.created_at,
            message_count=0
        )

        return StandardResponse(
            message="Room created successfully",
            data={"room": room_response.dict()}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in create_room: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
@router.get("/{room_id}", response_model=RoomWithMessages)
def get_room(room_id: str, current_user: User = Depends(get_current_user)):
    """Get a room and its last 10 messages from Redis OM"""
    try:
        room = Room.get(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")

        # Fetch last 10 messages for this room, ordered by created_at descending
        messages = Message.find(Message.room_id == room_id).sort_by("-created_at").limit(10).all()

        message_responses = [
            MessageResponse(
                id=msg.pk,
                m_id=msg.m_id,
                content=msg.content,
                user_id=msg.user_id,
                room_id=msg.room_id,
                message_type=msg.message_type,
                username=msg.username if hasattr(msg, "username") else "AI Assistant",
                created_at=msg.created_at
            )
            for msg in reversed(messages)  # reverse to chronological order
        ]

        # Count messages for room (if needed)
        message_count = Message.find(Message.room_id == room_id).count()

        room_response = RoomResponse(
            id=room.pk,
            name=room.name,
            description=room.description,
            created_by=room.created_by,
            created_at=room.created_at,
            message_count=message_count
        )

        return RoomWithMessages(
            **room_response.dict(),
            messages=message_responses
        )
    except Exception:
        logger.exception("Error in get_room")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=RoomsListResponse)
def get_all_rooms(current_user: User = Depends(get_current_user)):
    """Get list of all rooms with message counts from Redis OM"""
    try:
        rooms = Room.find().sort_by("-created_at").all()

        rooms_response = []
        for room in rooms:
            count = Message.find(Message.room_id == room.pk).count()
            rooms_response.append(
                RoomResponse(
                    id=room.pk,
                    name=room.name,
                    description=room.description,
                    created_by=room.created_by,
                    created_at=room.created_at,
                    message_count=count
                ).dict()
            )

        return RoomsListResponse(rooms=rooms_response, count=len(rooms_response))

    except Exception:
        logger.exception("Error in get_all_rooms")
        raise HTTPException(status_code=500, detail="Internal server error")
