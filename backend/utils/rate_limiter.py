import asyncio
import time
import random
from collections import defaultdict

class RateLimiter:
    def __init__(self, calls_per_second: float = 1.0):
        self.delay = 1.0 / calls_per_second if calls_per_second > 0 else 0
        self._last_call = defaultdict(float)
        self._locks = defaultdict(asyncio.Lock)

    async def acquire(self, service: str):
        async with self._locks[service]:
            elapsed = time.monotonic() - self._last_call[service]
            if elapsed < self.delay:
                await asyncio.sleep(self.delay - elapsed)
            self._last_call[service] = time.monotonic()

# Per-service rate limit instances
RATE_LIMITS = {
    "tomba":   RateLimiter(calls_per_second=0.5),   # 1 call per 2s
    "prospeo": RateLimiter(calls_per_second=1.0),   # 1 call per second
    "brevo":   RateLimiter(calls_per_second=2.0),   # 2 calls per second
    "gemini":  RateLimiter(calls_per_second=1.0),   # 1 call per second
    "serper":  RateLimiter(calls_per_second=2.0),   # 2 calls per second
}

class RateLimitError(Exception):
    pass

async def with_retry(func, max_retries=3, base_delay=1.0):
    for attempt in range(1, max_retries + 1):
        try:
            return await func()
        except RateLimitError:
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
            await asyncio.sleep(delay)
        except Exception as e:
            if attempt == max_retries:
                raise
            # Check if it looks like a rate limit error (status 429)
            if hasattr(e, 'status_code') and e.status_code == 429:
                delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                await asyncio.sleep(delay)
            else:
                raise
    raise Exception("Max retries exceeded")
