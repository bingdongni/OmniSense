"""
Redis cache management for OmniSense
Provides caching for frequently accessed data and rate limiting
"""

import redis.asyncio as redis
from typing import Any, Optional, Union
import json
import pickle
from datetime import timedelta

from omnisense.config import config
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)


class RedisCache:
    """Redis cache manager"""

    def __init__(self):
        self.client = None
        self._connect()

    def _connect(self):
        """Connect to Redis"""
        try:
            self.client = redis.Redis(
                host=config.database.redis_host,
                port=config.database.redis_port,
                db=config.database.redis_db,
                password=config.database.redis_password,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_keepalive=True
            )
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.client = None

    async def ping(self) -> bool:
        """Check Redis connection"""
        if not self.client:
            return False
        try:
            await self.client.ping()
            return True
        except:
            return False

    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache"""
        if not self.client:
            return default

        try:
            value = await self.client.get(key)
            if value is None:
                return default

            # Try to unpickle, fallback to JSON
            try:
                return pickle.loads(value)
            except:
                try:
                    return json.loads(value)
                except:
                    return value.decode('utf-8')

        except Exception as e:
            logger.error(f"Error getting key '{key}': {e}")
            return default

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[Union[int, timedelta]] = None
    ) -> bool:
        """Set value in cache"""
        if not self.client:
            return False

        try:
            # Serialize value
            if isinstance(value, (dict, list)):
                serialized = json.dumps(value).encode('utf-8')
            elif isinstance(value, (str, int, float, bool)):
                serialized = str(value).encode('utf-8')
            else:
                serialized = pickle.dumps(value)

            # Set with optional TTL
            if ttl:
                if isinstance(ttl, timedelta):
                    ttl = int(ttl.total_seconds())
                await self.client.setex(key, ttl, serialized)
            else:
                await self.client.set(key, serialized)

            return True

        except Exception as e:
            logger.error(f"Error setting key '{key}': {e}")
            return False

    async def delete(self, *keys: str) -> int:
        """Delete keys from cache"""
        if not self.client:
            return 0

        try:
            return await self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Error deleting keys: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.client:
            return False

        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Error checking key '{key}': {e}")
            return False

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        if not self.client:
            return 0

        try:
            return await self.client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Error incrementing key '{key}': {e}")
            return 0

    async def get_many(self, *keys: str) -> dict:
        """Get multiple values"""
        if not self.client:
            return {}

        try:
            values = await self.client.mget(*keys)
            result = {}
            for key, value in zip(keys, values):
                if value:
                    try:
                        result[key] = pickle.loads(value)
                    except:
                        try:
                            result[key] = json.loads(value)
                        except:
                            result[key] = value.decode('utf-8')
            return result
        except Exception as e:
            logger.error(f"Error getting multiple keys: {e}")
            return {}

    async def set_many(self, mapping: dict, ttl: Optional[int] = None) -> bool:
        """Set multiple values"""
        if not self.client:
            return False

        try:
            pipe = self.client.pipeline()
            for key, value in mapping.items():
                if isinstance(value, (dict, list)):
                    serialized = json.dumps(value).encode('utf-8')
                else:
                    serialized = pickle.dumps(value)

                if ttl:
                    pipe.setex(key, ttl, serialized)
                else:
                    pipe.set(key, serialized)

            await pipe.execute()
            return True

        except Exception as e:
            logger.error(f"Error setting multiple keys: {e}")
            return False

    async def get_keys_by_pattern(self, pattern: str) -> list:
        """Get keys matching pattern"""
        if not self.client:
            return []

        try:
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                keys.append(key.decode('utf-8'))
            return keys
        except Exception as e:
            logger.error(f"Error scanning keys: {e}")
            return []

    async def flush_db(self):
        """Clear all keys (use with caution)"""
        if not self.client:
            return

        try:
            await self.client.flushdb()
            logger.warning("Redis database flushed")
        except Exception as e:
            logger.error(f"Error flushing database: {e}")

    async def get_ttl(self, key: str) -> int:
        """Get time to live for key"""
        if not self.client:
            return -1

        try:
            return await self.client.ttl(key)
        except Exception as e:
            logger.error(f"Error getting TTL for key '{key}': {e}")
            return -1

    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")


# Rate limiting helper
class RateLimiter:
    """Rate limiter using Redis"""

    def __init__(self, cache: RedisCache):
        self.cache = cache

    async def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> bool:
        """Check if request is allowed under rate limit"""
        counter_key = f"rate_limit:{key}:{window_seconds}"

        current = await self.cache.get(counter_key, 0)
        if isinstance(current, bytes):
            current = int(current.decode('utf-8'))

        if int(current) >= max_requests:
            return False

        await self.cache.increment(counter_key)

        # Set TTL on first request
        if int(current) == 0:
            await self.cache.set(counter_key, 1, ttl=window_seconds)

        return True

    async def get_remaining(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> int:
        """Get remaining requests in current window"""
        counter_key = f"rate_limit:{key}:{window_seconds}"
        current = await self.cache.get(counter_key, 0)
        if isinstance(current, bytes):
            current = int(current.decode('utf-8'))
        return max(0, max_requests - int(current))
