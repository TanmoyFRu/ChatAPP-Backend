from redis_om import HashModel, Field, Migrator
from typing import Optional
from datetime import datetime
import uuid
from app.redis_client import redis_db



def generate_uuid() -> str:
    return str(uuid.uuid4())

class User(HashModel):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    username: str = Field(index=True)
    email: str = Field(index=True)
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Meta:
        database = redis_db
        global_key_prefix = "User"

class Room(HashModel):
    name: str = Field(index=True)
    description: Optional[str] = ""
    created_by: str = Field(index=True)  # add index here
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    class Meta:
        database = redis_db
        global_key_prefix = "Room"


class Message(HashModel):
    id: str = Field(default_factory=generate_uuid, index=True)
    content: str
    user_id: Optional[str] = Field(default=None, index=True)  # if you query by user_id too
    room_id: str = Field(index=True)
    message_type: str = Field(default="user")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Meta:
        database = redis_db
        global_key_prefix = "Message"

# Run migrations once after all models are defined
Migrator().run()
