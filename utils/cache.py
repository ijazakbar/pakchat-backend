# backend/utils/cache.py
import os
import json
import redis.asyncio as redis
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self):
        self.provider = os.getenv('REDIS_PROVIDER', 'local')
        
        if self.provider == 'upstash':
            # Upstash connection
            self.redis_url = os.getenv('UPSTASH_REDIS_REST_URL')
            self.redis_token = os.getenv('UPSTASH_REDIS_REST_TOKEN')
            # Upstash ke liye special URL format [citation:3]
            self.client = redis.from_url(
                f"rediss://default:{self.redis_token}@{self.redis_url.split('://')[1]}:6379",
                decode_responses=True
            )
        else:
            # Local Redis fallback
            self.client = redis.from_url("redis://localhost:6379", decode_responses=True)
    
    async def get(self, key):
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def setex(self, key, ttl, value):
        try:
            await self.client.setex(key, ttl, value)
        except Exception as e:
            logger.error(f"Cache set error: {e}")