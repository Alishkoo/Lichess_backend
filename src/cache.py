import json
from typing import Optional
from redis.asyncio import Redis

from src.config import settings

redis_client: Optional[Redis] = None


async def get_redis() -> Redis:
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
    return redis_client


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


async def get_profile_cache(user_id: int) -> Optional[dict]:
    redis = await get_redis()
    cache_key = f"profile:{user_id}"
    cached_data = await redis.get(cache_key)
    
    if cached_data:
        return json.loads(cached_data)
    return None


async def set_profile_cache(user_id: int, profile_data: dict, ttl: int = 3600):
    redis = await get_redis()
    cache_key = f"profile:{user_id}"
    await redis.setex(
        cache_key,
        ttl,
        json.dumps(profile_data)
    )
