from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    created_rooms = relationship("Room", back_populates="creator")
    messages = relationship("Message", back_populates="user")

class Room(Base):
    __tablename__ = "rooms"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    creator = relationship("User", back_populates="created_rooms")
    messages = relationship("Message", back_populates="room", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    m_id = Column(String, unique=True, nullable=False, default=generate_uuid, index=True)
    content = Column(Text, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)  # Nullable for AI messages
    room_id = Column(String, ForeignKey("rooms.id"), nullable=False)
    message_type = Column(String(20), default="user")  # 'user' or 'ai'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="messages")
    room = relationship("Room", back_populates="messages")