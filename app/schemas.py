from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

# User Schemas
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    created_at: datetime
    created_room_ids: Optional[List[str]] = Field(default_factory=list)  # safer default

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Room Schemas
class RoomCreate(BaseModel):
    name: str
    description: Optional[str] = ""

class RoomResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_by: str
    created_at: datetime
    message_count: int = 0
    message_ids: Optional[List[str]] = Field(default_factory=list)

    class Config:
        from_attributes = True

class RoomWithMessages(RoomResponse):
    messages: List['MessageResponse'] = []

# Message Schemas
class MessageCreate(BaseModel):
    content: str

class MessageResponse(BaseModel):
    id: str
    m_id: str
    content: str
    user_id: Optional[str]
    room_id: str
    message_type: str
    username: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# Response Schemas
class StandardResponse(BaseModel):
    message: str
    data: Optional[dict] = None

class RoomsListResponse(BaseModel):
    rooms: List[RoomResponse]
    count: int

# Update forward references
RoomWithMessages.model_rebuild()
