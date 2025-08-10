# app/routes/rooms.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from app.database import get_db
from app.models import User, Room, Message
from app.schemas import (
    RoomCreate, RoomResponse, RoomWithMessages,
    RoomsListResponse, StandardResponse, MessageResponse
)
from app.auth import get_current_user
from app.services.cache import (
    get_cached_rooms, set_cached_rooms, invalidate_rooms_cache,
    get_cached_room, set_cached_room
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rooms", tags=["Rooms"])


@router.post("/", response_model=StandardResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    room_data: RoomCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new room"""
    try:
        room = Room(
            name=room_data.name,
            description=room_data.description or "",
            created_by=current_user.id
        )
        db.add(room)
        db.commit()
        db.refresh(room)

        # Invalidate rooms cache after adding new room
        try:
            invalidate_rooms_cache()
        except Exception:
            # cache functions are resilient, but just in case
            logger.exception("Failed to invalidate rooms cache")

        room_response = RoomResponse.from_orm(room)
        room_response.message_count = 0

        return StandardResponse(
            message="Room created successfully",
            data={"room": room_response.dict()}
        )

    except Exception as e:
        db.rollback()
        logger.exception("Error in create_room")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{room_id}", response_model=RoomWithMessages)
async def get_room(
    room_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a single room with last 10 messages"""
    try:
        # 1. Try cache first
        cached_room = get_cached_room(room_id)
        if cached_room:
            return RoomWithMessages(**cached_room)

        # 2. Query DB
        room = db.query(Room).filter(Room.id == room_id).first()
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")

        messages = (
            db.query(Message)
            .filter(Message.room_id == room_id)
            .order_by(Message.created_at.desc())
            .limit(10)
            .all()
        )

        room_response = RoomResponse.from_orm(room)
        room_response.message_count = len(room.messages)

        message_responses = [
            MessageResponse(
                id=msg.id,
                m_id=msg.m_id,
                content=msg.content,
                user_id=msg.user_id,
                room_id=msg.room_id,
                message_type=msg.message_type,
                username=msg.user.username if msg.user else "AI Assistant",
                created_at=msg.created_at
            )
            for msg in reversed(messages)
        ]

        final_data = RoomWithMessages(
            **room_response.dict(),
            messages=message_responses
        )

        # 3. Cache the result (best-effort)
        try:
            set_cached_room(room_id, final_data.dict())
        except Exception:
            logger.exception("Failed to set cached room")

        return final_data

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error in get_room")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=RoomsListResponse)
async def get_all_rooms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all rooms with message count, cached"""
    try:
        # 1. Check cache (best-effort)
        cached_data = get_cached_rooms()
        if cached_data:
            return RoomsListResponse(**cached_data)

        # 2. Query DB
        rooms_query = (
            db.query(
                Room,
                func.count(Message.id).label('message_count')
            )
            .outerjoin(Message)
            .group_by(Room.id)
            .order_by(Room.created_at.desc())
            .all()
        )

        rooms_response = [
            RoomResponse(
                id=room.id,
                name=room.name,
                description=room.description,
                created_by=room.created_by,
                created_at=room.created_at,
                message_count=message_count or 0
            ).dict()
            for room, message_count in rooms_query
        ]

        data = {"rooms": rooms_response, "count": len(rooms_response)}

        # 3. Store in cache (best-effort)
        try:
            set_cached_rooms(data)
        except Exception:
            logger.exception("Failed to set cached rooms")

        return RoomsListResponse(**data)

    except Exception:
        logger.exception("Error in get_all_rooms")
        raise HTTPException(status_code=500, detail="Internal server error")
