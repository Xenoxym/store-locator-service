from fastapi import HTTPException, Request
from redis import RedisError

from app.core.config import settings
from app.core.redis_client import redis_client


def _increment_counter(key: str, ttl_seconds: int) -> int:
    """
    Increment a Redis counter and set TTL when key is first created.
    """
    current_count = redis_client.incr(key)

    if current_count == 1:
        redis_client.expire(key, ttl_seconds)

    return current_count


def rate_limit_public_search(request: Request) -> None:
    """
    Rate limit public search endpoint by client IP.

    Limits:
    - 10 requests per minute per IP
    - 100 requests per hour per IP
    """
    client_ip = request.client.host if request.client else "unknown"

    minute_key = f"rate_limit:{client_ip}:minute"
    hour_key = f"rate_limit:{client_ip}:hour"

    try:
        minute_count = _increment_counter(minute_key, 60)
        hour_count = _increment_counter(hour_key, 3600)

        if minute_count > settings.RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded: maximum 10 requests per minute.",
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(settings.RATE_LIMIT_PER_MINUTE),
                    "X-RateLimit-Window": "60 seconds",
                },
            )

        if hour_count > settings.RATE_LIMIT_PER_HOUR:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded: maximum 100 requests per hour.",
                headers={
                    "Retry-After": "3600",
                    "X-RateLimit-Limit": str(settings.RATE_LIMIT_PER_HOUR),
                    "X-RateLimit-Window": "3600 seconds",
                },
            )

    except RedisError:
        # Practical choice:
        # If Redis is down, do not block search API.
        # You can mention in README that rate limiting depends on Redis.
        return