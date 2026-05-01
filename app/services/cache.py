import json
from typing import Any, Optional

from redis import RedisError

from app.core.redis_client import redis_client


def get_cache(key: str) -> Optional[Any]:
    try:
        cached_value = redis_client.get(key)

        if cached_value is None:
            return None

        return json.loads(cached_value)

    except (RedisError, json.JSONDecodeError):
        return None


def set_cache(key: str, value: Any, ttl_seconds: int) -> None:
    try:
        redis_client.setex(
            key,
            ttl_seconds,
            json.dumps(value),
        )
    except RedisError:
        # Cache failure should not break the API.
        return


def delete_cache(key: str) -> None:
    try:
        redis_client.delete(key)
    except RedisError:
        return