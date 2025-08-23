"""
Caching utilities and decorators.
"""
import json
import hashlib
import logging
from functools import wraps
from typing import Any, Optional, Callable
import asyncio
from app.core.settings import settings

logger = logging.getLogger("app.cache")

# In-memory cache fallback when Redis is not available
_memory_cache = {}
_cache_timestamps = {}

async def get_cache_client():
    """Get cache client (Redis or in-memory fallback)."""
    if settings.redis_url:
        try:
            import redis.asyncio as redis
            client = redis.from_url(settings.redis_url)
            # Test connection
            await client.ping()
            return client
        except Exception as e:
            logger.warning(f"Redis connection failed, using memory cache: {e}")
    
    return None

def _memory_cache_key_exists(key: str, ttl: int) -> bool:
    """Check if memory cache key exists and is valid."""
    import time
    if key not in _memory_cache:
        return False
    
    timestamp = _cache_timestamps.get(key, 0)
    if time.time() - timestamp > ttl:
        # Expired
        _memory_cache.pop(key, None)
        _cache_timestamps.pop(key, None)
        return False
    
    return True

async def get_from_cache(key: str, ttl: int = None) -> Optional[Any]:
    """Get item from cache."""
    ttl = ttl or settings.cache_ttl
    
    # Try Redis first
    client = await get_cache_client()
    if client:
        try:
            cached = await client.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
    
    # Fallback to memory cache
    if _memory_cache_key_exists(key, ttl):
        return _memory_cache[key]
    
    return None

async def set_cache(key: str, value: Any, ttl: int = None) -> bool:
    """Set item in cache."""
    ttl = ttl or settings.cache_ttl
    
    # Try Redis first
    client = await get_cache_client()
    if client:
        try:
            await client.setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            logger.warning(f"Redis set failed: {e}")
    
    # Fallback to memory cache
    import time
    _memory_cache[key] = value
    _cache_timestamps[key] = time.time()
    
    # Simple cleanup: remove old entries if cache gets too large
    if len(_memory_cache) > 1000:
        oldest_keys = sorted(_cache_timestamps.items(), key=lambda x: x[1])[:100]
        for old_key, _ in oldest_keys:
            _memory_cache.pop(old_key, None)
            _cache_timestamps.pop(old_key, None)
    
    return True

def cache_result(expiration: int = None, key_prefix: str = ""):
    """Decorator to cache function results."""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            func_args = str(args) + str(sorted(kwargs.items()))
            cache_key = f"{key_prefix}{func.__name__}:{hashlib.md5(func_args.encode()).hexdigest()}"
            
            # Try to get from cache
            cached_result = await get_from_cache(cache_key, expiration)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Execute function and cache result
            logger.debug(f"Cache miss for {func.__name__}, executing...")
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Cache the result
            await set_cache(cache_key, result, expiration)
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For synchronous functions, run async cache operations in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(async_wrapper(*args, **kwargs))
            finally:
                loop.close()
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

async def clear_cache_pattern(pattern: str):
    """Clear cache entries matching pattern."""
    client = await get_cache_client()
    if client:
        try:
            keys = await client.keys(pattern)
            if keys:
                await client.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache entries matching {pattern}")
        except Exception as e:
            logger.warning(f"Failed to clear cache pattern {pattern}: {e}")
    
    # Clear from memory cache
    keys_to_remove = [key for key in _memory_cache.keys() if pattern in key]
    for key in keys_to_remove:
        _memory_cache.pop(key, None)
        _cache_timestamps.pop(key, None)
