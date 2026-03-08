import asyncio
import time
from functools import wraps


def async_ttl_cache(ttl: int):
    cache = {}
    timestamps = {}
    locks = {}

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = (args, tuple(kwargs.items()))
            now = time.time()

            if key in cache and now - timestamps[key] < ttl:
                return cache[key]

            if key not in locks:
                locks[key] = asyncio.Lock()

            async with locks[key]:
                if key in cache and now - timestamps[key] < ttl:
                    return cache[key]

                result = await func(*args, **kwargs)

                cache[key] = result
                timestamps[key] = time.time()

                return result

        return wrapper

    return decorator
