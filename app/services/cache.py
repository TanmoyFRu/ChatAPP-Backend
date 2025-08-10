# app/services/cache.py
import json
import logging
from typing import Any, Optional
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Try to create Redis client; if it fails, keep client None and continue
redis_client: Optional[redis.Redis]
try:
    redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    # quick ping to validate connection during startup (non-fatal)
    try:
        redis_client.ping()
    except Exception as e:
        logger.warning("Redis ping failed at startup: %s", e)
        redis_client = None
except Exception as e:
    logger.warning("Failed to initialize Redis client: %s", e)
    redis_client = None


# ----------------- ROOMS LIST CACHE -----------------
def get_cached_rooms() -> Optional[dict]:
    if not redis_client:
        return None
    try:
        data = redis_client.get("rooms_list")
        return json.loads(data) if data else None
    except Exception as e:
        logger.warning("get_cached_rooms: redis error: %s", e)
        return None


def set_cached_rooms(rooms: Any, expire_seconds: int = 60) -> None:
    if not redis_client:
        return
    try:
        redis_client.setex("rooms_list", expire_seconds, json.dumps(rooms, default=str))
    except Exception as e:
        logger.warning("set_cached_rooms: redis error: %s", e)


def invalidate_rooms_cache() -> None:
    if not redis_client:
        return
    try:
        redis_client.delete("rooms_list")
    except Exception as e:
        logger.warning("invalidate_rooms_cache: redis error: %s", e)


# ----------------- SINGLE ROOM CACHE -----------------
def get_cached_room(room_id: str) -> Optional[dict]:
    if not redis_client:
        return None
    key = f"room:{room_id}"
    try:
        data = redis_client.get(key)
        return json.loads(data) if data else None
    except Exception as e:
        logger.warning("get_cached_room(%s): redis error: %s", room_id, e)
        return None


def set_cached_room(room_id: str, room_data: Any, expire_seconds: int = 60) -> None:
    if not redis_client:
        return
    key = f"room:{room_id}"
    try:
        redis_client.setex(key, expire_seconds, json.dumps(room_data, default=str))
    except Exception as e:
        logger.warning("set_cached_room(%s): redis error: %s", room_id, e)


def invalidate_room_cache(room_id: str) -> None:
    if not redis_client:
        return
    key = f"room:{room_id}"
    try:
        redis_client.delete(key)
    except Exception as e:
        logger.warning("invalidate_room_cache(%s): redis error: %s", room_id, e)


# ----------------- ROOM MESSAGES CACHE (optional) -----------------
def get_cached_room_messages(room_id: str) -> Optional[list]:
    if not redis_client:
        return None
    key = f"room:{room_id}:messages"
    try:
        data = redis_client.get(key)
        return json.loads(data) if data else None
    except Exception as e:
        logger.warning("get_cached_room_messages(%s): redis error: %s", room_id, e)
        return None


def set_cached_room_messages(room_id: str, messages: Any, expire_seconds: int = 60) -> None:
    if not redis_client:
        return
    key = f"room:{room_id}:messages"
    try:
        redis_client.setex(key, expire_seconds, json.dumps(messages, default=str))
    except Exception as e:
        logger.warning("set_cached_room_messages(%s): redis error: %s", room_id, e)


def invalidate_room_messages_cache(room_id: str) -> None:
    if not redis_client:
        return
    key = f"room:{room_id}:messages"
    try:
        redis_client.delete(key)
    except Exception as e:
        logger.warning("invalidate_room_messages_cache(%s): redis error: %s", room_id, e)
