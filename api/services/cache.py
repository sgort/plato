import json
import logging
from typing import Any

import redis.asyncio as aioredis

from config import settings

logger = logging.getLogger(__name__)

_pool: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
        )
    return _pool


async def cache_get(key: str) -> Any | None:
    try:
        client = get_redis()
        value = await client.get(key)
        if value is None:
            return None
        return json.loads(value)
    except Exception:
        # Redis unavailable — skip cache, fetch live
        return None


async def cache_set(key: str, value: Any, ttl: int) -> None:
    try:
        client = get_redis()
        await client.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        # Redis unavailable — continue without caching
        pass


async def cache_close() -> None:
    global _pool
    if _pool:
        try:
            await _pool.close()
        except Exception:
            pass
        _pool = None
