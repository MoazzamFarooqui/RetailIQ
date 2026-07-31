"""Redis caching client and helpers."""

import json
import pickle
from functools import wraps
from typing import Any, Callable, Optional

from redis.asyncio import Redis

from app.core.config import settings

_redis_client: Optional[Redis] = None


async def get_redis_client() -> Redis:
    """Get or create the shared Redis connection."""
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=False,
            socket_connect_timeout=5,
            retry_on_timeout=True,
        )
    return _redis_client


async def close_redis():
    """Close the Redis connection."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


async def cache_get(key: str) -> Optional[Any]:
    """Get a value from the cache, deserializing from JSON."""
    client = await get_redis_client()
    data = await client.get(key)
    if data is None:
        return None
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return pickle.loads(data)


async def cache_set(key: str, value: Any, ttl: int = 300):
    """Set a value in the cache with a TTL (seconds)."""
    client = await get_redis_client()
    try:
        serialized = json.dumps(value, default=str)
    except (TypeError, ValueError):
        serialized = pickle.dumps(value)
    await client.setex(key, ttl, serialized)


async def cache_delete(key: str):
    """Delete a key from the cache."""
    client = await get_redis_client()
    await client.delete(key)


async def cache_delete_pattern(pattern: str):
    """Delete all keys matching a glob pattern."""
    client = await get_redis_client()
    async for key in client.scan_iter(match=pattern):
        await client.delete(key)


def cached(ttl: int = 300, key_prefix: str = ""):
    """Decorator: cache the return value of an async function.

    Usage:
        @cached(ttl=600, key_prefix="weather")
        async def get_weather(city: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Build a cache key from function name + args
            key_parts = [key_prefix or func.__name__]
            key_parts.extend(str(a) for a in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)

            # Check cache
            result = await cache_get(cache_key)
            if result is not None:
                return result

            # Compute and cache
            result = await func(*args, **kwargs)
            await cache_set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator
