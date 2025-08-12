from redis_om import get_redis_connection

redis_db = get_redis_connection(
    host="localhost",       # or your Redis host
    port=6379,              # your Redis port
    password=None,          # password if any
    decode_responses=True
)